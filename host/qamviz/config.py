from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass
class CaptureConfig:
    preset: str = "lab16qam"
    resource: str = "usb:0x1AB1:0x04CE"
    points: int = 1200
    sps: int = 8
    modulation: str = "qam16"
    symbol_rate: int = 20000

PRESETS = {
    "lab16qam": CaptureConfig(preset="lab16qam", modulation="qam16", symbol_rate=20000, sps=8),
    "lab64qam": CaptureConfig(preset="lab64qam", modulation="qam64", symbol_rate=20000, sps=8),
}

def get_preset(name: str) -> CaptureConfig:
    return PRESETS.get(name, CaptureConfig(preset=name))

def to_dict(cfg: CaptureConfig) -> dict:
    return asdict(cfg)