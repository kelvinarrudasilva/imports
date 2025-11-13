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
st.markdown("<div class='subtitle'>Tema: Preto & Dourado (alto contraste) • Abas: Visão Geral / Estoque / Vendas</div>", unsafe_allow_html=True)
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

c_custo_unit = find_col(compras, "CUSTO UNITÁRIO", "CUSTO UNIT", "CUSTO_UNIT")
c_custo_total = find_col(compras, "CUSTO TOTAL", "VALOR TOTAL", "TOTAL")

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

period_options = ["Geral"]
period_map = {"Geral": None}
for p in unique_periods:
    try:
        year, month = p.split("-")
        pretty = datetime(int(year), int(month), 1).strftime("%b %Y")
    except Exception:
        pretty = p
    label = f"{pretty} ({p})"
    period_options.append(label)
    period_map[label] = p

current_period = datetime.now().strftime("%Y-%m")
default_label = "Geral"
for lbl, val in period_map.items():
    if val == current_period:
        default_label = lbl
        break

# ======================
# Tabs
# ======================
# Copie todo o restante do seu código original aqui
# Tabs: Visão Geral, Estoque Atual, Vendas Detalhadas
# KPIs, Top10, gráficos, tabelas, diagnóstico
# Tudo igual ao app atual, só que agora usando 'estoque', 'vendas', 'compras' carregados do Google Drive
