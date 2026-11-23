from __future__ import annotations
import numpy as np

# Mirror firmware PRBS7 (firmware/esp32_qamgen/src/prbs.cpp)
class Prbs7:
    def __init__(self, seed: int = 42):
        self.reset(seed)

    def reset(self, seed: int = 42):
        self.state = seed & 0x7F
        if self.state == 0:
            self.state = 0x7F

    def next_bit(self) -> int:
        bit = ((self.state >> 6) ^ (self.state >> 5)) & 1
        self.state = ((self.state << 1) | bit) & 0x7F
        return bit

    def next_bits(self, n: int) -> int:
        v = 0
        for _ in range(n):
            v = (v << 1) | self.next_bit()
        return v


def _pam4_gray_to_level(g2: int) -> int:
    levels = [-3, -1, 3, 1]  # 00,01,11,10
    return levels[g2 & 0x3]


def _pam8_gray_to_level(g3: int) -> int:
    levels = [-7, -5, -1, -3, 7, 5, 1, 3]
    return levels[g3 & 0x7]


def qam16_symbol(bits4: int) -> complex:
    i_lvl = _pam4_gray_to_level((bits4 >> 2) & 0x3)
    q_lvl = _pam4_gray_to_level(bits4 & 0x3)
    return (i_lvl + 1j * q_lvl) / np.sqrt(10)


def qam64_symbol(bits6: int) -> complex:
    i_lvl = _pam8_gray_to_level((bits6 >> 3) & 0x7)
    q_lvl = _pam8_gray_to_level(bits6 & 0x7)
    return (i_lvl + 1j * q_lvl) / np.sqrt(42)


def training_bits(frame_pos: int, qam64: bool) -> int:
    if qam64:
        return (frame_pos * 11 + 7) & 0x3F
    return (frame_pos * 5 + 3) & 0x0F


def generate_symbols(modulation: str = "qam16", seed: int = 42, n_symbols: int = 1024) -> np.ndarray:
    is64 = str(modulation).lower() == "qam64"
    prbs = Prbs7(seed if seed else 42)
    out = np.empty(n_symbols, dtype=np.complex128)
    for i in range(n_symbols):
        frame_pos = i % 1024
        if frame_pos < 32:
            bits = training_bits(frame_pos, is64)
        else:
            bits = prbs.next_bits(6 if is64 else 4)
        out[i] = qam64_symbol(bits) if is64 else qam16_symbol(bits)
    return out


def training_sequence(modulation: str = "qam16", length: int = 32) -> np.ndarray:
    is64 = str(modulation).lower() == "qam64"
    out = np.empty(length, dtype=np.complex128)
    for i in range(length):
        bits = training_bits(i, is64)
        out[i] = qam64_symbol(bits) if is64 else qam16_symbol(bits)
    return out