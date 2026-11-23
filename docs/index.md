# riglol-QAMviz

ESP32 dual-DAC QAM constellation lab using a Rigol DS1054Z oscilloscope, NanoVNA, and [omariglol](https://github.com/brrrassica/omariglol).

## Overview

This project generates baseband **16-QAM / 64-QAM / 256-QAM** I/Q signals using an ESP32's two internal 8-bit DACs:

- **GPIO25 (DAC1)** - I
- **GPIO26 (DAC2)** - Q

The signals are viewed on a Rigol DS1054Z in X-Y mode as a constellation. The lab is intended to grow into a full HIL workflow with omariglol simultaneous readouts, NanoVNA S21 characterization, and an RF upconversion station.

## Current status

| Area | Status |
|---|---|
| ESP32 ECO1 dual-DAC sine bring-up | Done |
| 16-QAM firmware | Done |
| 64-QAM firmware | Done |
| 256-QAM firmware (PRNG 128-symbol buffer) | Done |
| Rigol X-Y capture workflow | Done (manual/SCPI) |
| Host `qamviz` CLI | Planned |
| omariglol simultaneous readout evidence | Planned |
| NanoVNA S21 / RF station | Planned |
| Live dashboard | Planned |

## Hardware

- **ESP32, Chip Rev >= 1.0** (`esp_chip_info_t.revision >= 100`) - firmware currently guards for rev 100.
- **Rigol DS1054Z** - USBTMC, `1AB1:04CE`.
- **NanoVNA-H USBFix** - USBTMC/SCPI image, planned for VNA/RF stations.
- **Linux host** - `arduino-cli`, ESP32 Arduino core 3.3.12, `riglol`.

## Wiring

| ESP32 pin | Signal | Scope |
|---|---|---|
| GPIO25 | I (DAC1) | CH1 |
| GPIO26 | Q (DAC2) | CH2 |
| GND | Ground | Probe/scope ground |

Use 10x probes if available and set the scope probe ratio accordingly. Keep a solid common ground.

## Firmware

| Sketch | Mode | Rate | Notes |
|---|---|---:|---|
| `firmware/dac-sine` | Sine bring-up | 2.5 kHz, 160 kS/s/ch | Known-good analog reference |
| `firmware/dac-16qam` | 16-QAM | 20 kbaud, 8 sps | 4x4 Gray |
| `firmware/dac-64qam` | 64-QAM | 20 kbaud, 8 sps | 8x8 Gray |
| `firmware/dac-256qam` | 256-QAM | 20 kbaud, 8 sps | 16x16 Gray, PRNG 128 symbols |

Build/flash example:

```bash
arduino-cli compile --fqbn esp32:esp32:esp32 firmware/dac-256qam
arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32 firmware/dac-256qam
```

## Rigol X-Y setup

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

For a crisp still capture:

```bash
$RIG scpi --usb --timeout 10 "$A" ':DISP:CLE'
$RIG scpi --usb --timeout 10 "$A" ':RUN'; sleep 0.5
$RIG scpi --usb --timeout 10 "$A" ':STOP'
$RIG screenshot --usb --timeout 25 --command ':DISP:DATA? ON,OFF,PNG' "$A" /tmp/qam.png
$RIG scpi --usb --timeout 10 "$A" ':RUN'
```

## DAC notes

- Uses modern `driver/dac_continuous.h`.
- In `DAC_CHANNEL_MODE_ALTER`, `freq_hz` is per-channel; default uses `160000` for 160 kS/s per DAC.
- `dac_continuous_write_cyclically()` can load fewer bytes than supplied; `loaded` is authoritative.
- ADC2 self-readback on DAC pins is not valid analog evidence.

## Known issues

- **X-Y smear on DS1054Z**: no frame sync / no true variable persistence; free-running repaint smears. Use DOTS + clear + brief run + STOP for crisp captures.
- **omariglol screenshot corruption**: DS1054Z USBTMC screenshots may have corrupted PNG IDAT/zlib tail; can be salvaged by partial IDAT decompression.
- **`:AUT` stops acquisition**: send `:RUN` after `:AUT`, or use `riglol autoscale`.
- **256-QAM full-coverage buffer rollback**: full 256-symbol cyclic buffer experiment caused display issues; current 256-QAM uses PRNG 128-symbol buffer.

## Repo

Source: [github.com/brrrassica/riglol-QAMviz](https://github.com/brrrassica/riglol-QAMviz)
