#pragma once
#include <Arduino.h>

struct QamConfig {
  char modulation[8]; // "qam16"
  uint32_t symbol_rate;
  uint32_t sps;
  float gain;
  char shape[8]; // "rect"
  uint32_t seed;
};

inline QamConfig default_qam_config() {
  QamConfig c = {};
  strlcpy(c.modulation, "qam16", sizeof(c.modulation));
  c.symbol_rate = 20000;
  c.sps = 8;
  c.gain = 0.8f;
  strlcpy(c.shape, "rect", sizeof(c.shape));
  c.seed = 42;
  return c;
}
