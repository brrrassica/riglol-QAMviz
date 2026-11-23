# esp32_qamgen (M1 closeout)

ESP32 dual-DAC I/Q generator firmware for riglol-QAMviz.

## Status

M1 closeout pass. Core MVP features compile/upload/smoke-test on ESP32 ECO1 rev 100. Analog scope validation remains pending when Rigol is connected.

## Features

- **ECO1 guard**: refuses to run if `esp_chip_info_t.revision != 100`.
- **DAC output**: `driver/dac_continuous.h`, `DAC_CHANNEL_MASK_ALL`, `DAC_CHANNEL_MODE_ALTER`, cyclic DMA, `desc_num=8`, `buf_size=512`.
- **Modulations**: 16-QAM and 64-QAM (Gray-coded).
- **Pulse shaping**: rectangular default; RRC `beta=0.35` scaffold (`shape="rrc"`, periodic convolution over cyclic buffer; analog validation pending).
- **Default preset**: 16-QAM, 20 kbaud, 8 sps, 160 kS/s per DAC, gain 0.8, seed 42.
- **PRBS7**: deterministic data-bit source seeded by config (seed 0x7f first nibbles: `0,2,0,C`).
- **Training burst**: deterministic 32-symbol training pattern every 1024 symbols.
- **Frame sync**: GPIO27 pulse on start/restart; best-effort logical 1024-symbol frame pulse from DMA `on_convert_done` callback (scaled by descriptor callback granularity). **Limitation**: not a sample-exact DAC-frame interrupt; validate on scope before hard triggering.
- **Status counters**: `frames` (start/restart count), `dma_done` (DMA convert-done callbacks), `dma_stop` (DMA stop callbacks), `config_hash`.
- **Selftest**: known 16-QAM/64-QAM mapper vectors + PRBS7 determinism/known-sequence check via `{"cmd":"selftest"}`.
- **USB CDC JSON control** (newline-delimited):

```json
{"cmd":"configure","modulation":"qam16","symbol_rate":20000,"sps":8,"gain":0.8,"shape":"rect","seed":42}
{"cmd":"start"}
{"cmd":"stop"}
{"cmd":"restart"}
{"cmd":"status"}
{"cmd":"selftest"}
```

`configure` stores a pending config; it is applied on `start` or `restart`.

## Build / upload

```bash
arduino-cli compile --fqbn esp32:esp32:esp32 firmware/esp32_qamgen
arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32 firmware/esp32_qamgen
```

## Smoke test (observed, 2026-11-23)

```text
{"ok":true,"cmd":"status",...,"modulation":"qam16",...,"dma_done":6841,"dma_stop":0,...}
{"ok":true,"cmd":"selftest","detail":"q16_00=32,32 q16_ff=160,160 q64_00=18,18 q64_3f=175,175 prbs=020C ok=true"}
{"ok":true,"cmd":"configure","msg":"pending config stored; apply with start/restart"}
{"ok":true,"cmd":"status",...,"modulation":"qam64",...,"config_hash":"bfda8ad2","frames":2,"dma_done":0,"dma_stop":0,...}
```

See `artifacts/firmware-bench.md` for details and pending analog validation.