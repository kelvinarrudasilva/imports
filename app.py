# ================================================
# app.py – NOVO DASHBOARD COMPLETO (Roxo Minimalista) 
# Loja Importados – Vendas / Compras / Estoque
# ================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime
import requests
from io import BytesIO


# --------------------------
# CONFIGURAÇÃO DO APP
# --------------------------
st.set_page_config(page_title="Loja Importados – Dashboard", layout="wide", initial_sidebar_state="collapsed")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b/export?format=xlsx"


# --------------------------
# CSS – THEMA DARK ROXO
# --------------------------
st.markdown("""
<style>
:root{
  --bg:#0b0b0b;
  --card:#141414;
  --accent:#8b5cf6;
  --accent2:#a78bfa;
  --text:#f2f2f2;
}
body, .stApp { background:var(--bg) !important; color:var(--text); font-family: Inter; }
h1,h2,h3,h4 { color: var(--accent2) !important; }

.kpi-box{
  background:var(--card);
  padding:14px 18px;
  border-radius:14px;
  border-left:5px solid var(--accent);
  box-shadow:0 4px 14px rgba(0,0,0,0.45);
}

.dataframe tbody tr td{
  color:white !important;
}
</style>
""", unsafe_allow_html=True)


# --------------------------
# FUNÇÕES
# --------------------------
def limpar_moeda(x):
    if pd.isna(x): return 0
    s=str(x).replace("R$","").replace(".","").replace(",",".")
    s=re.sub(r"[^0-9.\-]","",s)
    try: return float(s)
    except: return 0

def formatar(v):
    s=f"{v:,.0f}".replace(",",".")
    return f"R$ {s}"

def baixar_arquivo():
    r=requests.get(URL_PLANILHA,timeout=20)
    r.raise_for_status()
    return pd.ExcelFile(BytesIO(r.content))


# --------------------------
# CARREGAR PLANILHA
# --------------------------
try:
    xls = baixar_arquivo()
except:
    st.error("Erro ao carregar a planilha.")
    st.stop()

dfs = {}
for aba in ["VENDAS","COMPRAS","ESTOQUE"]:
    if aba in xls.sheet_names:
        df = pd.read_excel(xls, aba)
        dfs[aba] = df.copy()


# ===============================
#   ---------------------------
#       TRATAMENTO VENDAS
#   ---------------------------
# ===============================
if "VENDAS" in dfs:
    vendas = dfs["VENDAS"].copy()

    # identifica colunas
    if "DATA" in vendas.columns:
        vendas["DATA"] = pd.to_datetime(vendas["DATA"], errors="coerce")

    # normalizar
    if "VALOR TOTAL" in vendas.columns:
        vendas["VALOR TOTAL"] = vendas["VALOR TOTAL"].map(limpar_moeda)

    if "VALOR VENDA" in vendas.columns and "QTD" in vendas.columns and "VALOR TOTAL" not in vendas.columns:
        vendas["VALOR VENDA"] = vendas["VALOR VENDA"].map(limpar_moeda)
        vendas["VALOR TOTAL"] = vendas["VALOR VENDA"] * vendas["QTD"]

    if "QTD" in vendas.columns:
        vendas["QTD"] = vendas["QTD"].fillna(0).astype(int)

    vendas["MES_ANO"] = vendas["DATA"].dt.strftime("%Y-%m")

else:
    vendas = pd.DataFrame()


# ===============================
#       TRATAMENTO COMPRAS
# ===============================
if "COMPRAS" in dfs:
    compras = dfs["COMPRAS"].copy()

    if "DATA" in compras.columns:
        compras["DATA"] = pd.to_datetime(compras["DATA"], errors="coerce")

    # identificar custo unitário
    custo_col = None
    for c in compras.columns:
        if "CUSTO" in c.upper() and "UNIT" in c.upper():
            custo_col = c

    if custo_col:
        compras["CUSTO UNITARIO"] = compras[custo_col].map(limpar_moeda)

    if "QUANTIDADE" in compras.columns:
        compras["QUANTIDADE"] = compras["QUANTIDADE"].fillna(0).astype(int)

    compras["CUSTO TOTAL"] = compras["QUANTIDADE"] * compras.get("CUSTO UNITARIO", 0)
    compras["MES_ANO"] = compras["DATA"].dt.strftime("%Y-%m")

else:
    compras = pd.DataFrame()


# ===============================
#       TRATAMENTO ESTOQUE
# ===============================
if "ESTOQUE" in dfs:
    estoque = dfs["ESTOQUE"].copy()

    # normaliza valores
    col_custo = None
    for c in estoque.columns:
        if "CUSTO" in c.upper():
            col_custo = c
    if col_custo:
        estoque["CUSTO UNIT"] = estoque[col_custo].map(limpar_moeda)

    col_venda = None
    for c in estoque.columns:
        if "VENDA" in c.upper():
            col_venda = c
    if col_venda:
        estoque["PRECO VENDA"] = estoque[col_venda].map(limpar_moeda)

    # quantidade
    col_qtd = None
    for c in estoque.columns:
        if "ESTOQUE" in c.upper() or "QTD" in c.upper():
            col_qtd = c
    if col_qtd:
        estoque["EM ESTOQUE"] = estoque[col_qtd].fillna(0).astype(int)
    else:
        estoque["EM ESTOQUE"] = 0

    estoque["VALOR TOTAL CUSTO"] = estoque["CUSTO UNIT"] * estoque["EM ESTOQUE"]
    estoque["VALOR TOTAL VENDA"] = estoque["PRECO VENDA"] * estoque["EM ESTOQUE"]

else:
    estoque = pd.DataFrame()


# ==========================================
#             FILTRO MÊS
# ==========================================
meses = ["Todos"]
meses += sorted(vendas["MES_ANO"].dropna().unique().tolist(), reverse=True) if not vendas.empty else []

mes_atual = datetime.now().strftime("%Y-%m")
idx_padrao = meses.index(mes_atual) if mes_atual in meses else 0

mes escolhido = st.selectbox("Filtrar por mês (YYYY-MM):", meses, index=idx_padrao)

def filtrar(df):
    if df.empty: return df
    if mes_escolhido == "Todos": return df
    return df[df["MES_ANO"] == mes_escolhido]


vendas_f = filtrar(vendas)
compras_f = filtrar(compras)


# ==========================================
#               KPIs GERAIS
# ==========================================
total_vendas = vendas_f["VALOR TOTAL"].sum() if not vendas_f.empty else 0
total_qtd = vendas_f["QTD"].sum() if not vendas_f.empty else 0
total_compras = compras_f["CUSTO TOTAL"].sum() if not compras_f.empty else 0
valor_estoque = estoque["VALOR TOTAL VENDA"].sum() if not estoque.empty else 0
custo_estoque = estoque["VALOR TOTAL CUSTO"].sum() if not estoque.empty else 0

col1, col2, col3, col4, col5 = st.columns(5)

col1.markdown(f"<div class='kpi-box'><h4>💵 Vendas no período</h4><h2>{formatar(total_vendas)}</h2></div>", unsafe_allow_html=True)
col2.markdown(f"<div class='kpi-box'><h4>📦 Itens vendidos</h4><h2>{total_qtd}</h2></div>", unsafe_allow_html=True)
col3.markdown(f"<div class='kpi-box'><h4>💸 Compras no período</h4><h2>{formatar(total_compras)}</h2></div>", unsafe_allow_html=True)
col4.markdown(f"<div class='kpi-box'><h4>🏷 Valor Estoque Venda</h4><h2>{formatar(valor_estoque)}</h2></div>", unsafe_allow_html=True)
col5.markdown(f"<div class='kpi-box'><h4>📥 Custo Total Estoque</h4><h2>{formatar(custo_estoque)}</h2></div>", unsafe_allow_html=True)


# ==========================================
#              ABAS PRINCIPAIS
# ==========================================
aba1, aba2, aba3, aba4 = st.tabs(["🛒 VENDAS", "💸 COMPRAS", "📦 ESTOQUE", "🔍 PESQUISAR"])


# -----------------------
# ABA VENDAS
# -----------------------
with aba1:
    st.subheader("📊 Vendas — período selecionado")

    if vendas_f.empty:
        st.info("Nenhuma venda encontrada.")
    else:
        df = vendas_f.copy()

        fig = px.bar(
            df.sort_values("DATA"),
            x="DATA",
            y="VALOR TOTAL",
            text=df["VALOR TOTAL"].apply(formatar),
        )
        fig.update_traces(textposition="inside")
        fig.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.subheader("📄 Tabela de Vendas")
        st.dataframe(df.sort_values("DATA", ascending=False), use_container_width=True)


# -----------------------
# ABA COMPRAS
# -----------------------
with aba2:
    st.subheader("💸 Compras — período selecionado")

    if compras_f.empty:
        st.info("Nenhuma compra encontrada.")
    else:
        df = compras_f.copy()

        fig = px.bar(
            df.sort_values("DATA"),
            x="DATA",
            y="CUSTO TOTAL",
            text=df["CUSTO TOTAL"].apply(formatar),
            color_discrete_sequence=["#8b5cf6"]
        )
        fig.update_traces(textposition="inside")
        fig.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.subheader("📄 Tabela de Compras")
        st.dataframe(df.sort_values("DATA", ascending=False), use_container_width=True)


# -----------------------
# ABA ESTOQUE
# -----------------------
with aba3:
    st.subheader("📦 Estoque Atual")

    if estoque.empty:
        st.info("Nenhum item de estoque encontrado.")
    else:
        df = estoque.copy()
        df = df.sort_values("EM ESTOQUE", ascending=False)

        fig = px.bar(
            df.head(20),
            x="PRODUTO",
            y="EM ESTOQUE",
            text="EM ESTOQUE",
            color_discrete_sequence=["#8b5cf6"]
        )
        fig.update_traces(textposition="inside")
        fig.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.subheader("📄 Tabela completa")
        st.dataframe(df, use_container_width=True)


# -----------------------
# ABA PESQUISAR
# -----------------------
with aba4:
    st.subheader("🔍 Buscar produto no estoque")

    termo = st.text_input("Digite parte do nome:")

    if termo.strip():
        df = estoque[estoque["PRODUTO"].str.contains(termo, case=False, na=False)]
        if df.empty:
            st.warning("Nenhum produto encontrado.")
        else:
            st.dataframe(df.reset_index(drop=True), use_container_width=True)
