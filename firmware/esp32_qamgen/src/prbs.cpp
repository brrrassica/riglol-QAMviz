#include "prbs.h"

Prbs7::Prbs7(uint8_t seed) { reset(seed); }

void Prbs7::reset(uint8_t seed) {
  state_ = seed & 0x7f;
  if (state_ == 0) state_ = 0x7f;
}

uint8_t Prbs7::nextBit() {
  // PRBS7: x^7 + x^6 + 1, taps at bit6 and bit5 for 7-bit state (bit0 LSB)
  uint8_t bit = ((state_ >> 6) ^ (state_ >> 5)) & 1;
  state_ = ((state_ << 1) | bit) & 0x7f;
  return bit;
}

uint8_t Prbs7::nextBits(uint8_t n) {
  uint8_t v = 0;
  for (uint8_t i = 0; i < n; ++i) v = (v << 1) | nextBit();
  return v;
}

uint8_t prbs7_nth(uint8_t seed, uint32_t n, uint8_t bits) {
  Prbs7 p(seed);
  uint8_t v = 0;
  for (uint32_t i = 0; i < n; ++i) v = p.nextBits(bits);
  return v;
}
