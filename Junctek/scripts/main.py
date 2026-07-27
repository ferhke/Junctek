from bleak import BleakScanner, BleakClient, BleakError
import asyncio
import logger
import sys
import json
import mqtt
import sensors
from datetime import datetime
import signal
import os

class DeviceNotFoundError(Exception):
    pass

class JunctekMonitor:
    def __init__(self):
        self.should_quit        = False
        self.found              = []
        self.charging           = False
        file_path		        = '/data/options.json'
        self.local		        = False
        self.device             = None

        signal.signal(signal.SIGTERM, self.signal_handler)

        self.params = {
            # KL140F (KL-F series) — scales from official R50 example in user manual:
            #   2056 → 20.56V (/100), 200 → 2.00A (/100), 5408 → 5.408Ah (/1000),
            #   4592 → 4.592Ah cumulative (/1000), 9437 → 0.09437 kWh (/100000),
            #   134 → 34°C (raw-100), 162 → 162 min battery life
            # KL140F: voltage 0.01V, current 0.1A (protocol still /100), Ah 0.001, Wh 0.01
            "voltage":          "c0",       # V
            "current":          "c1",       # A
            "cur_soc":          "d0",       # device % (optional)
            "dir_of_current":   "d1",       # 0 forward (discharge), 1 reverse (charge) per R50
            "ah_remaining":     "d2",       # Ah — APP: Remaining AH.Rmn
            "discharge":        "d3",       # kWh — same scale as R50 watt-hour / Electricity
            "charge":           "d4",       # kWh
            "accum_charge_cap": "d5",       # Ah — APP: Cumulative / Elapsed AH
            "mins_remaining":   "d6",       # min — APP: BatLeft
            "power":            "d8",       # W
            "temp":             "d9",       # °C
            "full_charge_volt": "e6",
            "zero_charge_volt": "e7",
        }

        self.params_keys         = list(self.params.keys())
        self.params_values       = list(self.params.values())

        if not os.path.exists(file_path):
            self.local	= True
            file_path	= os.path.dirname(os.path.realpath(__file__))+file_path
					
        # Get Options
        with open(file_path, mode="r") as data_file:
            config = json.load(data_file)
            self.log_level           = config.get('log_level')
            self.mac_address         = config.get('macaddress').upper()
            self.battery_capacity    = int(config.get('battery capacity'))
            self.battery_voltage     = int(config.get('voltage'))

        self.logger                  = logger.Logger(self)

        if self.log_level == 'debug':
            self.debug              = True
        else:
            self.debug              = False

        self.MqqtToHa               = mqtt.MqqtToHa(self)

        self.stop_event             = asyncio.Event()
        self.disconnect_event       = asyncio.Event()
        

    def signal_handler(self, sig, frame):
        self.logger.warning(f'Received signal {sig}')
        self.logger.warning('Cleaning up...')
        
        # Set the shutdown flag
        self.should_quit    = True

    async def discover(self):
        try:
            devices    = await BleakScanner.discover()

            self.logger.debug("Found Devices")
            for device in devices:
                self.logger.info(f"BT Device found:\nName: {device.name}\nAddress: {device.address}")
                self.logger.debug(device)

            self.logger.debug("Finished discovery")
        except Exception as e:
            self.logger.error(f" {str(e)} on line {sys.exc_info()[-1].tb_lineno}")

    async def process_data(self, _, value):       
        try:
            data = str(value.hex())

            # split bs into a list of all values and hex keys
            bs_list             = [data[i:i+2] for i in range(0, len(data), 2)]

            # reverse the list so that values come after hex params
            bs_list_rev         = list(reversed(bs_list))

            values      = {}
            # iterate through the list and if a param is found,
            # add it as a key to the dict. The value for that key is a
            # concatenation of all following elements in the list
            # until a non-numeric element appears. This would either
            # be the next param or the beginning hex value.
            for i in range(len(bs_list_rev)-1):
                if bs_list_rev[i] in self.params_values:
                    value_str = ''
                    j = i + 1
                    while j < len(bs_list_rev) and bs_list_rev[j].isdigit():
                        value_str = bs_list_rev[j] + value_str
                        j += 1

                    position    = self.params_values.index(bs_list_rev[i])

                    key         = self.params_keys[position]
                    
                    values[key] = value_str
                    
            if self.debug:
                if not values: 
                    self.logger.warning(f"Nothing found for {data}")
                else:
                    self.logger.debug(f"Raw values: {values}")

            # Apply official KL-F / R50 scaling
            for key, value in list(values.items()):
                if not value.isdigit():
                    del values[key]
                    continue

                val_int = int(value)
                if key == "voltage":
                    voltage = val_int / 100
                    # Drop clearly bad BLE frames (KL140F valid band ~10–120 V self-powered)
                    if voltage > (self.battery_voltage - (self.battery_voltage * 0.2)):
                        values[key] = voltage
                    else:
                        del values[key]
                elif key == "current":
                    values[key] = val_int / 100
                elif key == "discharge":
                    # R50 watt-hour: 9437 → 0.09437 kWh
                    values[key] = val_int / 100000
                elif key == "charge":
                    values[key] = val_int / 100000
                elif key == "dir_of_current":
                    # R50: 0 = forward, 1 = reverse. APP: reverse/charge grows remaining Ah
                    self.charging = val_int == 1
                    del values[key]
                elif key == "ah_remaining":
                    values[key] = val_int / 1000
                elif key == "mins_remaining":
                    values[key] = val_int
                elif key == "power":
                    values[key] = val_int / 100
                elif key == "temp":
                    temp = val_int - 100
                    if -20 <= temp <= 120:
                        values[key] = temp
                    else:
                        del values[key]
                elif key == "accum_charge_cap":
                    values[key] = val_int / 1000
                elif key in ("cur_soc", "full_charge_volt", "zero_charge_volt"):
                    # Not published (SoC computed; e6/e7 unused)
                    del values[key]

            # Sign: charge positive, discharge negative (user preference)
            if "current" in values and not self.charging:
                values["current"] *= -1
            if "power" in values and not self.charging:
                values["power"] *= -1

            # SoC = remaining Ah / preset capacity (manual: remaining / AH.Preset)
            if "ah_remaining" in values and self.battery_capacity > 0:
                values["soc"] = values["ah_remaining"] / self.battery_capacity * 100

            if self.debug:
                self.logger.debug(f"Final values: {values} charging={self.charging}")

            await self.send_to_ha(values)

        except Exception as e:
            self.logger.error(f"{str(e)} on line {sys.exc_info()[-1].tb_lineno}")

    async def send_to_ha(self, values):
        try:
            for key, value in values.items():
                if key not in sensors.sensors:
                    continue

                # Rounding matches KL140F resolutions in the manual
                if key in ("ah_remaining", "accum_charge_cap"):
                    val = round(value, 3)          # 0.001 Ah
                elif key in ("discharge", "charge"):
                    val = round(value, 5)          # 0.01 Wh → 0.00001 kWh
                elif key == "voltage":
                    val = round(value, 2)          # 0.01 V
                elif key == "power":
                    val = round(value, 2)          # 0.01 W
                elif key == "current":
                    val = round(value, 1)          # KL140F: 0.1 A
                elif key == "mins_remaining":
                    val = round(value, 0)
                else:
                    val = round(value, 1)

                if val > -99:
                    self.MqqtToHa.send_value(key, val)
                    
            # https://www.home-assistant.io/docs/configuration/templating/#time
            # 2023-07-30T20:03:49.253717+00:00
            timestring  = str(datetime.now(datetime.now().astimezone().tzinfo).isoformat())
            if self.debug:
                self.logger.debug(f"Sending time: {timestring}") 

            self.MqqtToHa.send_value('last_message', timestring, False)
        except Exception as e:
            self.logger.error(f"{str(e)} on line {sys.exc_info()[-1].tb_lineno}")

    def scanner_callback(self, device, advertisement_data):
        try:
            name    = advertisement_data.local_name

            if device.address.upper() == self.mac_address:
                self.logger.info(f"Found device\nAddress: {device.address}\nName: {name}\nRssi: {advertisement_data.rssi}")
                self.device = device
                self.stop_event.set()
            elif not device.address in self.found:
                self.found.append(device.address)

                if name == None:
                    self.logger.debug(f"Found '{device.address}'")
                else:
                    self.logger.debug(f"Found '{name}' with address '{device.address}'")
            else:
                if name == None:
                    self.logger.debug(f"'{device.address}' is not: {self.mac_address}")
                else:
                    self.logger.debug(f"{name} with address '{device.address}' is not: {self.mac_address}")
        except Exception as e:
            self.logger.error(f" {str(e)} on line {sys.exc_info()[-1].tb_lineno}")

    def disconnected_callback(self, client):
        try:
            self.logger.debug(f"Disconnected {client}")
            self.disconnect_event.set()
            self.stop_event.clear()
            self.device = None
        except Exception as e:
            self.logger.error(f" {str(e)} on line {sys.exc_info()[-1].tb_lineno}")

    async def release_existing_connection(self):
        """Drop any leftover BlueZ/HA connection so the device advertises again."""
        try:
            self.logger.info(f"Releasing existing BT connection to {self.mac_address} if held")
            proc = await asyncio.create_subprocess_exec(
                "bluetoothctl", "disconnect", self.mac_address,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
            out = (stdout or b"").decode().strip()
            err = (stderr or b"").decode().strip()
            if out:
                self.logger.info(f"bluetoothctl: {out}")
            if err:
                self.logger.debug(f"bluetoothctl stderr: {err}")
            # Give BlueZ/HA a moment to fully release the link
            await asyncio.sleep(2)
        except FileNotFoundError:
            self.logger.warning("bluetoothctl not found; cannot release existing BT connection")
        except Exception as e:
            self.logger.warning(f"Could not release existing BT connection: {e}")

    async def connect(self):
        try:
            # Do not run if already connected
            if self.device != None:
                return
            
            async with BleakScanner(self.scanner_callback) as scanner:
                # Important! Wait for an event to trigger stop, otherwise scanner
                # will stop immediately.
                await self.stop_event.wait()
                self.logger.info(f"Connected to {self.device}")
        
            # scanner stops when block exits
        except Exception as e:
            self.logger.error(f" {str(e)} on line {sys.exc_info()[-1].tb_lineno}")

    async def main(self):
        read_characteristic_uuid = "0000fff1-0000-1000-8000-00805f9b34fb"

        while not self.should_quit:
            # HA Bluetooth often keeps the Junctek (CH9141) link after addon restart.
            # Connected devices stop advertising, so scanning never finds them.
            await self.release_existing_connection()

            self.logger.info(f"Connecting directly to {self.mac_address}")
            try:
                async with BleakClient(
                    self.mac_address,
                    disconnected_callback=self.disconnected_callback,
                    timeout=30.0,
                ) as client:
                    name = client.address
                    try:
                        if client.name:
                            name = client.name
                    except Exception:
                        pass
                    self.logger.info(f"Connected to {name}")

                    await client.start_notify(read_characteristic_uuid, self.process_data)

                    # Wait till disconnected
                    await self.disconnect_event.wait()
                    self.disconnect_event.clear()
            except BleakError as e:
                self.logger.error(f"Direct connect failed ({e}); falling back to scan")
                self.stop_event.clear()
                self.device = None
                await self.connect()
                if self.device is not None:
                    try:
                        async with BleakClient(
                            self.device,
                            disconnected_callback=self.disconnected_callback,
                            timeout=30.0,
                        ) as client:
                            self.logger.info(f"Connected to {self.device}")
                            await client.start_notify(read_characteristic_uuid, self.process_data)
                            await self.disconnect_event.wait()
                            self.disconnect_event.clear()
                    except Exception as scan_err:
                        self.logger.error(f"Scan connect failed: {scan_err}")
            except TimeoutError as e:
                self.logger.warning(f"Timeout connecting to {self.mac_address}: {e}")
            except Exception as e:
                if str(e) != '':
                    self.logger.error(f" {str(e)} on line {sys.exc_info()[-1].tb_lineno}")

            await asyncio.sleep(5)

if __name__ == "__main__":
    try:
        junctekMonitor  = JunctekMonitor()

        if junctekMonitor.mac_address == '':
            junctekMonitor.logger.debug("Starting discovery")
            asyncio.run(junctekMonitor.discover())
        else:
            junctekMonitor.logger.debug("Starting connection")
            asyncio.run(junctekMonitor.main())

            junctekMonitor.logger.info("Finished")
    except KeyboardInterrupt:
        junctekMonitor.logger.debug("ctrl+c pressed")
    except Exception as e:
        junctekMonitor.logger.error(f" {str(e)} on line {sys.exc_info()[-1].tb_lineno}")
        """         async with BleakClient(device) as client:
            self.logger.debug("connected")
            await client.stop_notify(read_characteristic_uuid) """
