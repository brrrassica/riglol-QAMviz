#pragma once
#include <Arduino.h>

class Prbs7 {
 public:
  explicit Prbs7(uint8_t seed = 0x7f);
  void reset(uint8_t seed = 0x7f);
  uint8_t nextBit();
  uint8_t nextBits(uint8_t n);
 private:
  uint8_t state_;
};

uint8_t prbs7_nth(uint8_t seed, uint32_t n, uint8_t bits);