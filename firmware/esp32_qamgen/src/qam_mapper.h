#pragma once
#include <Arduino.h>
#include "qam_config.h"

struct IqCode {
  uint8_t i;
  uint8_t q;
};

IqCode qam16_map(uint8_t bits, float gain);
IqCode symbol_to_codes(const QamConfig &cfg, uint16_t symbolIndex, uint32_t &prngState, uint8_t &trainingPhase);