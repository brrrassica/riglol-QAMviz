from __future__ import annotations
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

IDEAL_16QAM = np.array([complex(i, q) for i in [-3, -1, 1, 3] for q in [-3, -1, 1, 3]]) / np.sqrt(10)
IDEAL_64QAM = np.array([complex(i, q) for i in [-7,-5,-3,-1,1,3,5,7] for q in [-7,-5,-3,-1,1,3,5,7]]) / np.sqrt(42)

def _ideal_for(modulation: str):
    return IDEAL_64QAM if str(modulation).lower() == "qam64" else IDEAL_16QAM

def plot_constellation(symbols: np.ndarray, out_png: str | Path, title: str = "Constellation", modulation: str = "qam16"):
    ideal = _ideal_for(modulation)
    plt.figure(figsize=(6, 6))
    plt.scatter(np.real(ideal), np.imag(ideal), marker='x', s=60, label='ideal')
    if len(symbols):
        plt.scatter(np.real(symbols), np.imag(symbols), s=8, alpha=0.4, label='rx')
    plt.gca().set_aspect('equal')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.title(title)
    plt.xlabel('I'); plt.ylabel('Q')
    plt.tight_layout()
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=150)
    plt.close()

def plot_iq_time(t: np.ndarray, z: np.ndarray, out_png: str | Path, max_points: int = 1200):
    n = min(len(t), len(z), max_points)
    tt = t[:n] - t[0] if len(t) else np.arange(n)
    plt.figure(figsize=(10, 4))
    plt.plot(tt, np.real(z[:n]), label='I', lw=0.8)
    plt.plot(tt, np.imag(z[:n]), label='Q', lw=0.8)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.xlabel('time (s)'); plt.ylabel('V')
    plt.title('I/Q time series')
    plt.tight_layout()
    Path(out_png).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(out_png, dpi=150)
    plt.close()