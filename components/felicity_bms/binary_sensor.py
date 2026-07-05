import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import binary_sensor
from esphome.const import DEVICE_CLASS_PROBLEM, ENTITY_CATEGORY_DIAGNOSTIC

from . import CONF_FELICITY_BMS_ID, FelicityBMS

CONF_PROBLEM = "problem"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_FELICITY_BMS_ID): cv.use_id(FelicityBMS),
        cv.Optional(CONF_PROBLEM): binary_sensor.binary_sensor_schema(
            device_class=DEVICE_CLASS_PROBLEM,
            entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        ),
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_FELICITY_BMS_ID])
    if CONF_PROBLEM in config:
        b = await binary_sensor.new_binary_sensor(config[CONF_PROBLEM])
        cg.add(hub.set_problem_binary_sensor(b))
