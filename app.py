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
# Mapear colunas com segurança
# ======================
def check_col(df, col_name, display_name):
    if col_name is None or col_name not in df.columns:
        st.warning(f"Coluna '{display_name}' não encontrada!")
        return None
    return col_name

# ESTOQUE
e_prod = check_col(estoque, find_col(estoque, "PRODUTO"), "PRODUTO")
e_qtd = check_col(estoque, find_col(estoque, "EM ESTOQUE", "QTD", "QUANTIDADE"), "QUANTIDADE")
e_valor_unit = check_col(estoque, find_col(estoque, "Valor Venda Sugerido", "VALOR VENDA"), "VALOR VENDA")

# VENDAS
v_data = check_col(vendas, find_col(vendas, "DATA"), "DATA")
v_prod = check_col(vendas, find_col(vendas, "PRODUTO"), "PRODUTO")
v_qtd = check_col(vendas, find_col(vendas, "QTD", "QUANTIDADE"), "QTD")
v_val_unit = check_col(vendas, find_col(vendas, "VALOR VENDA", "VALOR_VENDA"), "VALOR VENDA")
v_val_total = check_col(vendas, find_col(vendas, "VALOR TOTAL", "VALOR_TOTAL", "TOTAL"), "VALOR TOTAL")
v_lucro = check_col(vendas, find_col(vendas, "LUCRO"), "LUCRO")

# COMPRAS (opcional)
c_data = check_col(compras, find_col(compras, "DATA"), "DATA")
c_prod = check_col(compras, find_col(compras, "PRODUTO"), "PRODUTO")
c_qtd = check_col(compras, find_col(compras, "QUANTIDADE", "QTD"), "QUANTIDADE")
c_custo_unit = check_col(compras, find_col(compras, "CUSTO UNITÁRIO", "CUSTO UNIT"), "CUSTO UNITÁRIO")
c_custo_total = check_col(compras, find_col(compras, "CUSTO TOTAL", "VALOR TOTAL"), "CUSTO TOTAL")

# ======================
# Normalizar dados
# ======================
if vendas is not None:
    if v_data in vendas.columns:
        vendas[v_data] = pd.to_datetime(vendas[v_data], errors="coerce")
    if v_val_unit in vendas.columns: vendas["_VAL_UNIT"] = to_num(vendas[v_val_unit])
    else: vendas["_VAL_UNIT"] = 0
    if v_qtd in vendas.columns: vendas["_QTD"] = to_num(vendas[v_qtd])
    else: vendas["_QTD"] = 0
    if v_val_total in vendas.columns: vendas["_VAL_TOTAL"] = to_num(vendas[v_val_total])
    else: vendas["_VAL_TOTAL"] = vendas["_VAL_UNIT"] * vendas["_QTD"]
    if v_lucro in vendas.columns: vendas["_LUCRO"] = to_num(vendas[v_lucro])
    else: vendas["_LUCRO"] = vendas["_VAL_UNIT"] * vendas["_QTD"]

if estoque is not None:
    if e_qtd in estoque.columns: estoque["_QTD_ESTOQUE"] = to_num(estoque[e_qtd])
    else: estoque["_QTD_ESTOQUE"] = 0
    if e_valor_unit in estoque.columns: estoque["_VAL_UNIT_ESTOQ"] = to_num(estoque[e_valor_unit])
    else: estoque["_VAL_UNIT_ESTOQ"] = 0
    estoque["_VAL_TOTAL_ESTOQUE"] = estoque["_QTD_ESTOQUE"] * estoque["_VAL_UNIT_ESTOQ"]

# ======================
# Sidebar filtros
# ======================
st.sidebar.header("Filtros")
prod_set = set()
if vendas is not None and v_prod in vendas.columns: prod_set.update(vendas[v_prod].dropna().astype(str).unique())
if estoque is not None and e_prod in estoque.columns: prod_set.update(estoque[e_prod].dropna().astype(str).unique())
prod_list = sorted([p for p in prod_set if str(p).strip() != ""])
prod_filter = st.sidebar.multiselect("Produtos (filtrar)", options=prod_list, default=prod_list)
st.sidebar.markdown("---")
st.sidebar.caption("Aplicar filtros atualiza KPIs e Top 10 automaticamente.")

# ======================
# Filtrar vendas
# ======================
vendas_f = vendas.copy() if vendas is not None else pd.DataFrame()
if v_prod in (vendas.columns if vendas is not None else []) and prod_filter:
    vendas_f = vendas_f[vendas_f[v_prod].astype(str).isin(prod_filter)]

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

    # Top 10 produtos vendidos
    if v_prod in (vendas_f.columns if vendas_f is not None else []) and v_qtd in (vendas_f.columns if vendas_f is not None else []):
        top = vendas_f.groupby(v_prod).agg(
            QTDE_SOMADA=(v_qtd, lambda s: to_num(s).sum()),
            VAL_TOTAL=("_VAL_TOTAL", lambda s: to_num(s).sum())
        ).reset_index().sort_values("VAL_TOTAL", ascending=False).head(10)
        if not top.empty:
            fig_top = px.bar(top, x="VAL_TOTAL", y=v_prod, orientation="h",
                             text="QTDE_SOMADA", color="VAL_TOTAL", color_continuous_scale=["#FFD700","#B8860B"])
            fig_top.update_traces(texttemplate='%{text:.0f} un', textposition='outside')
            fig_top.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000", font_color="#FFD700",
                                  yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_top, use_container_width=True)
            top_display = top.copy()
            top_display["VAL_TOTAL"] = top_display["VAL_TOTAL"].apply(fmt_brl)
            top_display["QTDE_SOMADA"] = top_display["QTDE_SOMADA"].astype(int)
            st.table(top_display.rename(columns={v_prod:"PRODUTO","QTDE_SOMADA":"QUANTIDADE","VAL_TOTAL":"VALOR TOTAL"}))

with tab2:
    st.markdown("## Estoque Atual")
    if estoque is not None and e_prod in estoque.columns:
        est_view = estoque.copy()
        est_view["PRODUTO"] = est_view[e_prod].astype(str)
        est_view["QUANTIDADE"] = est_view["_QTD_ESTOQUE"].astype(int)
        est_view["VALOR_TOTAL_ESTOQUE"] = est_view["_VAL_TOTAL_ESTOQUE"]
        if prod_filter: est_view = est_view[est_view["PRODUTO"].isin(prod_filter)]
        st.dataframe(est_view[["PRODUTO","QUANTIDADE","VALOR_TOTAL_ESTOQUE"]])

st.markdown("---")
st.caption("Dashboard — Preto + Dourado. Baseado em arquivo do OneDrive.")
