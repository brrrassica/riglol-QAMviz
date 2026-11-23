from __future__ import annotations
import numpy as np

IDEAL_16QAM = np.array([complex(i, q) for i in [-3, -1, 1, 3] for q in [-3, -1, 1, 3]]) / np.sqrt(10)
IDEAL_64QAM = np.array([complex(i, q) for i in [-7,-5,-3,-1,1,3,5,7] for q in [-7,-5,-3,-1,1,3,5,7]]) / np.sqrt(42)

def ideal_for(modulation: str):
    return IDEAL_64QAM if str(modulation).lower() == "qam64" else IDEAL_16QAM

def load_iq(ch1_npy: str, ch2_npy: str):
    a = np.load(ch1_npy)
    b = np.load(ch2_npy)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    t = a[:, 0] if a.ndim == 2 else np.arange(n)
    i = a[:, 1] if a.ndim == 2 else a
    q = b[:, 1] if b.ndim == 2 else b
    z = i.astype(np.float64) + 1j * q.astype(np.float64)
    return t[:n], z

def _normalize(z: np.ndarray, ideal: np.ndarray):
    z = z - np.mean(z)
    s = np.std(z)
    if s > 0:
        z = z / s
    z = z / (np.mean(np.abs(z)) + 1e-12) * np.mean(np.abs(ideal))
    return z

def sample_symbols(z: np.ndarray, sps: int = 8, modulation: str = "qam16"):
    ideal = ideal_for(modulation)
    best = None
    best_score = -1e18
    phases = np.linspace(-np.pi/8, np.pi/8, 9)
    for off in range(max(1, sps)):
        sym = z[off::sps]
        if len(sym) < 8:
            continue
        symn0 = _normalize(sym, ideal)
        for ph in phases:
            symn = symn0 * np.exp(1j * ph)
            d = np.min(np.abs(symn[:, None] - ideal[None, :])**2, axis=1)
            score = -float(np.mean(d))
            if score > best_score:
                best_score = score
                best = symn
    if best is None:
        best = _normalize(z, ideal)
    return best

def compute_evm(symbols: np.ndarray, ideal=IDEAL_16QAM):
    if len(symbols) == 0:
        return {"evm_percent": None, "n": 0}, symbols, symbols
    sym = symbols.copy()
    for _ in range(8):
        idx = np.argmin(np.abs(sym[:, None] - ideal[None, :])**2, axis=1)
        ref = ideal[idx]
        g = np.vdot(sym, ref) / (np.vdot(sym, sym) + 1e-12)
        sym = sym * g
    idx = np.argmin(np.abs(sym[:, None] - ideal[None, :])**2, axis=1)
    ref = ideal[idx]
    err = sym - ref
    evm = np.sqrt(np.mean(np.abs(err)**2)) / (np.sqrt(np.mean(np.abs(ref)**2)) + 1e-12) * 100.0
    return {
        "evm_percent": float(evm),
        "n": int(len(sym)),
        "mean_mag_err": float(np.mean(np.abs(np.abs(sym) - np.abs(ref)))),
        "mean_phase_err_deg": float(np.mean(np.abs(np.angle(sym) - np.angle(ref))) * 180.0 / np.pi),
    }, sym, ref