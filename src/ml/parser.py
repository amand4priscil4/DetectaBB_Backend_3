"""
Parser - Extrai campos estruturados de boletos
"""

import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def parse_dados_boleto(texto_ocr: str) -> dict:
    """
    Extrai campos estruturados do texto OCR de um boleto
    
    Args:
        texto_ocr: Texto extraído pelo OCR
    
    Returns:
        Dicionário com dados estruturados do boleto
    """
    
    dados = {
        'codigo_barras': None,
        'linha_digitavel': None,
        'valor': None,
        'vencimento': None,
        'beneficiario_nome': None,
        'beneficiario_cnpj': None,
        'codigo_banco': None,
        'banco_nome': None,
        'agencia': None
    }
    
    try:
        logger.info("Iniciando parsing de boleto...")
        
        # 1. EXTRAIR LINHA DIGITÁVEL (47 dígitos com pontos/espaços)
        linha_digitavel = extrair_linha_digitavel(texto_ocr)
        if linha_digitavel:
            dados['linha_digitavel'] = linha_digitavel
            logger.info(f"✅ Linha digitável: {linha_digitavel}")
            
            # Extrair código do banco da linha digitável (3 primeiros dígitos)
            dados['codigo_banco'] = linha_digitavel[:3]
        
        # 2. EXTRAIR CÓDIGO DE BARRAS (44 dígitos sem formatação)
        codigo_barras = extrair_codigo_barras(texto_ocr)
        if codigo_barras:
            dados['codigo_barras'] = codigo_barras
            logger.info(f"✅ Código de barras: {codigo_barras}")
        
        # 3. EXTRAIR VALOR
        valor = extrair_valor(texto_ocr)
        if valor:
            dados['valor'] = valor
            logger.info(f"✅ Valor: R$ {valor}")
        
        # 4. EXTRAIR VENCIMENTO
        vencimento = extrair_vencimento(texto_ocr)
        if vencimento:
            dados['vencimento'] = vencimento
            logger.info(f"✅ Vencimento: {vencimento}")
        
        # 5. EXTRAIR CNPJ
        cnpj = extrair_cnpj(texto_ocr)
        if cnpj:
            dados['beneficiario_cnpj'] = cnpj
            logger.info(f"✅ CNPJ: {cnpj}")
        
        # 6. IDENTIFICAR BANCO
        banco = identificar_banco(dados['codigo_banco'])
        if banco:
            dados['banco_nome'] = banco
            logger.info(f"✅ Banco: {banco}")
        
        logger.info("✅ Parsing concluído!")
        return dados
        
    except Exception as e:
        logger.error(f"❌ Erro no parsing: {str(e)}")
        return dados


def extrair_linha_digitavel(texto: str) -> str:
    """
    Extrai linha digitável do boleto (47 dígitos)
    Formato: AAAAA.AAAAA BBBBB.BBBBBB CCCCC.CCCCCC D EEEEEEEEEEEEEE
    """
    
    # Remover quebras de linha
    texto = texto.replace('\n', ' ')
    
    # Padrão: 5 dígitos . 5 dígitos espaço 5 dígitos . 6 dígitos espaço 5 dígitos . 6 dígitos espaço 1 dígito espaço 14 dígitos
    padrao = r'(\d{5})[.\s]?(\d{5})\s?(\d{5})[.\s]?(\d{6})\s?(\d{5})[.\s]?(\d{6})\s?(\d)\s?(\d{14})'
    
    match = re.search(padrao, texto)
    if match:
        # Reconstruir linha digitável formatada
        grupos = match.groups()
        linha = f"{grupos[0]}.{grupos[1]} {grupos[2]}.{grupos[3]} {grupos[4]}.{grupos[5]} {grupos[6]} {grupos[7]}"
        return linha
    
    # Tentar sem formatação (47 dígitos seguidos)
    padrao_simples = r'\b(\d{47})\b'
    match = re.search(padrao_simples, texto)
    if match:
        digitos = match.group(1)
        # Formatar
        return f"{digitos[0:5]}.{digitos[5:10]} {digitos[10:15]}.{digitos[15:21]} {digitos[21:26]}.{digitos[26:32]} {digitos[32]} {digitos[33:47]}"
    
    return None


def extrair_codigo_barras(texto: str) -> str:
    """
    Extrai código de barras (44 dígitos)
    """
    
    # Padrão: 44 dígitos seguidos
    padrao = r'\b(\d{44})\b'
    match = re.search(padrao, texto)
    
    if match:
        return match.group(1)
    
    return None


def extrair_valor(texto: str) -> float:
    """
    Extrai valor do boleto
    Procura por padrões como: R$ 54,01 ou 54.01
    """
    
    # Padrão: R$ seguido de números
    padroes = [
        r'R\$?\s?(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',  # R$ 1.234,56
        r'Valor[:\s]+R\$?\s?(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})',
        r'(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})'  # Qualquer valor no formato
    ]
    
    for padrao in padroes:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            valor_str = match.group(1)
            # Converter para float
            valor_str = valor_str.replace('.', '').replace(',', '.')
            try:
                return float(valor_str)
            except:
                continue
    
    return None


def extrair_vencimento(texto: str) -> str:
    """
    Extrai data de vencimento
    Formatos: DD/MM/AAAA ou DD/MM/AA
    """
    
    padroes = [
        r'Vencimento[:\s]+(\d{2}/\d{2}/\d{4})',
        r'(\d{2}/\d{2}/\d{4})',
        r'(\d{2}/\d{2}/\d{2})'
    ]
    
    for padrao in padroes:
        match = re.search(padrao, texto, re.IGNORECASE)
        if match:
            data_str = match.group(1)
            # Validar se é data válida
            try:
                if len(data_str) == 10:  # DD/MM/AAAA
                    datetime.strptime(data_str, '%d/%m/%Y')
                    return data_str
                else:  # DD/MM/AA
                    data = datetime.strptime(data_str, '%d/%m/%y')
                    return data.strftime('%d/%m/%Y')
            except:
                continue
    
    return None


def extrair_cnpj(texto: str) -> str:
    """
    Extrai CNPJ
    Formato: XX.XXX.XXX/XXXX-XX
    """
    
    # Padrão: CNPJ formatado ou não
    padroes = [
        r'(\d{2}[.\s]?\d{3}[.\s]?\d{3}[/\s]?\d{4}[-\s]?\d{2})',  # Formatado
        r'\b(\d{14})\b'  # Sem formatação
    ]
    
    for padrao in padroes:
        match = re.search(padrao, texto)
        if match:
            cnpj = match.group(1)
            # Remover formatação
            cnpj = re.sub(r'[^\d]', '', cnpj)
            if len(cnpj) == 14:
                # Formatar
                return f"{cnpj[0:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:14]}"
    
    return None


def identificar_banco(codigo_banco: str) -> str:
    """
    Identifica nome do banco pelo código
    """
    
    bancos = {
        '001': 'Banco do Brasil',
        '033': 'Santander',
        '104': 'Caixa Econômica Federal',
        '237': 'Bradesco',
        '341': 'Itaú',
        '748': 'Sicredi',
        '756': 'Bancoob',
        '077': 'Banco Inter',
        '260': 'Nubank',
        '290': 'PagSeguro',
        '403': 'Cora'
    }
    
    return bancos.get(codigo_banco, f"Banco {codigo_banco}")