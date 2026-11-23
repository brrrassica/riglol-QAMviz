#pragma once
#include <Arduino.h>
#include "qam_config.h"

void ctrl_uart_init(uint32_t baud = 115200);
void ctrl_uart_poll(QamConfig &active, QamConfig &pending, bool &pendingValid);