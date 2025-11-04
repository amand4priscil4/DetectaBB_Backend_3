"""
Explainer - Gera explicações humanizadas para detecção de fraudes
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


# Traduções e categorizações
TRADUCOES_ERROS = {
    "Primeiro dígito verificador do CNPJ inválido": {
        "simples": "CNPJ do beneficiário incorreto",
        "avancado": "Primeiro dígito verificador do CNPJ não corresponde ao algoritmo da Receita Federal",
        "categoria": "dados_beneficiario"
    },
    "Segundo dígito verificador do CNPJ inválido": {
        "simples": "CNPJ do beneficiário incorreto",
        "avancado": "Segundo dígito verificador do CNPJ não corresponde ao algoritmo da Receita Federal",
        "categoria": "dados_beneficiario"
    },
    "Código de barras não tem 44 dígitos": {
        "simples": "Código de barras inválido",
        "avancado": "Código de barras não possui o tamanho padrão FEBRABAN (44 dígitos)",
        "categoria": "codigo_barras"
    },
    "DV do código de barras inválido": {
        "simples": "Código de barras adulterado",
        "avancado": "Dígito verificador do código de barras não corresponde ao cálculo módulo 11",
        "categoria": "codigo_barras"
    },
    "Valor inconsistente": {
        "simples": "Valor do boleto suspeito",
        "avancado": "Valor informado não corresponde ao valor codificado na linha digitável",
        "categoria": "valor"
    }
}

TRADUCOES_FEATURES = {
    "banco": "Código do banco",
    "codigoBanco": "Código bancário FEBRABAN",
    "agencia": "Número da agência",
    "valor": "Valor do boleto",
    "linha_codBanco": "Código do banco na linha digitável",
    "linha_moeda": "Código da moeda",
    "linha_valor": "Valor codificado"
}

CATEGORIAS = {
    "dados_beneficiario": {
        "icone": "🏢",
        "nome": "Dados do Beneficiário",
        "cor": "red"
    },
    "codigo_barras": {
        "icone": "📊",
        "nome": "Código de Barras",
        "cor": "orange"
    },
    "valor": {
        "icone": "💰",
        "nome": "Valor do Boleto",
        "cor": "orange"
    },
    "vencimento": {
        "icone": "📅",
        "nome": "Data de Vencimento",
        "cor": "yellow"
    },
    "banco": {
        "icone": "🏦",
        "nome": "Instituição Bancária",
        "cor": "blue"
    },
    "padrao_ml": {
        "icone": "🤖",
        "nome": "Padrão Detectado por IA",
        "cor": "purple"
    }
}


def gerar_explicacao_completa(
    is_fraudulento: bool,
    validacao: dict,
    predicao_ml: dict,
    dados_extraidos: dict
) -> dict:
    """
    Gera explicação completa em modo simples e avançado
    
    Args:
        is_fraudulento: Se é fraude ou não
        validacao: Resultado da validação FEBRABAN
        predicao_ml: Resultado do modelo ML
        dados_extraidos: Dados extraídos do boleto
    
    Returns:
        Explicação completa estruturada
    """
    
    try:
        logger.info("Gerando explicação humanizada...")
        
        # Determinar nível de risco
        score = predicao_ml.get('score_fraude', 0)
        nivel_risco = determinar_nivel_risco(score, is_fraudulento)
        
        # Coletar razões
        razoes = coletar_razoes(validacao, predicao_ml)
        
        # Modo simples
        simples = gerar_modo_simples(is_fraudulento, razoes, nivel_risco, score)
        
        # Modo avançado
        avancado = gerar_modo_avancado(validacao, predicao_ml, dados_extraidos)
        
        # Recomendação
        recomendacao = gerar_recomendacao(is_fraudulento, nivel_risco, score)
        
        explicacao = {
            "simples": simples,
            "avancado": avancado,
            "razoes": razoes,
            "recomendacao": recomendacao,
            "gerado_em": datetime.utcnow().isoformat()
        }
        
        logger.info("✅ Explicação gerada com sucesso!")
        return explicacao
        
    except Exception as e:
        logger.error(f"Erro ao gerar explicação: {str(e)}")
        return gerar_explicacao_fallback(is_fraudulento)


def gerar_modo_simples(is_fraudulento: bool, razoes: list, nivel_risco: str, score: int) -> dict:
    """Gera explicação simplificada para usuário leigo"""
    
    if is_fraudulento:
        status_texto = "FRAUDULENTO"
        resumo = "Este boleto foi identificado como falso"
        principal_motivo = razoes[0]['titulo'] if razoes else "Inconsistências detectadas"
        acao = "NÃO PAGUE este boleto"
    else:
        status_texto = "VÁLIDO"
        resumo = "Este boleto aparenta ser autêntico"
        principal_motivo = "Todas as validações foram aprovadas"
        acao = "Você pode pagar, mas sempre confira os dados"
    
    # Confiança em texto
    if score >= 80:
        confianca_texto = "Muito Alta"
    elif score >= 60:
        confianca_texto = "Alta"
    elif score >= 40:
        confianca_texto = "Média"
    else:
        confianca_texto = "Baixa"
    
    return {
        "status": status_texto,
        "confianca": confianca_texto,
        "resumo": resumo,
        "principal_motivo": principal_motivo,
        "acao_recomendada": acao,
        "emoji": "🚨" if is_fraudulento else "✅"
    }


def gerar_modo_avancado(validacao: dict, predicao_ml: dict, dados_extraidos: dict) -> dict:
    """Gera explicação técnica detalhada"""
    
    # SHAP detalhado
    features_importantes = []
    if 'features_usadas' in predicao_ml:
        features = predicao_ml['features_usadas']
        # Simular importância (em produção, vem do SHAP real)
        for nome, valor in features.items():
            features_importantes.append({
                "feature": nome,
                "nome_humanizado": TRADUCOES_FEATURES.get(nome, nome),
                "valor": valor,
                "impacto": "alto" if abs(hash(nome) % 100) > 50 else "médio"
            })
    
    return {
        "analise_tecnica": {
            "validacao_febraban": {
                "aprovada": validacao.get('valido', False),
                "total_erros": len(validacao.get('erros', [])),
                "detalhes": validacao.get('detalhes', {})
            },
            "modelo_ml": {
                "classe_predita": predicao_ml.get('classe_predita'),
                "probabilidades": predicao_ml.get('probabilidades', {}),
                "features_usadas": len(predicao_ml.get('features_usadas', {}))
            }
        },
        "metricas": {
            "score_fraude": predicao_ml.get('score_fraude', 0),
            "confianca_modelo": predicao_ml.get('confianca', 0),
            "features_importantes": features_importantes[:5]  # Top 5
        },
        "detalhes_tecnicos": {
            "metodo_deteccao": determinar_metodos_deteccao(validacao, predicao_ml),
            "versao_modelo": "1.0",
            "dados_extraidos": {
                "banco": dados_extraidos.get('banco_nome'),
                "codigo_banco": dados_extraidos.get('codigo_banco'),
                "valor": dados_extraidos.get('valor'),
                "vencimento": dados_extraidos.get('vencimento')
            }
        }
    }


def coletar_razoes(validacao: dict, predicao_ml: dict) -> list:
    """Coleta e categoriza todas as razões de fraude"""
    
    razoes = []
    
    # Razões da validação FEBRABAN
    erros_febraban = validacao.get('erros', [])
    for erro in erros_febraban:
        traducao = TRADUCOES_ERROS.get(erro, {
            "simples": erro,
            "avancado": erro,
            "categoria": "outros"
        })
        
        categoria_key = traducao.get('categoria', 'outros')
        categoria_info = CATEGORIAS.get(categoria_key, CATEGORIAS['padrao_ml'])
        
        razoes.append({
            "gravidade": "critica",  # Erros FEBRABAN são sempre críticos
            "categoria": categoria_key,
            "categoria_nome": categoria_info['nome'],
            "icone": categoria_info['icone'],
            "cor": categoria_info['cor'],
            "titulo": traducao['simples'],
            "descricao_simples": traducao['simples'],
            "descricao_avancada": traducao['avancado'],
            "impacto": 1.0,
            "fonte": "Validação FEBRABAN"
        })
    
    # Razões do modelo ML (se detectou fraude)
    if predicao_ml.get('is_fraudulento'):
        confianca = predicao_ml.get('confianca', 0)
        
        # Determinar gravidade baseada na confiança
        if confianca >= 0.8:
            gravidade = "alta"
        elif confianca >= 0.6:
            gravidade = "media"
        else:
            gravidade = "baixa"
        
        razoes.append({
            "gravidade": gravidade,
            "categoria": "padrao_ml",
            "categoria_nome": "Padrão Detectado por IA",
            "icone": "🤖",
            "cor": "purple",
            "titulo": "Padrão suspeito identificado",
            "descricao_simples": "A inteligência artificial identificou características atípicas neste boleto",
            "descricao_avancada": f"Modelo de Machine Learning (Random Forest) detectou padrão com {confianca*100:.1f}% de confiança baseado em {len(predicao_ml.get('features_usadas', {}))} características analisadas",
            "impacto": confianca,
            "fonte": "Modelo de IA"
        })
    
    # Ordenar por gravidade e impacto
    ordem_gravidade = {"critica": 4, "alta": 3, "media": 2, "baixa": 1}
    razoes.sort(key=lambda x: (ordem_gravidade.get(x['gravidade'], 0), x['impacto']), reverse=True)
    
    return razoes


def gerar_recomendacao(is_fraudulento: bool, nivel_risco: str, score: int) -> dict:
    """Gera recomendação de ação para o usuário"""
    
    if not is_fraudulento:
        return {
            "nivel_risco": "BAIXO",
            "emoji": "✅",
            "cor": "green",
            "acao_principal": "PODE PAGAR",
            "mensagem": "Este boleto passou nas verificações de segurança. Ainda assim, sempre confira os dados do beneficiário antes de efetuar o pagamento.",
            "proximos_passos": [
                "Confira o nome do beneficiário",
                "Verifique o valor e vencimento",
                "Efetue o pagamento com segurança"
            ]
        }
    
    # Boleto fraudulento
    if nivel_risco == "CRITICO":
        return {
            "nivel_risco": "CRÍTICO",
            "emoji": "🚨",
            "cor": "red",
            "acao_principal": "NÃO PAGAR",
            "mensagem": "Este boleto apresenta sinais CLAROS de fraude. NÃO efetue o pagamento sob nenhuma circunstância. Entre em contato com o emissor através de canais oficiais para verificar a autenticidade.",
            "proximos_passos": [
                "❌ NÃO efetue o pagamento",
                "📞 Entre em contato com o emissor por canais oficiais",
                "🚨 Reporte a tentativa de fraude às autoridades",
                "⚠️ Alerte outras pessoas sobre este golpe"
            ]
        }
    elif nivel_risco == "ALTO":
        return {
            "nivel_risco": "ALTO",
            "emoji": "⚠️",
            "cor": "orange",
            "acao_principal": "SUSPEITO - NÃO PAGAR",
            "mensagem": "Este boleto apresenta características SUSPEITAS. Recomendamos fortemente que você NÃO efetue o pagamento até confirmar sua autenticidade com o emissor.",
            "proximos_passos": [
                "🛑 Suspenda o pagamento",
                "📞 Confirme com o emissor por telefone oficial",
                "🔍 Solicite um novo boleto se houver dúvidas",
                "⚠️ Mantenha vigilância contra possíveis golpes"
            ]
        }
    else:
        return {
            "nivel_risco": "MÉDIO",
            "emoji": "ℹ️",
            "cor": "yellow",
            "acao_principal": "VERIFICAR ANTES DE PAGAR",
            "mensagem": "Este boleto apresenta algumas inconsistências. Por precaução, confirme os dados com o emissor antes de efetuar o pagamento.",
            "proximos_passos": [
                "🔍 Verifique os dados do beneficiário",
                "📞 Confirme com o emissor se possível",
                "⏸️ Considere aguardar confirmação antes de pagar",
                "✅ Prossiga com cautela após verificação"
            ]
        }


def determinar_nivel_risco(score: int, is_fraudulento: bool) -> str:
    """Determina o nível de risco baseado no score"""
    
    if not is_fraudulento:
        return "BAIXO"
    
    if score >= 80:
        return "CRITICO"
    elif score >= 60:
        return "ALTO"
    elif score >= 40:
        return "MEDIO"
    else:
        return "BAIXO"


def determinar_metodos_deteccao(validacao: dict, predicao_ml: dict) -> list:
    """Determina quais métodos detectaram fraude"""
    
    metodos = []
    
    if not validacao.get('valido', True):
        metodos.append("validacao_febraban")
    
    if predicao_ml.get('is_fraudulento', False):
        metodos.append("modelo_ml")
    
    return metodos


def gerar_explicacao_fallback(is_fraudulento: bool) -> dict:
    """Gera explicação básica em caso de erro"""
    
    return {
        "simples": {
            "status": "FRAUDULENTO" if is_fraudulento else "VÁLIDO",
            "resumo": "Análise concluída",
            "acao_recomendada": "Verifique os detalhes"
        },
        "avancado": {},
        "razoes": [],
        "recomendacao": {
            "nivel_risco": "DESCONHECIDO",
            "mensagem": "Erro ao gerar explicação detalhada"
        }
    }