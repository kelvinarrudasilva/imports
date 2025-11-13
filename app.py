import pandas as pd
import os

# Nome do arquivo
arquivo = "LOJA IMPORTADOS.xlsx"

# Verifica se o arquivo existe
if not os.path.exists(arquivo):
    raise FileNotFoundError(f"Arquivo {arquivo} não encontrado no diretório atual.")

# Carrega o Excel
df = pd.read_excel(arquivo)

# Garante que todas as colunas tenham nome
df.columns = [f"coluna_{i+1}" if str(col).startswith('Unnamed') or pd.isna(col) else col for i, col in enumerate(df.columns)]

# Preenche valores nulos com vazio (opcional, para evitar erros nos gráficos)
df.fillna("", inplace=True)

# Converte colunas numéricas se possível (opcional)
for col in df.columns:
    try:
        df[col] = pd.to_numeric(df[col])
    except:
        pass

# Mostra as primeiras linhas para conferir
print(df.head())

# Salva o arquivo limpo
df.to_excel("LOJA_IMPORTADOS_limpo.xlsx", index=False)
print("Arquivo limpo salvo como 'LOJA_IMPORTADOS_limpo.xlsx'.")
