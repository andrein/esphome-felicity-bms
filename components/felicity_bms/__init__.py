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
CONF_CELL_VOLTAGE_MIN_CHANGE = "cell_voltage_min_change"

CONFIG_SCHEMA = (
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(FelicityBMS),
            # Minimum per-cell voltage change to publish. Cells jitter at the mV
            # level every poll; the default 0.1 mV logs that noise into history
            # (16 cells x ~1 point/poll). Raise it to thin per-cell history:
            # ~2 mV cuts points ~3.5x, ~5 mV ~12x — still far below any imbalance
            # worth acting on.
            cv.Optional(CONF_CELL_VOLTAGE_MIN_CHANGE, default="1mV"): cv.voltage,
        }
    )
    .extend(cv.polling_component_schema("10s"))
    .extend(ble_client.BLE_CLIENT_SCHEMA)
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await ble_client.register_ble_node(var, config)
    cg.add(var.set_cell_voltage_min_change(config[CONF_CELL_VOLTAGE_MIN_CHANGE]))
