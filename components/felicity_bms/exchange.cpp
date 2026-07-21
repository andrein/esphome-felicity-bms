#include "exchange.h"
#include "felicity_bms.h"

namespace esphome {
namespace felicity_bms {

void Exchange::pump_() {
  if (this->awaiting_ || this->queue_.empty())
    return;
  Pending req = std::move(this->queue_.front());
  this->queue_.erase(this->queue_.begin());
  if (!this->bms_->write_command_(req.cmd))
    return;  // link down; dropped, retried on the next request/poll
  this->awaiting_ = true;
  this->sent_at_ = millis();
  this->in_flight_ = std::move(req.cb);
}

}  // namespace felicity_bms
}  // namespace esphome
