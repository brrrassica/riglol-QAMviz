# 02 — EVM vs Gain

**Status:** stub (hardware validation pending)  
**Depends on:** M1, M2, M5 configs

## Goal

Measure EVM as DAC gain sweeps from 0.4 to 0.9 to identify clipping/nonlinearity onset for 16-QAM and 64-QAM.

## Procedure

1. Start from `configs/lab16qam.json` / `lab64qam.json`.
2. For each gain in `{0.4,0.5,0.6,0.7,0.8,0.9}`:
   - Configure ESP32 gain via CDC JSON `configure` + `restart`.
   - Capture with `qamviz capture`.
   - Record EVM, SNR estimate, symbol count, sync mode.
3. Plot EVM vs gain; mark clipping/nonlinearity onset.

## ESP32 config example

```json
{"cmd":"configure","modulation":"qam16","symbol_rate":20000,"sps":8,"gain":0.7,"shape":"rect","seed":42}
{"cmd":"restart"}
```

## Expected observations

- Low gain: noise/quantization dominates, EVM higher.
- Mid gain (~0.8 default): best tradeoff.
- High gain: DAC/scope clipping and nonlinearity increase EVM.

## Artifacts

- `artifacts/evm-gain/<modulation>/gain-<value>/session.json`
- Summary plot/table (to be added when run)
