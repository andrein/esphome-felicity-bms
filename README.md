# esphome-felicity-bms

An [ESPHome](https://esphome.io) external component that reads **Felicity Solar**
LiFePO4 batteries over Bluetooth LE and exposes them as native ESPHome entities.

## Why this exists

Felicity batteries require a **BLE passkey pairing/bond** before they will stream
data. That breaks the usual Home Assistant paths:

- The HA `bms_ble` integration does not pair → `NotConnected` at `start_notify`.
- An ESPHome **Bluetooth proxy cannot bond** a passkey device → the CCCD write
  fails with `Insufficient authentication`.

This component runs on an ESP32 near the batteries, bonds with the passkey using
ESPHome's `ble_client`, and publishes voltage, current, power, SOC, per-cell
voltages, temperatures and a problem flag — no Home Assistant BLE stack involved.

## Requirements

- An ESP32 within good BLE range of the battery.
- Global BLE security so the ESP32 can enter the passkey:

  ```yaml
  esp32_ble:
    io_capability: keyboard_only
    auth_req_mode: sc_mitm_bond
  ```

- One BLE connection slot per battery. On the classic ESP32 the total across
  `ble_client` + `bluetooth_proxy` is ~3, so budget accordingly
  (e.g. `bluetooth_proxy: { connection_slots: 1 }` alongside two batteries).

## Usage

```yaml
external_components:
  - source: github://andrein/esphome-felicity-bms
    components: [felicity_bms]

esp32_ble:
  io_capability: keyboard_only
  auth_req_mode: sc_mitm_bond

esp32_ble_tracker:

ble_client:
  - mac_address: A4:05:FD:18:84:3E
    id: bat_client
    on_passkey_request:
      then:
        - ble_client.passkey_reply:
            id: bat_client
            passkey: 123456

felicity_bms:
  - id: bat
    ble_client_id: bat_client
    update_interval: 10s

sensor:
  - platform: felicity_bms
    felicity_bms_id: bat
    voltage: {name: Voltage}
    current: {name: Current}
    power: {name: Power}
    soc: {name: SOC}
    min_cell_voltage: {name: Cell min}
    max_cell_voltage: {name: Cell max}
    cell_delta: {name: Cell delta}
    max_temperature: {name: Temp max}
    cell_voltage_1: {name: Cell 01}
    # ... cell_voltage_2 .. cell_voltage_16
    temperature_1: {name: Temp 1}
    # ... temperature_2 .. temperature_4

binary_sensor:
  - platform: felicity_bms
    felicity_bms_id: bat
    problem: {name: Problem}
```

Per-cell voltages, individual temperatures, cell min/max/delta, max temperature
and the problem flag default to `entity_category: diagnostic`.

## License

Apache-2.0. See [LICENSE](LICENSE).
