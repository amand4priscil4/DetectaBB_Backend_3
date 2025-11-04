"""
Worker simples usando threading (funciona no Windows)
"""

import sys
import os
import time
import logging
from threading import Thread
from redis import Redis
import json

# Adicionar src ao path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from database.mongodb import connect_mongodb
from tasks import processar_boleto
import asyncio

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SimpleWorker:
    """Worker simples que processa jobs da fila Redis"""
    
    def __init__(self):
        self.redis_conn = Redis.from_url(settings.redis_url)
        self.queue_name = 'boletos:jobs'
        self.running = True
        
    def processar_job(self, job_data):
        """Processa um job"""
        try:
            analise_id = job_data['analise_id']
            file_base64 = job_data['file_base64']
            file_type = job_data['file_type']
            
            logger.info(f"[WORKER] Processando job: {analise_id}")
            
            # Processar boleto
            processar_boleto(analise_id, file_base64, file_type)
            
            logger.info(f"[WORKER] ✅ Job concluído: {analise_id}")
            
        except Exception as e:
            logger.error(f"[WORKER] ❌ Erro ao processar job: {str(e)}")
    
    def run(self):
        """Loop principal do worker"""
        logger.info(" Worker iniciado!")
        logger.info(f"Escutando fila: {self.queue_name}")
        
        while self.running:
            try:
                # Buscar job da fila (blocking com timeout)
                result = self.redis_conn.blpop(self.queue_name, timeout=5)
                
                if result:
                    _, job_json = result
                    job_data = json.loads(job_json)
                    
                    # Processar em thread separada
                    thread = Thread(target=self.processar_job, args=(job_data,))
                    thread.start()
                    
            except KeyboardInterrupt:
                logger.info("\n Encerrando worker...")
                self.running = False
                break
            except Exception as e:
                logger.error(f"[WORKER] Erro: {str(e)}")
                time.sleep(1)


def main():
    """Inicializa o worker"""
    
    # Conectar MongoDB
    logger.info("Conectando ao MongoDB...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(connect_mongodb(settings.mongo_uri, settings.mongo_db_name))
    logger.info("✅ MongoDB conectado!")
    
    # Iniciar worker
    worker = SimpleWorker()
    worker.run()


if __name__ == '__main__':
    main()