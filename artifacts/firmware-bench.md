# Firmware bench — esp32_qamgen (M1 closeout)

Date: 2026-11-23  
Firmware: `firmware/esp32_qamgen`  
Board: ESP32-D0WDQ6, ECO1 `esp_chip_info_t.revision==100`, `/dev/ttyUSB0` (CP210x `10c4:ea60`)

## Build / flash

- `arduino-cli compile --fqbn esp32:esp32:esp32 firmware/esp32_qamgen` — **pass**
- Sketch: 295344 bytes (22%) program, 24428 bytes (7%) dynamic memory
- `arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32 ...` — **pass**

## Smoke test (USB CDC JSON, 115200)

Observed after upload/reset:

```json
{"ok":true,"cmd":"status","streaming":true,"symbol_rate":20000,"sps":8,"sample_rate":160000,"gain":0.800,"modulation":"qam16","shape":"rect","seed":42,"frames":1,"loaded":1920,"buf_bytes":2048,"config_hash":"ad370bbd","dma_done":6841,"dma_stop":0,"uptime_s":5.38,"last_error":"ok"}
```

Second status ~1.4s later: `dma_done=8712` (incrementing), `dma_stop=0`.

Selftest:

```json
{"ok":true,"cmd":"selftest","detail":"q16_00=32,32 q16_ff=160,160 q64_00=18,18 q64_3f=175,175 prbs=020C ok=true"}
```

64-QAM configure/restart:

```json
{"ok":true,"cmd":"configure","msg":"pending config stored; apply with start/restart"}
{"ok":true,"cmd":"status","streaming":true,"symbol_rate":20000,"sps":8,"sample_rate":160000,"gain":0.800,"modulation":"qam64","shape":"rect","seed":42,"frames":2,"loaded":1920,"buf_bytes":2048,"config_hash":"bfda8ad2","dma_done":0,"dma_stop":0,"uptime_s":7.99,"last_error":"ok"}
```

Post-restart status: `dma_done` incrementing, `dma_stop=0`.

## What this verifies

- ECO1 rev 100 guard passes on target hardware.
- Dual-DAC cyclic DMA starts with `DAC_CHANNEL_MASK_ALL`, `DAC_CHANNEL_MODE_ALTER`, `freq_hz=160000` (per-channel), `loaded=1920/2048`.
- 16-QAM and 64-QAM configure/restart paths work; `config_hash` changes with config.
- PRBS7 deterministic first-4 nibbles for seed 0x7f: `0,2,0,C`.
- 16-QAM and 64-QAM known mapper vectors pass selftest.
- DMA convert-done callback fires (heartbeat counter increments); no DMA stop events observed.

## Frame sync (M1 closeout)

- GPIO27 pulse on start/restart (`sync_pulse_frame_start`).
- Best-effort logical 1024-symbol frame pulse from DAC continuous `on_convert_done` ISR callback. Callback granularity is per DMA descriptor (`desc_num=8`); pulse interval is scaled by `bufs_per_frame * desc_num`.
- **Limitation**: cyclic DMA has no sample-exact frame-boundary interrupt tied to symbol index inside the loop; pulse is phase-aligned to DMA descriptor callbacks, not a guaranteed DAC sample edge. Validate phase/alignment on scope before using as a hard trigger.

## Live analog validation (2026-11-23, Rigol DS1054Z DS1ZA203012565)

- Scope IDN: `RIGOL TECHNOLOGIES,DS1054Z,DS1ZA203012565,00.04.04.SP4`
- X-Y capture: `artifacts/m1-analog/xy-dots.png` (DOTS, XY mode, CH1/CH2 offsets set to -1.65V for centering, then scope restored to MAIN/VECT with original offsets). Visual cluster count/compactness should be confirmed by operator from screenshot.
- Live M2 capture (`artifacts/m2-live-run1/session.json`): `qam16 20k/8sps/160kS/s seed=42`, preflight ok, ESP32 status ok. Metrics: `EVM 24.40%`, `SNR_est 12.25 dB`, `n=150`, `sync=blind` (sequence corr score 0.383 < 0.6; SER invalid). This confirms end-to-end analog capture path, but EVM/sync quality needs improvement.

## X-Y display quality findings (2026-11-23, live scope)

- 16-QAM structure (4x4 rows/clusters) is visible in X-Y, but each cluster shows a comet-trail smear with a consistent drift direction; shortening the paint window (2 s → 0.15 s) does not remove it, so it is not slow thermal drift of the whole frame.
- YT inspection (20 µs/div, 500 mV/div) shows clean flat symbol levels with overshoot/ringing at each transition — edge ringing, not level instability.
- Suspected smear causes, to check in order: (1) probe compensation / long ground leads (ringing at edges smears dots), (2) USB VBus ripple on ESP32 3V3 reference (moves both DAC axes coherently — matches diagonal comet direction), (3) DS1054Z X-Y raster scan skew while painting.
- `:DISP:TYPE DOTS` is honored in X-Y but transition traces are still drawn; DS1054Z X-Y has no way to suppress inter-sample vectors.
- "Function Limited!" toast appears if `:ACQ:MODE` is changed while in X-Y; set `:ACQ:MODE SAMple` before `:TIM:MODE XY`. Channel offsets can reset when leaving/entering X-Y — re-verify `:CHANn:OFFS` after mode switches.
- `riglol screenshot --usb` reliably produces corrupted PNG IDAT streams on this unit/FW; use `:DISP:DATA?` (IEEE BMP block) instead.

## Supply noise characterization (2026-11-23, live scope, Measure-All)

- 5V VBUS (CH1, AC, 10X): Vpp 1.0–1.2 V, Vrms ~423–489 mV; 3V3 rail (CH2, AC, 10X): Vpp 868 mV, Vrms ~303 mV. Both show a dominant **50.0 kHz** switching-ripple component (scope counter; npy FFT agrees within alias limits, `artifacts/m1-analog/supply/`).
- ESP32 DAC output tracks VDD3P3 as reference, so ~0.87 Vpp of 3V3 ripple directly scales/moves the constellation (~±0.29 V on a ~1.5 Vpp signal). This is consistent with the X-Y comet smear and the 24% EVM on live captures.
- Verdict: current supply **will** create problems. Mitigation order: different USB port/cable or powered hub → bulk 470 µF + 10 µF/100 nF at 3V3/VIN → external clean 5 V into the 5V pin. Re-measure rails and re-run X-Y/EVM after mitigation.
- **Mitigation applied (Invzi power brick, 2026-11-23):** rails now ~20 mVpp both channels (fast norm capture, 20 µs/div, `artifacts/m1-analog/supply-invzi/`) — ~40x reduction, no 50 kHz component. X-Y re-capture (`artifacts/m1-analog/xy-invzi.png`) shows all 16 clusters, tighter than the USB-supply run. Ferrite beads ruled out earlier: irrelevant at 50 kHz.

## Pending / not verified in this pass

- Operator confirmation of 16 compact clusters in `artifacts/m1-analog/xy-dots.png` — structure visible but comet-smeared (see X-Y display quality findings above).
- Measured symbol rate within 1% on analog capture (firmware/DMA reports 160kS/s; scope-side symbol-rate measurement not recorded).
- DAC level linearity/endpoints with scope/DMM.
- RRC analog validation, underrun stress test, long-run stability.
