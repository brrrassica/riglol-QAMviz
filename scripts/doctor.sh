#!/usr/bin/env bash
set -euo pipefail

# Read-only bench readiness checks for riglol-QAMviz.
# Does not modify devices, install packages, or require root.

RIGLOL_BIN="${RIGLOL_BIN:-}"
if [[ -z "$RIGLOL_BIN" ]]; then
  if command -v riglol >/dev/null 2>&1; then
    RIGLOL_BIN="$(command -v riglol)"
  elif [[ -x "$HOME/projects/omariglol/bin/riglol" ]]; then
    RIGLOL_BIN="$HOME/projects/omariglol/bin/riglol"
  fi
fi

echo "== riglol-QAMviz doctor =="
echo "date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo

echo "== USB devices (lsusb) =="
if command -v lsusb >/dev/null 2>&1; then
  lsusb | grep -E '1ab1:04ce|0483:5740|10c4:ea60|3923:717b' || echo "no known lab USB IDs found"
else
  echo "lsusb not found"
fi
echo

echo "== riglol =="
if [[ -n "$RIGLOL_BIN" ]]; then
  echo "bin: $RIGLOL_BIN"
  "$RIGLOL_BIN" --version || true
  echo
  echo "== riglol usb list --json =="
  "$RIGLOL_BIN" usb list --json || true
else
  echo "riglol not found; set RIGLOL_BIN=/path/to/riglol"
fi
echo

echo "== Optional instrument identity checks =="
echo "If instruments are attached, run manually:"
echo "  riglol scpi --usb usb:0x1AB1:0x04CE '*IDN?'"
echo "  riglol scpi --usb usb:0x0483:0x5740 '*IDN?'"
echo
echo "== USB permissions =="
echo "If USB access fails, install omariglol/NanoVNAUSBFix udev rules and replug devices. See https://github.com/acabtech/NanoVNAUSBFix"
echo "Do not use sudo for normal captures."
echo
echo "== Release gate =="
echo "M0 remains blocked until a tagged omariglol release contains f1cb86f."
echo "Check: cd ~/projects/omariglol && git fetch --all --tags && git tag --contains f1cb86f"
