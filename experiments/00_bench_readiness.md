# 00 — Bench Readiness

Status: **M0 partially complete; release gate blocked**

This note captures the stable bench-readiness facts for the current riglol-QAMviz bring-up. It is intentionally self-contained so the gitignored `plans/` directory is not required.

## Release gate

M0 cannot be marked complete until a **tagged omariglol release containing `f1cb86f`** is available. `v0.1.9` is investigation-only; do not pin to an untagged branch.

Check:

```bash
cd ~/projects/omariglol
git fetch --all --tags
git tag --contains f1cb86f
```

## Hardware baseline

- **ESP32, Chip Rev >= 1.0** (`esp_chip_info_t.revision >= 100`). Current sketches guard for revision `100`.
- **Rigol DS1054Z** (DS1000Z family), USBTMC `1AB1:04CE`.
- **NanoVNA-H with NanoVNAUSBFix USBTMC/SCPI image**, USB `0483:5740` (optional for later milestones).
- **Common ground** between ESP32 and scope.

## Wiring

| ESP32 pin | Signal | Scope |
|---|---|---|
| GPIO25 | DAC1 / I | CH1 |
| GPIO26 | DAC2 / Q | CH2 |
| GND | Ground | Probe ground |

If using 10x probes, set the scope probe ratio to match the physical probe.

## Read-only doctor check

```bash
./scripts/doctor.sh
# or
RIGLOL_BIN=/path/to/riglol ./scripts/doctor.sh
```

The script checks USB IDs, `riglol --version`, and `riglol usb list --json`. It does not modify devices.

## Quick X-Y scope setup

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

## Crisp capture pattern

DS1054Z X-Y has no frame sync and no true variable persistence; free-running repaint smears. For a still capture:

```bash
$RIG scpi --usb --timeout 10 "$A" ':DISP:CLE'
$RIG scpi --usb --timeout 10 "$A" ':RUN'; sleep 0.5
$RIG scpi --usb --timeout 10 "$A" ':STOP'
$RIG screenshot --usb --timeout 25 --command ':DISP:DATA? ON,OFF,PNG' "$A" /tmp/qam.png
$RIG scpi --usb --timeout 10 "$A" ':RUN'
```

## Known caveats

- **`:AUT` can leave DS1054Z stopped.** Follow `:AUT` with `:RUN`, or use `riglol autoscale`.
- **USBTMC screenshot corruption.** `riglol screenshot --usb` can produce PNGs with corrupted IDAT/zlib tail on DS1054Z; salvage by partial IDAT decompression if needed.
- **DAC evidence.** ADC2 self-readback on DAC pins is not valid analog evidence; use scope measurements.
- **DAC ALTER rate.** In `DAC_CHANNEL_MODE_ALTER`, `freq_hz` is per-channel. For 160 kS/s per DAC, use `freq_hz = 160000`.
- **Loaded bytes.** `dac_continuous_write_cyclically()` may load fewer bytes than supplied; treat `loaded` as authoritative.