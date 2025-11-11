"""
Middleware de autenticação
"""

from fastapi import Header, HTTPException, status
from typing import Optional
import logging
from .utils import decodificar_token

logger = logging.getLogger(__name__)


async def verificar_token_opcional(
    authorization: Optional[str] = Header(None)
) -> Optional[dict]:
    """
    Verifica token se fornecido, mas não obriga autenticação
    Retorna payload do token ou None se não autenticado
    """
    if not authorization:
        return None
    
    try:
        # Formato esperado: "Bearer <token>"
        scheme, token = authorization.split()
        
        if scheme.lower() != "bearer":
            return None
        
        payload = decodificar_token(token)
        return payload
        
    except Exception as e:
        logger.warning(f"Erro ao verificar token opcional: {e}")
        return None


async def verificar_token_obrigatorio(
    authorization: str = Header(...)
) -> dict:
    """
    Verifica token obrigatoriamente
    Retorna payload do token ou lança exceção
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticação não fornecido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Formato esperado: "Bearer <token>"
        scheme, token = authorization.split()
        
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Formato de autenticação inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        payload = decodificar_token(token)
        
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido ou expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return payload
        
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Erro ao verificar token: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Erro na autenticação",
            headers={"WWW-Authenticate": "Bearer"},
        )


def extrair_user_id(payload: dict) -> str:
    """Extrai user_id do payload do token"""
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )
    return user_id
