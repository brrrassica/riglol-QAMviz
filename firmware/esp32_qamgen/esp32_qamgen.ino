#include <Arduino.h>
#include "src/qam_config.h"
#include "src/dac_output.h"
#include "src/sync.h"
#include "src/ctrl_uart.h"
#include "esp_chip_info.h"

static QamConfig g_active = default_qam_config();
static QamConfig g_pending = default_qam_config();
static bool g_pendingValid = false;

void setup() {
  ctrl_uart_init(115200);
  delay(200);
  sync_init(27);

  esp_chip_info_t info;
  esp_chip_info(&info);
  Serial.printf("{\"ok\":true,\"cmd\":\"boot\",\"chip_model\":%d,\"revision\":%d,\"cores\":%d}\n",
                info.model, info.revision, info.cores);
  if (info.revision != 100) {
    Serial.printf("{\"ok\":false,\"cmd\":\"boot\",\"error\":\"Chip Rev guard: expected revision 100, got %d\"}\n", info.revision);
    return;
  }

  // Auto-start default config for bench bring-up.
  if (dac_output_start(g_active)) {
    DacStatus st = dac_output_status();
    Serial.printf("{\"ok\":true,\"cmd\":\"autostart\",\"modulation\":\"%s\",\"symbol_rate\":%u,\"sps\":%u,\"sample_rate\":%u,\"loaded\":%u}\n",
                  g_active.modulation, g_active.symbol_rate, g_active.sps, st.sample_rate, (unsigned)st.loaded_bytes);
  } else {
    Serial.printf("{\"ok\":false,\"cmd\":\"autostart\",\"error\":\"%s\"}\n", dac_output_last_error());
  }
}

void loop() {
  ctrl_uart_poll(g_active, g_pending, g_pendingValid);
  delay(5);
}