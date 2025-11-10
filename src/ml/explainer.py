"""
Sistema de Explicabilidade para Detecção de Fraudes em Boletos
Gera explicações humanizadas e compreensíveis sobre as decisões do modelo
COM LINGUAGEM CAUTELOSA E PROFISSIONAL
"""

import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def gerar_explicacao_humanizada(
    dados_extraidos: Dict,
    resultado_validacao: Dict,
    predicao_ml: Dict,
    shap_values: np.ndarray = None,
    feature_names: List[str] = None
) -> Dict:
    """
    Gera explicação humanizada e compreensível do resultado da análise
    COM LINGUAGEM CAUTELOSA, SUGESTIVA E PROFISSIONAL
    """
    
    is_fraudulento = predicao_ml.get('is_fraudulento', False)
    score_fraude = predicao_ml.get('score_fraude', 0.0)
    confianca = predicao_ml.get('confianca', 0.0)
    
    # Determinar níveis de confiança
    if confianca >= 0.9:
        nivel_confianca = "Muito Alta"
    elif confianca >= 0.75:
        nivel_confianca = "Alta"
    elif confianca >= 0.6:
        nivel_confianca = "Média"
    else:
        nivel_confianca = "Baixa"
    
    # LINGUAGEM SUGESTIVA E PROFISSIONAL
    if is_fraudulento:
        status = "POSSIVELMENTE FALSO"
        resumo = "Este boleto apresenta características suspeitas que sugerem possível falsificação."
        acao_recomendada = "Recomendamos NÃO efetuar o pagamento sem verificação adicional"
    else:
        status = "POSSIVELMENTE AUTÊNTICO"
        resumo = "Este boleto aparenta ser autêntico, mas sempre confira os dados com o emissor."
        acao_recomendada = "Você pode prosseguir com cautela, mas sempre verifique os dados"
    
    # Explicação simples para usuários leigos
    explicacao_simples = {
        "status": status,
        "confianca": nivel_confianca,
        "resumo": resumo,
        "principal_motivo": _identificar_principal_motivo(resultado_validacao, predicao_ml),
        "acao_recomendada": acao_recomendada
    }
    
    # Explicação avançada para usuários técnicos
    explicacao_avancada = {
        "analise_tecnica": {
            "modelo_ml": "Random Forest Classifier",
            "score_fraude": round(score_fraude * 100, 2),
            "confianca_percentual": round(confianca * 100, 2),
            "probabilidades": predicao_ml.get('probabilidades', {}),
            "limiar_decisao": 0.5
        },
        "metricas": {
            "features_analisadas": len(feature_names) if feature_names else 0,
            "validacoes_tecnicas": len(resultado_validacao.get('erros', [])),
            "peso_validacao": 0.4,
            "peso_ml": 0.6
        },
        "detalhes_tecnicos": {
            "validacao_febraban": not resultado_validacao.get('valido', True),
            "erros_encontrados": resultado_validacao.get('erros', []),
            "features_importantes": _extrair_features_importantes(shap_values, feature_names) if shap_values is not None else []
        }
    }
    
    # Gerar razões detalhadas COM LINGUAGEM SUGESTIVA
    razoes = _gerar_razoes_detalhadas(dados_extraidos, resultado_validacao, predicao_ml)
    
    # Recomendação final COM LINGUAGEM CAUTELOSA
    recomendacao = _gerar_recomendacao(is_fraudulento, confianca, score_fraude)
    
    return {
        "simples": explicacao_simples,
        "avancado": explicacao_avancada,
        "razoes": razoes,
        "recomendacao": recomendacao,
        "gerado_em": datetime.now().isoformat()
    }


def _identificar_principal_motivo(resultado_validacao: Dict, predicao_ml: Dict) -> str:
    """Identifica o principal motivo da classificação COM LINGUAGEM SUGESTIVA"""
    
    erros = resultado_validacao.get('erros', [])
    
    if erros:
        # Priorizar erros críticos
        erros_criticos = [e for e in erros if 'inválido' in e.lower() or 'incorreto' in e.lower()]
        if erros_criticos:
            return f"Possível irregularidade detectada: {erros_criticos[0]}"
        return f"Inconsistência identificada: {erros[0]}"
    
    score = predicao_ml.get('score_fraude', 0)
    if score > 0.8:
        return "Modelo de ML identificou padrão suspeito com alta confiança"
    elif score > 0.6:
        return "Modelo de ML identificou características atípicas"
    elif score < 0.3:
        return "Todas as verificações sugerem autenticidade"
    else:
        return "Análise inconclusiva - recomenda-se verificação manual"


def _gerar_razoes_detalhadas(
    dados_extraidos: Dict,
    resultado_validacao: Dict,
    predicao_ml: Dict
) -> List[Dict]:
    """
    Gera lista de razões detalhadas para a classificação
    COM LINGUAGEM SUGESTIVA E PROFISSIONAL
    """
    razoes = []
    
    # Razões baseadas em validação técnica
    erros = resultado_validacao.get('erros', [])
    for erro in erros:
        gravidade = _determinar_gravidade(erro)
        razoes.append({
            "gravidade": gravidade,
            "categoria": "validacao_tecnica",
            "categoria_nome": "Validação Técnica",
            "cor": _get_cor_gravidade(gravidade),
            "titulo": "Possível Inconsistência Técnica",
            "descricao_simples": f"Foi identificada uma possível irregularidade: {erro}",
            "descricao_avancada": f"Validação FEBRABAN: {erro}. Isso pode indicar adulteração ou erro na geração do boleto.",
            "impacto": _calcular_impacto(gravidade),
            "fonte": "Validação FEBRABAN"
        })
    
    # Razões baseadas em ML
    score_fraude = predicao_ml.get('score_fraude', 0)
    if score_fraude > 0.7:
        razoes.append({
            "gravidade": "alta",
            "categoria": "machine_learning",
            "categoria_nome": "Análise de Padrões",
            "cor": "danger",
            "titulo": "Padrão Suspeito Identificado",
            "descricao_simples": f"O modelo de IA identificou características que sugerem possível fraude (confiança: {score_fraude*100:.0f}%)",
            "descricao_avancada": f"Score de fraude: {score_fraude:.2f}. O modelo Random Forest, treinado com milhares de boletos reais e falsos, identificou padrões estatísticos atípicos que podem indicar falsificação.",
            "impacto": 85,
            "fonte": "Machine Learning"
        })
    elif score_fraude < 0.3:
        razoes.append({
            "gravidade": "baixa",
            "categoria": "machine_learning",
            "categoria_nome": "Análise de Padrões",
            "cor": "success",
            "titulo": "Padrão Aparentemente Normal",
            "descricao_simples": f"O modelo de IA não identificou características suspeitas significativas (confiança: {(1-score_fraude)*100:.0f}%)",
            "descricao_avancada": f"Score de autenticidade: {1-score_fraude:.2f}. As características analisadas sugerem conformidade com padrões de boletos legítimos.",
            "impacto": 15,
            "fonte": "Machine Learning"
        })
    
    # Razões baseadas em dados extraídos
    if dados_extraidos.get('valor', 0) > 10000:
        razoes.append({
            "gravidade": "media",
            "categoria": "valor",
            "categoria_nome": "Análise de Valor",
            "cor": "warning",
            "titulo": "Valor Elevado",
            "descricao_simples": f"O valor do boleto é elevado (R$ {dados_extraidos['valor']:,.2f}). Recomenda-se verificação adicional.",
            "descricao_avancada": f"Boletos com valores acima de R$ 10.000,00 merecem atenção extra. Em caso de fraude, o prejuízo seria significativo.",
            "impacto": 60,
            "fonte": "Análise de Risco"
        })
    
    # Se não houver razões, adicionar uma genérica
    if not razoes:
        razoes.append({
            "gravidade": "baixa",
            "categoria": "geral",
            "categoria_nome": "Análise Geral",
            "cor": "primary",
            "titulo": "Análise Completa Realizada",
            "descricao_simples": "Todas as verificações de segurança foram executadas.",
            "descricao_avancada": "O boleto passou por validação FEBRABAN, análise de Machine Learning e verificações de padrões suspeitos.",
            "impacto": 30,
            "fonte": "Sistema DetectaBB"
        })
    
    return razoes


def _gerar_recomendacao(is_fraudulento: bool, confianca: float, score_fraude: float) -> Dict:
    """Gera recomendação personalizada COM LINGUAGEM CAUTELOSA E PROFISSIONAL"""
    
    if is_fraudulento:
        if confianca >= 0.85:
            return {
                "nivel_risco": "ALTO",
                "cor": "danger",
                "acao_principal": "NÃO PAGAR (Alta Probabilidade de Fraude)",
                "mensagem": "Este boleto apresenta FORTES indícios de falsificação. Recomendamos fortemente não efetuar o pagamento.",
                "proximos_passos": [
                    "NÃO efetue o pagamento deste boleto",
                    "Entre em contato DIRETAMENTE com a empresa emissora pelos canais oficiais",
                    "Reporte este possível boleto falso às autoridades competentes",
                    "Solicite um novo boleto através de canais seguros e oficiais",
                    "Verifique se o e-mail/site de origem é legítimo"
                ]
            }
        elif confianca >= 0.65:
            return {
                "nivel_risco": "MÉDIO-ALTO",
                "cor": "warning",
                "acao_principal": "VERIFICAR ANTES DE PAGAR",
                "mensagem": "Este boleto apresenta características suspeitas. É necessária verificação adicional antes do pagamento.",
                "proximos_passos": [
                    "Aguarde! Não pague ainda",
                    "Confirme os dados com a empresa emissora pelos canais oficiais",
                    "Verifique se os dados bancários correspondem aos oficiais",
                    "Confirme a autenticidade do e-mail/site de origem",
                    "Solicite nova via por canal seguro, se necessário"
                ]
            }
        else:
            return {
                "nivel_risco": "MÉDIO",
                "cor": "warning",
                "acao_principal": "PROCEDER COM CAUTELA",
                "mensagem": "Algumas irregularidades foram detectadas. Recomendamos verificação antes do pagamento.",
                "proximos_passos": [
                    "Confira cuidadosamente todos os dados do boleto",
                    "Em caso de dúvida, contate a empresa emissora",
                    "Verifique se o valor e vencimento estão corretos",
                    "Confirme se o banco é o esperado para este tipo de cobrança"
                ]
            }
    else:
        if confianca >= 0.85:
            return {
                "nivel_risco": "BAIXO",
                "cor": "success",
                "acao_principal": "PODE PAGAR (Com Verificação)",
                "mensagem": "Este boleto aparenta ser autêntico. Mesmo assim, sempre confira os dados antes do pagamento.",
                "proximos_passos": [
                    "Boleto aparenta ser legítimo",
                    "Confira os dados: valor, vencimento e beneficiário",
                    "Verifique se o banco corresponde ao esperado",
                    "Em caso de qualquer dúvida, contate o emissor",
                    "Proceda com o pagamento normalmente"
                ]
            }
        elif confianca >= 0.65:
            return {
                "nivel_risco": "BAIXO-MÉDIO",
                "cor": "success",
                "acao_principal": "PROVÁVEL AUTENTICIDADE",
                "mensagem": "O boleto passou nas verificações básicas, mas sempre confirme os dados importantes.",
                "proximos_passos": [
                    "Verificações de segurança aprovadas",
                    "Confira valor e vencimento",
                    "Em caso de dúvida, confirme com o emissor",
                    "Você pode prosseguir com o pagamento"
                ]
            }
        else:
            return {
                "nivel_risco": "INCERTO",
                "cor": "medium",
                "acao_principal": "VERIFICAR MANUALMENTE",
                "mensagem": "Não foi possível determinar com certeza. Recomendamos verificação manual cuidadosa.",
                "proximos_passos": [
                    "Analise cuidadosamente todos os dados",
                    "Confirme a autenticidade com o emissor",
                    "Verifique os dados bancários",
                    "Proceda somente após confirmação"
                ]
            }


def _determinar_gravidade(erro: str) -> str:
    """Determina a gravidade de um erro"""
    erro_lower = erro.lower()
    
    if any(palavra in erro_lower for palavra in ['inválido', 'incorreto', 'falha crítica']):
        return 'critica'
    elif any(palavra in erro_lower for palavra in ['dígito verificador', 'código de barras']):
        return 'alta'
    elif any(palavra in erro_lower for palavra in ['formato', 'incompleto']):
        return 'media'
    else:
        return 'baixa'


def _calcular_impacto(gravidade: str) -> int:
    """Calcula o impacto numérico baseado na gravidade"""
    impactos = {
        'critica': 95,
        'alta': 80,
        'media': 60,
        'baixa': 30
    }
    return impactos.get(gravidade, 50)


def _get_cor_gravidade(gravidade: str) -> str:
    """Retorna cor Ionic para gravidade"""
    cores = {
        'critica': 'danger',
        'alta': 'warning',
        'media': 'medium',
        'baixa': 'primary'
    }
    return cores.get(gravidade, 'medium')


def _extrair_features_importantes(shap_values: np.ndarray, feature_names: List[str]) -> List[Dict]:
    """Extrai as features mais importantes baseado nos valores SHAP"""
    if shap_values is None or feature_names is None:
        return []
    
    try:
        # Pegar valores absolutos médios
        importancias = np.abs(shap_values).mean(axis=0)
        
        # Top 5 features
        top_indices = np.argsort(importancias)[-5:][::-1]
        
        features_importantes = []
        for idx in top_indices:
            features_importantes.append({
                "nome": feature_names[idx],
                "importancia": float(importancias[idx]),
                "impacto_percentual": float(importancias[idx] / importancias.sum() * 100)
            })
        
        return features_importantes
    except Exception as e:
        logger.error(f"Erro ao extrair features importantes: {e}")
        return []
