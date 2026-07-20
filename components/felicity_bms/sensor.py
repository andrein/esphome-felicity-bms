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
CELL_COUNT = 16
TEMP_COUNT = 4

# key -> (setter, unit, device_class, accuracy, diagnostic)
SIMPLE = {
    "voltage": ("set_voltage_sensor", UNIT_VOLT, DEVICE_CLASS_VOLTAGE, 2, False),
    "current": ("set_current_sensor", UNIT_AMPERE, DEVICE_CLASS_CURRENT, 1, False),
    "power": ("set_power_sensor", UNIT_WATT, DEVICE_CLASS_POWER, 0, False),
    "soc": ("set_soc_sensor", UNIT_PERCENT, DEVICE_CLASS_BATTERY, 1, False),
    "soh": ("set_soh_sensor", UNIT_PERCENT, None, 1, True),
    "min_cell_voltage": ("set_min_cell_voltage_sensor", UNIT_VOLT, DEVICE_CLASS_VOLTAGE, 3, True),
    "max_cell_voltage": ("set_max_cell_voltage_sensor", UNIT_VOLT, DEVICE_CLASS_VOLTAGE, 3, True),
    "cell_delta": ("set_cell_delta_sensor", UNIT_MILLIVOLT, None, 0, True),
    "max_temperature": ("set_max_temperature_sensor", UNIT_CELSIUS, DEVICE_CLASS_TEMPERATURE, 1, True),
}


def _schema(unit, device_class, accuracy, diagnostic):
    kwargs = dict(
        unit_of_measurement=unit,
        accuracy_decimals=accuracy,
        state_class=STATE_CLASS_MEASUREMENT,
    )
    if device_class is not None:
        kwargs["device_class"] = device_class
    if diagnostic:
        kwargs["entity_category"] = ENTITY_CATEGORY_DIAGNOSTIC
    return sensor.sensor_schema(**kwargs)


# key -> setter; raw BMS codes (undocumented bit layout), diagnostic, not measurements
CODES = {
    "fault_code": "set_fault_code_sensor",
    "warning_code": "set_warning_code_sensor",
}

_config = {cv.GenerateID(CONF_FELICITY_BMS_ID): cv.use_id(FelicityBMS)}
for _key, (_setter, _unit, _dc, _acc, _diag) in SIMPLE.items():
    _config[cv.Optional(_key)] = _schema(_unit, _dc, _acc, _diag)
for _key in CODES:
    _config[cv.Optional(_key)] = sensor.sensor_schema(
        accuracy_decimals=0,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        icon="mdi:alert-circle-outline",
    )
for _i in range(1, CELL_COUNT + 1):
    _config[cv.Optional(f"cell_voltage_{_i}")] = _schema(
        UNIT_VOLT, DEVICE_CLASS_VOLTAGE, 3, True
    )
for _i in range(1, TEMP_COUNT + 1):
    _config[cv.Optional(f"temperature_{_i}")] = _schema(
        UNIT_CELSIUS, DEVICE_CLASS_TEMPERATURE, 1, True
    )

CONFIG_SCHEMA = cv.Schema(_config)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_FELICITY_BMS_ID])
    for key, (setter, *_rest) in SIMPLE.items():
        if key in config:
            sens = await sensor.new_sensor(config[key])
            cg.add(getattr(hub, setter)(sens))
    for key, setter in CODES.items():
        if key in config:
            sens = await sensor.new_sensor(config[key])
            cg.add(getattr(hub, setter)(sens))
    for i in range(1, CELL_COUNT + 1):
        key = f"cell_voltage_{i}"
        if key in config:
            sens = await sensor.new_sensor(config[key])
            cg.add(hub.set_cell_voltage_sensor(i - 1, sens))
    for i in range(1, TEMP_COUNT + 1):
        key = f"temperature_{i}"
        if key in config:
            sens = await sensor.new_sensor(config[key])
            cg.add(hub.set_temperature_sensor(i - 1, sens))
