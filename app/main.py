# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from app.api.v1.endpoints.audios import router as audios_router
from app.api.v1.endpoints.realtime import router as realtime_router
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
    description="Esta API permite upload de áudios e futura predição de emoções via modelos CNN+RNN.",
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

@app.get("/")
def home():
    return {"msg": "API do TCC funcionando"}

app.include_router(audios_router)
app.include_router(realtime_router)
