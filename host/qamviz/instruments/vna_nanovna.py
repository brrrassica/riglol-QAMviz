"""NanoVNA (NanoVNAUSBFix USBTMC/SCPI) instrument scaffold for M4.

Binary-safe reads are required for :VNA:DATA:* responses. This module parses
IEEE-488.2 definite-length blocks and 12-byte VNA records (<Iff, little-endian:
uint32 frequency_hz, float32 re, float32 im).

Live hardware validation is pending; parsing/writing functions are testable with
mock data.
"""
from __future__ import annotations

import os, shutil, subprocess, struct
from pathlib import Path
from typing import Iterable

RECORD_STRUCT = struct.Struct("<Iff")
RECORD_SIZE = RECORD_STRUCT.size  # 12


def _riglol_bin() -> str:
    return os.environ.get("RIGLOL_BIN") or shutil.which("riglol") or os.path.expanduser("~/projects/omariglol/bin/riglol")


def riglol(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    cmd = [_riglol_bin(), *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def riglol_hex(resource: str, scpi: str, timeout: int = 30) -> bytes:
    """Query SCPI and return raw bytes via riglol --hex output.

    Fallback path because omariglol text query() can corrupt binary blocks.
    Expects riglol to print hex; if unavailable, callers should provide raw bytes.
    """
    p = riglol("scpi", "--usb", "--timeout", "10", "--hex", resource, scpi, timeout=timeout)
    if p.returncode != 0:
        raise RuntimeError(f"riglol hex query failed: {p.stderr.strip() or p.stdout.strip()}")
    # Accept hex with spaces/newlines, or raw if already bytes-like text.
    txt = p.stdout.strip()
    try:
        return bytes.fromhex(txt.replace("\n", " ").replace("\r", " "))
    except ValueError as e:
        raise RuntimeError(f"failed to parse riglol --hex output: {e}") from e


def parse_ieee4882_block(data: bytes) -> bytes:
    """Parse definite-length IEEE-488.2 block and return payload bytes.

    Format: #<n><length><payload> where n is number of length digits.
    Trailing newline after payload (if present) is not included.
    """
    if not data:
        raise ValueError("empty block")
    if data[:1] != b"#":
        raise ValueError("not an IEEE-488.2 block: missing '#'")
    if len(data) < 2:
        raise ValueError("truncated block header")
    n_digits = data[1:2]
    if not n_digits.isdigit():
        raise ValueError("invalid block length digit count")
    n = int(n_digits)
    if n <= 0:
        raise ValueError("unsupported indefinite block")
    if len(data) < 2 + n:
        raise ValueError("truncated block length field")
    length = int(data[2:2 + n])
    start = 2 + n
    end = start + length
    if len(data) < end:
        raise ValueError(f"truncated block payload: expected {length}, got {len(data) - start}")
    return data[start:end]


def parse_vna_records(payload: bytes) -> list[dict]:
    if len(payload) % RECORD_SIZE != 0:
        # Be tolerant: truncate trailing incomplete record but report via caller if needed.
        payload = payload[: len(payload) - (len(payload) % RECORD_SIZE)]
    out = []
    for (freq_hz, re, im) in RECORD_STRUCT.iter_unpack(payload):
        out.append({"freq_hz": int(freq_hz), "re": float(re), "im": float(im)})
    return out


def write_s2p(records: Iterable[dict], out_path: str | Path, z0: float = 50.0) -> Path:
    """Write a minimal S2P-like file.

    Default maps record re/im to S11 and zeroes S21/S12/S22. Callers may provide
    s21_re/s21_im fields for passive S21 correlation.
    """
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    rows = list(records)
    with out.open("w", encoding="utf-8") as f:
        f.write(f"# Hz S RI R {int(z0)}\n")
        f.write("! freq_hz S11_re S11_im S21_re S21_im S12_re S12_im S22_re S22_im\n")
        for r in rows:
            freq = int(r["freq_hz"])
            re = float(r.get("re", 0.0))
            im = float(r.get("im", 0.0))
            s21_re = float(r.get("s21_re", 0.0))
            s21_im = float(r.get("s21_im", 0.0))
            f.write(f"{freq} {re:.9g} {im:.9g} {s21_re:.9g} {s21_im:.9g} 0 0 0 0\n")
    return out


def plot_vna(records: list[dict], out_png: str | Path, title: str = "VNA S11") -> Path:
    import numpy as np
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    freqs = np.array([r["freq_hz"] for r in records], dtype=np.float64)
    re = np.array([r.get("re", 0.0) for r in records], dtype=np.float64)
    im = np.array([r.get("im", 0.0) for r in records], dtype=np.float64)
    mag_db = 20 * np.log10(np.sqrt(re * re + im * im) + 1e-18)
    phase_deg = np.degrees(np.arctan2(im, re))

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 5), sharex=True)
    ax1.plot(freqs / 1e6, mag_db, lw=1.0)
    ax1.set_ylabel("Magnitude (dB)")
    ax1.grid(True, alpha=0.3)
    ax1.set_title(title)
    ax2.plot(freqs / 1e6, phase_deg, lw=1.0, color="tab:orange")
    ax2.set_ylabel("Phase (deg)")
    ax2.set_xlabel("Frequency (MHz)")
    ax2.grid(True, alpha=0.3)
    fig.tight_layout()
    out = Path(out_png)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


class NanoVNA:
    """Minimal NanoVNAUSBFix SCPI wrapper. Uses riglol for transport."""

    def __init__(self, resource: str = "usb:0x0483:0x5740", timeout: int = 10):
        self.resource = resource
        self.timeout = timeout

    def scpi(self, cmd: str, timeout: int | None = None) -> str:
        p = riglol("scpi", "--usb", "--timeout", "10", self.resource, cmd, timeout=timeout or self.timeout)
        if p.returncode != 0:
            raise RuntimeError(p.stderr.strip() or p.stdout.strip() or f"scpi failed: {cmd}")
        return p.stdout.strip()

    def identify(self) -> str:
        return self.scpi("*IDN?")

    def configure_sweep(self, start_hz: int = 100_000, stop_hz: int = 5_000_000, points: int = 101) -> dict:
        self.scpi(f":VNA:SWE:START {int(start_hz)}")
        self.scpi(f":VNA:SWE:STOP {int(stop_hz)}")
        self.scpi(f":VNA:SWE:POINTS {int(points)}")
        return {"start_hz": int(start_hz), "stop_hz": int(stop_hz), "points": int(points)}

    def run_sweep(self) -> str:
        return self.scpi(":VNA:SWE:EXEC", timeout=max(self.timeout, 30))

    def data_pre(self) -> str:
        return self.scpi(":VNA:DATA:PRE?")

    def read_block(self, channel: int = 0) -> list[dict]:
        # Prefer BLOCK for small responses; caller must ensure within 4,084-byte limit.
        raw = riglol_hex(self.resource, f":VNA:DATA:BLOCK? {int(channel)}", timeout=max(self.timeout, 30))
        payload = parse_ieee4882_block(raw)
        return parse_vna_records(payload)

    def read_chunked(self, channel: int = 0, start: int = 0, count: int = 16) -> list[dict]:
        raw = riglol_hex(self.resource, f":VNA:DATA:CHUNK? {int(channel)},{int(start)},{int(count)}", timeout=max(self.timeout, 30))
        payload = parse_ieee4882_block(raw)
        return parse_vna_records(payload)