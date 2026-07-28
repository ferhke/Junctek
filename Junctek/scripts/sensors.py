# The main device that contains the sensors
device              = {
    "identifiers": [
        "solar_batteries_ble"
    ],
    "name": "Battery Status Monitor",
    "model": "KL140F",
    "manufacturer": "Juntek"
}

# Sensor definition — JUNCTEK KL-F / KL140F manual (R50 + APP field names)
sensors = {
    'voltage': {
        "name": "Voltage",
        "state": "measurement",
        "unit": "V",
        "type": "VOLTAGE",
        "icon": "mdi:flash-triangle"
    },
    'current': {
        "name": "Current",
        "state": "measurement",
        "unit": "A",
        "type": "CURRENT",
        "icon": "mdi:current-dc"
    },
    'power': {
        "name": "Power",
        "state": "measurement",
        "unit": "W",
        "type": "POWER",
        "icon": "mdi:home-lightning-bolt-outline"
    },
    'temp': {
        "name": "Temperature",
        "state": "measurement",
        "unit": "°C",
        "type": "TEMPERATURE",
        "icon": "mdi:thermometer"
    },
    'soc': {
        "name": "State of Charge",
        "state": "measurement",
        "unit": "%",
        "type": "BATTERY",
    },
    'ah_remaining': {
        "name": "Remaining Capacity",
        "state": "measurement",
        "unit": "Ah",
        "icon": "mdi:battery"
    },
    'energy_remaining': {
        "name": "Remaining Energy",
        "state": "measurement",
        "unit": "kWh",
        "type": "ENERGY_STORAGE",
        "icon": "mdi:battery-heart-variant"
    },
    'mins_remaining': {
        "name": "Battery Life",
        "state": "measurement",
        "unit": "min",
        "type": "DURATION",
    },
    'accum_charge_cap': {
        "name": "Cumulative Capacity",
        "state": "measurement",
        "unit": "Ah",
        "icon": "mdi:battery-sync"
    },
    'discharge': {
        "name": "Discharged Energy",
        "state": "total_increasing",
        "unit": "kWh",
        "type": "ENERGY",
    },
    'charge': {
        "name": "Charged Energy",
        "state": "total_increasing",
        "unit": "kWh",
        "type": "ENERGY",
    },
    'last_message': {
        'name': 'Last Message',
        "state": None,
        'type': 'timestamp',
        'icon': 'mdi:clock-check'
    },
}