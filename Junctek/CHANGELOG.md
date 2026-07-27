## 1.0.76
- Re-audit for **KL140F** against official KL-F manual (R50):
  - Confirm scales: V/100, A/100, Ah/1000, kWh/100000, temp−100, life=min
  - Fix sign: charge = negative current **and** power (was inconsistent)
  - Direction only from D1 (not from D3/D4 packets)
  - Rounding per KL140F resolution (0.01V, 0.1A, 0.01W, 0.001Ah, 0.01Wh)
  - Model set to KL140F

## 1.0.75
- Align sensors with JUNCTEK KL-F manual (R50): Remaining/Cumulative as **Ah**, Charge/Discharge as **kWh**
- Rename sensors to match APP (Remaining Capacity, Cumulative Capacity, Battery Life, Charged/Discharged Energy)
- Fix temperature filter to allow -20…120°C per manual

## 1.0.74
- Revert 1.0.73: Charged/Discharged Today are already kWh from the device
- Keep Ah→kWh (`* V / 1000`) only for Remaining Energy and Accumulated Charged Load

## 1.0.73
- (reverted) Incorrectly treated charge/discharge as Ah

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
