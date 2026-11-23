# 04 — Simultaneous Readout (omariglol)

**Status:** stub/scaffold (blocked by omariglol release gate + instruments)  
**Depends on:** M0 release gate, M2, M3, Rigol + NanoVNA attached

## Goal

Prove omariglol performs genuine concurrent instrumentation readouts (`riglol measure --json` fan-out), not serial convenience wrappers.

## Prerequisites

- Tagged omariglol release containing `f1cb86f` (32 MiB receive cap). Do not pin untagged `origin/develop`.
- Rigol DS1054Z and NanoVNAUSBFix attached and identified by `riglol usb list --json`.

## Procedure

1. Create workspace: `riglol workspace create "ESP32 QAM Lab"` and bind instruments.
2. Run A/B script:

```bash
python3 scripts/m3_ab_readout.py --workspace "ESP32 QAM Lab" \
  --scope-resource usb:0x1AB1:0x04CE --vna-resource usb:0x0483:0x5740 \
  --out artifacts/ab-readout.md
```

3. Confirm `overall_elapsed_ms` ≈ max(per-instrument), not sum.
4. Capture concurrent scope capture + VNA read + `riglol measure --json` evidence.

## Expected observations

- Parallel measure overall time near max instrument time.
- Per-instrument rows include command, value/error, elapsed_ms.
- NanoVNA may appear as liveness `*IDN?` row if default measurement is not VNA-specific.

## Artifacts

- `artifacts/ab-readout.md`
- `artifacts/run01/measure.json` / `qamviz.measure-evidence/0.1` payload
