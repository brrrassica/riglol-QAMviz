from __future__ import annotations
import numpy as np


def rrc_taps(sps: int = 8, span_symbols: int = 8, beta: float = 0.35) -> np.ndarray:
    """Root-raised-cosine FIR taps. Simple reference implementation."""
    n = span_symbols * sps
    t = np.arange(-n / 2, n / 2 + 1) / float(sps)
    taps = np.zeros_like(t, dtype=np.float64)
    for i, ti in enumerate(t):
        if abs(ti) < 1e-12:
            taps[i] = 1.0 - beta + (4 * beta / np.pi)
        elif beta > 0 and abs(abs(4 * beta * ti) - 1.0) < 1e-12:
            taps[i] = (beta / np.sqrt(2)) * (
                (1 + 2 / np.pi) * np.sin(np.pi / (4 * beta))
                + (1 - 2 / np.pi) * np.cos(np.pi / (4 * beta))
            )
        else:
            num = np.sin(np.pi * ti * (1 - beta)) + 4 * beta * ti * np.cos(np.pi * ti * (1 + beta))
            den = np.pi * ti * (1 - (4 * beta * ti) ** 2)
            taps[i] = num / den
    taps /= np.sqrt(np.sum(taps ** 2) + 1e-18)
    return taps


def matched_filter(z: np.ndarray, sps: int = 8, shape: str = "rect", beta: float = 0.35) -> np.ndarray:
    shape = str(shape).lower()
    if shape not in ("rrc", "root_raised_cosine", "root-raised-cosine"):
        return z
    h = rrc_taps(sps=sps, span_symbols=8, beta=beta)
    # Filter I and Q separately (linear filter).
    i = np.convolve(np.real(z), h, mode="same")
    q = np.convolve(np.imag(z), h, mode="same")
    return i + 1j * q