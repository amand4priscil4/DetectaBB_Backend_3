#!/usr/bin/env bash
set -o errexit

# Atualizar sistema
apt-get update

# Instalar Tesseract OCR e idioma português
apt-get install -y tesseract-ocr tesseract-ocr-por

# Instalar dependências Python
pip install --upgrade pip
pip install -r requirements.txt
