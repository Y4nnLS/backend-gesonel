# app/api/v1/endpoints/realtime.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, Query, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import asyncio
from app.api.core.notify import manager, start_simulator, stop_simulator, simulator_status

router = APIRouter(tags=["realtime"])

# ---- WebSocket
# app/api/v1/endpoints/realtime.py
import logging, asyncio
logger = logging.getLogger("realtime")

@router.websocket("/ws/stream")
async def ws_audio_updates(ws: WebSocket):
    await manager.connect(ws)
    logger.info("[WS] connect")
    try:
        while True:
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=60.0)
            except asyncio.TimeoutError:
                pass  # mantém vivo
    except WebSocketDisconnect:
        logger.info("[WS] disconnect (client)")
    except Exception as e:
        logger.exception("[WS] error: %r", e)
    finally:
        await manager.disconnect(ws)


# ---- HTTP helpers (aparecem no /docs)
class RealtimeInfo(BaseModel):
    websocket_url: str
    description: str
    example_payload: dict

@router.get("/v1/realtime", response_model=RealtimeInfo, summary="Info do canal realtime")
def realtime_info():
    return RealtimeInfo(
        websocket_url="/ws/stream",
        description="Mensagens de simulação ou do banco (quando ligado).",
        example_payload={
            "op": "UPDATE",
            "table": "audio_file",
            "id": "uuid",
            "rel_path": "datasets/cafe/0001.wav",
            "duration_s": 3.215,
            "at": "2025-09-28T12:34:56Z",
            "seq": 42,
        },
    )

_TEST_HTML = """
<!doctype html><meta charset="utf-8"><title>WS Test</title>
<h3>WebSocket Test – /ws/stream</h3>
<pre id="log" style="background:#111;color:#0f0;padding:12px;max-height:60vh;overflow:auto;"></pre>
<script>
  const log = (m)=>{const el=document.getElementById('log'); el.textContent+=m+"\\n"; el.scrollTop=el.scrollHeight;}
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const ws = new WebSocket(proto + '://' + location.host + '/ws/stream');
  ws.onopen = ()=>log('open');
  ws.onmessage = e=>log('msg: ' + e.data);
  ws.onclose = ()=>log('close');
  setInterval(()=>{ if (ws.readyState===1) ws.send('ping'); }, 30000);
</script>
"""
@router.get("/v1/realtime/test", response_class=HTMLResponse, include_in_schema=False)
def realtime_test_page():
    return _TEST_HTML

# ---- CONTROLE DO SIMULADOR (start/stop/status) ----
@router.post("/v1/realtime/simulator/start", status_code=status.HTTP_202_ACCEPTED)
async def simulator_start(request: Request, interval: float = Query(10.0, ge=0.2, le=3600)):
    started = await start_simulator(request.app, interval=interval)
    st = simulator_status(request.app)
    return {"started_now": started, **st}

@router.post("/v1/realtime/simulator/stop", status_code=status.HTTP_202_ACCEPTED)
async def simulator_stop(request: Request):
    stopped = await stop_simulator(request.app)
    st = simulator_status(request.app)
    return {"stopped_now": stopped, **st}

@router.get("/v1/realtime/simulator/status")
def simulator_get_status(request: Request):
    return simulator_status(request.app)
