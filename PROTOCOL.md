# Felicity BLE protocol — decode reference

Reverse-engineered notes on the Felicity real-info BLE frame. Field meanings are
our best decode, each tagged with a confidence level.

Verified against: live frames from a 2-pack bank (`FLB48314TG1-H`, 16S LiFePO4,
serials …597 / …599), the Felicity phone app, and — for protocol *structure only* —
the patman15/BMS_BLE-HA issue #466 capture (⚠️ a **different battery**; structure
transfers, values do not).

## Confidence legend

- ✅ **Confirmed** — verified against an independent source (the app, or a
  cross-pack diff that can only be explained one way).
- 🟡 **Inferred** — internally consistent but from a single source / one operating
  point; not independently confirmed.
- ❓ **Unknown** — name is suggestive at best; meaning is a guess.

## Transport

- Proprietary JSON over BLE. Poll = write `wifilocalMonitor:get dev real infor` to
  the TX characteristic; the unit answers with a JSON frame (`CommVer: 1`).
- ISSC/Microchip UART service; RX `49535458-…`, TX `49535258-…`. Single BLE client
  per pack (the Felicity app and this component cannot both hold the link).
- **Each pack has its own BLE radio and reports _itself_ at list index `[0]`.** Add
  each pack as its own `ble_client`. This is why the driver always reads `[0]` and
  still gets per-pack data.
- A separate `get dev basice infor` poll returns firmware/version fields
  (`PwHwVer`, `DHwVer`, … → the app's "Master/IAP/Sub Version"). Not covered here;
  this doc is the *real-info* frame.

## 1. Fields the driver parses → HA sensors

All parsing is in `felicity_bms.cpp :: handle_frame_`. Note scalings differ per field.

| Frame field | Sensor | Decode (as coded) | Conf. |
|---|---|---|---|
| `BattList[0][0]` | voltage | `÷1000` → V (pack, millivolts) | ✅ |
| `BattList[1][0]` | current | `÷10` → A (signed; − = discharge) | ✅ |
| — | power | `voltage × current` | ✅ |
| `BatsocList[0][0]` | soc | `÷100` → % | ✅ |
| `BatsocList[0][1]` | soh | `÷10` → % | 🟡ᵃ |
| `BatcelList[0][0..15]` | cell_voltage_1..16 | `÷1000` → V (16S) | ✅ |
| (computed from cells) | min/max_cell_voltage, cell_delta | min/max over cells; delta in mV | ✅ |
| `BtemList[0][0..3]` | temperature_1..4 | `÷10` → °C; `32767` = probe absent → NaN | ✅ |
| `BBfault` | fault_code + fault (binary) | raw int; binary = `!= 0` | ✅ |
| `BBwarn` | warning_code + warning (binary) | raw int; binary = `!= 0` | ✅ |

ᵃ `soh`: reads a flat 100.0% — as expected for a 3-week-old pack, so consistent
with SOH but not yet confirmed. Only a real age-related decline (months away) can
prove it actually tracks health.

Frame validity guard: the driver drops a frame whose `BattList[0][0]` is outside
`10000..70000` mV — a just-reconnected MCU can emit a valid-JSON frame with all
values still zero-initialized.

## 2. Decoded but NOT yet exposed (future-sensor candidates)

These are understood well enough to expose; they're just not wired up yet.

| Frame field | Meaning | Decode | Conf. |
|---|---|---|---|
| `BLVolCu[1][0]` | charge-current limit (CCL), **per-pack** | `÷10` → A. **Dynamic: 0 when full** (BMS tells inverter to stop charging) | ✅ |
| `BLVolCu[1][1]` | discharge-current limit (DCL), per-pack | `÷10` → A | ✅ |
| `BLVolCu[0][0]` | charge-voltage limit (CVL), per-pack | `÷10` → pack V (57.6 = 3.6 V/cell ×16) | ✅ |
| `BLVolCu[0][1]` | discharge-voltage limit (DVL), per-pack | `÷10` → pack V (48.0 = 3.0 V/cell ×16) | ✅ |
| `BTemp[1][0]` | a 2nd temperature (≈25.6 °C), distinct from cell probes | `÷10` → °C; role (MOSFET/board/ambient?) not confirmed | 🟡 |
| `BMaxMin[1][0]`,`[1][1]` | index of highest / lowest cell | 0-based (+1 for cell number) | ✅ |
| `BMaxMin[0][0]`,`[0][1]` | highest / lowest cell mV | `÷1000` → V (driver recomputes these itself instead) | ✅ |

## 3. Bank-level aggregates (mostly redundant with the Deye's own BMS sensors)

| Frame field | Meaning | Conf. |
|---|---|---|
| `Batt` | **bank** V/I: `[[V],[I],[null]]`, V `÷1000`, I `÷10` | ✅ bank (V identical across packs; I = sum of packs) |
| `Batsoc` | **bank** `[SOC÷100, SOH÷10, capacity]` | 🟡 (capacity sums 2× the per-pack value) |
| `LVolCur` | **bank** charge/discharge envelope (same layout as `BLVolCu`) | 🟡 (bank DCL = 2× per-pack) |
| `Bfault` / `Bwarn` | **bank** fault/warn word (OR across packs) | ✅ (both packs echo the same value while `BB*` differ) |

## 4. Not yet understood

| Frame field | Guess | Conf. |
|---|---|---|
| `BatsocList[0][2]` (=350000) | rated/design capacity? Does **not** match the 314 Ah nameplate at any scale. Maybe a 350 Ah BMS design default; maybe *remaining* capacity | ❓ |
| `Bstate` / `Estate` | per-pack / bank status bitfields (`Estate` looks like OR of `Bstate`) | ❓ bits |
| `warning`/`fault` code values | bit layout undocumented; `BBwarn = 4` seen on the imbalanced pack, but its exact trigger/threshold is unknown (didn't clear as spread fell from 231→80 mV) | ❓ |
| `workM` | work-mode index (0) | ❓ |
| `HtCuSt` | heater current status? (0 = not heating; app shows a heating block) | ❓ |
| `EMSpara` / `BMSpara` (=`[[2,6]]`) | config/param pair; the `6` may be the app's "Heat Request Curr 6 A" | ❓ |
| `Templist` | sparse multi-probe temp list (mostly `65535`/`0`) | ❓ |
| `Type` / `SubType` (112 / 7353) | numeric model/type codes | ❓ |
| `modID` (1 / 2) | position/address in the bank | 🟡 |

## 5. Per-pack vs bank — naming gotcha

The `…List` suffix does **not** reliably mean "list of packs":

- `BattList` / `BatcelList` / `BtemList` / `BatsocList` are **per-pack** (this pack
  at `[0]`; the other pack's slot is `65535`).
- `Batt` / `Batsoc` are the **bank** aggregates — despite having no `List` suffix.
- `LVolCur` (bank) vs `BLVolCu` (per-pack) **inverts** the convention entirely.

Rule of thumb that actually holds: a value that is **identical in both packs'
frames** is a bank aggregate; one that **differs** is per-pack. (E.g. `Batt`
voltage is identical across packs → bank; `BattList` voltage differs → per-pack,
and its per-pack currents even flip sign and sum to `Batt`'s.)

## 6. Open questions & how to resolve them

- **Capacity (`[0][2]`)**: if it tracks SOC down during a discharge it's *remaining*
  capacity; if it holds at 350000 it's a fixed design figure. Needs a real
  discharge/recharge cycle — the debug frame logger is set up to capture it.
- **`Bstate`/`workM`/`HtCuSt` bits**: unexercised at a single operating point
  (bank held at 100 % / standby). Diff frames across a full charge→discharge cycle.
- **Capturing a live frame**: expose a per-pack `api.respond` action that returns
  `id(<bms>).get_last_raw_frame()` — HA response data is exempt from the 255-char
  state cap, so the full ~820 B frame comes back intact.
