// ESP32 dual-DAC sine generator for riglol-QAMviz Rigol bring-up.
// GPIO25 (DAC1) = I, GPIO26 (DAC2) = Q, 160 ksample/s each, ALTER-mode cyclic DMA.
#include <Arduino.h>
#include <math.h>
#include "driver/dac_continuous.h"
#include "esp_chip_info.h"
#include "esp_system.h"

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

static dac_continuous_handle_t dac = nullptr;
static volatile uint32_t converted_bytes = 0;

static bool IRAM_ATTR on_convert(dac_continuous_handle_t h,
                                 const dac_event_data_t *e, void *ud) {
  converted_bytes += e->write_bytes;   // 8-bit mode: bytes == conversions
  return false;
}

static const size_t SINE_PERIOD = 64;   // samples per DAC per cycle
static const size_t BUF_BYTES   = 2048; // interleaved I/Q bytes

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
  cfg.freq_hz    = 160000;                 // 160 ksample/s per DAC
  cfg.offset     = 0;
  cfg.clk_src    = DAC_DIGI_CLK_SRC_DEFAULT;
  cfg.chan_mode  = DAC_CHANNEL_MODE_ALTER;  // I,Q,I,Q,... interleaved

  esp_err_t e = dac_continuous_new_channels(&cfg, &dac);
  Serial.printf("NEW_CHANNELS %s\n", esp_err_to_name(e));
  if (e != ESP_OK) return;

  dac_event_callbacks_t cbs = {};
  cbs.on_convert_done = on_convert;
  e = dac_continuous_register_event_callback(dac, &cbs, nullptr);
  Serial.printf("REGISTER_CB %s\n", esp_err_to_name(e));
  if (e != ESP_OK) return;

  static uint8_t buf[BUF_BYTES];
  for (size_t i = 0; i < BUF_BYTES; ++i) {
    const size_t n = i / 2;                // per-DAC sample index
    const double phase = 2.0 * M_PI * (n % SINE_PERIOD) / SINE_PERIOD;
    buf[i] = (uint8_t)lrint(128.0 + 100.0 * sin(phase));
  }

  e = dac_continuous_enable(dac);
  Serial.printf("ENABLE %s\n", esp_err_to_name(e));
  if (e != ESP_OK) return;

  size_t loaded = 0;
  e = dac_continuous_write_cyclically(dac, buf, sizeof(buf), &loaded);
  Serial.printf("WRITE_CYCLIC %s loaded=%u of %u\n",
                esp_err_to_name(e), loaded, sizeof(buf));
  Serial.printf("SINE per_dac_hz=%u period_samples=%u cycles_in_buffer=%u\n",
                160000 / SINE_PERIOD, SINE_PERIOD,
                (unsigned)(loaded / (2 * SINE_PERIOD)));
}

void loop() {
  static uint32_t last_ms = 0;
  static uint32_t last_bytes = 0;
  const uint32_t now = millis();
  if (now - last_ms >= 2000) {
    const uint32_t b = converted_bytes;
    const uint32_t db = b - last_bytes;
    const uint32_t dt = now - last_ms;
    const uint32_t conv_s = (uint32_t)(((uint64_t)db * 1000) / dt / 2);
    Serial.printf("RATE conv_per_s=%u per_dac=%u\n", conv_s, conv_s / 2);
    last_bytes = b;
    last_ms = now;
  }
}
