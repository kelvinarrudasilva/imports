# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re

# ======================
# Config visual (Claro + Verde)
# ======================
st.set_page_config(page_title="Painel - Loja Importados", layout="wide")

st.markdown("""
<style>
:root { --green:#28a745; --bg:#f5f5f5; --card:#ffffff; --muted:#6c757d; }
.stApp { background-color: var(--bg); color: var(--green); }
.title { color: var(--green); font-weight:700; font-size:22px; }
.subtitle { color: var(--muted); font-size:12px; margin-bottom:12px; }
.kpi { background: linear-gradient(90deg, #e8f5e9, #d0f0c0); padding:12px; border-radius:10px; text-align:center; }
.kpi-value { color: var(--green); font-size:20px; font-weight:700; }
.kpi-label { color:var(--muted); font-size:13px; }
.stDataFrame table { background-color:#ffffff; color:#000000; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='title'>📊 Painel — Loja Importados</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Tema: Claro & Verde • Navegue entre as abas</div>", unsafe_allow_html=True)
st.markdown("---")

# ======================
# Funções utilitárias
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
    return df, header_row

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
# Carregar planilha
# ======================
EXCEL = "LOJA IMPORTADOS.xlsx"
if not Path(EXCEL).exists():
    st.error(f"Arquivo '{EXCEL}' não encontrado.")
    st.stop()

xls = pd.ExcelFile(EXCEL)
available = set([s.upper() for s in xls.sheet_names])
needed = {"ESTOQUE", "VENDAS", "COMPRAS"}

def load_sheet(name):
    if name not in available:
        return None
    df, _ = detect_header(EXCEL, name)
    return clean_df(df)

estoque = load_sheet("ESTOQUE")
vendas = load_sheet("VENDAS")
compras = load_sheet("COMPRAS")

# ======================
# Mapear colunas essenciais
# ======================
# Estoque
e_prod = find_col(estoque, "PRODUTO")
e_qtd = find_col(estoque, "EM ESTOQUE", "QTD", "QUANTIDADE")
e_val_unit = find_col(estoque, "Valor Venda Sugerido", "VALOR VENDA")

# Vendas
v_data = find_col(vendas, "DATA")
v_prod = find_col(vendas, "PRODUTO")
v_qtd = find_col(vendas, "QTD", "QUANTIDADE")
v_val_unit = find_col(vendas, "VALOR VENDA", "VALOR_VENDA")
v_val_total = find_col(vendas, "VALOR TOTAL", "VALOR_TOTAL", "TOTAL")
v_lucro = find_col(vendas, "LUCRO")

# ======================
# Normalizar dados
# ======================
if vendas is not None:
    if v_data in vendas.columns: vendas[v_data] = pd.to_datetime(vendas[v_data], errors="coerce")
    if v_val_unit in vendas.columns: vendas["_VAL_UNIT"] = to_num(vendas[v_val_unit])
    if v_qtd in vendas.columns: vendas["_QTD"] = to_num(vendas[v_qtd])
    if v_val_total in vendas.columns:
        vendas["_VAL_TOTAL"] = to_num(vendas[v_val_total])
    elif "_VAL_UNIT" in vendas.columns and "_QTD" in vendas.columns:
        vendas["_VAL_TOTAL"] = vendas["_VAL_UNIT"] * vendas["_QTD"]
    else:
        vendas["_VAL_TOTAL"] = 0
    # Lucro
    if v_lucro in vendas.columns:
        vendas["_LUCRO"] = to_num(vendas[v_lucro])
    else:
        vendas["_LUCRO"] = vendas["_VAL_TOTAL"] * 0.2  # exemplo: 20% lucro padrão se não informado

if estoque is not None:
    if e_qtd in estoque.columns: estoque["_QTD_ESTOQUE"] = to_num(estoque[e_qtd])
    if e_val_unit in estoque.columns: estoque["_VAL_UNIT_ESTOQ"] = to_num(estoque[e_val_unit])
    if "_QTD_ESTOQUE" in estoque.columns and "_VAL_UNIT_ESTOQ" in estoque.columns:
        estoque["_VAL_TOTAL_ESTOQUE"] = estoque["_QTD_ESTOQUE"] * estoque["_VAL_UNIT_ESTOQ"]
    else:
        estoque["_VAL_TOTAL_ESTOQUE"] = 0

# ======================
# Sidebar filtros
# ======================
st.sidebar.header("Filtros Gerais")
# Data de vendas
if vendas is not None and v_data in vendas.columns:
    min_date = vendas[v_data].min().date()
    max_date = vendas[v_data].max().date()
    date_range = st.sidebar.date_input("Período de vendas", value=(min_date, max_date))
else:
    date_range = None

# Filtro de produtos
prod_set = set()
if vendas is not None and v_prod in vendas.columns: prod_set.update(vendas[v_prod].dropna().astype(str).unique())
if estoque is not None and e_prod in estoque.columns: prod_set.update(estoque[e_prod].dropna().astype(str).unique())
prod_list = sorted([p for p in prod_set if str(p).strip() != ""])
prod_filter = st.sidebar.multiselect("Produtos", options=prod_list, default=prod_list)

# Aplicar filtros
vendas_f = vendas.copy() if vendas is not None else pd.DataFrame()
if date_range and v_data in vendas.columns:
    d_from, d_to = date_range
    vendas_f = vendas_f[(vendas_f[v_data].dt.date >= d_from) & (vendas_f[v_data].dt.date <= d_to)]
if prod_filter:
    vendas_f = vendas_f[vendas_f[v_prod].astype(str).isin(prod_filter)]

# ======================
# Abas
# ======================
tab1, tab2, tab3 = st.tabs(["📈 Histórico de Vendas", "📦 Estoque", "📊 KPIs & Gráficos"])

# ----------------------
# Aba 1: Histórico de Vendas
# ----------------------
with tab1:
    st.subheader("🔍 Histórico de Vendas Filtrado")
    if not vendas_f.empty:
        st.dataframe(
            vendas_f[[v_data, v_prod, "_QTD", "_VAL_UNIT", "_VAL_TOTAL", "_LUCRO"]].rename(
                columns={
                    v_data:"DATA",
                    v_prod:"PRODUTO",
                    "_QTD":"QUANTIDADE",
                    "_VAL_UNIT":"VALOR UNITÁRIO",
                    "_VAL_TOTAL":"VALOR TOTAL",
                    "_LUCRO":"LUCRO"
                }
            ).assign(
                **{"VALOR UNITÁRIO": lambda x: x["VALOR UNITÁRIO"].apply(fmt_brl),
                   "VALOR TOTAL": lambda x: x["VALOR TOTAL"].apply(fmt_brl),
                   "LUCRO": lambda x: x["LUCRO"].apply(fmt_brl)}
            )
        )
    else:
        st.info("Nenhuma venda encontrada para os filtros aplicados.")

# ----------------------
# Aba 2: Estoque
# ----------------------
with tab2:
    st.subheader("📦 Estoque Atual")
    if estoque is not None and e_prod in estoque.columns:
        est_view = estoque.copy()
        est_view["PRODUTO"] = est_view[e_prod].astype(str)
        est_view["QUANTIDADE"] = est_view["_QTD_ESTOQUE"].astype(int)
        est_view["VALOR TOTAL"] = est_view["_VAL_TOTAL_ESTOQUE"].apply(fmt_brl)
        if prod_filter: est_view = est_view[est_view["PRODUTO"].isin(prod_filter)]
        
        st.dataframe(est_view[["PRODUTO", "QUANTIDADE", "VALOR TOTAL"]].sort_values("QUANTIDADE", ascending=False))

        st.subheader("📊 Gráfico - Top 15 produtos em estoque")
        top_est = est_view.sort_values("_VAL_TOTAL_ESTOQUE", ascending=False).head(15)
        if not top_est.empty:
            fig_est = px.bar(top_est, x="PRODUTO", y="_VAL_TOTAL_ESTOQUE", color="_VAL_TOTAL_ESTOQUE",
                             color_continuous_scale=["#28a745","#1e7e34"], labels={"_VAL_TOTAL_ESTOQUE":"Valor (R$)"})
            fig_est.update_layout(yaxis_title="Valor em R$", xaxis_title="Produto", plot_bgcolor="#f5f5f5", paper_bgcolor="#f5f5f5")
            st.plotly_chart(fig_est, use_container_width=True)
    else:
        st.info("Estoque não carregado ou colunas essenciais faltando.")

# ----------------------
# Aba 3: KPIs & Gráficos
# ----------------------
with tab3:
    st.subheader("💰 KPIs Principais")
    total_vendido = vendas_f["_VAL_TOTAL"].sum() if "_VAL_TOTAL" in vendas_f.columns else 0
    lucro_total = vendas_f["_LUCRO"].sum() if "_LUCRO" in vendas_f.columns else 0
    valor_estoque = estoque["_VAL_TOTAL_ESTOQUE"].sum() if estoque is not None else 0

    k1, k2, k3 = st.columns(3)
    k1.metric("💰 Total Vendido", fmt_brl(total_vendido))
    k2.metric("📈 Lucro Total", fmt_brl(lucro_total))
    k3.metric("📦 Valor Total Estoque", fmt_brl(valor_estoque))

    st.markdown("---")
    st.subheader("📅 Evolução Mensal de Vendas e Lucro")
    if not vendas_f.empty and v_data in vendas_f.columns:
        tmp = vendas_f.copy()
        tmp["_MES"] = tmp[v_data].dt.to_period("M").astype(str)
        vendas_mes = tmp.groupby("_MES")["_VAL_TOTAL"].sum().reset_index()
        lucro_mes = tmp.groupby("_MES")["_LUCRO"].sum().reset_index()
        
        fig_v = px.line(vendas_mes, x="_MES", y="_VAL_TOTAL", title="Vendas Mensais", markers=True, labels={"_VAL_TOTAL":"Vendas (R$)"})
        fig_v.update_traces(line=dict(color="#28a745"))
        fig_luc = px.line(lucro_mes, x="_MES", y="_LUCRO", title="Lucro Mensal", markers=True, labels={"_LUCRO":"Lucro (R$)"})
        fig_luc.update_traces(line=dict(color="#155724"))
        st.plotly_chart(fig_v, use_container_width=True)
        st.plotly_chart(fig_luc, use_container_width=True)
