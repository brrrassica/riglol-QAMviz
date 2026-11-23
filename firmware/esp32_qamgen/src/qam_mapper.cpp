#include "qam_mapper.h"
#include <math.h>

static uint8_t code_from_norm(float x, float gain) {
  float v = 128.0f + gain * 127.0f * x;
  if (v < 0) v = 0;
  if (v > 255) v = 255;
  return (uint8_t)lroundf(v);
}

static int pam4_gray_to_level(uint8_t g2) {
  // Gray 2-bit -> natural level index 0..3 -> {-3,-1,+1,+3}
  static const int levels[4] = {-3, -1, 3, 1}; // g2: 00->-3,01->-1,11->+3,10->+1
  return levels[g2 & 0x3];
}

IqCode qam16_map(uint8_t bits, float gain) {
  // bits: b3b2 = I gray, b1b0 = Q gray
  const float norm = 1.0f / sqrtf(10.0f);
  int iLvl = pam4_gray_to_level((bits >> 2) & 0x3);
  int qLvl = pam4_gray_to_level(bits & 0x3);
  IqCode c;
  c.i = code_from_norm(iLvl * norm, gain);
  c.q = code_from_norm(qLvl * norm, gain);
  return c;
}

static uint8_t lfsr8_next(uint8_t &s) {
  // x^8 + x^6 + x^5 + x^4 + 1
  uint8_t bit = ((s >> 0) ^ (s >> 2) ^ (s >> 3) ^ (s >> 4)) & 1;
  s = (s >> 1) | (bit << 7);
  return s;
}

IqCode symbol_to_codes(const QamConfig &cfg, uint16_t symbolIndex, uint32_t &prngState, uint8_t &trainingPhase) {
  (void)trainingPhase;
  const uint16_t framePos = symbolIndex % 1024;
  uint8_t bits = 0;
  if (framePos < 32) {
    // Deterministic training: walking 4-bit pattern
    bits = (uint8_t)((framePos * 5 + 3) & 0x0F);
  } else {
    uint8_t s = (uint8_t)(prngState & 0xFF);
    if (s == 0) s = 0xA5;
    lfsr8_next(s);
    bits = s & 0x0F;
    lfsr8_next(s);
    prngState = (prngState & 0xFFFFFF00u) | s;
  }
  return qam16_map(bits, cfg.gain);
}