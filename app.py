# ===============================================================
#  app.py — Versão FINAL • Inteligente • Blindado • Preto+Dourado
# ===============================================================

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
from io import BytesIO
import re

# ---------------------------------------------------------------
# VISUAL — Tema Preto + Dourado
# ---------------------------------------------------------------
st.set_page_config(page_title="Painel - Loja Importados", layout="wide")

st.markdown(
    """
    <style>
      :root { --gold:#FFD700; --bg:#000000; --muted:#bbbbbb; --white:#FFFFFF; }
      .stApp { background-color: var(--bg); color: var(--gold); }
      .title { color: var(--gold); font-weight:700; font-size:22px; }
      .subtitle { color: var(--muted); font-size:12px; margin-bottom:12px; }
      .kpi { background:linear-gradient(90deg,#151515,#0c0c0c); padding:12px; border-radius:10px; text-align:center; }
      .kpi-value { color:var(--gold); font-size:22px; font-weight:700; }
      .kpi-label { color:var(--muted); font-size:13px; }
      .stDataFrame table { background-color:#050505; color:var(--white); }
      div[data-baseweb="select"] > div {
          background-color:#0d0d0d !important; border:1px solid rgba(255,215,0,0.35) !important;
          border-radius:8px !important; padding:4px 8px !important; min-height:32px !important;
      }
      div[data-baseweb="select"] * { color:var(--gold) !important; font-size:13px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div class='title'>📊 Painel — Loja Importados</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Visão Geral • Estoque • Vendas</div>", unsafe_allow_html=True)
st.markdown("---")

# ---------------------------------------------------------------
# FUNÇÕES AUXILIARES
# ---------------------------------------------------------------

def clean_df(df):
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains("Unnamed")]
    df = df.dropna(how="all").reset_index(drop=True)
    return df

def parse_money(series):
    return (
        series.astype(str)
        .str.replace("R$", "", regex=False)
        .str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False)
        .astype(float)
        .fillna(0)
    )

def fmt_brl(val):
    try:
        return f"R$ {val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def find_col(df, keywords):
    """detecta coluna usando palavras-chave"""
    keys = [k.upper() for k in (keywords if isinstance(keywords, list) else [keywords])]
    for col in df.columns:
        uc = col.upper()
        if any(k in uc for k in keys):
            return col
    return None

# ---------------------------------------------------------------
# CARREGAR EXCEL DO GOOGLE DRIVE
# ---------------------------------------------------------------
URL = "https://drive.google.com/uc?id=1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b"

try:
    raw = requests.get(URL)
    raw.raise_for_status()
    buffer = BytesIO(raw.content)
    xls = pd.ExcelFile(buffer)
    sheets = {s.upper(): s for s in xls.sheet_names}
except Exception as e:
    st.error(f"Erro ao carregar planilha: {e}")
    st.stop()

def load(name):
    upper = name.upper()
    if upper not in sheets:
        return pd.DataFrame()
    return clean_df(pd.read_excel(buffer, sheet_name=sheets[upper]))

vendas = load("VENDAS")
estoque = load("ESTOQUE")

# ---------------------------------------------------------------
# PREPARAR VENDAS — DETECÇÃO AUTOMÁTICA
# ---------------------------------------------------------------
if not vendas.empty:
    col_data = find_col(vendas, ["DATA"])
    col_prod = find_col(vendas, ["PRODUTO", "DESC"])
    col_qtd  = find_col(vendas, ["QTD", "QUANT"])
    col_vu   = find_col(vendas, ["VALOR VENDA", "PREÇO", "PRECO"])
    col_vt   = find_col(vendas, ["VALOR TOTAL", "TOTAL"])
    col_luc  = find_col(vendas, ["LUCRO"])

    vendas["_DATA"] = pd.to_datetime(vendas[col_data], dayfirst=True, errors="coerce") if col_data else pd.NaT
    vendas["_PROD"] = vendas[col_prod].astype(str) if col_prod else "(sem produto)"
    vendas["_QTD"]  = pd.to_numeric(vendas[col_qtd], errors="coerce").fillna(0) if col_qtd else 0
    vendas["_VU"]   = parse_money(vendas[col_vu]) if col_vu else 0
    vendas["_VT"]   = parse_money(vendas[col_vt]) if col_vt else vendas["_QTD"] * vendas["_VU"]
    vendas["_LUCRO"] = parse_money(vendas[col_luc]) if col_luc else 0
    vendas["_LUCRO_TOTAL"] = vendas["_LUCRO"] * vendas["_QTD"]
    vendas["_PERIODO"] = vendas["_DATA"].dt.to_period("M").astype(str)

else:
    vendas = pd.DataFrame(columns=["_DATA","_PROD","_QTD","_VT","_LUCRO_TOTAL","_PERIODO"])

# ---------------------------------------------------------------
# PREPARAR ESTOQUE — DETECÇÃO AUTOMÁTICA
# ---------------------------------------------------------------
if not estoque.empty:
    e_prod = find_col(estoque, ["PROD"])
    e_qtd  = find_col(estoque, ["QTD","ESTOQUE"])
    e_val  = find_col(estoque, ["VENDA","PREÇO","PRECO"])

    estoque["_PROD"] = estoque[e_prod] if e_prod else "(sem)"
    estoque["_QTD"]  = pd.to_numeric(estoque[e_qtd], errors="coerce").fillna(0) if e_qtd else 0
    estoque["_VU"]   = parse_money(estoque[e_val]) if e_val else 0
    estoque["_VT"]   = estoque["_QTD"] * estoque["_VU"]
else:
    estoque = pd.DataFrame(columns=["_PROD","_QTD","_VU","_VT"])

# ---------------------------------------------------------------
# PERÍODOS DISPONÍVEIS
# ---------------------------------------------------------------
periods = sorted(vendas["_PERIODO"].dropna().unique(), reverse=True)
period_map = {"Geral": None}
for p in periods:
    y,m = p.split("-")
    pretty = datetime(int(y),int(m),1).strftime("%b %Y")
    period_map[f"{pretty} ({p})"] = p

# ---------------------------------------------------------------
# TABS
# ---------------------------------------------------------------
tab1, tab2 = st.tabs(["📈 Visão Geral", "📦 Estoque Atual"])

# ---------------------------------------------------------------
# TAB 1 - VISÃO GERAL
# ---------------------------------------------------------------
with tab1:
    periodo_sel = st.selectbox("Período", list(period_map.keys()))
    per_val = period_map[periodo_sel]

    dfp = vendas if per_val is None else vendas[vendas["_PERIODO"] == per_val]

    total_vendido = dfp["_VT"].sum()
    total_qtd = dfp["_QTD"].sum()
    total_lucro = dfp["_LUCRO_TOTAL"].sum()
    total_estoque = estoque["_VT"].sum()

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("💰 Vendido", fmt_brl(total_vendido))
    c2.metric("📦 Quantidade", int(total_qtd))
    c3.metric("💸 Lucro", fmt_brl(total_lucro))
    c4.metric("🏪 Valor Estoque", fmt_brl(total_estoque))

    st.markdown("---")
    st.subheader("🏆 Top 10 Produtos Mais Vendidos")

    if not dfp.empty:
        grp = dfp.groupby("_PROD").agg(
            QTDE=("_QTD","sum"),
            TOTAL=("_VT","sum")
        ).reset_index().sort_values("TOTAL", ascending=False).head(10)

        fig = px.bar(
            grp, x="TOTAL", y="_PROD",
            orientation="h",
            text="QTDE",
            color="TOTAL",
            color_continuous_scale=["#FFD700","#B8860B"]
        )
        fig.update_layout(plot_bgcolor="#000", paper_bgcolor="#000", font_color="#FFD700")
        fig.update_traces(textposition="outside")
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Nenhuma venda no período selecionado.")

    st.markdown("---")
    st.subheader("📋 Vendas do Período")

    if not dfp.empty:
        df_show = dfp[["_DATA","_PROD","_QTD","_VT","_LUCRO_TOTAL"]].copy()
        df_show["_DATA"] = df_show["_DATA"].dt.strftime("%d/%m/%Y")
        df_show["_VT"] = df_show["_VT"].apply(fmt_brl)
        df_show["_LUCRO_TOTAL"] = df_show["_LUCRO_TOTAL"].apply(fmt_brl)

        df_show.columns = ["Data","Produto","Qtd","Valor","Lucro"]

        st.dataframe(df_show)
    else:
        st.info("Nenhuma venda para exibir.")

# ---------------------------------------------------------------
# TAB 2 - ESTOQUE
# ---------------------------------------------------------------
with tab2:
    st.subheader("📦 Estoque Atual")

    if not estoque.empty:
        df_est = estoque[["_PROD","_QTD","_VU"]].copy()
        df_est["_VU"] = df_est["_VU"].apply(fmt_brl)
        df_est.columns = ["Produto","Estoque","Preço Venda"]
        st.dataframe(df_est)
    else:
        st.info("Estoque vazio ou inválido.")

# ---------------------------------------------------------------
# DEBUG OPCIONAL
# ---------------------------------------------------------------
with st.expander("🔧 Diagnóstico"):
    st.write("Sheets:", xls.sheet_names)
    st.write("Vendas:", vendas.head())
    st.write("Estoque:", estoque.head())

