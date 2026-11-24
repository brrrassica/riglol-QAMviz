# riglol-QAMviz

ESP32 dual-DAC QAM constellation lab using a Rigol DS1054Z oscilloscope, NanoVNA, and [omariglol](https://github.com/brrrassica/omariglol) for instrumentation.

This repo contains the firmware and bench evidence for generating **16-QAM, 64-QAM, and 256-QAM** baseband I/Q signals on an ESP32's two internal 8-bit DACs (GPIO25 = I, GPIO26 = Q) and viewing them on a Rigol DS1054Z in X-Y mode.

> **Status:** early bring-up / lab-in-progress. The firmware sketches and bench evidence are real; the host dashboard, NanoVNA S21 path, RF upconversion station, and omariglol integration described in the planning docs are not all implemented yet.

## What works now

- ESP32 ECO1 (v1.0, `esp_chip_info_t.revision == 100`) dual-DAC bring-up with `driver/dac_continuous.h`.
- `DAC_CHANNEL_MODE_ALTER` cyclic DMA at **160 ksample/s per DAC** (`freq_hz = 160000` in ALTER mode).
- Firmware sketches:
  - [`firmware/dac-sine`](firmware/dac-sine/dac-sine.ino) - 2.5 kHz sine on both DACs, bring-up/reference.
  - [`firmware/dac-16qam`](firmware/dac-16qam/dac-16qam.ino) - 16-QAM, 20 kbaud, 8 sps, 4x4 Gray.
  - [`firmware/dac-64qam`](firmware/dac-64qam/dac-64qam.ino) - 64-QAM, 20 kbaud, 8 sps, 8x8 Gray.
  - [`firmware/dac-256qam`](firmware/dac-256qam/dac-256qam.ino) - 256-QAM, 20 kbaud, 8 sps, 16x16 Gray, PRNG symbols.
- Rigol DS1054Z X-Y constellation viewing with `riglol` SCPI/screenshot helpers.
- Bench evidence in [`artifacts/env-report.json`](artifacts/env-report.json).

## Hardware

| Item | Details |
|---|---|
| ESP32 | ESP32 with Chip Rev >= 1.0 (`esp_chip_info_t.revision >= 100`), internal 8-bit DACs, USB-UART |
| Scope | Rigol DS1054Z (or compatible DS1000Z), USBTMC `1AB1:04CE` |
| VNA | NanoVNA-H with [NanoVNAUSBFix](https://github.com/acabtech/NanoVNAUSBFix) USBTMC/SCPI image, `0483:5740` (planned) |
| Host | Linux, `arduino-cli` + ESP32 core 3.3.12, `omariglol`/`riglol` |

The firmware expects ESP32 **Chip Rev >= 1.0** (`esp_chip_info_t.revision >= 100`). Current sketches guard for revision `100`; adjust the guard only if you have validated another compatible revision.

## Wiring

| ESP32 pin | Signal | Scope |
|---|---|---|
| GPIO25 | DAC1 / I | CH1 |
| GPIO26 | DAC2 / Q | CH2 |
| GND | Common ground | Probe ground / scope ground |

Use 10x probes if available. Set probe ratio on the scope to match the physical probe. Keep a common ground between ESP32 and scope.

## Quick start

### 1. Build and flash firmware

```bash
# From repo root
arduino-cli compile --fqbn esp32:esp32:esp32 firmware/dac-256qam
arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32 firmware/dac-256qam
```

Verify boot log over serial (115200):

```text
CHIP model=1 rev=100 cores=2
NEW_CHANNELS ESP_OK
REGISTER_CB ESP_OK
ENABLE ESP_OK
WRITE_CYCLIC ESP_OK loaded=1920 of 2048
QAM 256 baud=20000 sps=8 symbols_in_buffer=128 levels={-15..+15} spacing=8
```

### 2. Configure Rigol DS1054Z for X-Y

Using `riglol` (from omariglol):

```bash
RIG=/path/to/riglol
A='usb:0x1AB1:0x04CE'

$RIG scpi --usb --timeout 10 "$A" ':TIM:MODE XY'
$RIG scpi --usb --timeout 10 "$A" ':CHAN1:DISP 1'
$RIG scpi --usb --timeout 10 "$A" ':CHAN2:DISP 1'
$RIG scpi --usb --timeout 10 "$A" ':CHAN1:SCAL 0.5'
$RIG scpi --usb --timeout 10 "$A" ':CHAN2:SCAL 0.5'
$RIG scpi --usb --timeout 10 "$A" ':CHAN1:OFFS -1.65'
$RIG scpi --usb --timeout 10 "$A" ':CHAN2:OFFS -1.65'
$RIG scpi --usb --timeout 10 "$A" ':DISP:TYPE DOTS'
$RIG scpi --usb --timeout 10 "$A" ':ACQ:TYPE NORM'
$RIG scpi --usb --timeout 10 "$A" ':DISP:CLE'
$RIG scpi --usb --timeout 10 "$A" ':RUN'
```

For a still capture, **grab the screenshot while the scope is running** — do **not** press STOP first:

```bash
$RIG scpi --usb --timeout 10 "$A" ':DISP:CLE'
$RIG scpi --usb --timeout 10 "$A" ':RUN'
sleep 5   # let the constellation paint
$RIG scpi --usb --timeout 10 --hex "$A" ':DISP:DATA? ON,OFF' > /tmp/qam.hex
# decode the IEEE BMP block to PNG (see host/qamviz helpers)
```

> **Important (DS1054Z X-Y quirk):** pressing STOP in X-Y mode collapses the display to the
> points of the last acquisition — the accumulated constellation vanishes (verified repeatedly:
> STOP always leaves a single dot group). X-Y has no frame sync and no true variable persistence,
> so there is nothing to freeze. `:DISP:DATA?` returns a BMP snapshot of the *live* display,
> which is why captures must be taken while the scope is still running. This supersedes the
> earlier "clear then stop" advice.

## Signal model

| Mode | Levels/axis | Bits/symbol | Normalization | Default rate |
|---|---:|---:|---|---|
| 16-QAM | 4 | 4 | `1/sqrt(10)` | 20 kbaud, 8 sps |
| 64-QAM | 8 | 6 | `1/sqrt(42)` | 20 kbaud, 8 sps |
| 256-QAM | 16 | 8 | DAC code spacing 8 | 20 kbaud, 8 sps |

DAC code mapping:

```c
code = clamp(round(128 + gain * 127 * sample), 0, 255)
```

256-QAM currently uses a direct 16-level PAM mapping with `LEVEL_SPACING=8`, codes `8..248`.

## Important DAC notes

- Use `driver/dac_continuous.h`, not legacy I2S DAC mode.
- In `DAC_CHANNEL_MODE_ALTER`, `freq_hz` is **per-channel**. For 160 ksample/s per DAC, set `freq_hz = 160000`.
- `dac_continuous_write_cyclically()` may load fewer bytes than supplied; treat `loaded` as authoritative.
- ADC2 self-readback on DAC pins is **not** valid evidence. Use the scope for analog verification.

## Known issues / observations

- **DS1054Z X-Y smear**: X-Y has no frame sync and no true variable persistence. Free-running DAC repainting causes blur/smear. Use `DOTS`, `:DISP:CLE`, brief `:RUN`, then grab the screenshot **while still running** — pressing STOP collapses the X-Y display to one acquisition's points (single dot group).
- **omariglol USBTMC screenshot corruption**: `riglol screenshot --usb` on DS1054Z can produce PNGs with corrupted IDAT/zlib tail; salvage by decompressing partial IDAT and rewriting PNG chunks.
- **`riglol scpi --usb ':AUT'`** leaves DS1054Z stopped; follow with `:RUN` or use `riglol autoscale`.
- **256-QAM full-coverage buffer**: a 256-symbol full-coverage cyclic buffer experiment caused display issues and was rolled back; current 256-QAM uses a PRNG 128-symbol buffer.
- **ECO0 unsupported**: ECO0/v0.0 has known errata relevant to timing/DMA; this lab is ECO1-only.

## Repo layout

```text
firmware/
  dac-sine/      # dual-DAC sine bring-up
  dac-16qam/     # 16-QAM generator
  dac-64qam/     # 64-QAM generator
  dac-256qam/    # 256-QAM generator
artifacts/
  env-report.json
docs/            # GitHub Pages site
plans/           # gitignored local planning notes
```

## Roadmap

- [ ] Host capture + constellation/EVM CLI (`qamviz`)
- [ ] omariglol simultaneous scope+VNA readout evidence
- [ ] NanoVNA S21 passive filter characterization
- [ ] Live local dashboard (constellation, EVM, I/Q/eye, VNA)
- [ ] IQ-mixer RF upconversion station
- [ ] Reproducible experiment docs and acceptance report

## License

MIT. See [LICENSE](LICENSE).
