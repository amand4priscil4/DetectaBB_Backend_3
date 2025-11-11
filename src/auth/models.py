"""
Modelos de dados para autenticação
"""

from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, EmailStr, Field, validator
import re


class UsuarioCreate(BaseModel):
    """Schema para criação de usuário"""
    nome: str = Field(..., min_length=3, max_length=100)
    email: EmailStr
    senha: str = Field(..., min_length=8)
    
    @validator('senha')
    def validar_senha_forte(cls, v):
        """Valida senha forte"""
        if len(v) < 8:
            raise ValueError('Senha deve ter no mínimo 8 caracteres')
        if not re.search(r'[A-Z]', v):
            raise ValueError('Senha deve conter pelo menos uma letra maiúscula')
        if not re.search(r'[a-z]', v):
            raise ValueError('Senha deve conter pelo menos uma letra minúscula')
        if not re.search(r'[0-9]', v):
            raise ValueError('Senha deve conter pelo menos um número')
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', v):
            raise ValueError('Senha deve conter pelo menos um caractere especial')
        return v
    
    @validator('nome')
    def validar_nome(cls, v):
        """Valida nome"""
        if not v.strip():
            raise ValueError('Nome não pode estar vazio')
        if len(v.strip()) < 3:
            raise ValueError('Nome deve ter no mínimo 3 caracteres')
        return v.strip()


class UsuarioLogin(BaseModel):
    """Schema para login"""
    email: EmailStr
    senha: str


class UsuarioResponse(BaseModel):
    """Schema para resposta de usuário"""
    id: str
    nome: str
    email: str
    created_at: datetime
    analises_realizadas: int = 0
    plano: str = "gratuito"  # gratuito, premium, etc


class TokenResponse(BaseModel):
    """Schema para resposta de token"""
    access_token: str
    token_type: str = "bearer"
    user: UsuarioResponse


class UsuarioDatabase:
    """Modelo de usuário no banco de dados"""
    
    def __init__(
        self,
        nome: str,
        email: str,
        senha_hash: str,
        created_at: Optional[datetime] = None,
        analises_realizadas: int = 0,
        plano: str = "gratuito"
    ):
        self.nome = nome
        self.email = email.lower()
        self.senha_hash = senha_hash
        self.created_at = created_at or datetime.utcnow()
        self.analises_realizadas = analises_realizadas
        self.plano = plano
    
    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return {
            "nome": self.nome,
            "email": self.email,
            "senha_hash": self.senha_hash,
            "created_at": self.created_at,
            "analises_realizadas": self.analises_realizadas,
            "plano": self.plano
        }
    
    @staticmethod
    def from_dict(data: Dict) -> 'UsuarioDatabase':
        """Cria instância a partir de dicionário"""
        return UsuarioDatabase(
            nome=data["nome"],
            email=data["email"],
            senha_hash=data["senha_hash"],
            created_at=data.get("created_at"),
            analises_realizadas=data.get("analises_realizadas", 0),
            plano=data.get("plano", "gratuito")
        )


class AcessoAnonimo(BaseModel):
    """Schema para controle de acesso anônimo"""
    ip_address: str
    analises_hoje: int = 0
    ultima_analise: Optional[datetime] = None
    data_registro: datetime = Field(default_factory=datetime.utcnow)
