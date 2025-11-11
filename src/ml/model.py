"""
Carrega e usa o modelo Random Forest para detecção de fraudes
"""

import pickle
import pandas as pd
import numpy as np
import logging
import os

logger = logging.getLogger(__name__)

# Cache do modelo
_modelo_cache = None


def carregar_modelo(caminho: str = 'src/models/modelo_boleto.pkl'):
    """
    Carrega modelo treinado
    """
    global _modelo_cache
    
    if _modelo_cache is not None:
        return _modelo_cache
    
    try:
        logger.info(f"Carregando modelo: {caminho}")
        
        if not os.path.exists(caminho):
            raise Exception(f"Modelo não encontrado: {caminho}")
        
        with open(caminho, 'rb') as f:
            _modelo_cache = pickle.load(f)
        
        logger.info("✅ Modelo carregado com sucesso!")
        return _modelo_cache
        
    except Exception as e:
        logger.error(f"❌ Erro ao carregar modelo: {str(e)}")
        raise


def preparar_features(dados_extraidos: dict) -> dict:
    """
    Prepara features para o modelo a partir dos dados extraídos
    """
    
    try:
        # Extrair código do banco da linha digitável
        linha = dados_extraidos.get('linha_digitavel', '') or ''
        linha_digitos = linha.replace('.', '').replace(' ', '')
        
        linha_codBanco = int(linha_digitos[:3]) if len(linha_digitos) >= 3 else 0
        linha_moeda = int(linha_digitos[3]) if len(linha_digitos) >= 4 else 0
        
        # Extrair valor da linha digitável (últimos 10 dígitos são fator + valor)
        linha_valor = int(linha_digitos[37:47]) if len(linha_digitos) >= 47 else 0
        
        # Código do banco
        codigo_banco = dados_extraidos.get('codigo_banco', 0)
        if codigo_banco is None:
            codigo_banco = 0
        else:
            codigo_banco = int(codigo_banco)
        
        # Valor do boleto (converter para centavos)
        valor = dados_extraidos.get('valor', 0.0)
        if valor is None:
            valor = 0.0
        else:
            valor = float(valor)
        
        # Agência (se disponível)
        agencia = dados_extraidos.get('agencia', 0)
        if agencia is None:
            agencia = 0
        else:
            try:
                # Remove traço se houver (ex: "1234-5" -> "1234")
                if isinstance(agencia, str):
                    agencia = agencia.split('-')[0]
                agencia = int(agencia)
            except:
                agencia = 0
        
        features = {
            'banco': codigo_banco,
            'codigoBanco': codigo_banco,
            'agencia': agencia,
            'valor': valor,
            'linha_codBanco': linha_codBanco,
            'linha_moeda': linha_moeda,
            'linha_valor': linha_valor
        }
        
        logger.info(f"Features preparadas: {features}")
        return features
        
    except Exception as e:
        logger.error(f"Erro ao preparar features: {str(e)}")
        raise


def predizer_fraude(modelo, features: dict) -> dict:
    """
    Faz predição de fraude usando o modelo
    """
    
    try:
        # Criar DataFrame com as features
        feature_names = ['banco', 'codigoBanco', 'agencia', 'valor', 
                        'linha_codBanco', 'linha_moeda', 'linha_valor']
        
        features_array = [features[name] for name in feature_names]
        df = pd.DataFrame([features_array], columns=feature_names)
        
        # Predição
        classe = modelo.predict(df)[0]
        probabilidades = modelo.predict_proba(df)[0]
        
        # 0 = falso, 1 = verdadeiro
        prob_falso = probabilidades[0]
        prob_verdadeiro = probabilidades[1]
        
        resultado = {
    'is_fraudulento': bool(classe == 0),  # Converter para bool Python
    'classe_predita': int(classe),
    'score_fraude': int(prob_falso * 100),
    'confianca': float(max(prob_falso, prob_verdadeiro)),
    'probabilidades': {
        'falso': float(prob_falso),
        'verdadeiro': float(prob_verdadeiro)
    },
    'features_usadas': features
}
        
        logger.info(f"Predição: {'FALSO' if resultado['is_fraudulento'] else 'VERDADEIRO'} "
                   f"(confiança: {resultado['confianca']*100:.1f}%)")
        
        return resultado
        
    except Exception as e:
        logger.error(f"Erro na predição: {str(e)}")
        raise
