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
  static const int levels[4] = {-3, -1, 1, 3}; // 00,01,11,10
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
  // 16-QAM known vectors: 00,00 => -3,-3; 11,11 => +3,+3
  IqCode c16_00 = qam16_map(0x0, 0.8f);
  IqCode c16_ff = qam16_map(0xF, 0.8f);
  bool ok16 = (c16_00.i < 128 && c16_00.q < 128 && c16_ff.i > 128 && c16_ff.q > 128 &&
               c16_00.i == c16_00.q && c16_ff.i == c16_ff.q);
  // PAM4 Gray adjacency: single-bit Gray step must map to one PAM level step.
  IqCode c16_01 = qam16_map(0x1, 0.8f); // 0001: I=00, Q=01
  IqCode c16_03 = qam16_map(0x3, 0.8f); // 0011: I=00, Q=11
  int step_q = (int)c16_03.q - (int)c16_01.q;
  int step_i = (int)c16_03.i - (int)c16_01.i;
  bool ok16_gray = (step_i == 0) && (step_q > 30) && (step_q < 90);
  ok16 = ok16 && ok16_gray;

  // 64-QAM known vectors: 000,000 => -7,-7; 111,111 => +7,+7 (Gray mapping)
  IqCode c64_00 = qam64_map(0x00, 0.8f);
  IqCode c64_3f = qam64_map(0x3F, 0.8f);
  bool ok64 = (c64_00.i < 128 && c64_00.q < 128 && c64_3f.i > 128 && c64_3f.q > 128 &&
               c64_00.i == c64_00.q && c64_3f.i == c64_3f.q);

  // PRBS7 deterministic first-N check (seed 0x7f).
  Prbs7 p(0x7f);
  uint8_t s1 = p.nextBits(4);
  uint8_t s2 = p.nextBits(4);
  uint8_t s3 = p.nextBits(4);
  uint8_t s4 = p.nextBits(4);
  Prbs7 p2(0x7f);
  bool ok_prbs = (s1 == p2.nextBits(4)) && (s2 == p2.nextBits(4)) &&
                 (s3 == p2.nextBits(4)) && (s4 == p2.nextBits(4));
  // Known expected first 4 nibbles from this PRBS7 implementation/seed 0x7f.
  bool ok_prbs_known = (s1 == 0x0 && s2 == 0x2 && s3 == 0x0 && s4 == 0xC);

  bool ok = ok16 && ok64 && ok_prbs && ok_prbs_known;
  snprintf(out, outLen,
           "q16_00=%u,%u q16_ff=%u,%u q64_00=%u,%u q64_3f=%u,%u prbs=%X%X%X%X ok=%s",
           c16_00.i, c16_00.q, c16_ff.i, c16_ff.q,
           c64_00.i, c64_00.q, c64_3f.i, c64_3f.q,
           s1, s2, s3, s4, ok ? "true" : "false");
  return ok;
}