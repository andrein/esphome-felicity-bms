# Felicity BLE protocol reference

Reverse-engineered decode of the Felicity BLE interface: a proprietary JSON payload
polled over a BLE UART link. This document describes the transport, the envelope
common to every response, and then each known command and the frame it returns.
Every field maps a payload path to a decoded meaning and carries a confidence level.

## Confidence legend

- ✅ **Confirmed** — verified against an independent source (the phone app, a
  cross-pack diff that can only be explained one way, or a self-describing value).
- 🟡 **Inferred** — internally consistent, but from a single source / one operating
  point; not independently confirmed.
- ❓ **Unknown** — the name is suggestive at best; the meaning is a guess.

## Transport

- Proprietary JSON over BLE, on ISSC/Microchip-style UART characteristics:
  - Service `6e6f736a-4643-4d44-8fa9-0fafd005e455`
  - RX / notify `49535458-8341-43f4-a9d4-ec0e34729bb3`
  - TX / write  `49535258-184d-4bd9-bc61-20c647249616`
- **Poll:** write a command to TX; the unit answers with a JSON frame
  (`CommVer: 1`), streamed as one or more notifications on RX and brace-framed
  (`{` … `}`). See [Command reference](#command-reference) for the known commands
  and the frames they return.
- Each pack carries its own BLE radio and reports **itself** at list index `[0]`;
  the sibling pack's slot reads `65535` (or `-1`). Each pack is polled over its own
  connection, so `[0]` is always the pack you are talking to.
- A freshly-reconnected unit may answer with a well-formed frame whose values are
  all still zero-initialized (0 V / 0 % SOC / 0 °C at once) before its first real
  sample — an implausible pack voltage marks such a frame as a stale snapshot.

## Sentinel values

Common across frames:

| Value | Meaning |
|---|---|
| `65535` / `-1` | absent slot — the sibling pack in a per-pack list, or an unpopulated version/probe field |
| `32767` | absent temperature probe |
| `0` | uninitialized (see zero-frame note above) |
| `null` | field not present |

## Common envelope

These fields appear in every frame regardless of the poll command.

| Payload | Example | Decode | Conf. |
|---|---|---|---|
| `CommVer` | `1` | protocol / command version | ✅ |
| `wifiSN` | `"F075…"` | WiFi-module serial (`F`-prefixed) | ✅ |
| `DevSN` | `"075…"` | device serial | ✅ |
| `modID` | `1` | per-pack index within the bank (`1`, `2`, …; distinct per pack) | ✅ |
| `Type` | `112` | model / type code | ❓ |
| `SubType` | `7353` | model sub-type code | ❓ |

## Command reference

Each known poll command, followed by the decode of the frame it returns and a
sample capture.

### `wifilocalMonitor:get dev basice infor`

Returns the **basic-info** frame — identity and firmware/hardware versions. Beyond
the common envelope:

| Payload | Example | Decode | Conf. |
|---|---|---|---|
| `version` | `"2.15"` | WiFi-collector firmware, shown as **Version** in the app | ✅ |
| `COM` | `3` | unknown | ❓ |
| `iotType` | `3` | unknown | ❓ |
| `M1SwVer` | `203` | firmware version shown as **Master Version** in the app | ✅ |
| `M2SwVer` | `8` | firmware version shown as **IAP Version** in the app | ✅ |
| `DSwVer` | `65535` | display software version (`65535` = absent) | 🟡 |
| `DHwVer` | `0` | unknown | ❓ |
| `CtHwVer` | `0` | unknown | ❓ |
| `PwHwVer` | `65535` | unknown | ❓ |
| `BDsVer` | `65535` | unknown | ❓ |
| `RD` | `1` | unknown | ❓ |
| `RDT` | `4` | unknown | ❓ |

#### Sample

A complete `get dev basice infor` reply from one pack (`modID: 1`); serial tails
masked (`XXXX`).

```json
{
  "CommVer": 1, "version": "2.15", "wifiSN": "F0757048314XXXXXXXX", "COM": 3,
  "iotType": 3, "modID": 1, "DevSN": "0757048314XXXXXXXX", "Type": 112,
  "SubType": 7353, "DSwVer": 65535, "M1SwVer": 203, "M2SwVer": 8, "DHwVer": 0,
  "CtHwVer": 0, "PwHwVer": 65535, "BDsVer": 65535, "RD": 1, "RDT": 4
}
```

### `wifilocalMonitor:get dev real infor`

Returns the **real-info** frame — live telemetry: voltages, currents, SOC/SOH,
cells, temperatures, limits, flags. Adds `date` to the common envelope:

| Payload | Example | Decode | Conf. |
|---|---|---|---|
| `date` | `"20260722144050"` | timestamp `YYYYMMDDhhmmss`, unit local clock | ✅ |

#### Per-pack measurements

This pack at `[·][0]`; the sibling pack's slot is `65535` / `-1`.

| Payload | Example | Decode | Conf. |
|---|---|---|---|
| `BattList[0][0]` | `53530` | pack voltage, `÷1000` → V | ✅ |
| `BattList[1][0]` | `9` | pack current, `÷10` → A (signed; − = discharge) | ✅ |
| `BatsocList[0][0]` | `8400` | SOC, `÷100` → % | ✅ |
| `BatsocList[0][1]` | `1000` | likely SOH (`÷10` → 100 %); reads flat 100 % on new packs, so unconfirmed | 🟡 |
| `BatsocList[0][2]` | `350000` | unknown — guessed capacity, but `350000` (≈350 Ah as mAh) doesn't match the 314 Ah nameplate | ❓ |
| `BatcelList[0][0..15]` | `3347…` | cell voltages (16S), `÷1000` → V | ✅ |
| `BMaxMin[0][0]`, `[0][1]` | `3348`, `3347` | highest / lowest cell voltage, `÷1000` → V | ✅ |
| `BMaxMin[1][0]`, `[1][1]` | `2`, `0` | index of highest / lowest cell (0-based) | ✅ |
| `BtemList[0][0..3]` | `180…` | temperature probes, `÷10` → °C; `32767` = absent | ✅ |
| `BTemp[0]` | `[190, 180]` | pack temperature (tracks the cell probes), `÷10` → °C | 🟡 |
| `BTemp[1]` | `[513, 256]` | unknown — takes only a small discrete set (`256`/`259`/`512`/`513`, i.e. near `0x100`/`0x200`) with no intermediate values, so not a linear temperature | ❓ |
| `BBfault` | `0` | per-pack fault word (raw; bit layout unknown) | ✅ |
| `BBwarn` | `0` | per-pack warning word (raw; bit layout unknown). `4` observed at top of charge when one cell runs ahead of the rest | ✅ |

#### Per-pack limits — `BLVolCu`

| Payload | Example | Decode | Conf. |
|---|---|---|---|
| `BLVolCu[0][0]` | `576` | charge-voltage limit (CVL), `÷10` → V (57.6 = 3.6 V/cell ×16) | ✅ |
| `BLVolCu[0][1]` | `480` | discharge-voltage limit (DVL), `÷10` → V (48.0 = 3.0 V/cell ×16) | ✅ |
| `BLVolCu[1][0]` | `1280` | charge-current limit (CCL), `÷10` → A — **dynamic: drops to 0 when full** | ✅ |
| `BLVolCu[1][1]` | `1600` | discharge-current limit (DCL), `÷10` → A | ✅ |

#### Bank aggregates

Every pack echoes these identically (that is what marks them bank-level rather than
per-pack; see the naming note below).

| Payload | Example | Decode | Conf. |
|---|---|---|---|
| `Batt[0][0]` | `53500` | bank voltage, `÷1000` → V | ✅ |
| `Batt[1][0]` | `19` | bank current, `÷10` → A (sum across packs) | ✅ |
| `Batt[2][0]` | `null` | reserved / unused | ❓ |
| `Batsoc[0][0]` | `8450` | bank SOC, `÷100` → % | ✅ |
| `Batsoc[0][1]` | `1000` | likely SOH (see per-pack) | 🟡 |
| `Batsoc[0][2]` | `700000` | unknown — `2 × BatsocList[0][2]` (guessed capacity, see per-pack) | ❓ |
| `LVolCur[0][0]`, `[0][1]` | `576`, `480` | bank CVL / DVL, `÷10` → V | ✅ |
| `LVolCur[1][0]`, `[1][1]` | `2480`, `3200` | bank CCL / DCL, `÷10` → A (sum across packs) | ✅ |
| `Bfault` | `0` | bank fault word (OR across packs) | ✅ |
| `Bwarn` | `0` | bank warning word (OR across packs) | ✅ |

#### State, mode & config — not yet decoded

| Payload | Example | Guess | Conf. |
|---|---|---|---|
| `Estate` | `9152` | bank status bitfield (≈ OR of `Bstate`) | ❓ |
| `Bstate` | `9152` | per-pack status bitfield | ❓ |
| `workM` | `0` | work-mode index | ❓ |
| `HtCuSt` | `0` | heater-current status (`0` = not heating) | ❓ |
| `EMSpara` | `[[2,6]]` | config pair; the `6` may match the app's "Heat Request Curr 6 A" | ❓ |
| `BMSpara` | `[[2,6]]` | config pair (mirrors `EMSpara` here) | ❓ |
| `Templist` | `[[180,180],[0,0],[65535,65535],[65535,65535]]` | four 2-probe groups; group 0 equals the active `BtemList` probes (`÷10` → °C), group 1 reads ~`0`, groups 2–3 absent (`65535`); purpose/redundancy with `BtemList` unclear | ❓ |

#### Per-pack vs bank — naming convention

A frame mixes **per-pack** fields (this pack's own data) with **bank** fields (the
whole parallel bank). The field name does not tell you which — the `…List` suffix
especially does not mean "list of packs":

| Fields | Scope |
|---|---|
| `BattList`, `BatcelList`, `BtemList`, `BatsocList` | **per-pack** — this pack at `[·][0]`, the sibling pack's slot is `65535` |
| `Batt`, `Batsoc` | **bank** — despite having no `List` suffix |
| `BLVolCu` vs `LVolCur` | near-identical names, opposite scope (`BLVolCu` per-pack, `LVolCur` bank) |

To tell them apart, compare the two packs' frames: a value **identical** in both is
bank-level; one that **differs** is per-pack. (`Batt` voltage matches across packs →
bank; `BattList` voltage differs → per-pack.)

#### Sample

A complete `get dev real infor` reply from one pack (`modID: 1`) at 84 % SOC,
charging ~0.9 A. Serial tails are masked (`XXXX`); everything else is verbatim.
Whitespace added for readability — the wire frame is single-line.

```json
{
  "CommVer": 1, "wifiSN": "F0757048314XXXXXXXX", "modID": 1,
  "date": "20260722144050", "DevSN": "0757048314XXXXXXXX",
  "Type": 112, "SubType": 7353, "workM": 0,
  "Estate": 9152, "Bfault": 0, "Bwarn": 0, "Bstate": 9152,
  "BBfault": 0, "BBwarn": 0, "HtCuSt": 0,
  "BTemp": [[190, 180], [513, 256]],
  "Batt": [[53500], [19], [null]],
  "Batsoc": [[8450, 1000, 700000]],
  "Templist": [[180, 180], [0, 0], [65535, 65535], [65535, 65535]],
  "BattList": [[53530, 65535], [9, -1]],
  "BatsocList": [[8400, 1000, 350000]],
  "BatcelList": [
    [3347, 3347, 3348, 3347, 3347, 3347, 3347, 3347,
     3348, 3347, 3347, 3347, 3347, 3347, 3348, 3347],
    [65535, 65535, 65535, 65535, 65535, 65535, 65535, 65535,
     65535, 65535, 65535, 65535, 65535, 65535, 65535, 65535]
  ],
  "EMSpara": [[2, 6]],
  "BMaxMin": [[3348, 3347], [2, 0]],
  "LVolCur": [[576, 480], [2480, 3200]],
  "BMSpara": [[2, 6]],
  "BLVolCu": [[576, 480], [1280, 1600]],
  "BtemList": [[180, 180, 180, 180, 32767, 32767, 32767, 32767]]
}
```

The sibling pack (`modID: 2`) returns the same shape. Fields that **differ** per
pack: `wifiSN`, `DevSN`, `modID`, `BattList`, `BatcelList` (each pack's own 16 cells
at `[0]`, the other slot all `65535`), and `BMaxMin`. Fields **identical** across
both packs (bank-level): `Batt` voltage, `Batsoc`, `BatsocList`, `BLVolCu`,
`LVolCur`, and the `Bfault` / `Bwarn` / `Bstate` / `Estate` words.
