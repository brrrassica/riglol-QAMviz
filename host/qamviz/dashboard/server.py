from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

STATIC_DIR = Path(__file__).resolve().parent / "static"


def make_frame(stream: str, payload: dict[str, Any], schema: str = "qamviz.dashboard.frame/0.1") -> dict[str, Any]:
    return {
        "schema": schema,
        "ts": time.time(),
        "stream": stream,
        "payload": payload,
    }


class DashboardHub:
    """Bounded broadcast hub. Drops display frames when slow; acquisition records should not go through this path."""

    def __init__(self, max_queue: int = 32):
        self.max_queue = max_queue
        self.clients: set[asyncio.Queue] = set()

    def register(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=self.max_queue)
        self.clients.add(q)
        return q

    def unregister(self, q: asyncio.Queue) -> None:
        self.clients.discard(q)

    async def publish(self, frame: dict[str, Any]) -> None:
        dead = []
        for q in list(self.clients):
            try:
                if q.full():
                    try:
                        q.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                q.put_nowait(frame)
            except Exception:
                dead.append(q)
        for q in dead:
            self.unregister(q)


async def demo_publisher(hub: DashboardHub, stop: asyncio.Event) -> None:
    """Synthetic frame generator for scaffold/demo mode (no instruments required)."""
    import numpy as np
    from .frames import constellation_frame, iq_frame, vna_frame, measure_frame
    from ..analysis import ideal_for

    rng = np.random.default_rng(0)
    ideal = ideal_for("qam16")
    t0 = time.time()
    while not stop.is_set():
        n = 128
        idx = rng.integers(0, len(ideal), size=n)
        sym = ideal[idx] + (rng.normal(scale=0.08, size=n) + 1j * rng.normal(scale=0.08, size=n))
        metrics = {"evm_percent": float(8.0 + rng.normal(scale=0.3)), "snr_db_est": 20.0, "n": n}
        await hub.publish({"ts": time.time(), **constellation_frame(sym, metrics)})

        tt = np.linspace(0, 1e-3, 256)
        z = np.exp(1j * 2 * np.pi * 2000 * tt) + 0.05 * (rng.normal(size=256) + 1j * rng.normal(size=256))
        await hub.publish({"ts": time.time(), **iq_frame(tt, z)})

        freqs = np.linspace(100e3, 5e6, 101)
        recs = [{"freq_hz": int(f), "re": float(0.8 - 0.1*(f/5e6)), "im": float(-0.05)} for f in freqs]
        await hub.publish({"ts": time.time(), **vna_frame(recs)})

        await hub.publish({"ts": time.time(), **measure_frame({
            "workspace": "demo",
            "overall_elapsed_ms": 120.0,
            "parallelism_ratio": 1.05,
            "rows": [
                {"label": "Rigol DS1054Z", "type": "Oscilloscope", "command": ":MEAS:FREQ?", "value": "20000.0", "error": None, "elapsed_ms": 115.0, "ok": True},
                {"label": "NanoVNA", "type": "VectorNetworkAnalyzer", "command": "*IDN?", "value": "NanoVNA-H,USBFix,...", "error": None, "elapsed_ms": 40.0, "ok": True},
            ],
        })})
        try:
            await asyncio.wait_for(stop.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            pass


def create_app(hub: DashboardHub | None = None, demo: bool = False) -> FastAPI:
    hub = hub or DashboardHub()
    app = FastAPI(title="qamviz dashboard", version="0.1")
    app.state.hub = hub
    app.state.demo = demo
    app.state._demo_stop = asyncio.Event()
    app.state._demo_task = None

    @app.on_event("startup")
    async def _startup():
        if app.state.demo:
            app.state._demo_stop.clear()
            app.state._demo_task = asyncio.create_task(demo_publisher(app.state.hub, app.state._demo_stop))

    @app.on_event("shutdown")
    async def _shutdown():
        app.state._demo_stop.set()
        t = app.state._demo_task
        if t:
            t.cancel()

    @app.get("/")
    async def index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/status")
    async def status():
        return {"ok": True, "clients": len(hub.clients), "demo": bool(app.state.demo), "schema": "qamviz.dashboard.frame/0.1"}

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await ws.accept()
        q = hub.register()
        try:
            await ws.send_text(json.dumps(make_frame("status", {"msg": "connected", "clients": len(hub.clients)})))
            while True:
                try:
                    frame = await asyncio.wait_for(q.get(), timeout=1.0)
                    await ws.send_text(json.dumps(frame))
                except asyncio.TimeoutError:
                    try:
                        msg = await asyncio.wait_for(ws.receive_text(), timeout=0.01)
                        if msg == "ping":
                            await ws.send_text(json.dumps(make_frame("status", {"msg": "pong"})))
                    except asyncio.TimeoutError:
                        pass
        except WebSocketDisconnect:
            pass
        finally:
            hub.unregister(q)

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    return app


demo_mode = os.environ.get("QAMVIZ_DASHBOARD_DEMO", "").lower() in ("1", "true", "yes")
app = create_app(demo=demo_mode)


def run(host: str = "127.0.0.1", port: int = 8765, demo: bool = False) -> None:
    import uvicorn

    # When demo requested, set env so the app factory picks it up under uvicorn's import string.
    if demo:
        os.environ["QAMVIZ_DASHBOARD_DEMO"] = "1"
        global app
        app = create_app(demo=True)
    uvicorn.run(app, host=host, port=port, reload=False, log_level="info")