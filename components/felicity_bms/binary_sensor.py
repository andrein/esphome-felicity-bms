import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import binary_sensor
from esphome.const import DEVICE_CLASS_PROBLEM, ENTITY_CATEGORY_DIAGNOSTIC

from . import CONF_FELICITY_BMS_ID, FelicityBMS

# key -> setter. "fault"/"warning" mirror Bfault/Bwarn individually so automations
# can alert on faults without also firing for benign warnings.
FLAGS = {
    "fault": "set_fault_binary_sensor",
    "warning": "set_warning_binary_sensor",
}


def _flag_schema():
    return binary_sensor.binary_sensor_schema(
        device_class=DEVICE_CLASS_PROBLEM,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    )


CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_FELICITY_BMS_ID): cv.use_id(FelicityBMS),
        **{cv.Optional(key): _flag_schema() for key in FLAGS},
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_FELICITY_BMS_ID])
    for key, setter in FLAGS.items():
        if key in config:
            b = await binary_sensor.new_binary_sensor(config[key])
            cg.add(getattr(hub, setter)(b))
