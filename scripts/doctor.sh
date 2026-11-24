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
if command -v git >/dev/null 2>&1; then
  echo "git_head: $(git rev-parse --short HEAD 2>/dev/null || echo unknown)"
fi
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

echo "== Host toolchain =="
if command -v arduino-cli >/dev/null 2>&1; then
  arduino-cli version 2>&1 | tail -1 || true
  arduino-cli core list 2>&1 | grep -E 'esp32:esp32|ID' || true
else
  echo "arduino-cli not found"
fi
QAMVIZ_PYTHON_BIN=""
if [[ -n "${QAMVIZ_PYTHON:-}" ]]; then
  if [[ -x "$QAMVIZ_PYTHON" ]]; then
    QAMVIZ_PYTHON_BIN="$QAMVIZ_PYTHON"
  else
    echo "QAMVIZ_PYTHON is set but not executable: $QAMVIZ_PYTHON"
  fi
fi
if [[ -z "$QAMVIZ_PYTHON_BIN" && -n "${VIRTUAL_ENV:-}" && -x "$VIRTUAL_ENV/bin/python" ]]; then
  QAMVIZ_PYTHON_BIN="$VIRTUAL_ENV/bin/python"
fi
if [[ -z "$QAMVIZ_PYTHON_BIN" ]]; then
  for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      QAMVIZ_PYTHON_BIN="$(command -v "$candidate")"
      break
    fi
  done
fi
if [[ -n "$QAMVIZ_PYTHON_BIN" ]]; then
  echo "python: $QAMVIZ_PYTHON_BIN"
  "$QAMVIZ_PYTHON_BIN" --version 2>&1 || true
  "$QAMVIZ_PYTHON_BIN" -c "import numpy,matplotlib,serial,fastapi,uvicorn; print('qamviz deps: ok')" 2>&1 || true
else
  echo "python not found; set QAMVIZ_PYTHON=/path/to/python"
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