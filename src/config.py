"""
Configurações do projeto
Lê variáveis de ambiente
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Configurações da aplicação"""
    
    # MongoDB
    mongo_uri: str
    mongo_db_name: str = "detector_boletos"
    
    # Redis
    redis_url: str
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    environment: str = "development"
    
    # CORS
    allowed_origins: list = [
    'http://localhost:8100', 
    'http://localhost:4200',
    'https://detectabb.netlify.app'  # ← ADICIONE ESTA LINHA!
    ]
    
    # Sentry (opcional)
    sentry_dsn: str = ""
    
    # Paths
    model_path: str = "src/models/modelo_boleto.pkl"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Instância global
settings = Settings()
