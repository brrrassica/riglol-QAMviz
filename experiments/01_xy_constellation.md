# 01 — X-Y Constellation

**Status:** stub (hardware validation pending)  
**Depends on:** M1 firmware, M2 host capture, Rigol DS1054Z connected

## Goal

Verify 16-QAM/64-QAM I/Q mapping by observing compact constellation clusters in scope X-Y mode and in host-computed constellation plots.

## Setup

- ESP32 `/dev/ttyUSB0` running `firmware/esp32_qamgen`.
- Rigol CH1 = I (GPIO25), CH2 = Q (GPIO26), GND common.
- Scope X-Y mode for live view; YT mode for `qamviz capture`.

## Commands

```bash
# Firmware status
PYTHONPATH=host /tmp/opencode/qamviz-venv/bin/python -m qamviz doctor --resource usb:0x1AB1:0x04CE

# Capture (Rigol must be in YT/MAIN; qamviz pre-capture sets :TIM:MODE MAIN,:RUN)
PYTHONPATH=host /tmp/opencode/qamviz-venv/bin/python -m qamviz capture \
  --preset lab16qam --resource usb:0x1AB1:0x04CE --out artifacts/run-xy-16qam --esp32-port /dev/ttyUSB0
```

## Expected observations

- 16-QAM: 16 compact clusters; EVM target <= 12.5% (M5 acceptance).
- 64-QAM: 64 clusters; EVM target <= 8% (stretch <= 5%).
- If X-Y smears: use `:DISP:TYPE DOTS`, `:DISP:CLE`, brief `:RUN`, then `:STOP` for crisp capture.

## Artifacts

- `artifacts/run-xy-*/session.json`, `ch1.npy`, `ch2.npy`, `constellation.png`, `iq-time.png`
