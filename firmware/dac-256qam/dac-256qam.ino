// ESP32 dual-DAC 256-QAM generator for riglol-QAMviz.
// GPIO25 (DAC1) = I, GPIO26 (DAC2) = Q.
// Default preset: 20 kbaud at 8 samples/symbol => 160 ksample/s per DAC.
// Rectangular pulse shaping; 16x16 Gray-coded levels.
#include <Arduino.h>
#include "driver/dac_continuous.h"
#include "esp_chip_info.h"
#include "esp_system.h"

static dac_continuous_handle_t dac = nullptr;

static const uint32_t SAMPLE_RATE_HZ = 160000; // per DAC, ALTER mode
static const size_t   SPS            = 8;      // samples per symbol
static const size_t   BUF_BYTES      = 2048;   // interleaved I/Q bytes
static const size_t   SYMBOLS        = (BUF_BYTES / 2) / SPS;

// 256-QAM: 16 PAM levels {-15,-13,...,+15}, spacing 8 codes => 8..248.
static const int LEVEL_SPACING = 8;
static const uint8_t MIDDLE = 128;

static uint8_t code_for_level(int level) {
  return (uint8_t)(MIDDLE + level * LEVEL_SPACING);
}

// 4-bit Gray code: input treated as Gray symbol value, map to natural PAM index.
static int gray4_level(uint8_t v) {
  static const int levels[16] = {
    -15,-13,-11,-9,-7,-5,-3,-1, 1,3,5,7,9,11,13,15
  };
  static const uint8_t inv_gray[16] = {
    0, 1, 3, 2, 7, 6, 4, 5, 15, 14, 12, 13, 8, 9, 11, 10
  };
  return levels[inv_gray[v & 0xF]];
}

static void gray256qam(uint8_t bits, uint8_t *i_out, uint8_t *q_out) {
  // bits: b7b6b5b4 = I, b3b2b1b0 = Q, each 4-bit group as Gray code.
  *i_out = code_for_level(gray4_level((bits >> 4) & 0xF));
  *q_out = code_for_level(gray4_level(bits & 0xF));
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
    const uint8_t bits = prng_byte(&lfsr);
    uint8_t icode = 0, qcode = 0;
    gray256qam(bits, &icode, &qcode);
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
  Serial.printf("QAM 256 baud=%u sps=%u symbols_in_buffer=%u levels={-15..+15} spacing=%d\n",
                SAMPLE_RATE_HZ / SPS, SPS, SYMBOLS, LEVEL_SPACING);
}

void loop() {
  delay(1000);
}
