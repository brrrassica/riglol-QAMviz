# 03 — Bandwidth / ISI

**Status:** stub (hardware validation pending)  
**Depends on:** M1, M2, M4 NanoVNA S21, passive filter fixture

## Goal

Correlate baseband QAM EVM/ISI with passive reconstruction/filter S21 roll-off and group delay.

## Setup

- Passive filter fixture between ESP32 DAC outputs and scope/measurement point as appropriate.
- NanoVNAUSBFix with calibration for quantitative S21.
- Measure fixture with ESP32 disconnected for S21 baseline.

## Procedure

1. Capture NanoVNA S21 (`.s2p`, magnitude/phase) using M4 tooling.
2. Run 16-QAM at 20 kbaud and 50 kbaud (stretch); capture EVM/constellation.
3. Compare rectangular vs RRC (`beta=0.35`) when firmware RRC is available.
4. Overlay EVM vs symbol rate/gain with S21 roll-off; discuss group delay and ISI.

## Notes

- `configs/lab16qam_rrc.json` is a planned preset: host has RRC matched-filter scaffold; firmware RRC shaping is **not yet implemented**.
- 50 kbaud is stretch (`configs/lab50kbaud.json`); verify DAC DMA/sample-rate limits before use.

## Artifacts

- `artifacts/run01/dut.s2p`, `vna-s21.png`
- `artifacts/bw-isi/` capture sessions and comparison notes
