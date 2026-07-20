#pragma once

#include "esphome/core/component.h"
#include "esphome/components/ble_client/ble_client.h"
#include "esphome/components/esp32_ble_tracker/esp32_ble_tracker.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/binary_sensor/binary_sensor.h"

#include <esp_gattc_api.h>
#include <string>

namespace esphome {
namespace felicity_bms {

static const uint8_t CELL_COUNT = 16;
static const uint8_t TEMP_COUNT = 4;

class FelicityBMS : public PollingComponent, public ble_client::BLEClientNode {
 public:
  void update() override;
  void dump_config() override;
  void gattc_event_handler(esp_gattc_cb_event_t event, esp_gatt_if_t gattc_if,
                           esp_ble_gattc_cb_param_t *param) override;

  void set_voltage_sensor(sensor::Sensor *s) { this->voltage_ = s; }
  void set_current_sensor(sensor::Sensor *s) { this->current_ = s; }
  void set_power_sensor(sensor::Sensor *s) { this->power_ = s; }
  void set_soc_sensor(sensor::Sensor *s) { this->soc_ = s; }
  void set_min_cell_voltage_sensor(sensor::Sensor *s) { this->min_cell_voltage_ = s; }
  void set_max_cell_voltage_sensor(sensor::Sensor *s) { this->max_cell_voltage_ = s; }
  void set_cell_delta_sensor(sensor::Sensor *s) { this->cell_delta_ = s; }
  void set_max_temperature_sensor(sensor::Sensor *s) { this->max_temperature_ = s; }
  void set_cell_voltage_sensor(uint8_t i, sensor::Sensor *s) { this->cell_voltage_[i] = s; }
  void set_temperature_sensor(uint8_t i, sensor::Sensor *s) { this->temperature_[i] = s; }
  void set_cell_voltage_min_change(float v) { this->cell_voltage_min_change_ = v; }
  void set_fault_code_sensor(sensor::Sensor *s) { this->fault_code_ = s; }
  void set_warning_code_sensor(sensor::Sensor *s) { this->warning_code_ = s; }
  void set_fault_binary_sensor(binary_sensor::BinarySensor *s) { this->fault_ = s; }
  void set_warning_binary_sensor(binary_sensor::BinarySensor *s) { this->warning_ = s; }

  // Latest raw frame, for a YAML api.respond debug action; empty until first rx.
  const std::string &get_last_raw_frame() const { return this->last_frame_; }
  uint32_t get_last_raw_frame_age_ms() const;

 protected:
  void feed_(const uint8_t *data, uint16_t len);
  void handle_frame_(const std::string &frame);

  uint16_t rx_handle_{0};
  uint16_t tx_handle_{0};
  std::string buffer_;
  float cell_voltage_min_change_{0.001f};  // volts; suppress sub-threshold cell noise

  // Stored before parsing, so frames later dropped as implausible stay visible.
  std::string last_frame_;
  uint32_t last_frame_ms_{0};

  sensor::Sensor *voltage_{nullptr};
  sensor::Sensor *current_{nullptr};
  sensor::Sensor *power_{nullptr};
  sensor::Sensor *soc_{nullptr};
  sensor::Sensor *min_cell_voltage_{nullptr};
  sensor::Sensor *max_cell_voltage_{nullptr};
  sensor::Sensor *cell_delta_{nullptr};
  sensor::Sensor *max_temperature_{nullptr};
  sensor::Sensor *cell_voltage_[CELL_COUNT]{};
  sensor::Sensor *temperature_[TEMP_COUNT]{};
  sensor::Sensor *fault_code_{nullptr};
  sensor::Sensor *warning_code_{nullptr};
  binary_sensor::BinarySensor *fault_{nullptr};
  binary_sensor::BinarySensor *warning_{nullptr};
};

}  // namespace felicity_bms
}  // namespace esphome
