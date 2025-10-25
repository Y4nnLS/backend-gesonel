#!/usr/bin/env python3
"""
Teste completo do sistema de reconhecimento de emoções
"""
import requests
import json
import time
import os
import numpy as np
from scipy.io import wavfile
import asyncio
import websockets

# Configuração
API_BASE = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/stream"

def create_test_audio():
    """Cria um arquivo de áudio de teste"""
    print("🎵 Criando arquivo de áudio de teste...")
    
    # Gera um tom com frequência específica
    sample_rate = 22050
    duration = 2.0
    frequency = 440  # Lá central
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    audio_data = np.sin(2 * np.pi * frequency * t) * 0.5
    
    # Adiciona um pouco de ruído para tornar mais realista
    noise = np.random.normal(0, 0.1, audio_data.shape)
    audio_data = audio_data + noise
    
    # Salva como WAV
    test_file = f"test_complete_{int(time.time())}.wav"
    wavfile.write(test_file, sample_rate, (audio_data * 32767).astype(np.int16))
    
    print(f"✅ Arquivo criado: {test_file}")
    return test_file

def test_health_check():
    """Testa health check"""
    print("🔍 Testando health check...")
    try:
        response = requests.get(f"{API_BASE}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health OK: {data}")
            return data.get("models_ready", False)
        else:
            print(f"❌ Health check falhou: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro no health check: {e}")
        return False

def test_list_audios():
    """Testa listagem de áudios"""
    print("📋 Testando listagem de áudios...")
    try:
        response = requests.get(f"{API_BASE}/v1/audios")
        if response.status_code == 200:
            audios = response.json()
            print(f"✅ {len(audios)} áudios encontrados")
            for audio in audios:
                print(f"   - ID: {audio['id']}")
                print(f"     Status: {audio['processing_status']}")
                print(f"     Emoção: {audio.get('predicted_emotion', 'N/A')}")
            return audios
        else:
            print(f"❌ Listagem falhou: {response.status_code}")
            return []
    except Exception as e:
        print(f"❌ Erro na listagem: {e}")
        return []

def test_upload_audio(audio_file):
    """Testa upload de áudio"""
    print(f"📤 Testando upload: {audio_file}")
    try:
        with open(audio_file, 'rb') as f:
            files = {'file': (audio_file, f, 'audio/wav')}
            response = requests.post(f"{API_BASE}/v1/upload/audio", files=files)
        
        if response.status_code == 201:
            data = response.json()
            print(f"✅ Upload bem-sucedido!")
            print(f"   ID: {data['id']}")
            print(f"   Status: {data['processing_status']}")
            return data['id']
        else:
            print(f"❌ Upload falhou: {response.status_code}")
            print(f"   Resposta: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Erro no upload: {e}")
        return None

def test_processing_status(audio_id):
    """Testa status de processamento"""
    print(f"⏳ Monitorando processamento: {audio_id}")
    
    max_attempts = 30
    attempt = 0
    
    while attempt < max_attempts:
        try:
            response = requests.get(f"{API_BASE}/v1/upload/status/{audio_id}")
            
            if response.status_code == 200:
                data = response.json()
                status = data['processing_status']
                print(f"   Status: {status}")
                
                if status == "completed":
                    print(f"✅ Processamento concluído!")
                    print(f"   Emoção: {data.get('predicted_emotion', 'N/A')}")
                    print(f"   Confiança: {data.get('confidence_score', 'N/A')}")
                    return True
                elif status == "failed":
                    print(f"❌ Processamento falhou!")
                    print(f"   Erro: {data.get('processing_error', 'N/A')}")
                    return False
                elif status in ["pending", "processing"]:
                    print(f"   Aguardando... ({attempt + 1}/{max_attempts})")
                    time.sleep(1)
                    attempt += 1
                else:
                    print(f"   Status desconhecido: {status}")
                    time.sleep(1)
                    attempt += 1
            else:
                print(f"❌ Erro ao verificar status: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao verificar status: {e}")
            return False
    
    print(f"⏰ Timeout: processamento não concluído em {max_attempts} segundos")
    return False

async def test_websocket():
    """Testa WebSocket"""
    print("🔌 Testando WebSocket...")
    try:
        async with websockets.connect(WS_URL) as websocket:
            print("✅ WebSocket conectado!")
            
            # Envia ping
            await websocket.send("ping")
            print("📤 Ping enviado")
            
            # Recebe pong
            response = await websocket.recv()
            print(f"📥 Resposta: {response}")
            
            if response == "pong":
                print("✅ WebSocket funcionando!")
                return True
            else:
                print("❌ WebSocket com problema")
                return False
                
    except Exception as e:
        print(f"❌ Erro no WebSocket: {e}")
        return False

def test_database_persistence():
    """Testa persistência no banco"""
    print("💾 Testando persistência no banco...")
    try:
        response = requests.get(f"{API_BASE}/v1/audios")
        if response.status_code == 200:
            audios = response.json()
            print(f"✅ {len(audios)} áudios persistidos no banco")
            
            # Verifica se há áudios processados
            processed = [a for a in audios if a['processing_status'] == 'completed']
            print(f"✅ {len(processed)} áudios processados")
            
            for audio in processed:
                print(f"   - ID: {audio['id']}")
                print(f"     Emoção: {audio.get('predicted_emotion', 'N/A')}")
                print(f"     Confiança: {audio.get('confidence_score', 'N/A')}")
            
            return len(audios) > 0
        else:
            print(f"❌ Erro ao consultar banco: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Erro na consulta ao banco: {e}")
        return False

def cleanup_test_files():
    """Remove arquivos de teste"""
    test_files = [f for f in os.listdir('.') if f.startswith('test_complete_') and f.endswith('.wav')]
    for file in test_files:
        try:
            os.remove(file)
            print(f"🗑️ Arquivo removido: {file}")
        except:
            pass

def main():
    """Função principal de teste"""
    print("🚀 INICIANDO TESTE COMPLETO DO SISTEMA")
    print("=" * 60)
    
    results = {}
    
    # 1. Health Check
    results['health'] = test_health_check()
    
    # 2. Listagem de áudios
    results['list'] = len(test_list_audios()) > 0
    
    # 3. Persistência no banco
    results['database'] = test_database_persistence()
    
    # 4. WebSocket
    results['websocket'] = asyncio.run(test_websocket())
    
    # 5. Upload e processamento
    if results['health']:
        audio_file = create_test_audio()
        try:
            audio_id = test_upload_audio(audio_file)
            if audio_id:
                results['upload'] = True
                results['processing'] = test_processing_status(audio_id)
            else:
                results['upload'] = False
                results['processing'] = False
        finally:
            cleanup_test_files()
    else:
        results['upload'] = False
        results['processing'] = False
    
    # Resumo dos resultados
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES")
    print("=" * 60)
    
    for test, result in results.items():
        status = "✅ PASSOU" if result else "❌ FALHOU"
        print(f"{test.upper()}: {status}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"\n🎯 RESULTADO FINAL: {passed_tests}/{total_tests} testes passaram")
    
    if passed_tests == total_tests:
        print("🎉 SISTEMA FUNCIONANDO PERFEITAMENTE!")
    else:
        print("⚠️ ALGUNS TESTES FALHARAM - VERIFICAR SISTEMA")
    
    return passed_tests == total_tests

if __name__ == "__main__":
    main()
