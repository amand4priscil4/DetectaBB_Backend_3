"""
API FastAPI - Detector de Boletos Falsos
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import uuid
import base64
import logging
import sys
import os
import json

# Adicionar pasta src ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Imports locais
from database.mongodb import connect_mongodb, close_mongodb, get_db
from redis import Redis

# Configurações
from config import settings

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar app FastAPI
app = FastAPI(
    title="Detector de Boletos Falsos API",
    description="API para análise e detecção de fraudes em boletos bancários",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================
# ENDPOINTS
# =============================================

@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "message": "Detector de Boletos Falsos API",
        "version": "1.0.0",
        "status": "online"
    }


@app.get("/health")
async def health_check():
    """Health check para Render"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "environment": settings.environment
    }


@app.post("/api/analisar")
async def analisar_boleto(file: UploadFile = File(...)):
    """
    Endpoint para upload e análise de boleto
    
    Aceita: image/jpeg, image/png, application/pdf
    Retorna: ID da análise para consulta posterior
    """
    
    try:
        # 1. Validar tipo de arquivo
        allowed_types = ['image/jpeg', 'image/png', 'application/pdf']
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de arquivo inválido. Aceitos: {', '.join(allowed_types)}"
            )
        
        # 2. Validar tamanho (max 10MB)
        file_bytes = await file.read()
        file_size = len(file_bytes)
        
        if file_size > 10 * 1024 * 1024:  # 10MB
            raise HTTPException(
                status_code=400,
                detail="Arquivo muito grande. Máximo: 10MB"
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="Arquivo vazio"
            )
        
        # 3. Converter para base64 (para processar em memória)
        file_base64 = base64.b64encode(file_bytes).decode('utf-8')
        
        # 4. Gerar ID único
        analise_id = str(uuid.uuid4())
        
        logger.info(f"Recebido arquivo: {file.filename} ({file_size} bytes) - ID: {analise_id}")
        
        # 5. Salvar no MongoDB
        db = get_db()
        await db.analises.insert_one({
            '_id': analise_id,
            'status': 'processing',
            'uploadedAt': datetime.utcnow(),
            'fileType': file.content_type,
            'fileSize': file_size,
            'fileName': file.filename
        })
        
        logger.info(f"✅ Análise salva no MongoDB: {analise_id}")
        
        # 6. Adicionar na fila Redis (simples)
        redis_conn = Redis.from_url(settings.redis_url)
        
        job_data = {
            'analise_id': analise_id,
            'file_base64': file_base64,
            'file_type': file.content_type
        }
        
        redis_conn.rpush('boletos:jobs', json.dumps(job_data))
        
        logger.info(f"✅ Job adicionado à fila: {analise_id}")
        
        # 7. Retornar resposta
        return {
            "id": analise_id,
            "status": "processing",
            "message": "Boleto recebido e adicionado à fila de processamento",
            "fileName": file.filename,
            "fileSize": file_size,
            "fileType": file.content_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao processar upload: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao processar arquivo: {str(e)}"
        )


@app.get("/api/analise/{analise_id}")
async def consultar_analise(analise_id: str):
    """
    Consultar status e resultado da análise
    """
    
    try:
        # Buscar no MongoDB
        db = get_db()
        analise = await db.analises.find_one({'_id': analise_id})
        
        if not analise:
            raise HTTPException(
                status_code=404,
                detail="Análise não encontrada"
            )
        
        # Remover _id do MongoDB (não serializável)
        analise['id'] = analise.pop('_id')
        
        return analise
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao consultar análise: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao consultar análise: {str(e)}"
        )


@app.post("/api/test-ocr")
async def test_ocr(file: UploadFile = File(...)):
    """
    Endpoint de teste completo: OCR + Parser + Validação + ML
    """
    
    try:
        from ml.ocr import extrair_texto_tesseract
        from ml.parser import parse_dados_boleto
        from ml.validator import validar_boleto_febraban
        from ml.model import carregar_modelo, preparar_features, predizer_fraude
        
        # Ler arquivo
        file_bytes = await file.read()
        
        # 1. OCR - Extrair texto
        texto = extrair_texto_tesseract(file_bytes)
        
        # 2. Parser - Extrair dados estruturados
        dados = parse_dados_boleto(texto)
        
        # 3. Validação FEBRABAN
        validacao = validar_boleto_febraban(dados)
        
        # 4. Modelo ML - Predição de fraude
        modelo = carregar_modelo()
        features = preparar_features(dados)
        predicao_ml = predizer_fraude(modelo, features)
        
        # 5. Resultado final combinado
        resultado_final = {
            "is_fraudulento": validacao['valido'] == False or predicao_ml['is_fraudulento'],
            "metodo_deteccao": []
        }
        
        if not validacao['valido']:
            resultado_final['metodo_deteccao'].append('validacao_febraban')
        
        if predicao_ml['is_fraudulento']:
            resultado_final['metodo_deteccao'].append('modelo_ml')
        
        return {
            "success": True,
            "dados_extraidos": dados,
            "validacao_febraban": validacao,
            "predicao_ml": predicao_ml,
            "resultado_final": resultado_final
        }
        
    except Exception as e:
        logger.error(f"Erro no teste: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro: {str(e)}"
        )


# =============================================
# STARTUP/SHUTDOWN
# =============================================

@app.on_event("startup")
async def startup_event():
    """Executado quando a API inicia"""
    logger.info(" API iniciada!")
    logger.info(f"Ambiente: {settings.environment}")
    
    # Conectar MongoDB
    await connect_mongodb(settings.mongo_uri, settings.mongo_db_name)


@app.on_event("shutdown")
async def shutdown_event():
    """Executado quando a API desliga"""
    logger.info(" API desligando...")
    
    # Fechar MongoDB
    await close_mongodb()


# =============================================
# RODAR LOCAL (apenas para desenvolvimento)
# =============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True  # Auto-reload em desenvolvimento
    )