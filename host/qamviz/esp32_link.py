from __future__ import annotations
import json, time
from dataclasses import dataclass

try:
    import serial  # type: ignore
except Exception:  # pragma: no cover
    serial = None

@dataclass
class Esp32Status:
    ok: bool
    raw: dict

class Esp32Link:
    def __init__(self, port: str = "/dev/ttyUSB0", baud: int = 115200, timeout: float = 1.0):
        if serial is None:
            raise RuntimeError("pyserial is required for esp32_link")
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.ser = None

    def open(self):
        self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
        self.ser.setDTR(False); self.ser.setRTS(True); time.sleep(0.1)
        self.ser.setRTS(False); time.sleep(0.2)
        self.ser.reset_input_buffer()
        return self

    def close(self):
        if self.ser:
            self.ser.close()
            self.ser = None

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def command(self, obj: dict, wait: float = 0.3) -> list[dict]:
        if not self.ser:
            raise RuntimeError("serial not open")
        self.ser.write((json.dumps(obj) + "\n").encode())
        time.sleep(wait)
        out = []
        while self.ser.in_waiting:
            line = self.ser.readline().decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except Exception:
                out.append({"ok": False, "raw": line})
        return out

    def status(self) -> Esp32Status:
        msgs = self.command({"cmd": "status"})
        for m in reversed(msgs):
            if m.get("cmd") == "status":
                return Esp32Status(ok=bool(m.get("ok")), raw=m)
        return Esp32Status(ok=False, raw={"messages": msgs})