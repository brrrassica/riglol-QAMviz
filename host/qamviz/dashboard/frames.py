from __future__ import annotations

from typing import Any
import numpy as np


def constellation_frame(symbols: np.ndarray, metrics: dict[str, Any], schema: str = "qamviz.dashboard.frame/0.1") -> dict[str, Any]:
    pts = [[float(np.real(s)), float(np.imag(s))] for s in symbols[:2000]]
    return {
        "schema": schema,
        "stream": "constellation",
        "payload": {
            "points": pts,
            "metrics": metrics,
            "n": int(len(symbols)),
        },
    }


def iq_frame(t: np.ndarray, z: np.ndarray, max_points: int = 1200) -> dict[str, Any]:
    n = min(len(t), len(z), max_points)
    tt = t[:n]
    zz = z[:n]
    t0 = float(tt[0]) if n else 0.0
    iq = [[float(np.real(v)), float(np.imag(v)), float(tt[i] - t0)] for i, v in enumerate(zz)]
    return {
        "schema": "qamviz.dashboard.frame/0.1",
        "stream": "iq",
        "payload": {"iq": [[p[0], p[1]] for p in iq], "t": [p[2] for p in iq], "n": n},
    }


def vna_frame(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "qamviz.dashboard.frame/0.1",
        "stream": "vna",
        "payload": {"records": records, "n": len(records)},
    }


def measure_frame(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "qamviz.dashboard.frame/0.1",
        "stream": "omariglol.measure",
        "payload": payload,
    }