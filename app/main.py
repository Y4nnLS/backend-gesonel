from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints.audios import router as audios_router
from app.api.v1.endpoints.upload import router as upload_router
from app.api.websocket import manager

app = FastAPI(
    title="API de Reconhecimento de Emoções",
    description="Esta API permite upload de áudios e predição de emoções via modelos CNN+RNN.",
    version="1.0.0",
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
