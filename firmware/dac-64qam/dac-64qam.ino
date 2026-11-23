// ESP32 dual-DAC 64-QAM generator for riglol-QAMviz.
// GPIO25 (DAC1) = I, GPIO26 (DAC2) = Q.
// Default preset: 20 kbaud at 8 samples/symbol => 160 ksample/s per DAC.
// Rectangular pulse shaping; 8x8 Gray-coded levels.
#include <Arduino.h>
#include "driver/dac_continuous.h"
#include "esp_chip_info.h"
#include "esp_system.h"

static dac_continuous_handle_t dac = nullptr;

static const uint32_t SAMPLE_RATE_HZ = 160000; // per DAC, ALTER mode
static const size_t   SPS            = 8;      // samples per symbol
static const size_t   BUF_BYTES      = 2048;   // interleaved I/Q bytes
static const size_t   SYMBOLS        = (BUF_BYTES / 2) / SPS;

// 64-QAM levels {-7,-5,-3,-1,+1,+3,+5,+7}
static const int LEVELS[8] = {-7, -5, -3, -1, 1, 3, 5, 7};
static const int LEVEL_SPACING = 16;           // codes between adjacent levels
static const uint8_t MIDDLE = 128;

static uint8_t code_for_level(int level) {
  return (uint8_t)(MIDDLE + level * LEVEL_SPACING);
}

// Map 3-bit natural binary value to a PAM-8 level using Gray ordering so
// adjacent levels differ by one bit: idx 0..7 -> -7,-5,-3,-1,+1,+3,+5,+7.
static int gray3_level(uint8_t v) {
  static const int levels[8] = {-7, -5, -3, -1, 1, 3, 5, 7};
  static const uint8_t g[8] = {0, 1, 3, 2, 6, 7, 5, 4}; // binary index -> Gray
  // Place level for Gray code g[v] at natural position v? Simpler: use Gray as
  // level selector directly: binary input v selects LEVELS[g[v]]? No. Standard:
  // Gray-code the axis value so adjacent amplitudes differ by 1 bit.
  // levels_by_natural_index[i] = LEVELS[i], bits = gray(i) transmitted.
  // For a PRNG stream we can just pick Gray-ordered levels by a 3-bit value:
  static const int gray_levels[8] = {-7, -5, -3, -1, 1, 3, 5, 7}; // natural order
  // g[v] gives gray code; we want the level whose gray code is v -> inv_gray.
  static const uint8_t inv_gray[8] = {0, 1, 3, 2, 7, 6, 4, 5};
  return gray_levels[inv_gray[v & 0x7]];
}

static void gray64qam(uint8_t bits, uint8_t *i_out, uint8_t *q_out) {
  // bits: b5b4b3 = I, b2b1b0 = Q. Each 3-bit group is treated as a Gray code
  // selecting one of 8 PAM levels.
  *i_out = code_for_level(gray3_level((bits >> 3) & 0x7));
  *q_out = code_for_level(gray3_level(bits & 0x7));
}

static uint8_t prng_byte(uint16_t *state) {
  for (int i = 0; i < 8; ++i) {
    const uint16_t bit = ((*state >> 0) ^ (*state >> 2) ^ (*state >> 3) ^ (*state >> 5)) & 1;
    *state = (uint16_t)((*state >> 1) | (bit << 15));
  }
  return (uint8_t)(*state & 0xFF);
}

void setup() {
  Serial.begin(115200);
  delay(300);

  esp_chip_info_t info;
  esp_chip_info(&info);
  Serial.printf("CHIP model=%d rev=%d cores=%d\n", info.model, info.revision, info.cores);
  if (info.revision != 100) {
    Serial.println("ERR not ECO1 (revision v1.0 == 100); refusing to run");
    return;
  }

  dac_continuous_config_t cfg = {};
  cfg.chan_mask  = DAC_CHANNEL_MASK_ALL;
  cfg.desc_num   = 8;
  cfg.buf_size   = 512;
  cfg.freq_hz    = SAMPLE_RATE_HZ;
  cfg.offset     = 0;
  cfg.clk_src    = DAC_DIGI_CLK_SRC_DEFAULT;
  cfg.chan_mode  = DAC_CHANNEL_MODE_ALTER;

  esp_err_t e = dac_continuous_new_channels(&cfg, &dac);
  Serial.printf("NEW_CHANNELS %s\n", esp_err_to_name(e));
  if (e != ESP_OK) return;

  dac_event_callbacks_t cbs = {};
  e = dac_continuous_register_event_callback(dac, &cbs, nullptr);
  Serial.printf("REGISTER_CB %s\n", esp_err_to_name(e));
  if (e != ESP_OK) return;

  e = dac_continuous_enable(dac);
  Serial.printf("ENABLE %s\n", esp_err_to_name(e));
  if (e != ESP_OK) return;

  static uint8_t buf[BUF_BYTES];
  uint16_t lfsr = 0xACE1;
  for (size_t s = 0; s < SYMBOLS; ++s) {
    const uint8_t bits = (uint8_t)(prng_byte(&lfsr) & 0x3F);
    uint8_t icode = 0, qcode = 0;
    gray64qam(bits, &icode, &qcode);
    for (size_t k = 0; k < SPS; ++k) {
      const size_t idx = (s * SPS + k) * 2;
      buf[idx + 0] = icode;
      buf[idx + 1] = qcode;
    }
  }

  size_t loaded = 0;
  e = dac_continuous_write_cyclically(dac, buf, sizeof(buf), &loaded);
  Serial.printf("WRITE_CYCLIC %s loaded=%u of %u\n",
                esp_err_to_name(e), loaded, sizeof(buf));
  Serial.printf("QAM 64 baud=%u sps=%u symbols_in_buffer=%u levels={-7..+7} spacing=%d\n",
                SAMPLE_RATE_HZ / SPS, SPS, SYMBOLS, LEVEL_SPACING);
}

void loop() {
  delay(1000);
}
