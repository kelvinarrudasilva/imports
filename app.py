# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re

st.set_page_config(page_title="Painel Loja Importados", layout="wide")

# ======================
# Estilo Dark Moderno
# ======================
st.markdown("""
<style>
:root {
    --bg:#000000; 
    --card:#111111; 
    --text:#FFFFFF; 
    --primary:#00FF00; 
    --muted:#AAAAAA;
}
body { background-color: var(--bg); color: var(--text);}
.title { font-size:36px; font-weight:900; color: var(--primary); margin-bottom:5px; }
.subtitle { font-size:18px; color: var(--muted); margin-bottom:15px; }
.kpi { background: var(--card); padding:20px; border-radius:15px; text-align:center; margin-bottom:10px;}
.kpi-value { color: var(--primary); font-size:32px; font-weight:900; }
.kpi-label { color:var(--muted); font-size:18px; }
.stDataFrame table { background-color:var(--card); color:var(--text); font-size:16px;}
.stDataFrame thead th { color: var(--primary); font-weight:700; font-size:16px;}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='title'>📊 Painel — Loja Importados</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Dashboard Escuro | Contraste Máximo | Responsivo</div>", unsafe_allow_html=True)
st.markdown("---")

# ======================
# Funções auxiliares
# ======================
def detect_header(path, sheet_name, look_for="PRODUTO"):
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
    header_row = None
    for i in range(min(len(raw), 12)):
        row = raw.iloc[i].astype(str).str.upper().fillna("")
        if any(look_for.upper() in v for v in row):
            header_row = i
            break
    if header_row is None:
        header_row = 0
    df = pd.read_excel(path, sheet_name=sheet_name, header=header_row)
    return df

def clean_df(df):
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
# Carregar planilha
# ======================
EXCEL = "LOJA IMPORTADOS.xlsx"
if not Path(EXCEL).exists():
    st.error(f"Arquivo '{EXCEL}' não encontrado no diretório.")
    st.stop()

xls = pd.ExcelFile(EXCEL)
available = set([s.upper() for s in xls.sheet_names])
def load_sheet(name):
    if name.upper() not in available:
        return None
    df = detect_header(EXCEL, name)
    df = clean_df(df)
    return df

estoque = load_sheet("ESTOQUE")
vendas = load_sheet("VENDAS")
compras = load_sheet("COMPRAS")

# ======================
# Mapear colunas principais
# ======================
e_prod = find_col(estoque, "PRODUTO")
e_qtd = find_col(estoque, "EM ESTOQUE", "QTD")
e_valor_unit = find_col(estoque, "Valor Venda Sugerido", "VALOR VENDA")

v_data = find_col(vendas, "DATA")
v_prod = find_col(vendas, "PRODUTO")
v_qtd = find_col(vendas, "QTD", "QUANTIDADE")
v_val_unit = find_col(vendas, "VALOR VENDA", "VALOR_VENDA")
v_val_total = find_col(vendas, "VALOR TOTAL", "VALOR_TOTAL")
v_lucro = find_col(vendas, "LUCRO")

# ======================
# Normalizar dados
# ======================
if vendas is not None:
    vendas[v_data] = pd.to_datetime(vendas[v_data], errors="coerce")
    vendas["_QTD"] = to_num(vendas[v_qtd])
    vendas["_VAL_UNIT"] = to_num(vendas[v_val_unit])
    if v_val_total in vendas.columns:
        vendas["_VAL_TOTAL"] = to_num(vendas[v_val_total])
    else:
        vendas["_VAL_TOTAL"] = vendas["_VAL_UNIT"] * vendas["_QTD"]
    if v_lucro in vendas.columns:
        vendas["_LUCRO"] = to_num(vendas[v_lucro])
    else:
        vendas["_LUCRO"] = vendas["_VAL_TOTAL"]

if estoque is not None:
    estoque["_QTD_ESTOQUE"] = to_num(estoque[e_qtd])
    estoque["_VAL_UNIT_ESTOQ"] = to_num(estoque[e_valor_unit])
    estoque["_VAL_TOTAL_ESTOQUE"] = estoque["_QTD_ESTOQUE"] * estoque["_VAL_UNIT_ESTOQ"]

# ======================
# Sidebar filtros
# ======================
st.sidebar.header("Filtros")
if vendas is not None:
    min_date = vendas[v_data].min().date()
    max_date = vendas[v_data].max().date()
    date_range = st.sidebar.date_input("Período (Vendas)", value=(min_date, max_date), min_value=min_date, max_value=max_date)
else:
    date_range = None

prod_list = sorted(list(set(vendas[v_prod].dropna().astype(str).unique()) if vendas is not None else []))
prod_filter = st.sidebar.multiselect("Produtos", options=prod_list, default=prod_list)

vendas_f = vendas.copy() if vendas is not None else pd.DataFrame()
if date_range and isinstance(date_range, (list, tuple)) and len(date_range)==2:
    d_from, d_to = date_range
    vendas_f = vendas_f[(vendas_f[v_data].dt.date >= d_from) & (vendas_f[v_data].dt.date <= d_to)]
if prod_filter:
    vendas_f = vendas_f[vendas_f[v_prod].astype(str).isin(prod_filter)]

# ======================
# Botões modernos
# ======================
selected_tab = st.radio(
    "",
    ("📈 Visão Geral", "📦 Estoque Atual", "🛒 Vendas Detalhadas"),
    horizontal=True,
    index=0
)

# ======================
# VISÃO GERAL
# ======================
if selected_tab == "📈 Visão Geral":
    st.markdown("## KPIs")
    total_vendido = vendas_f["_VAL_TOTAL"].sum() if "_VAL_TOTAL" in vendas_f.columns else 0
    lucro_total = vendas_f["_LUCRO"].sum() if "_LUCRO" in vendas_f.columns else 0
    valor_estoque = estoque["_VAL_TOTAL_ESTOQUE"].sum() if estoque is not None else 0
    k1, k2, k3 = st.columns(3)
    k1.markdown(f"<div class='kpi'><div class='kpi-label'>💰 Vendido</div><div class='kpi-value'>{fmt_brl(total_vendido)}</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi'><div class='kpi-label'>📈 Lucro</div><div class='kpi-value'>{fmt_brl(lucro_total)}</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='kpi'><div class='kpi-label'>📦 Valor Estoque</div><div class='kpi-value'>{fmt_brl(valor_estoque)}</div></div>", unsafe_allow_html=True)

    st.markdown("---")
    # ÚLTIMAS VENDAS
    st.markdown("## 🕒 Últimas Vendas")
    if not vendas_f.empty:
        ult_vendas = vendas_f.sort_values(v_data, ascending=False).head(15)
        ult_display = ult_vendas[[v_data, v_prod, "_QTD", "_VAL_UNIT", "_VAL_TOTAL", "_LUCRO"]].copy()
        ult_display.columns = ["DATA","PRODUTO","QUANTIDADE","PREÇO UNITÁRIO","VALOR TOTAL","LUCRO"]
        for col in ["PREÇO UNITÁRIO","VALOR TOTAL","LUCRO"]:
            ult_display[col] = ult_display[col].apply(fmt_brl)
        st.dataframe(ult_display, use_container_width=True)
    else:
        st.info("Nenhuma venda no período/produto filtrado.")

    st.markdown("---")
    # Top 10 produtos vendidos - gráfico torre
    st.markdown("## 🏆 Top 10 Produtos Vendidos (Quantidade)")
    if not vendas_f.empty:
        top_prod = vendas_f.groupby(v_prod)["_QTD"].sum().reset_index().sort_values("_QTD", ascending=False).head(10)
        fig_top = px.bar(top_prod, x=v_prod, y="_QTD", text="_QTD", color="_QTD", color_continuous_scale=["#00FF00","#007700"])
        fig_top.update_traces(textposition="outside")
        fig_top.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000", font_color="#FFFFFF")
        st.plotly_chart(fig_top, use_container_width=True)

    st.markdown("---")
    # Comparação vendas últimos 4 meses - gráfico torre
    st.markdown("## 📊 Vendas Últimos 4 Meses")
    if not vendas_f.empty:
        vendas_f["_MES"] = vendas_f[v_data].dt.to_period("M").astype(str)
        ult_4_meses = sorted(vendas_f["_MES"].unique())[-4:]
        vendas_4 = vendas_f[vendas_f["_MES"].isin(ult_4_meses)].groupby("_MES")["_VAL_TOTAL"].sum().reset_index()
        fig_4m = px.bar(vendas_4, x="_MES", y="_VAL_TOTAL", text="_VAL_TOTAL", color="_VAL_TOTAL", color_continuous_scale=["#00FF00","#007700"])
        fig_4m.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig_4m.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000", font_color="#FFFFFF")
        st.plotly_chart(fig_4m, use_container_width=True)
