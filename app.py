# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime
import requests
from io import BytesIO

# ======================
# Config visual (Alto contraste: Preto + Dourado)
# ======================
st.set_page_config(page_title="Painel - Loja Importados", layout="wide")

st.markdown(
    """
    <style>
      :root { --gold:#FFD700; --bg:#000000; --card:#0f0f0f; --muted:#bbbbbb; --white:#FFFFFF; }
      .stApp { background-color: var(--bg); color: var(--gold); }
      .title { color: var(--gold); font-weight:700; font-size:22px; }
      .subtitle { color: var(--muted); font-size:12px; margin-bottom:12px; }
      .kpi { background: linear-gradient(90deg, #111111, #0b0b0b); padding:12px; border-radius:10px; text-align:center; }
      .kpi-value { color: var(--gold); font-size:22px; font-weight:700; }
      .kpi-label { color:var(--muted); font-size:13px; }
      .stDataFrame table { background-color:#050505; color:var(--white); }
      .small { color: var(--muted); font-size:12px; }
      .table-card { background: linear-gradient(90deg,#0b0b0b,#111111); border: 1px solid rgba(255,215,0,0.08); padding:12px; border-radius:10px; }
      .table-card h4 { color: var(--gold); margin:0 0 8px 0; }
      .table-card .big { font-size:15px; color:var(--white); }
      .small-select .stSelectbox>div>div { font-size:14px; }
      .summary-table .dataframe td, .summary-table .dataframe th { font-size:13px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div class='title'>📊 Painel — Loja Importados</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Tema: Preto & Dourado (alto contraste) • Abas: Visão Geral / Estoque</div>", unsafe_allow_html=True)
st.markdown("---")

# ======================
# Helpers
# ======================
def detect_header(path_or_buffer, sheet_name, look_for="PRODUTO"):
    try:
        raw = pd.read_excel(path_or_buffer, sheet_name=sheet_name, header=None)
    except Exception:
        return None, None
    header_row = None
    for i in range(min(len(raw), 12)):
        row = raw.iloc[i].astype(str).str.upper().fillna("")
        if any(look_for.upper() in v for v in row):
            header_row = i
            break
    if header_row is None:
        header_row = 0
    try:
        df = pd.read_excel(path_or_buffer, sheet_name=sheet_name, header=header_row)
        return df, header_row
    except Exception:
        return None, None

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
        if cand is None:
            continue
        pat = re.sub(r"\s+", " ", str(cand)).strip().upper()
        for c in df.columns:
            if pat in str(c).upper():
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
# Load Excel from Google Drive
# ======================
GDRIVE_URL = "https://drive.google.com/uc?id=1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b"

try:
    res = requests.get(GDRIVE_URL)
    res.raise_for_status()
    excel_buffer = BytesIO(res.content)
    xls = pd.ExcelFile(excel_buffer)
    available_sheets = [s.upper() for s in xls.sheet_names]
except Exception as e:
    st.error(f"Erro ao acessar planilha do Google Drive: {e}")
    st.stop()

def load_and_clean(name):
    if name not in available_sheets:
        return None
    df, hdr = detect_header(excel_buffer, name)
    df = clean_df(df)
    return df

estoque = load_and_clean("ESTOQUE")
vendas = load_and_clean("VENDAS")
compras = load_and_clean("COMPRAS")

if vendas is None:
    vendas = pd.DataFrame()
if estoque is None:
    estoque = pd.DataFrame()
if compras is None:
    compras = pd.DataFrame()

# ======================
# Map columns
# ======================
e_prod = find_col(estoque, "PRODUTO")
e_qtd = find_col(estoque, "EM ESTOQUE", "QTD", "QUANTIDADE", "QUANT")
e_val_venda = find_col(estoque, "Valor Venda Sugerido", "VALOR VENDA", "VALOR VENDA SUGERIDO")
e_val_custo = find_col(estoque, "Media C. UNITARIO", "MEDIA C. UNITARIO", "CUSTO UNITARIO", "CUSTO")

v_data = find_col(vendas, "DATA", "DT")
v_prod = find_col(vendas, "PRODUTO")
v_qtd = find_col(vendas, "QTD", "QUANTIDADE", "QUANT")
v_val_unit = find_col(vendas, "VALOR VENDA", "VALOR_VENDA", "PRECO")
v_val_total = find_col(vendas, "VALOR TOTAL", "VALOR_TOTAL", "TOTAL")
v_lucro = find_col(vendas, "LUCRO")

# ======================
# Prepare numeric columns
# ======================
if not vendas.empty:
    if v_data and v_data in vendas.columns:
        vendas[v_data] = pd.to_datetime(vendas[v_data], errors="coerce")
    vendas["_QTD"] = to_num(vendas[v_qtd]) if v_qtd in vendas.columns else 0
    if v_val_total and v_val_total in vendas.columns:
        vendas["_VAL_TOTAL"] = to_num(vendas[v_val_total])
    elif v_val_unit and v_val_unit in vendas.columns:
        vendas["_VAL_TOTAL"] = to_num(vendas[v_val_unit]) * vendas["_QTD"]
    else:
        vendas["_VAL_TOTAL"] = 0
    if v_lucro and v_lucro in vendas.columns:
        vendas["_LUCRO"] = to_num(vendas[v_lucro])
    else:
        vendas["_LUCRO"] = 0
else:
    vendas["_QTD"] = pd.Series(dtype=float)
    vendas["_VAL_TOTAL"] = pd.Series(dtype=float)
    vendas["_LUCRO"] = pd.Series(dtype=float)

if not estoque.empty:
    estoque["_QTD"] = to_num(estoque[e_qtd]) if e_qtd in estoque.columns else 0
    estoque["_VAL_VENDA_UNIT"] = to_num(estoque[e_val_venda]) if e_val_venda in estoque.columns else 0
    estoque["_VAL_CUSTO_UNIT"] = to_num(estoque[e_val_custo]) if e_val_custo in estoque.columns else 0
    estoque["_VAL_TOTAL_VENDA"] = estoque["_QTD"] * estoque["_VAL_VENDA_UNIT"]
    estoque["_VAL_TOTAL_CUSTO"] = estoque["_QTD"] * estoque["_VAL_CUSTO_UNIT"]
else:
    estoque["_QTD"] = pd.Series(dtype=float)
    estoque["_VAL_VENDA_UNIT"] = pd.Series(dtype=float)
    estoque["_VAL_CUSTO_UNIT"] = pd.Series(dtype=float)
    estoque["_VAL_TOTAL_VENDA"] = pd.Series(dtype=float)
    estoque["_VAL_TOTAL_CUSTO"] = pd.Series(dtype=float)

# ======================
# Periodos (meses)
# ======================
if not vendas.empty and "_VAL_TOTAL" in vendas.columns and v_data in vendas.columns:
    vendas["_PERIODO"] = vendas[v_data].dt.to_period("M").astype(str)
    unique_periods = sorted(vendas["_PERIODO"].unique(), reverse=True)
else:
    unique_periods = []

period_map = {"Geral": None}
for p in unique_periods:
    year, month = p.split("-")
    pretty = datetime(int(year), int(month), 1).strftime("%b %Y")
    label = f"{pretty} ({p})"
    period_map[label] = p

period_options = ["Geral"] + [k for k in period_map.keys() if k != "Geral"]

# ======================
# Tabs
# ======================
tab1, tab2 = st.tabs(["📈 Visão Geral", "📦 Estoque Atual"])

# ---- Tab 1: Visão Geral ----
with tab1:
    periodo_sel = st.selectbox("Selecione o período", period_options, index=0)
    periodo_val = period_map.get(periodo_sel)
    if periodo_val is None:
        vendas_period = vendas.copy()
    else:
        vendas_period = vendas[vendas["_PERIODO"] == periodo_val].copy()

    # KPIs
    total_vendido = vendas_period["_VAL_TOTAL"].sum() if not vendas_period.empty else 0
    total_qtd = vendas_period["_QTD"].sum() if not vendas_period.empty else 0
    lucro_period = vendas_period["_LUCRO"].sum() if not vendas_period.empty else 0
    valor_estoque_venda = estoque["_VAL_TOTAL_VENDA"].sum() if not estoque.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Vendido", fmt_brl(total_vendido))
    c2.metric("📈 Qtde Vendida", f"{int(total_qtd)}")
    c3.metric("💸 Lucro do Período", fmt_brl(lucro_period))
    c4.metric("📦 Valor Estoque (Venda)", fmt_brl(valor_estoque_venda))

    st.markdown("---")

    # Top10 produtos
    st.subheader("🏆 Top 10 — Produtos Mais Vendidos")
    if not vendas_period.empty and v_prod in vendas_period.columns:
        grp = vendas_period.groupby(v_prod).agg(QTDE_SOMADA=("_QTD", "sum"), VAL_TOTAL=("_VAL_TOTAL","sum")).reset_index()
        grp = grp.sort_values("VAL_TOTAL", ascending=False).head(10)
        fig_top = px.bar(grp, x="VAL_TOTAL", y=v_prod, orientation="h", text="QTDE_SOMADA",
                         color="VAL_TOTAL", color_continuous_scale=["#FFD700","#B8860B"])
        fig_top.update_traces(texttemplate='%{text:.0f} un', textposition='outside')
        fig_top.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000", font_color="#FFD700",
                              yaxis={'categoryorder':'total ascending'}, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig_top, use_container_width=True)

    st.markdown("---")

    # Vendas do período
    st.subheader("📋 Vendas do Período")
    if not vendas_period.empty:
        vendas_disp = vendas_period.copy()
        vendas_disp[v_data] = vendas_disp[v_data].dt.strftime("%d/%m/%Y")
        vendas_disp["_VAL_TOTAL"] = vendas_disp["_VAL_TOTAL"].apply(fmt_brl)
        vendas_disp["_LUCRO"] = vendas_disp["_LUCRO"].apply(fmt_brl)
        vendas_disp = vendas_disp.rename(columns={v_data:"Data", v_prod:"Produto","_QTD":"Quantidade","_VAL_TOTAL":"Valor","_LUCRO":"Lucro"})
        st.dataframe(vendas_disp.reset_index(drop=True))
    else:
        st.info("Nenhuma venda registrada para o período selecionado.")

# ---- Tab 2: Estoque Atual ----
with tab2:
    st.subheader("📦 Estoque Atual (consulta)")
    if not estoque.empty and e_prod in estoque.columns:
        est = estoque.copy()
        est["PRODUTO"] = est[e_prod].astype(str)
        est["QTD"] = est["_QTD"].astype(int)
        est["PRECO VENDA"] = est["_VAL_VENDA_UNIT"].apply(fmt_brl)
        est["PRECO CUSTO"] = est["_VAL_CUSTO_UNIT"].apply(fmt_brl)
        st.dataframe(est[["PRODUTO","QTD","PRECO VENDA","PRECO CUSTO"]].reset_index(drop=True))
    else:
        st.info("Estoque vazio ou coluna de produto não encontrada.")
