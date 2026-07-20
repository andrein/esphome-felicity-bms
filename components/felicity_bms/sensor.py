import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import sensor
from esphome.const import (
    DEVICE_CLASS_BATTERY,
    DEVICE_CLASS_CURRENT,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_VOLTAGE,
    ENTITY_CATEGORY_DIAGNOSTIC,
    STATE_CLASS_MEASUREMENT,
    UNIT_AMPERE,
    UNIT_CELSIUS,
    UNIT_PERCENT,
    UNIT_VOLT,
    UNIT_WATT,
)

from . import CONF_FELICITY_BMS_ID, FelicityBMS

UNIT_MILLIVOLT = "mV"

# One row per sensor. Defaults: state_class=measurement (set None for raw codes),
# accuracy=0, diagnostic=False, count=1 (>1 expands to <key>_1..N with an indexed
# setter). Omit `icon` to keep the device_class default (SOC's dynamic battery
# level, temps' thermometer). Omit `unit`/`device_class` when there isn't one.
SENSORS = [
    {"key": "voltage", "setter": "set_voltage_sensor", "unit": UNIT_VOLT, "device_class": DEVICE_CLASS_VOLTAGE, "accuracy": 2, "icon": "mdi:flash-outline"},
    {"key": "current", "setter": "set_current_sensor", "unit": UNIT_AMPERE, "device_class": DEVICE_CLASS_CURRENT, "accuracy": 1, "icon": "mdi:current-dc"},
    {"key": "power", "setter": "set_power_sensor", "unit": UNIT_WATT, "device_class": DEVICE_CLASS_POWER, "icon": "mdi:lightning-bolt"},
    {"key": "soc", "setter": "set_soc_sensor", "unit": UNIT_PERCENT, "device_class": DEVICE_CLASS_BATTERY, "accuracy": 1},
    {"key": "soh", "setter": "set_soh_sensor", "unit": UNIT_PERCENT, "accuracy": 1, "diagnostic": True, "icon": "mdi:battery-heart-variant"},
    {"key": "min_cell_voltage", "setter": "set_min_cell_voltage_sensor", "unit": UNIT_VOLT, "device_class": DEVICE_CLASS_VOLTAGE, "accuracy": 3, "diagnostic": True, "icon": "mdi:arrow-collapse-down"},
    {"key": "max_cell_voltage", "setter": "set_max_cell_voltage_sensor", "unit": UNIT_VOLT, "device_class": DEVICE_CLASS_VOLTAGE, "accuracy": 3, "diagnostic": True, "icon": "mdi:arrow-collapse-up"},
    {"key": "cell_delta", "setter": "set_cell_delta_sensor", "unit": UNIT_MILLIVOLT, "diagnostic": True, "icon": "mdi:delta"},
    {"key": "max_temperature", "setter": "set_max_temperature_sensor", "unit": UNIT_CELSIUS, "device_class": DEVICE_CLASS_TEMPERATURE, "accuracy": 1, "diagnostic": True, "icon": "mdi:thermometer-high"},
    # Raw BMS codes: undocumented bit layout, not a measurement (no state_class).
    {"key": "fault_code", "setter": "set_fault_code_sensor", "state_class": None, "diagnostic": True, "icon": "mdi:alert-octagon"},
    {"key": "warning_code", "setter": "set_warning_code_sensor", "state_class": None, "diagnostic": True, "icon": "mdi:alert"},
    # Arrays: <key>_1..N, setter takes a zero-based index.
    {"key": "cell_voltage", "setter": "set_cell_voltage_sensor", "unit": UNIT_VOLT, "device_class": DEVICE_CLASS_VOLTAGE, "accuracy": 3, "diagnostic": True, "icon": "mdi:battery-outline", "count": 16},
    {"key": "temperature", "setter": "set_temperature_sensor", "unit": UNIT_CELSIUS, "device_class": DEVICE_CLASS_TEMPERATURE, "accuracy": 1, "diagnostic": True, "count": 4},
]


def _schema(row):
    kwargs = {"accuracy_decimals": row.get("accuracy", 0)}
    if "unit" in row:
        kwargs["unit_of_measurement"] = row["unit"]
    if "device_class" in row:
        kwargs["device_class"] = row["device_class"]
    state_class = row.get("state_class", STATE_CLASS_MEASUREMENT)
    if state_class is not None:
        kwargs["state_class"] = state_class
    if row.get("diagnostic"):
        kwargs["entity_category"] = ENTITY_CATEGORY_DIAGNOSTIC
    if "icon" in row:
        kwargs["icon"] = row["icon"]
    return sensor.sensor_schema(**kwargs)


def _keys(row):
    n = row.get("count", 1)
    return [row["key"]] if n == 1 else [f"{row['key']}_{i}" for i in range(1, n + 1)]


CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_FELICITY_BMS_ID): cv.use_id(FelicityBMS),
        **{cv.Optional(key): _schema(row) for row in SENSORS for key in _keys(row)},
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_FELICITY_BMS_ID])
    for row in SENSORS:
        setter = getattr(hub, row["setter"])
        for idx, key in enumerate(_keys(row)):
            if key not in config:
                continue
            sens = await sensor.new_sensor(config[key])
            cg.add(setter(sens) if row.get("count", 1) == 1 else setter(idx, sens))
