# =========================
# Painel de Estoque - KELVIN ARRUDA
# =========================

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

# -------------------------
# CONFIGURAÇÕES BÁSICAS
# -------------------------
st.set_page_config(page_title="Painel de Estoque", layout="wide")

# -------------------------
# CABEÇALHO
# -------------------------
st.title("📦 Painel de Estoque")
st.markdown("### **KELVIN ARRUDA**")
st.write("Monitoramento inteligente de produtos, vendas e reposição 🧠💡")

# -------------------------
# FUNÇÕES AUXILIARES
# -------------------------
def normalize_columns(df):
    df.columns = df.columns.str.strip().str.lower()
    return df

def to_number_series(s):
    return pd.to_numeric(s, errors='coerce').fillna(0)

# -------------------------
# SIDEBAR - UPLOAD
# -------------------------
st.sidebar.header("Dados")
file = st.sidebar.file_uploader("📁 Envie seu arquivo CSV do estoque", type=["csv"])

if file is not None:
    # -------------------------
    # TENTA LER O CSV COM DIFERENTES ENCODINGS E SEPARADORES
    # -------------------------
    try:
        df = pd.read_csv(file, sep=";", skip_blank_lines=True, encoding="latin1")
        if df.empty or len(df.columns) <= 1:
            file.seek(0)
            df = pd.read_csv(file, sep=",", skip_blank_lines=True, encoding="latin1")
    except Exception:
        try:
            file.seek(0)
            df = pd.read_csv(file, sep=";", skip_blank_lines=True, encoding="utf-8")
            if df.empty or len(df.columns) <= 1:
                file.seek(0)
                df = pd.read_csv(file, sep=",", skip_blank_lines=True, encoding="utf-8")
        except Exception as e:
            st.error(f"❌ Erro ao ler o arquivo CSV: {e}")
            st.stop()

    df = normalize_columns(df)

    # -------------------------
    # AJUSTA NOMES DAS COLUNAS
    # -------------------------
    rename_map = {
        "produto": "Produto",
        "em estoque": "Estoque",
        "estoque": "Estoque",
        "compras": "Compras",
        "media c. unitario": "Custo_Unitario",
        "valor venda sugerido": "Preco_Venda",
        "vendas": "Vendas"
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Corrige colunas numéricas
    for col in ["Estoque", "Compras", "Custo_Unitario", "Preco_Venda", "Vendas"]:
        if col in df.columns:
            df[col] = to_number_series(df[col])

    # Remove linhas sem produto
    if "Produto" in df.columns:
        df = df[df["Produto"].notna() & (df["Produto"] != "")]
    else:
        st.error("❌ Não foi possível identificar a coluna 'Produto'. Verifique o nome no CSV.")
        st.stop()

    # -------------------------
    # PAINEL PRINCIPAL
    # -------------------------
    st.divider()
    st.subheader("📊 Visão Geral")

    total_produtos = len(df)
    total_estoque = int(df["Estoque"].sum()) if "Estoque" in df.columns else 0
    total_vendas = int(df["Vendas"].sum()) if "Vendas" in df.columns else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Produtos Cadastrados", f"{total_produtos}")
    col2.metric("Itens em Estoque", f"{total_estoque:,}".replace(",", "."))
    col3.metric("Total de Vendas", f"{total_vendas:,}".replace(",", "."))

    # -------------------------
    # RESUMO INTELIGENTE
    # -------------------------
    st.divider()
    st.subheader("🧠 Resumo Automático")
    low_stock = df[df["Estoque"] <= 5]
    no_sales = df[df["Vendas"] == 0] if "Vendas" in df.columns else pd.DataFrame()

    resumo = f"""
    - 🔻 {len(low_stock)} produtos estão com estoque abaixo de 5 unidades.  
    - 💤 {len(no_sales)} produtos sem nenhuma venda registrada.  
    - 📦 Total atual de produtos: {total_produtos}.
    """
    st.markdown(resumo)

    # -------------------------
    # ALERTAS DE REPOSIÇÃO
    # -------------------------
    st.divider()
    st.subheader("⚠️ Alertas de Reposição")
    if not low_stock.empty:
        st.dataframe(low_stock[["Produto", "Estoque", "Vendas"]].head(15), use_container_width=True)
    else:
        st.success("Todos os produtos estão com níveis de estoque adequados 🎉")

    # -------------------------
    # GRÁFICO DE ESTOQUE
    # -------------------------
    st.divider()
    st.subheader("📈 Estoque por Produto")
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.bar(df["Produto"], df["Estoque"], color="#1f77b4")
    ax.set_ylabel("Quantidade em Estoque")
    ax.set_xlabel("Produto")
    plt.xticks(rotation=90, fontsize=8)
    st.pyplot(fig)

    # -------------------------
    # GRÁFICO DE VENDAS
    # -------------------------
    st.divider()
    st.subheader("💸 Vendas por Produto")
    if "Vendas" in df.columns:
        fig2, ax2 = plt.subplots(figsize=(10, 4))
        ax2.bar(df["Produto"], df["Vendas"], color="#2ca02c")
        ax2.set_ylabel("Quantidade Vendida")
        ax2.set_xlabel("Produto")
        plt.xticks(rotation=90, fontsize=8)
        st.pyplot(fig2)
    else:
        st.info("Coluna 'Vendas' não encontrada no arquivo.")

    # -------------------------
    # RELATÓRIO DETALHADO
    # -------------------------
    st.divider()
    st.subheader("📋 Relatório Completo")
    st.dataframe(df, use_container_width=True)

else:
    st.info("⬅️ Envie um arquivo CSV para começar.")
