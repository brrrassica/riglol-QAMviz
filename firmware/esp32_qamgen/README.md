# esp32_qamgen (M1 MVP)

ESP32 dual-DAC I/Q generator firmware for riglol-QAMviz.

## Status

M1 MVP/hardening pass. Not all M1 exit criteria are complete.

## Features

- **ECO1 guard**: refuses to run if `esp_chip_info_t.revision != 100`.
- **DAC output**: `driver/dac_continuous.h`, `DAC_CHANNEL_MASK_ALL`, `DAC_CHANNEL_MODE_ALTER`, cyclic DMA.
- **Modulations**: 16-QAM and 64-QAM (Gray-coded), rectangular shaping.
- **Default preset**: 16-QAM, 20 kbaud, 8 sps, 160 kS/s per DAC, gain 0.8, seed 42.
- **PRBS7**: deterministic data-bit source seeded by config.
- **Training burst**: deterministic 32-symbol training pattern every 1024 symbols.
- **Frame sync**: GPIO27 pulse on start/restart.
- **USB CDC JSON control** (newline-delimited):

```json
{"cmd":"configure","modulation":"qam16","symbol_rate":20000,"sps":8,"gain":0.8,"shape":"rect","seed":42}
{"cmd":"start"}
{"cmd":"stop"}
{"cmd":"restart"}
{"cmd":"status"}
{"cmd":"selftest"}
```

`configure` stores a pending config; it is applied on `start` or `restart`. `status` includes `config_hash`.

## Build / upload

```bash
arduino-cli compile --fqbn esp32:esp32:esp32 firmware/esp32_qamgen
arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32 firmware/esp32_qamgen
```

## Smoke test (observed)

```text
{"ok":true,"cmd":"boot","chip_model":1,"revision":100,"cores":2}
{"ok":true,"cmd":"autostart","modulation":"qam16","symbol_rate":20000,"sps":8,"sample_rate":160000,"loaded":1920}
{"ok":true,"cmd":"status",...,"modulation":"qam16","config_hash":"ad370bbd",...}
{"ok":true,"cmd":"selftest","detail":"qam16_00=32,32 qam16_ff=160,160 prbs=0 ok=true"}
{"ok":true,"cmd":"configure","msg":"pending config stored; apply with start/restart"}
{"ok":true,"cmd":"status",...,"modulation":"qam64","config_hash":"bfda8ad2","frames":2,...}
```