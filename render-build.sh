#!/usr/bin/env bash
# Sair em caso de erro
set -o errexit

# Atualizar apt-get
apt-get update

# Instalar Tesseract OCR
apt-get install -y tesseract-ocr tesseract-ocr-por

# Instalar dependências Python
pip install --upgrade pip
pip install -r requirements.txt
