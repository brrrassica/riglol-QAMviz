# M2 Capture Runbook (readiness)

## Preflight

```bash
scripts/doctor.sh
PYTHONPATH=host /tmp/opencode/qamviz-venv/bin/python -m qamviz doctor --resource usb:0x1AB1:0x04CE
```

Check:
- ESP32 on `/dev/ttyUSB0` (CP210x) if using `--esp32-port`
- Rigol DS1054Z `usb:0x1AB1:0x04CE` visible in `riglol usb list --json`
- omariglol release gate still applies to M0/M3 completeness; v0.1.9 is investigation-only

## Capture

```bash
PYTHONPATH=host /tmp/opencode/qamviz-venv/bin/python -m qamviz capture \
  --preset lab16qam \
  --resource usb:0x1AB1:0x04CE \
  --esp32-port /dev/ttyUSB0 \
  --out artifacts/run-$(date -u +%Y%m%dT%H%M%SZ)
```

Notes:
- `qamviz capture` runs read-only preflight (`riglol` bin, `usb list`, resource visible). If preflight fails, it writes `session.json` with `status=preflight_failed` and exits `2`. Use `--force` only when you intentionally want to attempt capture anyway.
- Capture prelude sets `:TIM:MODE MAIN` and `:RUN` before `riglol capture`.
- For crisp X-Y scope screenshots, use `:DISP:TYPE DOTS`, `:DISP:CLE`, brief `:RUN`, then `:STOP`. YT mode is required for waveform capture.

## Artifacts

Expected on success: `ch1.npy`, `ch2.npy`, `iq-time.png`, `constellation.png`, `session.json` with config hash, git head, preflight, ESP32 status (optional), sync, and metrics.