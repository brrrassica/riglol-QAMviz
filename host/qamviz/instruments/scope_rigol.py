from __future__ import annotations
import os, shutil, subprocess
from pathlib import Path


def _riglol_bin() -> str:
    return os.environ.get("RIGLOL_BIN") or shutil.which("riglol") or os.path.expanduser("~/projects/omariglol/bin/riglol")


def riglol(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    cmd = [_riglol_bin(), *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def doctor(resource: str | None = None) -> dict:
    info = {"riglol": _riglol_bin()}
    p = riglol("usb", "list", "--json", timeout=20)
    info["usb_list_rc"] = p.returncode
    info["usb_list_stdout"] = p.stdout.strip()
    info["usb_list_stderr"] = p.stderr.strip()
    if resource:
        i = riglol("scpi", "--usb", "--timeout", "10", resource, "*IDN?", timeout=20)
        info["idn_rc"] = i.returncode
        info["idn"] = i.stdout.strip() or i.stderr.strip()
    return info


def capture_channel(resource: str, source: str, out_npy: Path, points: int = 1200, mode: str = "norm") -> dict:
    """Capture a scope channel to .npy via riglol.

    mode="norm": normal screen capture (default).
    mode="raw": scaffold for deeper memory capture; stops scope first. Full
    250k-window chunked RAW read with retries is not yet implemented.
    """
    out_npy.parent.mkdir(parents=True, exist_ok=True)
    mode = (mode or "norm").lower()
    if mode == "raw":
        # RAW requires stopped acquisition for stable deep-memory reads.
        riglol("scpi", "--usb", "--timeout", "10", resource, ":STOP", timeout=15)
    p = riglol("capture", "--usb", "--mode", mode, "--source", source, "--points", str(points), resource, str(out_npy), timeout=90)
    return {
        "source": source,
        "path": str(out_npy),
        "mode": mode,
        "rc": p.returncode,
        "stdout": p.stdout.strip(),
        "stderr": p.stderr.strip(),
    }