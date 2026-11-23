#pragma once
#include <Arduino.h>
#include "qam_config.h"

struct DacStatus {
  bool streaming;
  uint32_t sample_rate;
  uint32_t frames_emitted;
  size_t loaded_bytes;
  size_t buf_bytes;
  uint32_t config_hash;
  uint32_t dma_convert_done_count;
  uint32_t dma_stop_count;
};

bool dac_output_init();
bool dac_output_start(const QamConfig &cfg);
void dac_output_stop();
DacStatus dac_output_status();
const char *dac_output_last_error();