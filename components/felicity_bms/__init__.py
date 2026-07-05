import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import ble_client
from esphome.const import CONF_ID

CODEOWNERS = ["@andrein"]
DEPENDENCIES = ["ble_client"]
AUTO_LOAD = ["json"]
MULTI_CONF = True

felicity_bms_ns = cg.esphome_ns.namespace("felicity_bms")
FelicityBMS = felicity_bms_ns.class_(
    "FelicityBMS", cg.PollingComponent, ble_client.BLEClientNode
)

CONF_FELICITY_BMS_ID = "felicity_bms_id"

CONFIG_SCHEMA = (
    cv.Schema({cv.GenerateID(): cv.declare_id(FelicityBMS)})
    .extend(cv.polling_component_schema("10s"))
    .extend(ble_client.BLE_CLIENT_SCHEMA)
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await ble_client.register_ble_node(var, config)
