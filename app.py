import pandas as pd
import matplotlib.pyplot as plt
import os

# --- Configurações ---
arquivo = "LOJA IMPORTADOS.xlsx"
arquivo_limpo = "LOJA_IMPORTADOS_limpo.xlsx"

# Verifica se o arquivo existe
if not os.path.exists(arquivo):
    raise FileNotFoundError(f"Arquivo {arquivo} não encontrado no diretório atual.")

# --- Carrega o Excel ---
df = pd.read_excel(arquivo)

# Arruma colunas sem nome
df.columns = [f"coluna_{i+1}" if str(col).startswith('Unnamed') or pd.isna(col) else col for i, col in enumerate(df.columns)]

# Preenche valores nulos com 0 em colunas de interesse
for col in ['estoque', 'vendas', 'preco_venda']:
    if col in df.columns:
        df[col].fillna(0, inplace=True)

# Converte colunas numéricas
for col in df.columns:
    try:
        df[col] = pd.to_numeric(df[col])
    except:
        pass

# Salva arquivo limpo
df.to_excel(arquivo_limpo, index=False)
print(f"Arquivo limpo salvo como '{arquivo_limpo}'.")

# --- Função para gerar gráficos ---
def gerar_grafico(df, x_col, y_col, titulo, cor, arquivo_saida):
    if x_col in df.columns and y_col in df.columns:
        plt.figure(figsize=(10,6))
        df.plot(kind='bar', x=x_col, y=y_col, color=cor, legend=False)
        plt.title(titulo)
        plt.ylabel(y_col.capitalize())
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(arquivo_saida)
        plt.close()  # Fecha a figura para não abrir janela
        print(f"Gráfico salvo: {arquivo_saida}")

# --- Gera os gráficos ---
gerar_grafico(df, 'produto', 'estoque', 'Estoque por Produto', 'skyblue', 'estoque_por_produto.png')
gerar_grafico(df, 'produto', 'vendas', 'Vendas por Produto', 'orange', 'vendas_por_produto.png')
