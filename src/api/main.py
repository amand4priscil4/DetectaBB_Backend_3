"""
API FastAPI - Detector de Boletos Falsos
COM SISTEMA DE AUTENTICAÇÃO E ACESSO RÁPIDO
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request, status
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

# Autenticação
from auth.routes import router as auth_router
from auth.middleware import verificar_token_opcional

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar app FastAPI
app = FastAPI(
    title="Detector de Boletos Falsos API",
    description="API para análise e detecção de fraudes em boletos bancários com autenticação",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rotas de autenticação
app.include_router(auth_router)


# =============================================
# ENDPOINTS
# =============================================

@app.get("/")
async def root():
    """Endpoint raiz"""
    return {
        "message": "Detector de Boletos Falsos API",
        "version": "2.0.0",
        "status": "online",
        "features": [
            "Autenticação JWT",
            "Acesso rápido (2 análises/dia)",
            "Análises ilimitadas para usuários autenticados",
            "Histórico de análises"
        ]
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
async def analisar_boleto(
    file: UploadFile = File(...),
    request: Request = None,
    token_payload: dict = Depends(verificar_token_opcional)
):
    """
    Endpoint para upload e análise de boleto
    Suporta usuários autenticados e anônimos (limite: 2/dia)
    
    Aceita: image/jpeg, image/png, application/pdf
    Retorna: ID da análise para consulta posterior
    """
    
    try:
        # Verificar se é usuário autenticado
        is_authenticated = token_payload is not None
        user_id = token_payload.get("sub") if is_authenticated else None
        
        # Se não autenticado, verificar limite de acesso anônimo
        if not is_authenticated:
            db = get_db()
            ip_address = request.client.host
            
            hoje = datetime.utcnow().date()
            acesso = await db.acessos_anonimos.find_one({"ip_address": ip_address})
            
            if acesso:
                ultima_analise = acesso.get("ultima_analise")
                analises_hoje = acesso.get("analises_hoje", 0)
                
                # Verificar se é novo dia
                if ultima_analise and ultima_analise.date() < hoje:
                    analises_hoje = 0
                
                # Verificar limite
                if analises_hoje >= 2:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Limite diário de 2 análises atingido. Faça login para análises ilimitadas!"
                    )
            
            # Registrar análise anônima
            await db.acessos_anonimos.update_one(
                {"ip_address": ip_address},
                {
                    "$inc": {"analises_hoje": 1},
                    "$set": {"ultima_analise": datetime.utcnow()}
                },
                upsert=True
            )
            
            logger.info(f"📊 Acesso anônimo registrado: {ip_address}")
        
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
        
        # 3. Converter para base64
        file_base64 = base64.b64encode(file_bytes).decode('utf-8')
        
        # 4. Gerar ID único
        analise_id = str(uuid.uuid4())
        
        logger.info(f"📄 Recebido arquivo: {file.filename} ({file_size} bytes) - ID: {analise_id}")
        
        # 5. Salvar no MongoDB
        db = get_db()
        analise_doc = {
            '_id': analise_id,
            'status': 'processing',
            'uploadedAt': datetime.utcnow(),
            'fileType': file.content_type,
            'fileSize': file_size,
            'fileName': file.filename,
            'is_authenticated': is_authenticated
        }
        
        # Se autenticado, vincular ao usuário
        if is_authenticated:
            analise_doc['user_id'] = user_id
        else:
            analise_doc['ip_address'] = request.client.host
        
        await db.analises.insert_one(analise_doc)
        
        logger.info(f"✅ Análise salva no MongoDB: {analise_id}")
        
        # 6. Adicionar na fila Redis
        redis_conn = Redis.from_url(settings.redis_url)
        
        job_data = {
            'analise_id': analise_id,
            'file_base64': file_base64,
            'file_type': file.content_type,
            'user_id': user_id,
            'is_authenticated': is_authenticated
        }
        
        redis_conn.rpush('boletos:jobs', json.dumps(job_data))
        
        logger.info(f"✅ Job adicionado à fila: {analise_id}")
        
        # 7. Incrementar contador do usuário se autenticado
        if is_authenticated:
            from bson import ObjectId
            await db.usuarios.update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"analises_realizadas": 1}}
            )
        
        # 8. Retornar resposta
        response = {
            "id": analise_id,
            "status": "processing",
            "message": "Boleto recebido e adicionado à fila de processamento",
            "fileName": file.filename,
            "fileSize": file_size,
            "fileType": file.content_type,
            "is_authenticated": is_authenticated
        }
        
        if not is_authenticated:
            # Calcular análises restantes
            acesso = await db.acessos_anonimos.find_one({"ip_address": request.client.host})
            analises_hoje = acesso.get("analises_hoje", 0) if acesso else 0
            response["analises_restantes"] = max(0, 2 - analises_hoje)
            response["mensagem_acesso"] = "Faça login para análises ilimitadas e histórico completo!"
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao processar upload: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno ao processar arquivo: {str(e)}"
        )


@app.get("/api/analise/{analise_id}")
async def consultar_analise(
    analise_id: str,
    token_payload: dict = Depends(verificar_token_opcional)
):
    """
    Consultar status e resultado da análise
    Usuários autenticados veem detalhes completos
    """
    
    try:
        is_authenticated = token_payload is not None
        user_id = token_payload.get("sub") if is_authenticated else None
        
        # Buscar no MongoDB
        db = get_db()
        analise = await db.analises.find_one({'_id': analise_id})
        
        if not analise:
            raise HTTPException(
                status_code=404,
                detail="Análise não encontrada"
            )
        
        # Se autenticado, verificar se é o dono da análise
        if is_authenticated and analise.get('user_id') != user_id:
            raise HTTPException(
                status_code=403,
                detail="Acesso negado a esta análise"
            )
        
        # Remover _id do MongoDB
        analise['id'] = analise.pop('_id')
        
        # Se não autenticado, remover detalhes sensíveis
        if not is_authenticated:
            # Remover explicação detalhada
            if 'fraudeAnalise' in analise and 'explicacao' in analise['fraudeAnalise']:
                analise['fraudeAnalise']['explicacao'] = {
                    "mensagem": "Faça login para ver explicação detalhada!"
                }
            
            analise['acesso_limitado'] = True
            analise['mensagem'] = "Resultados básicos. Faça login para ver detalhes completos!"
        
        return analise
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao consultar análise: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao consultar análise: {str(e)}"
        )


@app.get("/api/historico")
async def obter_historico(
    token_payload: dict = Depends(verificar_token_opcional),
    limit: int = 10,
    skip: int = 0
):
    """
    Obter histórico de análises do usuário autenticado
    Requer autenticação
    """
    
    if not token_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticação necessária para acessar histórico"
        )
    
    try:
        user_id = token_payload.get("sub")
        db = get_db()
        
        # Buscar análises do usuário
        cursor = db.analises.find(
            {"user_id": user_id}
        ).sort("uploadedAt", -1).skip(skip).limit(limit)
        
        analises = []
        async for doc in cursor:
            doc['id'] = str(doc.pop('_id'))
            analises.append(doc)
        
        # Contar total
        total = await db.analises.count_documents({"user_id": user_id})
        
        return {
            "total": total,
            "analises": analises,
            "limit": limit,
            "skip": skip
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar histórico: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro ao buscar histórico"
        )


@app.post("/api/test-ocr")
async def test_ocr(
    file: UploadFile = File(...),
    request: Request = None,
    token_payload: dict = Depends(verificar_token_opcional)
):
    """
    Endpoint de teste completo: OCR + Parser + Validação + ML + Explicabilidade
    Suporta usuários autenticados e anônimos
    """
    
    try:
        # Verificar autenticação
        is_authenticated = token_payload is not None
        user_id = token_payload.get("sub") if is_authenticated else None
        
        # Se não autenticado, verificar limite
        if not is_authenticated:
            db = get_db()
            ip_address = request.client.host
            
            hoje = datetime.utcnow().date()
            acesso = await db.acessos_anonimos.find_one({"ip_address": ip_address})
            
            if acesso:
                ultima_analise = acesso.get("ultima_analise")
                analises_hoje = acesso.get("analises_hoje", 0)
                
                if ultima_analise and ultima_analise.date() < hoje:
                    analises_hoje = 0
                
                if analises_hoje >= 2:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Limite diário atingido. Faça login para continuar!"
                    )
            
            # Registrar análise
            await db.acessos_anonimos.update_one(
                {"ip_address": ip_address},
                {
                    "$inc": {"analises_hoje": 1},
                    "$set": {"ultima_analise": datetime.utcnow()}
                },
                upsert=True
            )
        
        # Imports
        from ml.ocr import extrair_texto_tesseract
        from ml.parser import parse_dados_boleto
        from ml.validator import validar_boleto_febraban
        from ml.model import carregar_modelo, preparar_features, predizer_fraude
        from ml.explainer import gerar_explicacao_humanizada
        
        # Ler arquivo
        file_bytes = await file.read()
        
        logger.info(f"📄 Processando: {file.filename}")
        
        # 1. OCR
        texto = extrair_texto_tesseract(file_bytes)
        
        # 2. Parser
        dados = parse_dados_boleto(texto)
        
        # 3. Validação FEBRABAN
        validacao = validar_boleto_febraban(dados)
        
        # 4. Modelo ML
        modelo = carregar_modelo()
        features = preparar_features(dados)
        predicao_ml = predizer_fraude(modelo, features)
        
        # 5. Explicabilidade
        explicacao = gerar_explicacao_humanizada(
            dados_extraidos=dados,
            resultado_validacao=validacao,
            predicao_ml=predicao_ml
        )
        
        # 6. Resultado final
        resultado_final = {
            "isFraudulento": validacao.get('valido') == False or predicao_ml['is_fraudulento'],
            "score": predicao_ml.get('score_fraude', 0),
            "confianca": predicao_ml.get('confianca', 0),
            "metodos": []
        }
        
        if not validacao.get('valido'):
            resultado_final['metodos'].append('validacao_febraban')
            resultado_final['motivos'] = validacao.get('erros', [])
        
        if predicao_ml['is_fraudulento']:
            resultado_final['metodos'].append('modelo_ml')
        
        # Se autenticado, adicionar explicação completa
        if is_authenticated:
            resultado_final['explicacao'] = explicacao
        
        # Incrementar contador do usuário
        if is_authenticated:
            from bson import ObjectId
            await db.usuarios.update_one(
                {"_id": ObjectId(user_id)},
                {"$inc": {"analises_realizadas": 1}}
            )
        
        # Preparar resposta
        response = {
            "success": True,
            "dados_extraidos": dados,
            "resultado_final": resultado_final,
            "is_authenticated": is_authenticated
        }
        
        if not is_authenticated:
            response["mensagem"] = "Faça login para ver explicação detalhada e histórico completo!"
            acesso = await db.acessos_anonimos.find_one({"ip_address": request.client.host})
            analises_hoje = acesso.get("analises_hoje", 0) if acesso else 0
            response["analises_restantes"] = max(0, 2 - analises_hoje)
        else:
            response["historico_disponivel"] = True
        
        logger.info(f"✅ Análise concluída: {file.filename}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro no teste: {str(e)}")
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
    logger.info("🚀 API iniciada!")
    logger.info(f"📊 Ambiente: {settings.environment}")
    
    # Conectar MongoDB
    await connect_mongodb(settings.mongo_uri, settings.mongo_db_name)
    
    # Criar índices
    db = get_db()
    await db.usuarios.create_index("email", unique=True)
    await db.acessos_anonimos.create_index("ip_address")
    await db.analises.create_index("user_id")
    
    logger.info("✅ Índices criados!")


@app.on_event("shutdown")
async def shutdown_event():
    """Executado quando a API desliga"""
    logger.info("🔴 API desligando...")
    
    # Fechar MongoDB
    await close_mongodb()


# =============================================
# RODAR LOCAL
# =============================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True
    )
