#pragma once
#include <Arduino.h>
#include "qam_config.h"
#include "prbs.h"

struct IqCode {
  uint8_t i;
  uint8_t q;
};

IqCode qam16_map(uint8_t bits4, float gain);
IqCode qam64_map(uint8_t bits6, float gain);
IqCode symbol_to_codes(const QamConfig &cfg, uint16_t symbolIndex, Prbs7 &prbs);
bool qam_selftest(char *out, size_t outLen);