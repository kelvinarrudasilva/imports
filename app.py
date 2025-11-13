# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO
import re

# ======================
# Config visual (Alto contraste: Preto + Dourado)
# ======================
st.set_page_config(page_title="Painel - Loja Importados", layout="wide")

st.markdown("""
<style>
  :root { --gold:#FFD700; --bg:#000000; --card:#0f0f0f; --muted:#bfbfbf; }
  .stApp { background-color: var(--bg); color: var(--gold); }
  .title { color: var(--gold); font-weight:700; font-size:22px; }
  .subtitle { color: var(--muted); font-size:12px; margin-bottom:12px; }
  .kpi { background: linear-gradient(90deg, #111111, #0b0b0b); padding:12px; border-radius:10px; text-align:center; }
  .kpi-value { color: var(--gold); font-size:20px; font-weight:700; }
  .kpi-label { color:var(--muted); font-size:13px; }
  .stDataFrame table { background-color:#050505; color:#e6e2d3; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='title'>📊 Painel — Loja Importados</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Tema: Alto contraste — Preto & Dourado • Abas: Visão Geral / Estoque</div>", unsafe_allow_html=True)
st.markdown("---")

# ======================
# Funções utilitárias
# ======================
def clean_df(df):
    if df is None:
        return None
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains("^Unnamed", na=False)]
    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all").reset_index(drop=True)
    return df

def find_col(df, *candidates):
    if df is None:
        return None
    for cand in candidates:
        pattern = re.sub(r"\s+", " ", str(cand)).strip().upper()
        for c in df.columns:
            if pattern in str(c).upper():
                return c
    return None

def to_num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0)

def fmt_brl(x):
    try:
        return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

# ======================
# Download do Excel do OneDrive
# ======================
ONEDRIVE_LINK = "https://1drv.ms/x/c/bc81746c0a7c734e/IQDHyRSnkqqEQZT1Vg9e3VJwARLyccQhj9JG3uL2lBdduGg?download=1"

try:
    r = requests.get(ONEDRIVE_LINK)
    r.raise_for_status()
    excel_bytes = BytesIO(r.content)
except Exception as e:
    st.error(f"Erro ao baixar o arquivo do OneDrive: {e}")
    st.stop()

# ======================
# Carregar planilhas
# ======================
EXCEL = excel_bytes
xls = pd.ExcelFile(EXCEL)
available = set([s.upper() for s in xls.sheet_names])
st.sidebar.markdown("### Fonte")
st.sidebar.write("Abas encontradas:", list(xls.sheet_names))
st.sidebar.markdown("---")

def load_sheet(name):
    if name.upper() not in available:
        return None, f"Aba '{name}' não encontrada"
    df = pd.read_excel(EXCEL, sheet_name=name)
    df = clean_df(df)
    return df, None

estoque, err_e = load_sheet("ESTOQUE")
vendas, err_v = load_sheet("VENDAS")
compras, err_c = load_sheet("COMPRAS")

# ======================
# Mapear colunas
# ======================
e_prod = find_col(estoque, "PRODUTO")
e_qtd = find_col(estoque, "EM ESTOQUE", "QTD", "QUANTIDADE")
e_valor_unit = find_col(estoque, "Valor Venda Sugerido", "VALOR VENDA")

v_data = find_col(vendas, "DATA")
v_prod = find_col(vendas, "PRODUTO")
v_qtd = find_col(vendas, "QTD", "QUANTIDADE")
v_val_unit = find_col(vendas, "VALOR VENDA", "VALOR_VENDA")
v_val_total = find_col(vendas, "VALOR TOTAL", "VALOR_TOTAL", "TOTAL")
v_lucro = find_col(vendas, "LUCRO")

# ======================
# Preparar dados
# ======================
if vendas is not None and v_data in vendas.columns:
    vendas[v_data] = pd.to_datetime(vendas[v_data], errors="coerce")
    vendas["_VAL_UNIT"] = to_num(vendas[v_val_unit]) if v_val_unit in vendas.columns else 0
    vendas["_QTD"] = to_num(vendas[v_qtd]) if v_qtd in vendas.columns else 0
    vendas["_VAL_TOTAL"] = to_num(vendas[v_val_total]) if v_val_total in vendas.columns else vendas["_VAL_UNIT"] * vendas["_QTD"]
    vendas["_LUCRO"] = to_num(vendas[v_lucro]) if v_lucro in vendas.columns else vendas["_VAL_UNIT"] * vendas["_QTD"]

if estoque is not None:
    estoque["_QTD_ESTOQUE"] = to_num(estoque[e_qtd]) if e_qtd in estoque.columns else 0
    estoque["_VAL_UNIT_ESTOQ"] = to_num(estoque[e_valor_unit]) if e_valor_unit in estoque.columns else 0
    estoque["_VAL_TOTAL_ESTOQUE"] = estoque["_QTD_ESTOQUE"] * estoque["_VAL_UNIT_ESTOQ"]

# ======================
# Sidebar filtros
# ======================
st.sidebar.header("Filtros")
prod_set = set()
if vendas is not None: prod_set.update(vendas[v_prod].dropna().astype(str).unique())
if estoque is not None: prod_set.update(estoque[e_prod].dropna().astype(str).unique())
prod_list = sorted([p for p in prod_set if str(p).strip() != ""])
prod_filter = st.sidebar.multiselect("Produtos (filtrar)", options=prod_list, default=prod_list)
st.sidebar.markdown("---")
st.sidebar.caption("Aplicar filtros atualiza KPIs automaticamente.")

# ======================
# Filtrar vendas
# ======================
vendas_f = vendas.copy() if vendas is not None else pd.DataFrame()
if prod_filter: vendas_f = vendas_f[vendas_f[v_prod].astype(str).isin(prod_filter)]

# ======================
# Abas
# ======================
tab1, tab2 = st.tabs(["📈 Visão Geral", "📦 Estoque Atual"])

with tab1:
    st.markdown("## Visão Geral — vendas e lucro")
    total_vendido = vendas_f["_VAL_TOTAL"].sum() if "_VAL_TOTAL" in vendas_f.columns else 0
    lucro_total = vendas_f["_LUCRO"].sum() if "_LUCRO" in vendas_f.columns else 0
    valor_estoque = estoque["_VAL_TOTAL_ESTOQUE"].sum() if estoque is not None else 0
    k1, k2, k3 = st.columns(3)
    k1.metric("💰 Vendido", f"{fmt_brl(total_vendido)}")
    k2.metric("📈 Lucro", f"{fmt_brl(lucro_total)}")
    k3.metric("📦 Estoque", f"{fmt_brl(valor_estoque)}")

with tab2:
    st.markdown("## Estoque Atual")
    if estoque is not None:
        est_view = estoque.copy()
        est_view["PRODUTO"] = est_view[e_prod].astype(str)
        est_view["QUANTIDADE"] = est_view["_QTD_ESTOQUE"].astype(int)
        est_view["VALOR_TOTAL_ESTOQUE"] = est_view["_VAL_TOTAL_ESTOQUE"]
        if prod_filter: est_view = est_view[est_view["PRODUTO"].isin(prod_filter)]
        st.dataframe(est_view[["PRODUTO","QUANTIDADE","VALOR_TOTAL_ESTOQUE"]])

st.markdown("---")
st.caption("Dashboard — Preto + Dourado. Baseado em arquivo do OneDrive.")
