# app.py completo com Dashboard integrado
import streamlit as st
import pandas as pd
import plotly.express as px
import re
from io import BytesIO
import requests

# =============================================================================
# CONFIGURAÇÃO VISUAL
# =============================================================================
st.set_page_config(page_title="Painel - Loja Importados", layout="wide")

st.markdown(
    """
    <style>
      :root {
        --gold:#FFD700;
      }
      body {
        background-color: #111 !important;
        color: white !important;
      }
      .stTabs [data-baseweb="tab"] {
        background: #222;
        color: white;
        border-radius: 5px;
        margin-right: 5px;
        padding: 8px;
        border: 1px solid #444;
      }
      .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: var(--gold);
        color: black !important;
        font-weight: bold;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================================
# FUNÇÃO: CARREGAR PLANILHA direto do Google Sheets
# =============================================================================
def carregar_planilha(link):
    try:
        if "edit" in link:
            link = link.replace("/edit", "/export?format=csv")
        elif "view" in link:
            link = link.replace("/view", "/export?format=csv")

        # Tentativa com UTF-8, fallback para Latin-1
try:
        df = pd.read_csv(link, encoding="utf-8", sep=",", engine="python", on_bad_lines="skip")
    except Exception:
        df = pd.read_csv(link, encoding="latin1", sep=",", engine="python", on_bad_lines="skip")
        return df
    except Exception as e:
        st.error(f"Erro ao carregar planilha: {e}")
        return None

# =============================================================================
# PADRONIZAÇÃO DE COLUNAS
# =============================================================================
def padrao(col):
    col = col.strip()
    col = col.replace(" ", " ")
    col = re.sub(r" +", " ", col)
    return col.upper()

# =============================================================================
# CORREÇÃO AUTOMÁTICA DE COLUNAS
# =============================================================================
def corrigir_colunas(df, esperadas):
    df_corr = df.copy()
    df_corr.columns = [padrao(c) for c in df_corr.columns]

    esperadas_upper = [padrao(c) for c in esperadas]
    mapa = {}

    for col in df_corr.columns:
        melhor = None
        score_melhor = 0
        for esp in esperadas_upper:
            iguais = sum(1 for a, b in zip(col, esp) if a == b)
            score = iguais / max(len(col), len(esp))
            if score > score_melhor:
                score_melhor = score
                melhor = esp
        if melhor:
            mapa[col] = melhor

    df_corr.rename(columns=mapa, inplace=True)

    colunas_faltando = [c for c in esperadas_upper if c not in df_corr.columns]
    colunas_extras = [c for c in df_corr.columns if c not in esperadas_upper]

    return df_corr, colunas_faltando, colunas_extras

# =============================================================================
# INTERFACE – INPUT PLANILHA
# =============================================================================
st.title("📊 Dashboard Geral – Gestão Loja Importados")

# Link fixo da planilha Google Drive
URL_PLANILHA = "https://drive.google.com/uc?export=download&id=1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b"

df = carregar_planilha(URL_PLANILHA)
if df is None:
    st.stop()

df = carregar_planilha(link)
if df is None:
    st.stop()

# =============================================================================
# COLUNAS ESPERADAS
# =============================================================================
colunas_estoque = [
    "PRODUTO",
    "EM ESTOQUE",
    "COMPRAS",
    "MEDIA C. UNITARIO",
    "VALOR VENDA SUGERIDO",
    "VENDAS",
]

colunas_vendas = [
    "DATA",
    "PRODUTO",
    "QTD",
    "VALOR VENDA",
    "VALOR TOTAL",
    "MEDIA CUSTO UNITARIO",
    "LUCRO UNITARIO",
    "MAKEUP",
    "% DE LUCRO SOBRE CUSTO",
    "STATUS",
    "CLIENTE",
    "OBS",
]

# Detectar automaticamente aba
if "EM ESTOQUE" in df.columns or "ESTOQUE" in df.columns:
    tipo = "ESTOQUE"
    esperadas = colunas_estoque
else:
    tipo = "VENDAS"
    esperadas = colunas_vendas

st.subheader(f"🔍 Identificada aba: **{tipo}**")

# Corrigir colunas
corrigido, faltando, extras = corrigir_colunas(df, esperadas)

if faltando:
    st.warning("⚠️ Colunas faltando:")
    st.write(faltando)
if extras:
    st.info("ℹ️ Colunas extras detectadas:")
    st.write(extras)

st.success("✔️ Colunas ajustadas automaticamente!")
st.dataframe(corrigido)

# =============================================================================
# DASHBOARD
# Link fixo da planilha Google Drive
URL_PLANILHA = "https://drive.google.com/uc?export=download&id=1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b"

# =============================================================================
st.header("📈 Dashboard Analítico")

# Garantir colunas numéricas
for c in corrigido.columns:
    try:
        corrigido[c] = pd.to_numeric(corrigido[c], errors="ignore")
    except:
        pass

# ==========================
# DASHBOARD ESTOQUE
# ==========================
if tipo == "ESTOQUE":
    col1, col2, col3 = st.columns(3)

    with col1:
        total_estoque = corrigido["EM ESTOQUE"].sum()
        st.metric("📦 Total em Estoque", total_estoque)

    with col2:
        total_vendas = corrigido["VENDAS"].sum()
        st.metric("🛒 Total Vendido (Qtde)", total_vendas)

    with col3:
        ticket = corrigido["VALOR VENDA SUGERIDO"].mean()
        st.metric("💰 Preço Médio Sugerido", f"R$ {ticket:,.2f}")

    fig = px.bar(
        corrigido.sort_values("VENDAS", ascending=False).head(15),
        x="PRODUTO", y="VENDAS", title="TOP 15 Produtos Mais Vendidos",
    )
    st.plotly_chart(fig, use_container_width=True)

# ==========================
# DASHBOARD VENDAS
# ==========================
else:
    corrigido["DATA"] = pd.to_datetime(corrigido["DATA"], errors="coerce")

    col1, col2, col3 = st.columns(3)

    with col1:
        total_faturado = corrigido["VALOR TOTAL"].sum()
        st.metric("💵 Faturamento Total", f"R$ {total_faturado:,.2f}")

    with col2:
        lucro_total = corrigido["LUCRO UNITARIO"].sum()
        st.metric("💰 Lucro Total", f"R$ {lucro_total:,.2f}")

    with col3:
        qtd_total = corrigido["QTD"].sum()
        st.metric("🛒 Quantidade Vendida", int(qtd_total))

    fig = px.line(
        corrigido.groupby("DATA")["VALOR TOTAL"].sum().reset_index(),
        x="DATA", y="VALOR TOTAL", title="📅 Faturamento Diário",
    )
    st.plotly_chart(fig, use_container_width=True)

    fig2 = px.bar(
        corrigido.groupby("PRODUTO")["QTD"].sum().reset_index().sort_values("QTD", ascending=False).head(20),
        x="PRODUTO", y="QTD", title="🏆 TOP 20 Produtos Vendidos",
    )
    st.plotly_chart(fig2, use_container_width=True)


st.success("✅ Dashboard carregado com sucesso!")
