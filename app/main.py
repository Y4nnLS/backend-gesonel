from fastapi import FastAPI
from app.api.v1.endpoints.audios import router as audios_router

app = FastAPI(
    title="API de Reconhecimento de Emoções",
    description="Esta API permite upload de áudios e futura predição de emoções via modelos CNN+RNN.",
    version="1.0.0",
)

@app.get("/")
def home():
    return {"msg": "API do TCC funcionando"}

app.include_router(audios_router)
