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
voltages, temperatures and fault/warning flags — no Home Assistant BLE stack involved.

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
    cell_voltage_min_change: 1mV   # min per-cell change to publish (default 1mV)

sensor:
  - platform: felicity_bms
    felicity_bms_id: bat
    voltage: {name: Voltage}
    current: {name: Current}
    power: {name: Power}
    soc: {name: SOC}
    min_cell_voltage: {name: Cell min}
    max_cell_voltage: {name: Cell max}
    max_voltage_cell: {name: Cell max index}   # 0-based index of the highest-voltage cell
    min_voltage_cell: {name: Cell min index}   # 0-based index of the lowest-voltage cell
    cell_delta: {name: Cell delta}
    charge_voltage_limit: {name: Charge voltage limit}
    discharge_voltage_limit: {name: Discharge voltage limit}
    charge_current_limit: {name: Charge current limit}
    discharge_current_limit: {name: Discharge current limit}
    cell_voltage_1: {name: Cell 01}
    # ... cell_voltage_2 .. cell_voltage_16
    temperature_1: {name: Temp 1}
    # ... temperature_2 .. temperature_4
    fault_code: {name: Fault code}
    warning_code: {name: Warning code}

binary_sensor:
  - platform: felicity_bms
    felicity_bms_id: bat
    fault: {name: Fault}
    warning: {name: Warning}
```

`fault`/`warning` mirror **this pack's own** `BBfault`/`BBwarn` words — the
per-pack flags, as opposed to the bank-aggregate `Bfault`/`Bwarn` that every
parallel pack echoes identically. Alert on `fault` if you don't want
notifications for benign warnings (e.g. the cell overvoltage warning some packs
raise at top of charge). `fault_code` and `warning_code` expose the raw values;
Felicity doesn't document the bit layout, so the codes are the only way to tell
conditions apart.

Frames whose pack voltage is implausible (outside 10–70 V) are dropped whole:
right after a (re)connect the battery's monitor MCU can answer with a valid but
zero-initialized snapshot, which would otherwise publish 0 V / 0 % / 0 °C spikes.

Per-cell voltages, individual temperatures, cell min/max/delta, max temperature
and the fault/warning flags default to `entity_category: diagnostic`.

`max_voltage_cell`/`min_voltage_cell` report the **0-based index** of the
highest- and lowest-voltage cell (which cell, not its voltage), as the BMS itself
reports it — pair them with `cell_delta` to spot a persistently weak cell.

Cells jitter at the mV level every poll, so publishing every change floods
recorder history and makes 16-cell graphs slow to load. `cell_voltage_min_change`
(default `1mV`) sets the minimum per-cell change that gets published — raise it
to thin history further (`2mV` ≈ 3.5× fewer points, `5mV` ≈ 12×), all still far
below any cell imbalance worth acting on.

## Protocol

[PROTOCOL.md](PROTOCOL.md) documents the Felicity BLE JSON frame field by field —
scalings, which values are per-pack vs bank, and how firmly each is pinned down.

## License

Apache-2.0. See [LICENSE](LICENSE).
