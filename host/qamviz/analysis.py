from __future__ import annotations
import numpy as np
from .tx_model import generate_symbols, training_sequence
from .pulse_shape import matched_filter

IDEAL_16QAM = np.array([complex(i, q) for i in [-3, -1, 1, 3] for q in [-3, -1, 1, 3]], dtype=np.complex128) / np.sqrt(10)
IDEAL_64QAM = np.array([complex(i, q) for i in [-7, -5, -3, -1, 1, 3, 5, 7] for q in [-7, -5, -3, -1, 1, 3, 5, 7]], dtype=np.complex128) / np.sqrt(42)


def ideal_for(modulation: str) -> np.ndarray:
    return IDEAL_64QAM if str(modulation).lower() == "qam64" else IDEAL_16QAM


def load_iq(ch1_npy: str, ch2_npy: str):
    a = np.load(ch1_npy)
    b = np.load(ch2_npy)
    n = min(len(a), len(b))
    a, b = a[:n], b[:n]
    t = a[:, 0] if a.ndim == 2 else np.arange(n, dtype=np.float64)
    i = a[:, 1] if a.ndim == 2 else a
    q = b[:, 1] if b.ndim == 2 else b
    z = i.astype(np.float64) + 1j * q.astype(np.float64)
    return t[:n], z


def _normalize(z: np.ndarray, ideal: np.ndarray) -> np.ndarray:
    z = z - np.mean(z)
    s = np.std(z)
    if s > 0:
        z = z / s
    z = z / (np.mean(np.abs(z)) + 1e-12) * np.mean(np.abs(ideal))
    return z


def _best_phase(symn: np.ndarray, ideal: np.ndarray) -> tuple[np.ndarray, float]:
    best = symn
    best_score = -1e18
    best_ph = 0.0
    for ph in np.linspace(-np.pi / 4, np.pi / 4, 33):
        c = symn * np.exp(1j * ph)
        d = np.min(np.abs(c[:, None] - ideal[None, :]) ** 2, axis=1)
        score = -float(np.mean(d))
        if score > best_score:
            best_score, best, best_ph = score, c, ph
    return best, best_ph


def sample_symbols(z: np.ndarray, sps: int = 8, modulation: str = "qam16", shape: str = "rect") -> np.ndarray:
    zf = matched_filter(z, sps=sps, shape=shape)
    ideal = ideal_for(modulation)
    best = None
    best_score = -1e18
    for off in range(max(1, sps)):
        sym = zf[off::sps]
        if len(sym) < 8:
            continue
        symn0 = _normalize(sym, ideal)
        symn, _ = _best_phase(symn0, ideal)
        d = np.min(np.abs(symn[:, None] - ideal[None, :]) ** 2, axis=1)
        score = -float(np.mean(d))
        if score > best_score:
            best_score = score
            best = symn
    if best is None:
        best = _normalize(zf, ideal)
    return best


def sync_and_sample(z: np.ndarray, sps: int = 8, modulation: str = "qam16", seed: int = 42, shape: str = "rect"):
    """Try TX-sequence correlation; fall back to blind symbol sampling.

    Searches a 32-symbol window over the full 1024-symbol generated TX sequence,
    so alignment works even when the training burst is not in the capture.
    """
    zf = matched_filter(z, sps=sps, shape=shape)
    ideal = ideal_for(modulation)
    tx = generate_symbols(modulation=modulation, seed=seed, n_symbols=1024)
    win_len = 32
    best = {"score": -1e18, "offset": 0, "start": 0, "frame_pos": 0, "method": "blind"}

    for off in range(max(1, sps)):
        sym = zf[off::sps]
        if len(sym) < win_len + 4:
            continue
        symn = _normalize(sym, ideal)
        symn, _ = _best_phase(symn, ideal)
        for start in range(0, len(symn) - win_len + 1):
            win = symn[start:start + win_len]
            denom = (np.linalg.norm(win) + 1e-12)
            # Search all possible frame positions for this window.
            for frame_pos in range(1024):
                tpl = tx[np.arange(frame_pos, frame_pos + win_len) % 1024]
                tpl_n = tpl / (np.linalg.norm(tpl) + 1e-12)
                score = float(np.real(np.vdot(win / denom, tpl_n)))
                if score > best["score"]:
                    best = {"score": score, "offset": off, "start": start, "frame_pos": frame_pos, "method": "sequence_corr"}

    if best["method"] == "sequence_corr" and best["score"] > 0.6:
        off, start, frame_pos = best["offset"], best["start"], best["frame_pos"]
        sym = zf[off::sps]
        symn = _normalize(sym, ideal)
        symn, _ = _best_phase(symn, ideal)
        sym_out = symn[start:]
        info = {
            "sync": "sequence_corr",
            "offset_samples": int(off),
            "symbol_start": int(start),
            "frame_pos_at_start": int(frame_pos),
            "corr_score": float(best["score"]),
            # frame_pos0_at is index in sym_out where frame_pos==0.
            "frame_pos0_at": int((-frame_pos) % 1024),
        }
        return sym_out, info

    sym_out = sample_symbols(zf, sps=sps, modulation=modulation, shape="rect")
    return sym_out, {"sync": "blind", "offset_samples": None, "corr_score": float(best["score"])}


def compute_evm(symbols: np.ndarray, ideal: np.ndarray | None = None, modulation: str = "qam16"):
    if ideal is None:
        ideal = ideal_for(modulation)
    if len(symbols) == 0:
        return {"evm_percent": None, "n": 0}, symbols, symbols
    sym = symbols.copy()
    for _ in range(10):
        idx = np.argmin(np.abs(sym[:, None] - ideal[None, :]) ** 2, axis=1)
        ref = ideal[idx]
        g = np.vdot(sym, ref) / (np.vdot(sym, sym) + 1e-12)
        sym = sym * g
    idx = np.argmin(np.abs(sym[:, None] - ideal[None, :]) ** 2, axis=1)
    ref = ideal[idx]
    err = sym - ref
    evm = np.sqrt(np.mean(np.abs(err) ** 2)) / (np.sqrt(np.mean(np.abs(ref) ** 2)) + 1e-12) * 100.0
    sig_pow = np.mean(np.abs(ref) ** 2)
    err_pow = np.mean(np.abs(err) ** 2)
    snr_db = 10 * np.log10(sig_pow / (err_pow + 1e-18))
    metrics = {
        "evm_percent": float(evm),
        "snr_db_est": float(snr_db),
        "n": int(len(sym)),
        "mean_mag_err": float(np.mean(np.abs(np.abs(sym) - np.abs(ref)))),
        "mean_phase_err_deg": float(np.mean(np.abs(np.angle(sym) - np.angle(ref))) * 180.0 / np.pi),
    }
    return metrics, sym, ref


def symbol_error_count(symbols: np.ndarray, modulation: str = "qam16", seed: int = 0x7F, frame_pos0_at: int = 0):
    """Compare demodulated symbols against expected TX sequence.

    frame_pos0_at: index in `symbols` where logical frame_pos==0 (training start).
    """
    ideal = ideal_for(modulation)
    tx = generate_symbols(modulation=modulation, seed=seed, n_symbols=1024)
    n = len(symbols)
    if n == 0:
        return {"symbol_errors": None, "symbol_total": 0}
    # Build expected sequence aligned to symbols.
    exp = np.empty(n, dtype=np.complex128)
    for i in range(n):
        frame_pos = (i - frame_pos0_at) % 1024
        exp[i] = tx[frame_pos]
    rx_idx = np.argmin(np.abs(symbols[:, None] - ideal[None, :]) ** 2, axis=1)
    ex_idx = np.argmin(np.abs(exp[:, None] - ideal[None, :]) ** 2, axis=1)
    errors = int(np.sum(rx_idx != ex_idx))
    return {
        "symbol_errors": errors,
        "symbol_total": int(n),
        "symbol_error_rate": float(errors / n),
        "frame_pos0_at": int(frame_pos0_at),
    }