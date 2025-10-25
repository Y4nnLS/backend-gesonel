"""
WebSocket para updates em tempo real do processamento de áudio
"""
import json
import asyncio
from typing import Dict, Set
from fastapi import WebSocket, WebSocketDisconnect
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Gerenciador de conexões WebSocket"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Conecta um novo cliente"""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Cliente WebSocket conectado. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Desconecta um cliente"""
        self.active_connections.discard(websocket)
        logger.info(f"Cliente WebSocket desconectado. Total: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Envia mensagem para um cliente específico"""
        try:
            await websocket.send_text(message)
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: str):
        """Envia mensagem para todos os clientes conectados"""
        if not self.active_connections:
            return
        
        # Cria uma cópia da lista para evitar problemas durante iteração
        connections = list(self.active_connections)
        
        for connection in connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Erro ao enviar broadcast: {e}")
                self.disconnect(connection)
    
    async def broadcast_audio_update(self, audio_id: str, status: str, data: Dict = None):
        """Envia update específico de áudio para todos os clientes"""
        message = {
            "type": "audio_update",
            "audio_id": audio_id,
            "status": status,
            "data": data or {},
            "timestamp": asyncio.get_event_loop().time()
        }
        
        await self.broadcast(json.dumps(message))
        logger.info(f"Broadcast enviado: {message}")

# Instância global do gerenciador
manager = ConnectionManager()

async def websocket_endpoint(websocket: WebSocket):
    """Endpoint WebSocket principal"""
    await manager.connect(websocket)
    
    try:
        while True:
            # Recebe mensagens do cliente (ping, etc.)
            data = await websocket.receive_text()
            
            # Responde a pings
            if data == "ping":
                await manager.send_personal_message("pong", websocket)
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Erro no WebSocket: {e}")
        manager.disconnect(websocket)
