"""
MongoDB - Conexão com banco de dados
"""

import logging
import motor.motor_asyncio
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

# Cliente global
client = None
db = None


async def connect_mongodb(mongo_uri: str, db_name: str):
    """Conecta ao MongoDB Atlas"""
    global client, db
    
    try:
        logger.info(f"Conectando ao MongoDB: {db_name}")
        
        # Criar cliente com SSL relaxado (Windows workaround)
        client = AsyncIOMotorClient(
            mongo_uri,
            serverSelectionTimeoutMS=30000,
            tlsAllowInvalidCertificates=True
        )
        
        db = client[db_name]
        
        # Testar conexão
        await client.admin.command('ping')
        
        logger.info("✅ MongoDB conectado com sucesso!")
        
    except Exception as e:
        logger.error(f"❌ Erro ao conectar MongoDB: {str(e)}")
        raise


async def close_mongodb():
    """Fecha conexão com MongoDB"""
    global client
    
    if client:
        client.close()
        logger.info("👋 MongoDB desconectado")


def get_db():
    """Retorna instância do banco"""
    return db