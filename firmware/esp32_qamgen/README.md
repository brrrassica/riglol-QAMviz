# esp32_qamgen (M1 MVP)

ESP32 dual-DAC I/Q generator firmware for riglol-QAMviz.

## Status

M1 MVP scaffold/smoke-tested. Not all M1 exit criteria are complete.

## Features

- **ECO1 guard**: refuses to run if `esp_chip_info_t.revision != 100`.
- **DAC output**: `driver/dac_continuous.h`, `DAC_CHANNEL_MASK_ALL`, `DAC_CHANNEL_MODE_ALTER`, cyclic DMA.
- **Default preset**: 16-QAM, 20 kbaud, 8 sps, 160 kS/s per DAC, gain 0.8, seed 42.
- **Frame sync**: GPIO27 pulse on start/frame event.
- **USB CDC JSON control** (newline-delimited):

```json
{"cmd":"configure","modulation":"qam16","symbol_rate":20000,"sps":8,"gain":0.8,"shape":"rect","seed":42}
{"cmd":"start"}
{"cmd":"stop"}
{"cmd":"restart"}
{"cmd":"status"}
```

`configure` stores a pending config; it is applied on `start` or `restart`.

## Build / upload

```bash
arduino-cli compile --fqbn esp32:esp32:esp32 firmware/esp32_qamgen
arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32 firmware/esp32_qamgen
```

## Smoke test (observed)

```text
{"ok":true,"cmd":"boot","chip_model":1,"revision":100,"cores":2}
{"ok":true,"cmd":"autostart","modulation":"qam16","symbol_rate":20000,"sps":8,"sample_rate":160000,"loaded":1920}
{"ok":true,"cmd":"status",...,"streaming":true,"gain":0.800,"seed":42,"frames":1,"loaded":1920,...}
{"ok":true,"cmd":"configure","msg":"pending config stored; apply with start/restart"}
{"ok":true,"cmd":"status",...,"gain":0.700,"seed":7,"frames":2,...}
```