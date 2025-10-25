# app/api/core/notify.py
import asyncio, json, uuid
from datetime import datetime, timezone
from typing import Set, Optional
from contextlib import suppress
from fastapi import WebSocket

class WSConnectionManager:
    def __init__(self) -> None:
        self.active: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self.active.add(ws)

    async def disconnect(self, ws: WebSocket) -> None:
        async with self._lock:
            self.active.discard(ws)

    async def broadcast_text(self, message: str) -> None:
        async with self._lock:
            drop = []
            for ws in list(self.active):
                try:
                    await ws.send_text(message)
                except Exception:
                    drop.append(ws)
            for ws in drop:
                self.active.discard(ws)

manager = WSConnectionManager()

# ---------- SIMULADOR (loop controlado por start/stop) ----------
# app/api/core/notify.py
import logging
logger = logging.getLogger("realtime")

async def _sim_loop(stop: asyncio.Event, interval: float) -> None:
    i = 0
    while not stop.is_set():
        i += 1
        payload = {
            "op": ["INSERT", "UPDATE", "DELETE"][i % 3],
            "table": "audio_file",
            "id": str(uuid.uuid4()),
            "rel_path": f"datasets/cafe/{i:04d}.wav",
            "duration_s": round(1.5 + (i % 5) * 0.25, 3),
            "at": datetime.now(timezone.utc).isoformat(),
            "seq": i,
        }
        logger.info("[SIM] broadcasting seq=%s payload=%s", i, payload)   # <- AQUI
        await manager.broadcast_text(json.dumps(payload, ensure_ascii=False))

        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except asyncio.TimeoutError:
            pass


def _ensure_state(app):
    # cria campos na app.state se não existirem
    if not hasattr(app.state, "sim_task"):
        app.state.sim_task = None
    if not hasattr(app.state, "sim_stop"):
        app.state.sim_stop = None
    if not hasattr(app.state, "sim_interval"):
        app.state.sim_interval = None

async def start_simulator(app, interval: float = 10.0) -> bool:
    """
    Inicia o simulador. Retorna True se iniciou agora, False se já estava rodando.
    """
    _ensure_state(app)
    if app.state.sim_task and not app.state.sim_task.done():
        return False  # já rodando
    stop = asyncio.Event()
    task = asyncio.create_task(_sim_loop(stop, interval))
    app.state.sim_stop = stop
    app.state.sim_task = task
    app.state.sim_interval = interval
    return True

async def stop_simulator(app) -> bool:
    """
    Para o simulador. Retorna True se parou agora, False se já estava parado.
    """
    _ensure_state(app)
    task = app.state.sim_task
    stop = app.state.sim_stop
    if not task or task.done():
        return False
    if stop:
        stop.set()
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task
    app.state.sim_task = None
    app.state.sim_stop = None
    return True

def simulator_status(app) -> dict:
    _ensure_state(app)
    running = bool(app.state.sim_task and not app.state.sim_task.done())
    return {"running": running, "interval": app.state.sim_interval}
