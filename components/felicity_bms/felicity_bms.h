#pragma once

#include "esphome/core/component.h"
#include "esphome/components/ble_client/ble_client.h"
#include "esphome/components/esp32_ble_tracker/esp32_ble_tracker.h"

#include <esp_gattc_api.h>
#include <string>

namespace esphome {
namespace felicity_bms {

class FelicityBMS : public PollingComponent, public ble_client::BLEClientNode {
 public:
  void update() override;
  void dump_config() override;
  void gattc_event_handler(esp_gattc_cb_event_t event, esp_gatt_if_t gattc_if,
                           esp_ble_gattc_cb_param_t *param) override;

 protected:
  void feed_(const uint8_t *data, uint16_t len);
  void handle_frame_(const std::string &frame);

  uint16_t rx_handle_{0};
  uint16_t tx_handle_{0};
  std::string buffer_;
};

}  // namespace felicity_bms
}  // namespace esphome
