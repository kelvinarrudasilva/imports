# app.py — Versão Completa (Tema Claro Verde + Lucro Formatado + TOP10 Refeito)
# Kelvin, aqui está o arquivo COMPLETO, prontinho para rodar.

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
from io import BytesIO

# ------------------------------------------------------
# CONFIG
# ------------------------------------------------------
st.set_page_config(page_title="Loja Importados — Dashboard", layout="wide")

# ------------------------------------------------------
# TEMA CLARO VERDE — COMPLETO
# ------------------------------------------------------
st.markdown(
    """
    <style>
        :root {
            --verde:#0e8c4a;
            --verde-escuro:#0a5e34;
            --verde-claro:#17d976;
        }
        body, .stApp {
            background-color:#f2f2f2 !important;
            color:#222 !important;
            font-family: 'Segoe UI', sans-serif !important;
        }
        h1,h2,h3,h4 {
            color: var(--verde-escuro) !important;
            font-weight: 700 !important;
        }
        .stMetric label { color:#333 !important; font-weight:600 !important; }
        .stMetric div { color: var(--verde) !important; font-weight:800 !important; }
        .stTabs [data-baseweb="tab"] {
            color: var(--verde-escuro) !important;
            font-weight: 600 !important;
        }
        .stTabs [data-baseweb="tab"]:hover {
            color: var(--verde) !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("📊 Loja Importados — Dashboard (Tema Claro 🟢)")

# ------------------------------------------------------
# LINK FIXO DA PLANILHA
# ------------------------------------------------------
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b/export?format=xlsx"

@st.cache_data(show_spinner=False)
def carregar_dados():
    try:
        arquivo = requests.get(URL_PLANILHA)
        df = pd.read_excel(BytesIO(arquivo.content))
        return df
    except:
        st.error("Erro ao carregar arquivo do Google Drive.")
        return None

# ------------------------------------------------------
# CARREGAR
# ------------------------------------------------------
df = carregar_dados()
if df is None:
    st.stop()

# ------------------------------------------------------
# LIMPEZA
# ------------------------------------------------------
colunas = [c.upper().strip() for c in df.columns]
df.columns = colunas

if "DATA" in df.columns:
    df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")
else:
    st.error("A planilha precisa ter a coluna DATA.")
    st.stop()

if "VALOR_VENDA" not in df.columns or "CUSTO" not in df.columns:
    st.error("A planilha precisa de VALOR_VENDA e CUSTO.")
    st.stop()

df["LUCRO"] = df["VALOR_VENDA"] - df["CUSTO"]

# ------------------------------------------------------
# RESUMO
# ------------------------------------------------------
st.subheader("📈 Visão Geral — Últimas Vendas")

col1, col2, col3 = st.columns(3)
col1.metric("Faturamento", f"R$ {df['VALOR_VENDA'].sum():,.2f}")
col2.metric("Custos", f"R$ {df['CUSTO'].sum():,.2f}")
col3.metric("Lucro Total", f"R$ {df['LUCRO'].sum():,.2f}")

# ------------------------------------------------------
# GRÁFICO PRINCIPAL
# ------------------------------------------------------
st.subheader("📆 Evolução das Vendas")

graf = df.groupby(df["DATA"].dt.date)["VALOR_VENDA"].sum().reset_index()

fig = px.line(graf, x="DATA", y="VALOR_VENDA", title="Faturamento por Dia")
fig.update_traces(mode="lines+markers", line_width=3)
st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------
# TOP10 LUCRO — SEÇÃO COMPLETA REFEITA
# ------------------------------------------------------
st.subheader("🏆 Top 10 Produtos por Lucro")

top_lucro = (
    df.groupby("PRODUTO")["LUCRO"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
    .reset_index()
)

top_lucro["LUCRO_LABEL"] = top_lucro["LUCRO"].map(lambda x: f"R$ {x:,.2f}")

fig2 = px.bar(
    top_lucro,
    x="LUCRO",
    y="PRODUTO",
    orientation="h",
    text="LUCRO_LABEL",
    title="Produtos mais lucrativos",
)

fig2.update_traces(textposition="outside", marker_color="#0e8c4a")
fig2.update_layout(yaxis={'categoryorder':'total ascending'})
st.plotly_chart(fig2, use_container_width=True)

# ------------------------------------------------------
# FIM
# ------------------------------------------------------
st.success("Dashboard carregado com sucesso! Tema e gráficos atualizados.")
