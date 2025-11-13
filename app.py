# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re

# ======================
# Configuração da página e tema dark
# ======================
st.set_page_config(page_title="Painel Loja", layout="wide")

st.markdown("""
<style>
:root {
    --bg:#000000;
    --text:#FFFFFF;
    --muted:#BBBBBB;
    --primary:#8000FF;
    --card:#111111;
}
.stApp {
    background-color: var(--bg);
    color: var(--text);
}
.stButton>button {
    background-color: var(--primary);
    color: var(--text);
    border-radius: 8px;
    padding: 0.5em 1em;
    font-weight: bold;
}
.stButton>button:hover {
    background-color: #AA33FF;
}
.kpi {
    background: var(--card);
    padding:12px;
    border-radius:10px;
    text-align:center;
}
.kpi-value { font-size:20px; font-weight:700; color:var(--primary);}
.kpi-label { font-size:14px; color:var(--muted);}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 style='color:#FFFFFF'>📊 Painel — Loja Importados</h1>", unsafe_allow_html=True)
st.markdown("---")

# ======================
# Helpers
# ======================
def detect_header(path, sheet_name, look_for="PRODUTO"):
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
    header_row = 0
    for i in range(min(len(raw), 12)):
        row = raw.iloc[i].astype(str).str.upper().fillna("")
        if any(look_for.upper() in v for v in row):
            header_row = i
            break
    df = pd.read_excel(path, sheet_name=sheet_name, header=header_row)
    return df

def clean_df(df):
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains("^Unnamed", na=False)]
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all").reset_index(drop=True)
    return df

def to_num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0)

def fmt_brl(x):
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def find_col(df, *candidates):
    for cand in candidates:
        pattern = re.sub(r"\s+", " ", str(cand)).strip().upper()
        for c in df.columns:
            if pattern in str(c).upper():
                return c
    return None

# ======================
# Carregar planilha
# ======================
EXCEL = "LOJA IMPORTADOS.xlsx"
if not Path(EXCEL).exists():
    st.error(f"Arquivo '{EXCEL}' não encontrado.")
    st.stop()

xls = pd.ExcelFile(EXCEL)
estoque = clean_df(detect_header(EXCEL, "ESTOQUE"))
vendas = clean_df(detect_header(EXCEL, "VENDAS"))

# Mapear colunas
e_prod = find_col(estoque, "PRODUTO")
e_qtd = find_col(estoque, "EM ESTOQUE", "QTD", "QUANTIDADE")

v_data = find_col(vendas, "DATA")
v_prod = find_col(vendas, "PRODUTO")
v_qtd = find_col(vendas, "QTD", "QUANTIDADE")
v_val_total = find_col(vendas, "VALOR TOTAL", "VALOR_TOTAL", "TOTAL")

# Normalizar vendas
vendas[v_data] = pd.to_datetime(vendas[v_data], errors="coerce")
vendas["_VAL_TOTAL"] = to_num(vendas[v_val_total])
vendas["_QTD"] = to_num(vendas[v_qtd])

# Normalizar estoque
estoque["_QTD_ESTOQUE"] = to_num(estoque[e_qtd])

# ======================
# Sidebar
# ======================
st.sidebar.header("Filtros Gerais")
prod_list = sorted(vendas[v_prod].dropna().astype(str).unique())
prod_filter = st.sidebar.multiselect("Produtos", prod_list, default=prod_list)

date_range = st.sidebar.date_input("Período (Vendas)", value=(vendas[v_data].min(), vendas[v_data].max()))

vendas_f = vendas.copy()
if date_range and len(date_range) == 2:
    d_from, d_to = date_range
    vendas_f = vendas_f[(vendas_f[v_data].dt.date >= d_from) & (vendas_f[v_data].dt.date <= d_to)]
if prod_filter:
    vendas_f = vendas_f[vendas_f[v_prod].astype(str).isin(prod_filter)]

# ======================
# Abas
# ======================
tab1, tab2, tab3 = st.tabs(["📈 Visão Geral", "📦 Estoque Atual", "🛒 Vendas Detalhadas"])

# ----------------------
# Visão Geral
# ----------------------
with tab1:
    st.markdown("## KPIs")
    total_vendido = vendas_f["_VAL_TOTAL"].sum()
    total_qtd = vendas_f["_QTD"].sum()
    k1, k2 = st.columns(2)
    k1.markdown(f"<div class='kpi'><div class='kpi-label'>💰 Vendido</div><div class='kpi-value'>{fmt_brl(total_vendido)}</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi'><div class='kpi-label'>📦 Qtde total vendida</div><div class='kpi-value'>{int(total_qtd)}</div></div>", unsafe_allow_html=True)
    
    # Top 10 produtos vendidos
    st.markdown("## Top 10 Produtos Mais Vendidos")
    top10 = vendas_f.groupby(v_prod)["_QTD"].sum().reset_index().sort_values("_QTD", ascending=False).head(10)
    fig_top10 = px.bar(top10, x=v_prod, y="_QTD", color="_QTD", color_continuous_scale=["#8000FF","#D280FF"], text="_QTD")
    fig_top10.update_traces(textposition='outside')
    fig_top10.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000", font_color="#FFFFFF", xaxis_title="Produto", yaxis_title="Quantidade")
    st.plotly_chart(fig_top10, use_container_width=True)
    
    # Vendas últimos 4 meses
    st.markdown("## Vendas Últimos 4 Meses")
    vendas_f["_MES"] = vendas_f[v_data].dt.strftime("%b %Y")
    ult_4 = sorted(vendas_f["_MES"].unique())[-4:]
    df_4m = vendas_f[vendas_f["_MES"].isin(ult_4)].groupby("_MES")["_VAL_TOTAL"].sum().reset_index()
    fig_4m = px.bar(df_4m, x="_MES", y="_VAL_TOTAL", color="_VAL_TOTAL", color_continuous_scale=["#8000FF","#D280FF"], text="_VAL_TOTAL")
    fig_4m.update_traces(texttemplate='R$ %{text:,.2f}', textposition='outside')
    fig_4m.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000", font_color="#FFFFFF", xaxis_title="Mês", yaxis_title="Total R$")
    st.plotly_chart(fig_4m, use_container_width=True)

# ----------------------
# Estoque Atual
# ----------------------
with tab2:
    st.markdown("## Estoque Atual")
    est_view = estoque.copy()
    if prod_filter:
        est_view = est_view[est_view[e_prod].astype(str).isin(prod_filter)]
    
    total_est = est_view["_QTD_ESTOQUE"].sum()
    st.metric("📦 Quantidade Total em Estoque", f"{int(total_est)}")
    
    st.markdown("## Top 15 Produtos em Estoque (Quantidade)")
    top_est = est_view[[e_prod, "_QTD_ESTOQUE"]].sort_values("_QTD_ESTOQUE", ascending=False).head(15)
    fig_est = px.bar(top_est, x=e_prod, y="_QTD_ESTOQUE", color="_QTD_ESTOQUE", color_continuous_scale=["#8000FF","#D280FF"], text="_QTD_ESTOQUE")
    fig_est.update_traces(textposition='outside')
    fig_est.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000", font_color="#FFFFFF", xaxis_title="Produto", yaxis_title="Quantidade")
    st.plotly_chart(fig_est, use_container_width=True)
    
    st.markdown("## Estoque Completo")
    st.dataframe(est_view[[e_prod, "_QTD_ESTOQUE"]])

# ----------------------
# Vendas Detalhadas
# ----------------------
with tab3:
    st.markdown("## Últimas Vendas")
    st.dataframe(vendas_f[[v_data, v_prod, "_QTD", "_VAL_TOTAL"]].sort_values(v_data, ascending=False))
