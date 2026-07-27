## 1.0.73
- Fix Charged/Discharged Today: device values are Ah, convert with `Ah * V / 1000` to kWh
  (96.55 was Ah ≈ 4.6 kWh at 48V, not 96.55 kWh)

## 1.0.72
- Rebuild bump so Home Assistant Supervisor picks up 1.0.71 BT reconnect fix

## 1.0.71
- Fix reconnect after restart: disconnect leftover BlueZ/HA BT link, then connect by MAC
- Avoid waiting for advertisements (connected CH9141 devices stop advertising)

## 1.0.70
- Rename changelog to `CHANGELOG.md` so Home Assistant can find it
- Force store refresh for energy scaling fix (1.0.69)

## 1.0.69
- Fix energy sensor scaling: Ah→kWh now uses `Ah * V / 1000` (was Wh labeled as kWh)
- Stop multiplying charge/discharge by voltage (device already reports kWh)

## 1.0.68
- Fix MQTT Supervisor URL (`http://supervisor/services/mqtt` instead of double slash)
- Build from local Dockerfile (removed prebuilt `ghcr.io/tsjippy` image)
- Repository restructured as a valid Home Assistant app repository

## 1.0.67
- Upstream release from [Tsjippy/ha-addons](https://github.com/Tsjippy/ha-addons/tree/main/Junctek)
