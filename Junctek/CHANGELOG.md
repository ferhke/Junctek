## 1.0.85
- Restore absolute `Charged Energy` and `Discharged Energy` values from the shunt
- Stop subtracting a daily zero offset from MQTT `total_increasing` sensors

## 1.0.84
- Keep a single `Battery Life` sensor and publish signed minutes: `+` for charge, `-` for discharge

## 1.0.83
- Add separate `Charge Time Remaining` and `Discharge Time Remaining` sensors from the device Battery Life field

## 1.0.82
- Fix MQTT spam: stop gating publishes on `homeassistant/status` (use broker connection)
- Unique MQTT client id, non-blocking reconnect, rate-limit queue warnings
- Fix daily energy offset check (`total_increasing` case)

## 1.0.81
- Fix charge/discharge sign: BLE notify almost never sends D1, so direction stayed stuck on discharge (−)
- Infer direction from remaining Ah trend and charge/discharge kWh counters (verified vs Solar01)

## 1.0.80
- Invert D1 charge/discharge mapping (forward=charge +, reverse=discharge −) to match inverter

## 1.0.79
- Fix Power: compute as Voltage × Current (BLE D8 was ~10× low, e.g. 164W vs ~1627W at 51V/−31.9A)
- Keep Current/Power signs consistent (charge +, discharge −)
- Allow publishing large negative discharge power

## 1.0.78
- Current/Power sign: charge = positive, discharge = negative

## 1.0.77
- Stop negating Current/Power while charging (show positive amps like the JUNCTEK APP)

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
