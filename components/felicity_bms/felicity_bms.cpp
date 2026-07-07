#include "felicity_bms.h"
#include "esphome/core/log.h"
#include "esphome/components/json/json_util.h"

#include <cmath>
#include <cstring>

namespace esphome {
namespace felicity_bms {

namespace espbt = esp32_ble_tracker;

static const char *const TAG = "felicity_bms";
static const char *const POLL_CMD = "wifilocalMonitor:get dev real infor";

// Publish only on change to keep the API send buffer from overflowing.
static void pub(sensor::Sensor *s, float v) {
  if (s == nullptr)
    return;
  bool cur_nan = std::isnan(s->state), v_nan = std::isnan(v);
  if (cur_nan != v_nan || (!v_nan && std::fabs(s->state - v) > 1e-4f))
    s->publish_state(v);
}
static void pub(binary_sensor::BinarySensor *s, bool v) {
  if (s != nullptr && (!s->has_state() || s->state != v))
    s->publish_state(v);
}

static espbt::ESPBTUUID service_uuid() {
  return espbt::ESPBTUUID::from_raw("6e6f736a-4643-4d44-8fa9-0fafd005e455");
}
static espbt::ESPBTUUID rx_uuid() {
  return espbt::ESPBTUUID::from_raw("49535458-8341-43f4-a9d4-ec0e34729bb3");
}
static espbt::ESPBTUUID tx_uuid() {
  return espbt::ESPBTUUID::from_raw("49535258-184d-4bd9-bc61-20c647249616");
}

void FelicityBMS::dump_config() {
  ESP_LOGCONFIG(TAG, "Felicity BMS (update every %u ms)", (unsigned) this->get_update_interval());
}

void FelicityBMS::gattc_event_handler(esp_gattc_cb_event_t event, esp_gatt_if_t gattc_if,
                                      esp_ble_gattc_cb_param_t *param) {
  switch (event) {
    case ESP_GATTC_DISCONNECT_EVT:
    case ESP_GATTC_CLOSE_EVT:
      this->rx_handle_ = 0;
      this->tx_handle_ = 0;
      this->buffer_.clear();
      this->node_state = espbt::ClientState::IDLE;
      break;

    case ESP_GATTC_SEARCH_CMPL_EVT: {
      auto *rx = this->parent()->get_characteristic(service_uuid(), rx_uuid());
      auto *tx = this->parent()->get_characteristic(service_uuid(), tx_uuid());
      if (rx == nullptr || tx == nullptr) {
        ESP_LOGW(TAG, "RX/TX characteristics not found");
        break;
      }
      this->rx_handle_ = rx->handle;
      this->tx_handle_ = tx->handle;
      auto status = esp_ble_gattc_register_for_notify(this->parent()->get_gattc_if(),
                                                      this->parent()->get_remote_bda(), rx->handle);
      if (status != ESP_OK)
        ESP_LOGW(TAG, "register_for_notify failed, status=%d", status);
      break;
    }

    case ESP_GATTC_REG_FOR_NOTIFY_EVT: {
      if (param->reg_for_notify.handle != this->rx_handle_)
        break;
      if (param->reg_for_notify.status != ESP_GATT_OK) {
        ESP_LOGW(TAG, "notify registration failed, status=%d", param->reg_for_notify.status);
        break;
      }
      this->node_state = espbt::ClientState::ESTABLISHED;
      ESP_LOGI(TAG, "connected and subscribed");
      this->update();
      break;
    }

    case ESP_GATTC_NOTIFY_EVT: {
      if (param->notify.handle != this->rx_handle_)
        break;
      this->feed_(param->notify.value, param->notify.value_len);
      break;
    }

    default:
      break;
  }
}

void FelicityBMS::update() {
  if (this->node_state != espbt::ClientState::ESTABLISHED || this->tx_handle_ == 0)
    return;
  auto status = esp_ble_gattc_write_char(this->parent()->get_gattc_if(), this->parent()->get_conn_id(),
                                         this->tx_handle_, std::strlen(POLL_CMD),
                                         reinterpret_cast<uint8_t *>(const_cast<char *>(POLL_CMD)),
                                         ESP_GATT_WRITE_TYPE_NO_RSP, ESP_GATT_AUTH_REQ_NONE);
  if (status != ESP_OK)
    ESP_LOGW(TAG, "poll write failed, status=%d", status);
}

void FelicityBMS::feed_(const uint8_t *data, uint16_t len) {
  if (len == 0)
    return;
  if (data[0] == '{')
    this->buffer_.clear();
  if (this->buffer_.size() > 4096) {  // runaway guard
    this->buffer_.clear();
    return;
  }
  this->buffer_.append(reinterpret_cast<const char *>(data), len);
  if (data[len - 1] != '}')
    return;  // incomplete frame
  std::string frame;
  frame.swap(this->buffer_);
  this->handle_frame_(frame);
}

void FelicityBMS::handle_frame_(const std::string &frame) {
  json::parse_json(frame, [this](JsonObject root) -> bool {
    if (root["CommVer"].as<int>() != 1)
      return false;

    JsonArray batt = root["Batt"].as<JsonArray>();
    if (!batt.isNull()) {
      float v = batt[0][0].as<long>() / 1000.0f;
      float i = batt[1][0].as<long>() / 10.0f;
      pub(this->voltage_, v);
      pub(this->current_, i);
      pub(this->power_, v * i);
    }

    JsonArray soc = root["BatsocList"].as<JsonArray>();
    if (!soc.isNull())
      pub(this->soc_, soc[0][0].as<long>() / 100.0f);

    JsonArray cells = root["BatcelList"][0].as<JsonArray>();
    if (!cells.isNull()) {
      long mn = 1000000, mx = -1000000;
      uint8_t idx = 0;
      for (JsonVariant cv : cells) {
        long mv = cv.as<long>();
        // Only publish plausible readings; a garbled/partial BLE frame can yield
        // 0 (or junk) for a cell, and an unconditional publish pushes that 0 into
        // HA history. Same guard the min/max accumulation below uses.
        if (idx < CELL_COUNT && mv > 0 && mv < 60000)
          pub(this->cell_voltage_[idx], mv / 1000.0f);
        if (mv > 0 && mv < 60000) {
          if (mv < mn)
            mn = mv;
          if (mv > mx)
            mx = mv;
        }
        idx++;
      }
      if (mx >= mn) {
        pub(this->min_cell_voltage_, mn / 1000.0f);
        pub(this->max_cell_voltage_, mx / 1000.0f);
        pub(this->cell_delta_, (float) (mx - mn));
      }
    }

    JsonArray temps = root["BtemList"][0].as<JsonArray>();
    if (!temps.isNull()) {
      float tmax = -1000.0f;
      uint8_t idx = 0;
      for (JsonVariant tv : temps) {
        long raw = tv.as<long>();
        if (idx < TEMP_COUNT)
          pub(this->temperature_[idx], (raw == 32767) ? NAN : raw / 10.0f);
        if (raw != 32767 && raw / 10.0f > tmax)
          tmax = raw / 10.0f;
        idx++;
      }
      if (tmax > -1000.0f)
        pub(this->max_temperature_, tmax);
    }

    pub(this->problem_, (root["Bfault"].as<long>() + root["Bwarn"].as<long>()) != 0);
    return true;
  });
}

}  // namespace felicity_bms
}  // namespace esphome
