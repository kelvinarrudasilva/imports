import pandas as pd
import streamlit as st

# ======================================
# CONFIGURAÇÃO INICIAL
# ======================================
st.set_page_config(page_title="📊 Painel Loja Importados", layout="wide")
st.title("🛒 Painel de Controle - Loja Importados")

# ======================================
# CARREGAMENTO DO ARQUIVO
# ======================================
try:
    # Lê diretamente o arquivo Excel fixo
    df = pd.read_excel("LOJA IMPORTADOS.xlsx")

    # Remove linhas totalmente vazias
    df.dropna(how='all', inplace=True)

    # Remove espaços extras dos nomes das colunas
    df.columns = df.columns.str.strip().str.lower()

    # ======================================
    # MAPEAMENTO AUTOMÁTICO DAS COLUNAS
    # ======================================
    colunas = {
        "produto": None,
        "estoque": None,
        "preco_venda": None,
        "vendas": None
    }

    for col in df.columns:
        c = col.lower()
        if "prod" in c:
            colunas["produto"] = col
        elif "estoque" in c or "em estoque" in c:
            colunas["estoque"] = col
        elif "preco" in c or "valor venda" in c or "preço" in c:
            colunas["preco_venda"] = col
        elif "venda" in c:
            colunas["vendas"] = col

    st.write("🔍 Colunas detectadas (verifique)")
    st.json(colunas)

    # ======================================
    # FORMATAÇÃO E CÁLCULOS
    # ======================================
    # Garante que colunas numéricas sejam tratadas como números
    for key in ["estoque", "preco_venda", "vendas"]:
        if colunas[key] and colunas[key] in df.columns:
            df[colunas[key]] = pd.to_numeric(df[colunas[key]], errors="coerce").fillna(0)

    # Calcula o valor total em estoque e total vendido
    valor_estoque = (df[colunas["estoque"]] * df[colunas["preco_venda"]]).sum()
    valor_vendido = (df[colunas["vendas"]] * df[colunas["preco_venda"]]).sum()

    # Mostra o resumo principal com formatação em reais
    st.markdown(f"""
    ### 💰 Resumo Financeiro
    - **Valor total em estoque:** R$ {valor_estoque:,.2f}
    - **Valor total vendido:** R$ {valor_vendido:,.2f}
    """.replace(",", "X").replace(".", ",").replace("X", "."))

    # ======================================
    # EXIBIÇÃO DA TABELA
    # ======================================
    # Cria uma cópia formatada
    tabela = df.copy()
    if colunas["preco_venda"]:
        tabela[colunas["preco_venda"]] = tabela[colunas["preco_venda"]].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    st.dataframe(tabela, use_container_width=True)

except Exception as e:
    st.error(f"❌ Erro ao processar o arquivo: {e}")
