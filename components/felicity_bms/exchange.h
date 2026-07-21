#pragma once

#include "esphome/core/hal.h"

#include <functional>
#include <string>
#include <vector>

namespace esphome {
namespace felicity_bms {

class FelicityBMS;

// Owns the request→response cycle: one command outstanding at a time, its reply
// routed to that request's callback, with a lost-reply timeout. Correlation is by
// order — the single BLE link carries one command and its reply at a time.
class Exchange {
 public:
  using Callback = std::function<void(const std::string &reply)>;

  explicit Exchange(FelicityBMS *bms) : bms_(bms) {}
  void set_timeout(uint32_t ms) { this->timeout_ = ms; }

  // Queue a command; its reply is delivered to cb.
  void request(const std::string &cmd, Callback cb) {
    this->queue_.push_back({cmd, std::move(cb)});
    this->pump_();
  }

  // Feed each complete frame here; routes it to the in-flight request.
  void on_reply(const std::string &frame) {
    if (!this->awaiting_)
      return;
    this->awaiting_ = false;
    Callback cb = std::move(this->in_flight_);
    this->in_flight_ = nullptr;
    if (cb)
      cb(frame);
    this->pump_();
  }

  // Call periodically; recovers if a reply never arrives.
  void tick() {
    if (this->awaiting_ && millis() - this->sent_at_ > this->timeout_) {
      this->awaiting_ = false;
      this->in_flight_ = nullptr;
      this->pump_();
    }
  }

  bool idle() const { return !this->awaiting_ && this->queue_.empty(); }

 protected:
  void pump_();  // send the next queued command if the link is free

  struct Pending {
    std::string cmd;
    Callback cb;
  };

  FelicityBMS *bms_;
  std::vector<Pending> queue_;
  Callback in_flight_{nullptr};
  bool awaiting_{false};
  uint32_t sent_at_{0};
  uint32_t timeout_{5000};
};

}  // namespace felicity_bms
}  // namespace esphome
