#include "sync.h"
#include "driver/gpio.h"
#include "rom/ets_sys.h"

static uint8_t g_sync_pin = 27;

void sync_init(uint8_t pin) {
  g_sync_pin = pin;
  pinMode(g_sync_pin, OUTPUT);
  digitalWrite(g_sync_pin, LOW);
}

void sync_pulse_frame_start() {
  gpio_set_level((gpio_num_t)g_sync_pin, 1);
  ets_delay_us(10);
  gpio_set_level((gpio_num_t)g_sync_pin, 0);
}

void IRAM_ATTR sync_pulse_frame_start_isr() {
  gpio_set_level((gpio_num_t)g_sync_pin, 1);
  ets_delay_us(10);
  gpio_set_level((gpio_num_t)g_sync_pin, 0);
}