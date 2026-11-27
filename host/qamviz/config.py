from __future__ import annotations
from dataclasses import dataclass, asdict
import json
from pathlib import Path

@dataclass
class CaptureConfig:
    preset: str = "lab16qam"
    resource: str = "usb:0x1AB1:0x04CE"
    points: int = 1200
    sps: int = 8
    modulation: str = "qam16"
    symbol_rate: int = 20000
    seed: int = 42
    mode: str = "norm"
    shape: str = "rect"
    gain: float = 0.8
    rrc_beta: float = 0.35


def _configs_dir() -> Path:
    return Path(__file__).resolve().parents[2] / "configs"


def get_preset(name: str) -> CaptureConfig:
    cfg_path = _configs_dir() / f"{name}.json"
    if not cfg_path.exists():
        available = sorted(p.stem for p in _configs_dir().glob("*.json")) if _configs_dir().exists() else []
        hint = f" Available: {', '.join(available)}" if available else ""
        raise SystemExit(f"error: unknown preset '{name}'.{hint}")
    try:
        data = json.loads(cfg_path.read_text())
    except Exception as e:
        raise SystemExit(f"error: failed to load preset '{name}' from {cfg_path}: {e}") from e
    for key in ("modulation", "symbol_rate", "sps"):
        if key not in data:
            raise SystemExit(f"error: preset '{name}' missing required field '{key}' in {cfg_path}")
    return CaptureConfig(
        preset=name,
        modulation=str(data["modulation"]),
        symbol_rate=int(data["symbol_rate"]),
        sps=int(data["sps"]),
        points=int(data.get("points", 1200)),
        seed=int(data.get("seed", 42)),
        mode=str(data.get("mode", "norm")),
        shape=str(data.get("shape", "rect")),
        gain=float(data.get("gain", 0.8)),
        rrc_beta=float(data.get("rrc_beta", 0.35)),
    )

def to_dict(cfg: CaptureConfig) -> dict:
    return asdict(cfg)