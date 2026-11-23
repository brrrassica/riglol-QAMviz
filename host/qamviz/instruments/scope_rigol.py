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


def _resource_ids(resource: str):
    # Accept forms like usb:0x1AB1:0x04CE or usb:1ab1:04ce
    parts = resource.lower().replace("0x", "").split(":")
    if len(parts) >= 3 and parts[0] == "usb":
        try:
            return int(parts[1], 16), int(parts[2], 16)
        except Exception:
            return None
    return None


def preflight_capture(resource: str) -> dict:
    """Read-only preflight checks before capture. Does not modify instrument state."""
    out = {"resource": resource, "ok": True, "checks": []}
    bin_path = _riglol_bin()
    out["riglol"] = bin_path
    if not Path(bin_path).exists() and shutil.which(bin_path) is None:
        out["ok"] = False
        out["checks"].append({"name": "riglol_bin", "ok": False, "detail": f"not found: {bin_path}"})
        return out
    out["checks"].append({"name": "riglol_bin", "ok": True, "detail": bin_path})

    p = riglol("usb", "list", "--json", timeout=20)
    out["checks"].append({"name": "usb_list", "ok": p.returncode == 0, "rc": p.returncode, "stderr": p.stderr.strip()})
    found = resource in p.stdout
    ids = _resource_ids(resource)
    if not found and ids and p.returncode == 0:
        try:
            import json as _json
            devs = _json.loads(p.stdout)
            vid, pid = ids
            found = any(int(d.get("id", {}).get("vendor", -1)) == vid and int(d.get("id", {}).get("product", -1)) == pid for d in devs)
        except Exception:
            pass
    out["checks"].append({"name": "resource_visible", "ok": found, "detail": resource})
    if not found:
        out["ok"] = False
    return out


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