import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import unicodedata

# -----------------------------------------
# CONFIGURAÇÃO INICIAL
# -----------------------------------------
st.set_page_config(page_title="Painel de Estoque - Kelvin Arruda", layout="wide")
st.title("📦 Painel de Estoque - Kelvin Arruda")

# -----------------------------------------
# FUNÇÕES AUXILIARES
# -----------------------------------------
def limpar_nome(texto):
    """Remove acentos, espaços e coloca tudo em minúsculo."""
    if not isinstance(texto, str):
        return ""
    texto = texto.strip().lower()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )
    return texto

def detectar_coluna(df, possiveis):
    """Procura colunas compatíveis dentro do DataFrame."""
    for nome in df.columns:
        nome_limpo = limpar_nome(nome)
        for p in possiveis:
            if p in nome_limpo:
                return nome
    return None

# -----------------------------------------
# LEITURA DO ARQUIVO EXCEL DIRETO
# -----------------------------------------
try:
    df = pd.read_excel("LOJA IMPORTADOS.xlsx", engine="openpyxl")
    st.sidebar.success(f"Arquivo Excel carregado! ({len(df)} linhas)")

    # Normalizar colunas
    df.columns = [limpar_nome(c) for c in df.columns]

    # Detectar colunas principais
    col_produto = detectar_coluna(df, ["produto", "descricao", "item", "nome"])
    col_estoque = detectar_coluna(df, ["estoque", "quantidade", "em estoque", "qtd"])
    col_preco = detectar_coluna(df, ["preco", "valor", "venda", "sugerido"])
    col_vendas = detectar_coluna(df, ["venda", "vendida", "saida", "qtd vendida"])

    # Garantir que não confunda preço com vendas
    if col_vendas == col_preco:
        col_vendas = None

    st.write("### 🔍 Colunas detectadas:")
    st.json({
        "produto": col_produto,
        "estoque": col_estoque,
        "preco_venda": col_preco,
        "vendas": col_vendas,
    })

    # Verificação mínima
    if not col_produto or not col_estoque:
        st.error("❌ Não foi possível identificar as colunas principais (produto/estoque). Verifique o Excel.")
        st.stop()

    # Limpar e converter dados
    df = df.dropna(subset=[col_produto])
    df = df[df[col_produto].astype(str).str.strip() != ""]

    for col in [col_estoque, col_preco, col_vendas]:
        if col and col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # -----------------------------------------
    # MÉTRICAS
    # -----------------------------------------
    total_itens = len(df)
    total_estoque = df[col_estoque].sum()
    valor_total = (df[col_estoque] * df[col_preco]).sum() if col_preco else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Produtos Cadastrados", total_itens)
    col2.metric("Quantidade Total em Estoque", f"{total_estoque:,.0f}".replace(",", "."))
    col3.metric("Valor Total do Estoque (R$)", f"{valor_total:,.2f}".replace(".", ","))

    st.divider()

    # -----------------------------------------
    # GRÁFICO
    # -----------------------------------------
    top_produtos = df.sort_values(by=col_estoque, ascending=False).head(15)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.barh(top_produtos[col_produto], top_produtos[col_estoque], color="#4C72B0")
    ax.invert_yaxis()
    ax.set_xlabel("Quantidade em Estoque")
    ax.set_ylabel("Produto")
    ax.set_title("Top 15 Produtos em Estoque")
    st.pyplot(fig)

    st.divider()

    # -----------------------------------------
    # ALERTAS DE REPOSIÇÃO
    # -----------------------------------------
    limite = st.slider("Defina o limite para alerta de reposição", 0, 50, 5)
    alerta = df[df[col_estoque] <= limite]
    st.subheader("⚠️ Produtos com Estoque Baixo")
    if not alerta.empty:
        st.dataframe(alerta[[col_produto, col_estoque]])
    else:
        st.success("✅ Nenhum produto abaixo do limite definido.")

    st.divider()

    # -----------------------------------------
    # TABELA COMPLETA
    # -----------------------------------------
    with st.expander("📋 Ver tabela completa"):
        st.dataframe(df)

except FileNotFoundError:
    st.error("❌ Arquivo 'LOJA IMPORTADOS.xlsx' não encontrado na pasta do app.")
except Exception as e:
    st.error(f"❌ Erro ao processar o arquivo: {e}")
