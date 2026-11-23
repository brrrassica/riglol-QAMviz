#include "qam_mapper.h"
#include <math.h>
#include <stdio.h>

static uint8_t code_from_norm(float x, float gain) {
  float v = 128.0f + gain * 127.0f * x;
  if (v < 0) v = 0;
  if (v > 255) v = 255;
  return (uint8_t)lroundf(v);
}

static int pam4_gray_to_level(uint8_t g2) {
  static const int levels[4] = {-3, -1, 3, 1}; // 00,01,11,10
  return levels[g2 & 0x3];
}

static int pam8_gray_to_level(uint8_t g3) {
  // Gray 3-bit -> levels {-7,-5,-3,-1,+1,+3,+5,+7}
  static const int levels[8] = {-7, -5, -1, -3, 7, 5, 1, 3};
  return levels[g3 & 0x7];
}

IqCode qam16_map(uint8_t bits4, float gain) {
  const float norm = 1.0f / sqrtf(10.0f);
  int iLvl = pam4_gray_to_level((bits4 >> 2) & 0x3);
  int qLvl = pam4_gray_to_level(bits4 & 0x3);
  IqCode c;
  c.i = code_from_norm(iLvl * norm, gain);
  c.q = code_from_norm(qLvl * norm, gain);
  return c;
}

IqCode qam64_map(uint8_t bits6, float gain) {
  const float norm = 1.0f / sqrtf(42.0f);
  int iLvl = pam8_gray_to_level((bits6 >> 3) & 0x7);
  int qLvl = pam8_gray_to_level(bits6 & 0x7);
  IqCode c;
  c.i = code_from_norm(iLvl * norm, gain);
  c.q = code_from_norm(qLvl * norm, gain);
  return c;
}

static uint8_t training_bits(uint16_t framePos, bool qam64) {
  if (qam64) return (uint8_t)((framePos * 11 + 7) & 0x3F);
  return (uint8_t)((framePos * 5 + 3) & 0x0F);
}

IqCode symbol_to_codes(const QamConfig &cfg, uint16_t symbolIndex, Prbs7 &prbs) {
  const bool is64 = strcmp(cfg.modulation, "qam64") == 0;
  const uint16_t framePos = symbolIndex % 1024;
  uint8_t bits = 0;
  if (framePos < 32) {
    bits = training_bits(framePos, is64);
  } else {
    bits = is64 ? prbs.nextBits(6) : prbs.nextBits(4);
  }
  return is64 ? qam64_map(bits, cfg.gain) : qam16_map(bits, cfg.gain);
}

bool qam_selftest(char *out, size_t outLen) {
  // Known 16-QAM: bits 0000 => I gray 00=-3, Q gray 00=-3
  IqCode c0 = qam16_map(0x0, 0.8f);
  IqCode cf = qam16_map(0xF, 0.8f); // 11,11 => +3,+3
  bool ok = (c0.i < 128 && c0.q < 128 && cf.i > 128 && cf.q > 128 && c0.i == c0.q && cf.i == cf.q);
  // PRBS7 sanity: first bit sequence from seed 0x7f should be deterministic
  Prbs7 p(0x7f);
  uint8_t b1 = p.nextBits(4);
  Prbs7 p2(0x7f);
  uint8_t b2 = p2.nextBits(4);
  ok = ok && (b1 == b2);
  snprintf(out, outLen, "qam16_00=%u,%u qam16_ff=%u,%u prbs=%u ok=%s", c0.i, c0.q, cf.i, cf.q, b1, ok ? "true" : "false");
  return ok;
}