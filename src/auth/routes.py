"""
Rotas de autenticação
"""

from fastapi import APIRouter, HTTPException, status, Depends, Request
from datetime import datetime, timedelta
from typing import Optional
import logging

from .models import (
    UsuarioCreate, 
    UsuarioLogin, 
    UsuarioResponse, 
    TokenResponse,
    UsuarioDatabase,
    AcessoAnonimo
)
from .utils import hash_senha, verificar_senha, criar_access_token
from .middleware import verificar_token_obrigatorio, extrair_user_id
from database.mongodb import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def registrar_usuario(usuario: UsuarioCreate):
    """
    Registra novo usuário e retorna token de acesso
    """
    db = get_db()
    
    try:
        # Verificar se email já existe
        usuario_existente = await db.usuarios.find_one({"email": usuario.email.lower()})
        
        if usuario_existente:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já cadastrado"
            )
        
        # Criar hash da senha
        senha_hash = hash_senha(usuario.senha)
        
        # Criar usuário
        novo_usuario = UsuarioDatabase(
            nome=usuario.nome,
            email=usuario.email.lower(),
            senha_hash=senha_hash
        )
        
        # Inserir no banco
        resultado = await db.usuarios.insert_one(novo_usuario.to_dict())
        user_id = str(resultado.inserted_id)
        
        logger.info(f"✅ Usuário registrado: {usuario.email}")
        
        # Criar token
        access_token = criar_access_token(data={"sub": user_id})
        
        # Preparar resposta
        user_response = UsuarioResponse(
            id=user_id,
            nome=novo_usuario.nome,
            email=novo_usuario.email,
            created_at=novo_usuario.created_at,
            analises_realizadas=0,
            plano="gratuito"
        )
        
        return TokenResponse(
            access_token=access_token,
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao registrar usuário: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao registrar usuário"
        )


@router.post("/login", response_model=TokenResponse)
async def login(credenciais: UsuarioLogin):
    """
    Autentica usuário e retorna token de acesso
    """
    db = get_db()
    
    try:
        # Buscar usuário
        usuario = await db.usuarios.find_one({"email": credenciais.email.lower()})
        
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos"
            )
        
        # Verificar senha
        if not verificar_senha(credenciais.senha, usuario["senha_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos"
            )
        
        logger.info(f"✅ Login realizado: {credenciais.email}")
        
        # Criar token
        access_token = criar_access_token(data={"sub": str(usuario["_id"])})
        
        # Preparar resposta
        user_response = UsuarioResponse(
            id=str(usuario["_id"]),
            nome=usuario["nome"],
            email=usuario["email"],
            created_at=usuario["created_at"],
            analises_realizadas=usuario.get("analises_realizadas", 0),
            plano=usuario.get("plano", "gratuito")
        )
        
        return TokenResponse(
            access_token=access_token,
            user=user_response
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao fazer login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao autenticar"
        )


@router.get("/me", response_model=UsuarioResponse)
async def obter_usuario_atual(payload: dict = Depends(verificar_token_obrigatorio)):
    """
    Retorna dados do usuário autenticado
    """
    db = get_db()
    user_id = extrair_user_id(payload)
    
    try:
        from bson import ObjectId
        usuario = await db.usuarios.find_one({"_id": ObjectId(user_id)})
        
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado"
            )
        
        return UsuarioResponse(
            id=str(usuario["_id"]),
            nome=usuario["nome"],
            email=usuario["email"],
            created_at=usuario["created_at"],
            analises_realizadas=usuario.get("analises_realizadas", 0),
            plano=usuario.get("plano", "gratuito")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Erro ao buscar usuário: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao buscar dados do usuário"
        )


@router.post("/quick-access")
async def verificar_acesso_anonimo(request: Request):
    """
    Verifica se usuário anônimo pode fazer análise
    Limite: 2 análises por dia por IP
    """
    db = get_db()
    ip_address = request.client.host
    
    try:
        # Buscar registro de acesso
        hoje = datetime.utcnow().date()
        acesso = await db.acessos_anonimos.find_one({"ip_address": ip_address})
        
        if not acesso:
            # Primeiro acesso
            novo_acesso = AcessoAnonimo(ip_address=ip_address, analises_hoje=0)
            await db.acessos_anonimos.insert_one(novo_acesso.dict())
            return {
                "permitido": True,
                "analises_restantes": 2,
                "mensagem": "Bem-vindo! Você tem 2 análises gratuitas hoje."
            }
        
        # Verificar se é um novo dia
        ultima_analise = acesso.get("ultima_analise")
        if ultima_analise and ultima_analise.date() < hoje:
            # Resetar contador
            await db.acessos_anonimos.update_one(
                {"ip_address": ip_address},
                {"$set": {"analises_hoje": 0}}
            )
            return {
                "permitido": True,
                "analises_restantes": 2,
                "mensagem": "Novo dia! Você tem 2 análises gratuitas."
            }
        
        # Verificar limite
        analises_hoje = acesso.get("analises_hoje", 0)
        if analises_hoje >= 2:
            return {
                "permitido": False,
                "analises_restantes": 0,
                "mensagem": "Limite diário atingido. Faça login para análises ilimitadas!"
            }
        
        return {
            "permitido": True,
            "analises_restantes": 2 - analises_hoje,
            "mensagem": f"Você ainda tem {2 - analises_hoje} análise(s) gratuita(s) hoje."
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar acesso anônimo: {e}")
        # Em caso de erro, permitir acesso (fail-open para melhor UX)
        return {
            "permitido": True,
            "analises_restantes": 2,
            "mensagem": "Acesso liberado"
        }


@router.post("/quick-access/register")
async def registrar_analise_anonima(request: Request):
    """
    Registra uma análise anônima
    """
    db = get_db()
    ip_address = request.client.host
    
    try:
        await db.acessos_anonimos.update_one(
            {"ip_address": ip_address},
            {
                "$inc": {"analises_hoje": 1},
                "$set": {"ultima_analise": datetime.utcnow()}
            },
            upsert=True
        )
        
        return {"success": True}
        
    except Exception as e:
        logger.error(f"❌ Erro ao registrar análise anônima: {e}")
        return {"success": False}
