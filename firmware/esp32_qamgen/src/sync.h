#pragma once
#include <Arduino.h>

void sync_init(uint8_t pin = 27);
void sync_pulse_frame_start();
void sync_pulse_frame_start_isr();