"""
Tasks - Jobs que serão processados pelo worker
"""

from datetime import datetime
import logging
import base64

# Imports do explainer
from ml.explainer import gerar_explicacao_completa

logger = logging.getLogger(__name__)


def processar_boleto(analise_id: str, file_base64: str, file_type: str):
    """
    Job principal: processa boleto completo
    
    Args:
        analise_id: ID da análise no MongoDB
        file_base64: Arquivo em base64
        file_type: Tipo do arquivo (image/jpeg, application/pdf)
    
    Returns:
        Resultado da análise
    """
    
    try:
        logger.info(f"[JOB] Iniciando processamento: {analise_id}")
        inicio = datetime.utcnow()
        
        # Imports locais
        from database.mongodb import get_db
        from ml.ocr import extrair_texto_de_base64
        from ml.parser import parse_dados_boleto
        from ml.validator import validar_boleto_febraban
        from ml.model import carregar_modelo, preparar_features, predizer_fraude
        
        # Atualizar status no MongoDB
        db = get_db()
        db.analises.update_one(
            {'_id': analise_id},
            {'$set': {'status': 'processing'}}
        )
        
        # PIPELINE COMPLETO
        
        # 1. OCR - Extrair texto
        logger.info(f"[JOB] {analise_id} - Etapa 1: OCR")
        texto = extrair_texto_de_base64(file_base64)
        
        # 2. Parser - Extrair dados estruturados
        logger.info(f"[JOB] {analise_id} - Etapa 2: Parser")
        dados = parse_dados_boleto(texto)
        
        # 3. Validação FEBRABAN
        logger.info(f"[JOB] {analise_id} - Etapa 3: Validação FEBRABAN")
        validacao = validar_boleto_febraban(dados)
        
        # 4. Modelo ML
        logger.info(f"[JOB] {analise_id} - Etapa 4: Modelo ML")
        modelo = carregar_modelo()
        features = preparar_features(dados)
        predicao_ml = predizer_fraude(modelo, features)
        
        # 5. Resultado final
        is_fraudulento = (not validacao['valido']) or predicao_ml['is_fraudulento']
        
        metodos = []
        if not validacao['valido']:
            metodos.append('validacao_febraban')
        if predicao_ml['is_fraudulento']:
            metodos.append('modelo_ml')
        
        # 6. Gerar explicação humanizada
        logger.info(f"[JOB] {analise_id} - Etapa 5: Explicabilidade")
        explicacao = gerar_explicacao_completa(
            is_fraudulento=is_fraudulento,
            validacao=validacao,
            predicao_ml=predicao_ml,
            dados_extraidos=dados
        )
        
        # Calcular tempo de processamento
        tempo_processamento = (datetime.utcnow() - inicio).total_seconds()
        
        # Salvar resultado no MongoDB
        logger.info(f"[JOB] {analise_id} - Salvando resultado")
        db.analises.update_one(
            {'_id': analise_id},
            {'$set': {
                'status': 'completed',
                'processedAt': datetime.utcnow(),
                'processingTime': tempo_processamento,
                'dadosExtraidos': dados,
                'validacaoTecnica': validacao,
                'predicaoML': predicao_ml,
                'fraudeAnalise': {
                    'isFraudulento': is_fraudulento,
                    'score': predicao_ml['score_fraude'],
                    'confianca': predicao_ml['confianca'],
                    'metodos': metodos,
                    'motivos': validacao['erros'] if not validacao['valido'] else [],
                    'explicacao': explicacao  # Explicabilidade completa!
                }
            }}
        )
        
        logger.info(f"[JOB] ✅ {analise_id} - Concluído em {tempo_processamento:.2f}s")
        logger.info(f"[JOB] Resultado: {'FRAUDULENTO' if is_fraudulento else 'VÁLIDO'}")
        
        return {
            'analise_id': analise_id,
            'status': 'completed',
            'is_fraudulento': is_fraudulento,
            'tempo_processamento': tempo_processamento
        }
        
    except Exception as e:
        logger.error(f"[JOB] ❌ Erro no processamento {analise_id}: {str(e)}")
        
        # Salvar erro no MongoDB
        db = get_db()
        db.analises.update_one(
            {'_id': analise_id},
            {'$set': {
                'status': 'failed',
                'error': str(e),
                'failedAt': datetime.utcnow()
            }}
        )
        
        raise