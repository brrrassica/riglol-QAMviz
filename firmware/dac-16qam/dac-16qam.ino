// ESP32 dual-DAC 16-QAM generator for riglol-QAMviz.
// GPIO25 (DAC1) = I, GPIO26 (DAC2) = Q.
// Default preset: 20 kbaud at 8 samples/symbol => 160 ksample/s per DAC.
// Rectangular (no) pulse shaping; RRC beta=0.35 is a selectable follow-up.
#include <Arduino.h>
#include "driver/dac_continuous.h"
#include "esp_chip_info.h"
#include "esp_system.h"

static dac_continuous_handle_t dac = nullptr;

// --- Preset -------------------------------------------------------------
static const uint32_t SAMPLE_RATE_HZ = 160000; // per DAC, ALTER mode
static const size_t   SPS            = 8;      // samples per symbol
static const size_t   BUF_BYTES      = 2048;   // interleaved I/Q bytes
static const size_t   SYMBOLS        = (BUF_BYTES / 2) / SPS;

// 16-QAM levels {-3,-1,+1,+3} scaled to fit the 0..255 DAC code range.
static const int LEVELS[4] = {-3, -1, 1, 3};
static const int LEVEL_SPACING = 20;          // codes between adjacent levels
static const uint8_t MIDDLE = 128;

static uint8_t code_for_level(int level) {
  return (uint8_t)(MIDDLE + level * LEVEL_SPACING);
}

// Gray-coded 16-QAM map: bits b3b2 -> I level, b1b0 -> Q level (Gray).
static void gray16qam(uint8_t bits, uint8_t *i_out, uint8_t *q_out) {
  static const uint8_t gray[4] = {0, 1, 3, 2};  // -3,-1,+1,+3 in Gray order
  const uint8_t gi = gray[(bits >> 2) & 0x3];
  const uint8_t gq = gray[bits & 0x3];
  *i_out = code_for_level(LEVELS[gi]);
  *q_out = code_for_level(LEVELS[gq]);
}

// Tiny LFSR for a deterministic but non-repeating-looking symbol stream.
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
  // ESP-IDF encodes revision as major*100 + minor; ECO1 / v1.0 == 100.
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
  cfg.chan_mode  = DAC_CHANNEL_MODE_ALTER;   // I,Q,I,Q,... interleaved

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

  // Build the interleaved symbol buffer: rectangular shaping (hold each
  // symbol's I/Q level for SPS samples).
  static uint8_t buf[BUF_BYTES];
  uint16_t lfsr = 0xACE1;
  for (size_t s = 0; s < SYMBOLS; ++s) {
    const uint8_t bits = (uint8_t)(prng_byte(&lfsr) & 0x0F);
    uint8_t icode = 0, qcode = 0;
    gray16qam(bits, &icode, &qcode);
    for (size_t k = 0; k < SPS; ++k) {
      const size_t idx = (s * SPS + k) * 2;
      buf[idx + 0] = icode;   // -> GPIO25
      buf[idx + 1] = qcode;   // -> GPIO26
    }
  }

  size_t loaded = 0;
  e = dac_continuous_write_cyclically(dac, buf, sizeof(buf), &loaded);
  Serial.printf("WRITE_CYCLIC %s loaded=%u of %u\n",
                esp_err_to_name(e), loaded, sizeof(buf));
  Serial.printf("QAM 16 baud=%u sps=%u symbols_in_buffer=%u levels={-3,-1,+1,+3} spacing=%d\n",
                SAMPLE_RATE_HZ / SPS, SPS, SYMBOLS, LEVEL_SPACING);
}

void loop() {
  // Symbol stream is DMA-cyclic; nothing to do.
  delay(1000);
}
