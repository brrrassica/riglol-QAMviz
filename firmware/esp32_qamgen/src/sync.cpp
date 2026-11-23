#include "sync.h"

static uint8_t g_sync_pin = 27;

void sync_init(uint8_t pin) {
  g_sync_pin = pin;
  pinMode(g_sync_pin, OUTPUT);
  digitalWrite(g_sync_pin, LOW);
}

void sync_pulse_frame_start() {
  digitalWrite(g_sync_pin, HIGH);
  delayMicroseconds(10);
  digitalWrite(g_sync_pin, LOW);
}