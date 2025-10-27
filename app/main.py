from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints.audios import router as audios_router
from app.api.v1.endpoints.upload import router as upload_router
from app.api.websocket import manager
# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.api.v1.endpoints.audios import router as audios_router
from app.api.v1.endpoints.realtime import router as realtime_router
from app.api.v1.endpoints.predict import router as predict_router

# app/main.py (logo após os imports)
import logging
logging.basicConfig(
    level=logging.INFO,  # mude para DEBUG se quiser mais verbosidade
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

_env_origins = os.getenv("FRONT_ORIGINS")
ALLOW_ORIGINS = [o.strip() for o in _env_origins.split(",")] if _env_origins else [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # nada ao iniciar; o simulador é controlado por rotas
    yield
    # nada ao finalizar (rotas já param a task)

app = FastAPI(
    title="API de Reconhecimento de Emoções",
    description="Esta API permite upload de áudios e predição de emoções via modelos CNN+RNN.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOW_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuração CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especifique os domínios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"msg": "API do TCC funcionando"}

@app.get("/health")
def health_check():
    """Verifica se a API está funcionando e se os modelos estão carregados"""
    from app.api.services.emotion_service import emotion_service
    return {
        "status": "ok",
        "models_ready": emotion_service.is_ready()
    }

app.include_router(audios_router)

app.include_router(upload_router)

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket para updates em tempo real"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Recebe mensagens do cliente (ping, etc.)
            data = await websocket.receive_text()
            
            # Responde a pings
            if data == "ping":
                await manager.send_personal_message("pong", websocket)
            
    except Exception as e:
        manager.disconnect(websocket)
app.include_router(realtime_router)
app.include_router(predict_router)
