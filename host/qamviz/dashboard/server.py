from __future__ import annotations

import asyncio
import json
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
                    # Backpressure: drop oldest display frame, keep latest.
                    try:
                        q.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                q.put_nowait(frame)
            except Exception:
                dead.append(q)
        for q in dead:
            self.unregister(q)


def create_app(hub: DashboardHub | None = None) -> FastAPI:
    hub = hub or DashboardHub()
    app = FastAPI(title="qamviz dashboard", version="0.1")
    app.state.hub = hub

    @app.get("/")
    async def index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/api/status")
    async def status():
        return {"ok": True, "clients": len(hub.clients), "schema": "qamviz.dashboard.frame/0.1"}

    @app.websocket("/ws")
    async def ws_endpoint(ws: WebSocket):
        await ws.accept()
        q = hub.register()
        try:
            await ws.send_text(json.dumps(make_frame("status", {"msg": "connected", "clients": len(hub.clients)})))
            while True:
                # Drain outgoing frames; also receive pings/commands from client.
                try:
                    frame = await asyncio.wait_for(q.get(), timeout=1.0)
                    await ws.send_text(json.dumps(frame))
                except asyncio.TimeoutError:
                    # Keepalive / allow receive check.
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


app = create_app()


def run(host: str = "127.0.0.1", port: int = 8765) -> None:
    import uvicorn

    uvicorn.run("qamviz.dashboard.server:app", host=host, port=port, reload=False, log_level="info")