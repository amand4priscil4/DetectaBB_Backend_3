"""
Script para treinar modelo de detecção de boletos falsos
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import pickle
import os

# Criar diretório de modelos se não existir
os.makedirs('src/models', exist_ok=True)

print("Gerando dataset sintético...")

# Gerar dados sintéticos com regras de fraude
np.random.seed(42)

dados = []

# Gerar 1000 boletos (500 válidos, 500 falsos)
for i in range(1000):
    
    # Decidir se é verdadeiro ou falso
    is_falso = i >= 500
    
    if not is_falso:
        # BOLETO VÁLIDO
        banco = np.random.choice([341, 237, 104, 1, 33, 403])
        codigo_banco_linha = banco  # Consistente
        valor = round(np.random.uniform(50, 5000), 2)
        valor_linha = int(valor * 100)  # Consistente
        moeda = 9  # Moeda padrão
        agencia = np.random.randint(1, 9999)
        
    else:
        # BOLETO FALSO - introduzir inconsistências
        banco = np.random.choice([341, 237, 104, 1, 33, 403])
        
        tipo_fraude = np.random.choice([
            'banco_diferente',
            'valor_diferente', 
            'moeda_invalida',
            'multiplos_erros'
        ])
        
        if tipo_fraude == 'banco_diferente':
            codigo_banco_linha = np.random.choice([999, 000, 123])  # Banco inválido
            valor = round(np.random.uniform(50, 5000), 2)
            valor_linha = int(valor * 100)
            moeda = 9
            agencia = np.random.randint(1, 9999)
            
        elif tipo_fraude == 'valor_diferente':
            codigo_banco_linha = banco
            valor = round(np.random.uniform(50, 5000), 2)
            valor_linha = int(np.random.uniform(5000, 50000))  # Valor diferente!
            moeda = 9
            agencia = np.random.randint(1, 9999)
            
        elif tipo_fraude == 'moeda_invalida':
            codigo_banco_linha = banco
            valor = round(np.random.uniform(50, 5000), 2)
            valor_linha = int(valor * 100)
            moeda = np.random.choice([0, 5, 7])  # Moeda inválida
            agencia = np.random.randint(1, 9999)
            
        else:  # multiplos_erros
            codigo_banco_linha = np.random.choice([999, 000])
            valor = round(np.random.uniform(50, 5000), 2)
            valor_linha = int(np.random.uniform(5000, 50000))
            moeda = np.random.choice([0, 5])
            agencia = 0  # Agência inválida
    
    dados.append({
        'banco': banco,
        'codigoBanco': banco,
        'agencia': agencia,
        'valor': valor,
        'linha_codBanco': codigo_banco_linha,
        'linha_moeda': moeda,
        'linha_valor': valor_linha,
        'classe': 1 if not is_falso else 0  # 1=verdadeiro, 0=falso
    })

# Criar DataFrame
df = pd.DataFrame(dados)

print(f"\nDataset criado: {len(df)} boletos")
print(f"Válidos: {(df['classe'] == 1).sum()}")
print(f"Falsos: {(df['classe'] == 0).sum()}")

# Separar features e target
features = ['banco', 'codigoBanco', 'agencia', 'valor', 'linha_codBanco', 'linha_moeda', 'linha_valor']
X = df[features]
y = df['classe']

# Split treino/teste
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

print("\nTreinando Random Forest...")

# Treinar modelo
model = RandomForestClassifier(
    n_estimators=100,
    max_depth=10,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)

# Avaliar
y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)

print(f"\n✅ Modelo treinado!")
print(f"Acurácia: {accuracy * 100:.2f}%")
print("\nRelatório de classificação:")
print(classification_report(y_test, y_pred, target_names=['Falso', 'Verdadeiro']))

# Salvar modelo
model_path = 'src/models/modelo_boleto.pkl'
with open(model_path, 'wb') as f:
    pickle.dump(model, f)

print(f"\n✅ Modelo salvo em: {model_path}")
print(f"Tamanho do arquivo: {os.path.getsize(model_path) / 1024:.2f} KB")