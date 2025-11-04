"""
OCR - Extração de texto usando Tesseract
"""

import pytesseract
from PIL import Image
import io
import base64
import logging
import os
from pdf2image import convert_from_bytes

logger = logging.getLogger(__name__)

# Configurar caminho do Tesseract (Windows)
if os.name == 'nt':  # Windows
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


def extrair_texto_tesseract(imagem_bytes: bytes, idioma: str = 'por') -> str:
    """
    Extrai texto de uma imagem ou PDF usando Tesseract OCR
    
    Args:
        imagem_bytes: Bytes da imagem ou PDF
        idioma: Idioma do OCR ('por' para português)
    
    Returns:
        Texto extraído
    """
    
    try:
        logger.info("Iniciando OCR com Tesseract...")
        
        # Tentar abrir como imagem
        try:
            imagem = Image.open(io.BytesIO(imagem_bytes))
        except Exception:
            # Se falhar, tentar converter PDF para imagem
            logger.info("Detectado PDF, convertendo para imagem...")
            imagens = convert_from_bytes(imagem_bytes, first_page=1, last_page=1)
            if not imagens:
                raise Exception("Não foi possível converter PDF")
            imagem = imagens[0]
        
        # Configuração do Tesseract
        config = '--psm 6 --oem 3'
        
        # Extrair texto
        texto = pytesseract.image_to_string(
            imagem,
            lang=idioma,
            config=config
        )
        
        logger.info(f"✅ OCR concluído. {len(texto)} caracteres extraídos")
        
        return texto.strip()
        
    except Exception as e:
        logger.error(f"❌ Erro no OCR: {str(e)}")
        raise Exception(f"Erro ao extrair texto: {str(e)}")


def extrair_texto_de_base64(base64_string: str, idioma: str = 'por') -> str:
    """
    Extrai texto de uma imagem em base64
    """
    
    try:
        imagem_bytes = base64.b64decode(base64_string)
        return extrair_texto_tesseract(imagem_bytes, idioma)
        
    except Exception as e:
        logger.error(f"❌ Erro ao processar base64: {str(e)}")
        raise Exception(f"Erro ao processar base64: {str(e)}")