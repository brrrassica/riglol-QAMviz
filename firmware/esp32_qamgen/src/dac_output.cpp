#include "dac_output.h"
#include "qam_mapper.h"
#include "sync.h"
#include "prbs.h"
#include "driver/dac_continuous.h"
#include "esp_chip_info.h"
#include <Arduino.h>
#include <string.h>

static dac_continuous_handle_t g_dac = nullptr;
static bool g_streaming = false;
static uint32_t g_frames = 0;
static size_t g_loaded = 0;
static size_t g_buf_bytes = 0;
static uint32_t g_sample_rate = 0;
static uint32_t g_cfg_hash = 0;
static char g_last_error[64] = "ok";
static uint8_t g_buf[2048];
static volatile uint32_t g_dma_convert_done_count = 0;
static volatile uint32_t g_dma_stop_count = 0;
static volatile uint32_t g_frame_pulse_every = 64; // default: 1024-symbol frame / 128-symbol buffer * 8 desc callbacks

static bool IRAM_ATTR on_dac_convert_done(dac_continuous_handle_t, const dac_event_data_t *, void *) {
  uint32_t n = ++g_dma_convert_done_count;
  uint32_t every = g_frame_pulse_every;
  if (every == 0) every = 1;
  // Best-effort logical frame marker. Callback rate is per DMA descriptor;
  // every is scaled so pulse targets 1024-symbol frame boundaries.
  if ((n % every) == 0) {
    sync_pulse_frame_start_isr();
  }
  return false;
}

static bool IRAM_ATTR on_dac_stop(dac_continuous_handle_t, const dac_event_data_t *, void *) {
  g_dma_stop_count++;
  return false;
}

static void set_err(const char *msg) { strlcpy(g_last_error, msg, sizeof(g_last_error)); }

static uint32_t cfg_hash(const QamConfig &cfg) {
  uint32_t h = 2166136261u;
  const uint8_t *p = (const uint8_t *)&cfg;
  for (size_t i = 0; i < sizeof(QamConfig); ++i) { h ^= p[i]; h *= 16777619u; }
  return h;
}

bool dac_output_init() {
  esp_chip_info_t info;
  esp_chip_info(&info);
  if (info.revision != 100) {
    set_err("not ECO1 rev100");
    return false;
  }
  set_err("ok");
  return true;
}

static bool build_buffer(const QamConfig &cfg) {
  const uint32_t sps = cfg.sps ? cfg.sps : 8;
  const size_t symbols = (sizeof(g_buf) / 2) / sps;
  g_buf_bytes = symbols * sps * 2;
  Prbs7 prbs((uint8_t)(cfg.seed ? (cfg.seed & 0x7F) : 0x7F));
  for (size_t s = 0; s < symbols; ++s) {
    IqCode c = symbol_to_codes(cfg, (uint16_t)s, prbs);
    for (uint32_t k = 0; k < sps; ++k) {
      size_t idx = (s * sps + k) * 2;
      g_buf[idx + 0] = c.i;
      g_buf[idx + 1] = c.q;
    }
  }
  return true;
}

bool dac_output_start(const QamConfig &cfg) {
  dac_output_stop();
  if (!dac_output_init()) return false;
  if (!build_buffer(cfg)) { set_err("buffer build failed"); return false; }

  g_sample_rate = cfg.symbol_rate * cfg.sps;
  g_cfg_hash = cfg_hash(cfg);
  g_dma_convert_done_count = 0;
  g_dma_stop_count = 0;
  {
    const uint32_t sps = cfg.sps ? cfg.sps : 8;
    const uint32_t symbols_per_buf = (uint32_t)((sizeof(g_buf) / 2) / sps);
    const uint32_t bufs_per_frame = (symbols_per_buf > 0 && (1024 % symbols_per_buf) == 0) ? (1024 / symbols_per_buf) : 1;
    // on_convert_done fires per DMA descriptor; desc_num=8.
    g_frame_pulse_every = bufs_per_frame * 8;
  }
  dac_continuous_config_t dcfg = {};
  dcfg.chan_mask = DAC_CHANNEL_MASK_ALL;
  dcfg.desc_num = 8;
  dcfg.buf_size = 512;
  dcfg.freq_hz = g_sample_rate; // per-channel in ALTER mode
  dcfg.offset = 0;
  dcfg.clk_src = DAC_DIGI_CLK_SRC_DEFAULT;
  dcfg.chan_mode = DAC_CHANNEL_MODE_ALTER;

  esp_err_t e = dac_continuous_new_channels(&dcfg, &g_dac);
  if (e != ESP_OK) { set_err("new_channels failed"); return false; }

  dac_event_callbacks_t cbs = {};
  cbs.on_convert_done = on_dac_convert_done;
  cbs.on_stop = on_dac_stop;
  e = dac_continuous_register_event_callback(g_dac, &cbs, nullptr);
  if (e != ESP_OK) {
    set_err("register_event_callback failed");
    dac_continuous_del_channels(g_dac);
    g_dac = nullptr;
    return false;
  }

  e = dac_continuous_enable(g_dac);
  if (e != ESP_OK) { set_err("enable failed"); dac_continuous_del_channels(g_dac); g_dac=nullptr; return false; }
  g_loaded = 0;
  e = dac_continuous_write_cyclically(g_dac, g_buf, g_buf_bytes, &g_loaded);
  if (e != ESP_OK) { set_err("write_cyclically failed"); dac_output_stop(); return false; }
  g_streaming = true;
  g_frames++;
  sync_pulse_frame_start();
  set_err("ok");
  return true;
}

void dac_output_stop() {
  if (g_dac) {
    dac_continuous_disable(g_dac);
    dac_continuous_del_channels(g_dac);
    g_dac = nullptr;
  }
  g_streaming = false;
}

DacStatus dac_output_status() {
  DacStatus s = {};
  s.streaming = g_streaming;
  s.sample_rate = g_sample_rate;
  s.frames_emitted = g_frames;
  s.loaded_bytes = g_loaded;
  s.buf_bytes = g_buf_bytes;
  s.config_hash = g_cfg_hash;
  s.dma_convert_done_count = g_dma_convert_done_count;
  s.dma_stop_count = g_dma_stop_count;
  return s;
}

const char *dac_output_last_error() { return g_last_error; }