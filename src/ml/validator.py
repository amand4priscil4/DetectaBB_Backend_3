"""
Validação FEBRABAN - Valida boletos segundo regras do padrão bancário brasileiro
"""

import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def validar_boleto_febraban(dados: dict) -> dict:
    """
    Valida boleto segundo regras FEBRABAN
    
    Args:
        dados: Dicionário com dados extraídos do boleto
    
    Returns:
        {
            'valido': bool,
            'erros': [str],
            'detalhes': {...}
        }
    """
    
    erros = []
    detalhes = {}
    
    logger.info("Iniciando validação FEBRABAN...")
    
    try:
        # 1. VALIDAR LINHA DIGITÁVEL
        if dados.get('linha_digitavel'):
            resultado_linha = validar_linha_digitavel(dados['linha_digitavel'])
            if not resultado_linha['valido']:
                erros.extend(resultado_linha['erros'])
            detalhes['linha_digitavel'] = resultado_linha
        else:
            erros.append("Linha digitável não encontrada")
        
        # 2. VALIDAR CÓDIGO DE BARRAS
        if dados.get('codigo_barras'):
            resultado_codigo = validar_codigo_barras(dados['codigo_barras'])
            if not resultado_codigo['valido']:
                erros.extend(resultado_codigo['erros'])
            detalhes['codigo_barras'] = resultado_codigo
        
        # 3. VALIDAR VALOR
        if dados.get('valor'):
            resultado_valor = validar_valor(dados['valor'])
            if not resultado_valor['valido']:
                erros.extend(resultado_valor['erros'])
            detalhes['valor'] = resultado_valor
        else:
            erros.append("Valor não encontrado")
        
        # 4. VALIDAR VENCIMENTO
        if dados.get('vencimento'):
            resultado_vencimento = validar_vencimento(dados['vencimento'])
            if not resultado_vencimento['valido']:
                erros.extend(resultado_vencimento['erros'])
            detalhes['vencimento'] = resultado_vencimento
        else:
            erros.append("Vencimento não encontrado")
        
        # 5. VALIDAR CNPJ
        if dados.get('beneficiario_cnpj'):
            resultado_cnpj = validar_cnpj(dados['beneficiario_cnpj'])
            if not resultado_cnpj['valido']:
                erros.extend(resultado_cnpj['erros'])
            detalhes['cnpj'] = resultado_cnpj
        
        # 6. VALIDAR BANCO
        if dados.get('codigo_banco'):
            resultado_banco = validar_codigo_banco(dados['codigo_banco'])
            if not resultado_banco['valido']:
                erros.extend(resultado_banco['erros'])
            detalhes['banco'] = resultado_banco
        else:
            erros.append("Código do banco não encontrado")
        
        valido = len(erros) == 0
        
        if valido:
            logger.info("✅ Boleto VÁLIDO segundo FEBRABAN")
        else:
            logger.warning(f"❌ Boleto INVÁLIDO: {len(erros)} erros encontrados")
        
        return {
            'valido': valido,
            'erros': erros,
            'detalhes': detalhes
        }
        
    except Exception as e:
        logger.error(f"Erro na validação: {str(e)}")
        return {
            'valido': False,
            'erros': [f"Erro na validação: {str(e)}"],
            'detalhes': {}
        }


def validar_linha_digitavel(linha: str) -> dict:
    """
    Valida linha digitável (47 dígitos com 3 dígitos verificadores)
    """
    
    erros = []
    
    try:
        # Remover formatação
        digitos = re.sub(r'[^\d]', '', linha)
        
        # Verificar tamanho
        if len(digitos) != 47:
            erros.append(f"Linha digitável deve ter 47 dígitos (tem {len(digitos)})")
            return {'valido': False, 'erros': erros}
        
        # Dividir em campos
        campo1 = digitos[0:10]   # 10 dígitos (9 + DV)
        campo2 = digitos[10:21]  # 11 dígitos (10 + DV)
        campo3 = digitos[21:32]  # 11 dígitos (10 + DV)
        campo4 = digitos[32:33]  # 1 dígito (DV geral)
        campo5 = digitos[33:47]  # 14 dígitos (fator + valor)
        
        # Validar DV do campo 1
        dv1_informado = campo1[9]
        dv1_calculado = calcular_dv_modulo10(campo1[0:9])
        if dv1_informado != dv1_calculado:
            erros.append(f"DV1 inválido (esperado: {dv1_calculado}, encontrado: {dv1_informado})")
        
        # Validar DV do campo 2
        dv2_informado = campo2[10]
        dv2_calculado = calcular_dv_modulo10(campo2[0:10])
        if dv2_informado != dv2_calculado:
            erros.append(f"DV2 inválido (esperado: {dv2_calculado}, encontrado: {dv2_informado})")
        
        # Validar DV do campo 3
        dv3_informado = campo3[10]
        dv3_calculado = calcular_dv_modulo10(campo3[0:10])
        if dv3_informado != dv3_calculado:
            erros.append(f"DV3 inválido (esperado: {dv3_calculado}, encontrado: {dv3_informado})")
        
        return {
            'valido': len(erros) == 0,
            'erros': erros
        }
        
    except Exception as e:
        return {
            'valido': False,
            'erros': [f"Erro ao validar linha digitável: {str(e)}"]
        }


def validar_codigo_barras(codigo: str) -> dict:
    """
    Valida código de barras (44 dígitos com DV na posição 4)
    """
    
    erros = []
    
    try:
        # Remover formatação
        digitos = re.sub(r'[^\d]', '', codigo)
        
        # Verificar tamanho
        if len(digitos) != 44:
            erros.append(f"Código de barras deve ter 44 dígitos (tem {len(digitos)})")
            return {'valido': False, 'erros': erros}
        
        # DV está na posição 4 (índice 4)
        dv_informado = digitos[4]
        
        # Montar código sem o DV
        codigo_sem_dv = digitos[0:4] + digitos[5:44]
        
        # Calcular DV
        dv_calculado = calcular_dv_modulo11(codigo_sem_dv)
        
        if dv_informado != dv_calculado:
            erros.append(f"DV do código de barras inválido (esperado: {dv_calculado}, encontrado: {dv_informado})")
        
        return {
            'valido': len(erros) == 0,
            'erros': erros
        }
        
    except Exception as e:
        return {
            'valido': False,
            'erros': [f"Erro ao validar código de barras: {str(e)}"]
        }


def validar_valor(valor: float) -> dict:
    """
    Valida valor do boleto
    """
    
    erros = []
    
    if valor <= 0:
        erros.append("Valor deve ser maior que zero")
    
    if valor > 9999999.99:
        erros.append("Valor excede limite máximo (R$ 9.999.999,99)")
    
    return {
        'valido': len(erros) == 0,
        'erros': erros
    }


def validar_vencimento(vencimento_str: str) -> dict:
    """
    Valida data de vencimento
    """
    
    erros = []
    
    try:
        # Converter para datetime
        vencimento = datetime.strptime(vencimento_str, '%d/%m/%Y')
        hoje = datetime.now()
        
        # Vencimento não pode ser muito antigo (>5 anos)
        if (hoje - vencimento).days > 5 * 365:
            erros.append(f"Boleto com vencimento muito antigo ({vencimento_str})")
        
        # Vencimento não pode ser muito futuro (>2 anos)
        if (vencimento - hoje).days > 2 * 365:
            erros.append(f"Boleto com vencimento muito distante ({vencimento_str})")
        
        return {
            'valido': len(erros) == 0,
            'erros': erros
        }
        
    except Exception as e:
        return {
            'valido': False,
            'erros': [f"Data de vencimento inválida: {str(e)}"]
        }


def validar_cnpj(cnpj: str) -> dict:
    """
    Valida CNPJ brasileiro
    """
    
    erros = []
    
    try:
        # Remover formatação
        cnpj_digitos = re.sub(r'[^\d]', '', cnpj)
        
        # Verificar tamanho
        if len(cnpj_digitos) != 14:
            erros.append(f"CNPJ deve ter 14 dígitos")
            return {'valido': False, 'erros': erros}
        
        # Verificar se não é sequência repetida
        if cnpj_digitos == cnpj_digitos[0] * 14:
            erros.append("CNPJ inválido (sequência repetida)")
            return {'valido': False, 'erros': erros}
        
        # Validar primeiro dígito verificador
        soma = 0
        peso = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        for i in range(12):
            soma += int(cnpj_digitos[i]) * peso[i]
        
        resto = soma % 11
        dv1 = 0 if resto < 2 else 11 - resto
        
        if int(cnpj_digitos[12]) != dv1:
            erros.append("Primeiro dígito verificador do CNPJ inválido")
        
        # Validar segundo dígito verificador
        soma = 0
        peso = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        for i in range(13):
            soma += int(cnpj_digitos[i]) * peso[i]
        
        resto = soma % 11
        dv2 = 0 if resto < 2 else 11 - resto
        
        if int(cnpj_digitos[13]) != dv2:
            erros.append("Segundo dígito verificador do CNPJ inválido")
        
        return {
            'valido': len(erros) == 0,
            'erros': erros
        }
        
    except Exception as e:
        return {
            'valido': False,
            'erros': [f"Erro ao validar CNPJ: {str(e)}"]
        }


def validar_codigo_banco(codigo: str) -> dict:
    """
    Valida se código do banco existe
    """
    
    bancos_validos = {
        '001', '033', '104', '237', '341', '748', '756',
        '077', '260', '290', '403', '422', '140', '197'
    }
    
    erros = []
    
    if codigo not in bancos_validos:
        erros.append(f"Código de banco desconhecido: {codigo}")
    
    return {
        'valido': len(erros) == 0,
        'erros': erros
    }


def calcular_dv_modulo10(sequencia: str) -> str:
    """
    Calcula dígito verificador usando módulo 10
    Usado nos campos da linha digitável
    """
    
    soma = 0
    multiplicador = 2
    
    # Processar da direita para esquerda
    for i in range(len(sequencia) - 1, -1, -1):
        resultado = int(sequencia[i]) * multiplicador
        if resultado > 9:
            resultado = resultado // 10 + resultado % 10
        soma += resultado
        multiplicador = 1 if multiplicador == 2 else 2
    
    resto = soma % 10
    dv = 0 if resto == 0 else 10 - resto
    
    return str(dv)


def calcular_dv_modulo11(sequencia: str) -> str:
    """
    Calcula dígito verificador usando módulo 11
    Usado no código de barras
    """
    
    soma = 0
    multiplicador = 2
    
    # Processar da direita para esquerda
    for i in range(len(sequencia) - 1, -1, -1):
        soma += int(sequencia[i]) * multiplicador
        multiplicador += 1
        if multiplicador > 9:
            multiplicador = 2
    
    resto = soma % 11
    dv = 11 - resto
    
    # Regras especiais do módulo 11
    if dv == 0 or dv == 10 or dv == 11:
        dv = 1
    
    return str(dv)