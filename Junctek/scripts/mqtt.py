#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import json
from datetime import datetime
from time import strftime, localtime
import time
import importlib.metadata
import sys
import os
import uuid
import requests
import sensors


class MqqtToHa:
    def __init__(self, parent):
        self.device = sensors.device
        self.sensors = sensors.sensors
        # Unique per start — fixed id caused broker kick / reconnect storms on restart
        self.client_id = f"battery_mon_{uuid.uuid4().hex[:8]}"
        self.logger = parent.logger

        self.sent = {}
        self.queue = {}
        self._last_warn = 0.0

        if importlib.metadata.version("paho-mqtt")[0] == "1":
            self.client = mqtt.Client(client_id=self.client_id)
        else:
            self.client = mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION2, client_id=self.client_id
            )

        self.broker_connected = False
        self.device_name = self.device["name"].lower().replace(" ", "_")

        try:
            token = os.getenv("SUPERVISOR_TOKEN")
            url = "http://supervisor/services/mqtt"
            headers = {
                "Authorization": f"Bearer {token}",
                "content-type": "application/json",
            }
            response = requests.get(url, headers=headers, timeout=30)

            if response.ok:
                data = response.json()["data"]
                self.username = data["username"]
                self.password = data["password"]
                self.host = data["host"]
                self.port = data["port"]
                self.main()
            else:
                self.logger.error("Not connected to mqtt")
                self.logger.debug(response)
        except Exception as e:
            self.logger.error(
                f"MQTT init failed: {e} on line {sys.exc_info()[-1].tb_lineno}"
            )

    def __str__(self):
        return f"{self.device.name}"

    def create_sensors(self):
        self.logger.debug("Creating Sensors")

        device_id = self.device["identifiers"][0]

        for key, sensor in self.sensors.items():
            sensortype = sensor.get("sensortype", "sensor")

            sensor_name = sensor["name"].replace(" ", "_").lower()
            self.sensors[key]["base_topic"] = (
                f"homeassistant/{sensortype}/{device_id}/{sensor_name}"
            )
            unique_id = f"{self.device_name}_{sensor_name}"

            self.logger.debug(
                f"Creating sensor '{sensor_name}' with unique id {unique_id}"
            )

            config_payload = {
                "name": sensor["name"],
                "state_topic": sensor["base_topic"] + "/state",
                "unique_id": unique_id,
                "device": self.device,
                "platform": "mqtt",
            }

            if "state" in sensor:
                config_payload["state_class"] = sensor["state"]

            if "unit" in sensor:
                config_payload["unit_of_measurement"] = sensor["unit"]

            if "type" in sensor:
                config_payload["device_class"] = sensor["type"]

            if "icon" in sensor:
                config_payload["icon"] = sensor["icon"]

            payload = json.dumps(config_payload)
            result = self.client.publish(
                topic=self.sensors[key]["base_topic"] + "/config",
                payload=payload,
                qos=1,
                retain=False,
            )
            self.sent[result.mid] = payload

            if "init" in sensor:
                self.send_value(key, sensor["init"])

    def _reason_ok(self, reason_code):
        try:
            return int(reason_code) == 0
        except Exception:
            return reason_code == 0 or str(reason_code) in ("0", "Success")

    def on_connect(self, client, userdata, flags, reason_code, properties=None):
        if self._reason_ok(reason_code):
            self.logger.info("Successfully connected to MQTT broker")
        else:
            self.logger.error(f"Connected with result code {reason_code}")

        self.broker_connected = True
        client.subscribe("homeassistant/status")
        self.create_sensors()
        self._flush_queue()
        self.logger.debug("Sensors created")

    def on_disconnect(self, client, userdata, flags, reason_code, properties=None):
        # Do NOT block here — paho network loop thread must keep running.
        self.broker_connected = False
        self.logger.warning(f"Disconnected from MQTT broker ({reason_code})")

    def on_message(self, client, userdata, message):
        if message.topic == "homeassistant/status":
            status = message.payload.decode()
            if status == "online":
                self.logger.info("Home Assistant MQTT status: online")
                self.create_sensors()
            elif status == "offline":
                # Broker may still be up — keep publishing; HA will catch up.
                self.logger.info("Home Assistant MQTT status: offline")
        elif "SYS/" not in message.topic:
            self.logger.debug(f"{message.topic} {message.payload.decode()}")

    def on_log(self, client, userdata, paho_log_level, message):
        if paho_log_level == mqtt.LogLevel.MQTT_LOG_ERR:
            self.logger.error(message)

    def on_publish(self, client, userdata, mid, reason_code="", properties=""):
        self.sent.pop(mid, None)

    def _flush_queue(self):
        if not self.queue:
            return
        pending = dict(self.queue)
        self.queue.clear()
        for topic, payload in pending.items():
            result = self.client.publish(
                topic=topic, payload=payload, qos=1, retain=False
            )
            self.sent[result.mid] = payload

    def send_value(self, key, value, send_json=True):
        try:
            if "base_topic" not in self.sensors[key]:
                if self.client.is_connected():
                    self.create_sensors()
                else:
                    return

            topic = self.sensors[key]["base_topic"] + "/state"

            self.sensors[key]["last_update"] = time.time()

            payload = json.dumps(value) if send_json else value
            self.queue[topic] = payload

            if self.client.is_connected() and self.broker_connected:
                self._flush_queue()
            else:
                now = time.time()
                if now - self._last_warn > 30:
                    self._last_warn = now
                    self.logger.warning(
                        "MQTT not connected yet, queuing values (retry quiet for 30s)"
                    )
        except Exception as e:
            self.logger.error(f"{str(e)} on line {sys.exc_info()[-1].tb_lineno}")

    def main(self):
        self.logger.debug("Starting MQTT client")

        self.client.username_pw_set(self.username, self.password)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_log = self.on_log
        self.client.on_publish = self.on_publish
        self.client.will_set(
            f"system-sensors/sensor/{self.device_name}/availability",
            "offline",
            retain=True,
        )
        # Automatic reconnect without blocking the network loop
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

        self.logger.debug(f"Connecting to MQTT {self.host}:{self.port}")

        while True:
            try:
                self.client.connect(self.host, self.port, keepalive=60)
                break
            except ConnectionRefusedError:
                self.logger.warning("MQTT broker refused connection, retry in 10s")
                time.sleep(10)
            except OSError as e:
                self.logger.warning(f"MQTT broker unreachable ({e}), retry in 30s")
                time.sleep(30)
            except Exception as e:
                self.logger.error(
                    f"{str(e)} on line {sys.exc_info()[-1].tb_lineno}"
                )
                time.sleep(10)

        self.client.loop_start()
