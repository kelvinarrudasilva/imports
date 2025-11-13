# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re

# ======================
# Configuração da página
# ======================
st.set_page_config(page_title="Painel - Loja Importados", layout="wide")

# ======================
# Estilo (Claro + Verde)
# ======================
st.markdown("""
<style>
:root { --green:#2ECC71; --bg:#F9F9F9; --card:#FFFFFF; --muted:#555555; }
.stApp { background-color: var(--bg); color: var(--green); }
.title { color: var(--green); font-weight:700; font-size:22px; }
.subtitle { color: var(--muted); font-size:12px; margin-bottom:12px; }
.kpi { background: linear-gradient(90deg, #e6fff0, #ccffdd); padding:12px; border-radius:10px; text-align:center; }
.kpi-value { color: var(--green); font-size:20px; font-weight:700; }
.kpi-label { color:var(--muted); font-size:13px; }
.stDataFrame table { background-color:#FFFFFF; color:#333333; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='title'>📊 Painel — Loja Importados</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Tema: Claro & Verde • Abas: Visão Geral / Estoque / Vendas Detalhadas</div>", unsafe_allow_html=True)
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
    st.error(f"Arquivo '{EXCEL}' não encontrado no diretório do app.")
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
# Mapear colunas
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

c_data = find_col(compras, "DATA")
c_prod = find_col(compras, "PRODUTO")
c_qtd = find_col(compras, "QUANTIDADE", "QTD")
c_custo_unit = find_col(compras, "CUSTO UNITÁRIO")
c_custo_total = find_col(compras, "CUSTO TOTAL")

# ======================
# Normalizar dados
# ======================
# Vendas
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
        vendas["_LUCRO"] = vendas["_VAL_TOTAL"]  # simples, se lucro não informado

# Estoque
if estoque is not None:
    estoque["_QTD_ESTOQUE"] = to_num(estoque[e_qtd])
    estoque["_VAL_UNIT_ESTOQ"] = to_num(estoque[e_valor_unit])
    estoque["_VAL_TOTAL_ESTOQUE"] = estoque["_QTD_ESTOQUE"] * estoque["_VAL_UNIT_ESTOQ"]

# ======================
# Sidebar - filtros
# ======================
st.sidebar.header("Filtros Gerais")

# Filtro de data (simples, calendário compacto)
if vendas is not None:
    min_date = vendas[v_data].min().date()
    max_date = vendas[v_data].max().date()
    date_range = st.sidebar.date_input("Período (Vendas)", value=(min_date, max_date), min_value=min_date, max_value=max_date)
else:
    date_range = None

# Filtro de produtos
prod_list = sorted(list(set(vendas[v_prod].dropna().astype(str).unique()) if vendas is not None else []))
prod_filter = st.sidebar.multiselect("Produtos", options=prod_list, default=prod_list)

# ======================
# Aplicar filtros
# ======================
vendas_f = vendas.copy() if vendas is not None else pd.DataFrame()
if date_range and isinstance(date_range, (list, tuple)) and len(date_range)==2:
    d_from, d_to = date_range
    vendas_f = vendas_f[(vendas_f[v_data].dt.date >= d_from) & (vendas_f[v_data].dt.date <= d_to)]
if prod_filter:
    vendas_f = vendas_f[vendas_f[v_prod].astype(str).isin(prod_filter)]

# ======================
# Abas
# ======================
tab1, tab2, tab3 = st.tabs(["📈 Visão Geral", "📦 Estoque Atual", "🛒 Vendas Detalhadas"])

with tab1:
    st.markdown("## KPIs")
    total_vendido = vendas_f["_VAL_TOTAL"].sum() if "_VAL_TOTAL" in vendas_f.columns else 0
    lucro_total = vendas_f["_LUCRO"].sum() if "_LUCRO" in vendas_f.columns else 0
    valor_estoque = estoque["_VAL_TOTAL_ESTOQUE"].sum() if estoque is not None else 0

    k1, k2, k3 = st.columns(3)
    k1.metric("💰 Vendido", fmt_brl(total_vendido))
    k2.metric("📈 Lucro", fmt_brl(lucro_total))
    k3.metric("📦 Valor Estoque", fmt_brl(valor_estoque))

    st.markdown("---")
    st.markdown("## Top 10 Produtos (Valor total)")
    if not vendas_f.empty:
        top = vendas_f.groupby(v_prod).agg(
            QTDE=pd.NamedAgg(column="_QTD", aggfunc="sum"),
            VAL_TOTAL=pd.NamedAgg(column="_VAL_TOTAL", aggfunc="sum")
        ).reset_index().sort_values("VAL_TOTAL", ascending=False).head(10)
        fig_top = px.bar(top, x="VAL_TOTAL", y=v_prod, orientation="h", text="QTDE",
                         color="VAL_TOTAL", color_continuous_scale=["#2ECC71","#27AE60"])
        fig_top.update_traces(texttemplate='%{text:.0f} un', textposition='outside')
        fig_top.update_layout(plot_bgcolor="#F9F9F9", paper_bgcolor="#F9F9F9", font_color="#2ECC71", yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_top, use_container_width=True)

with tab2:
    st.markdown("## Estoque Atual")
    est_view = estoque.copy() if estoque is not None else pd.DataFrame()
    if not est_view.empty:
        if prod_filter:
            est_view = est_view[est_view[e_prod].astype(str).isin(prod_filter)]
        est_view_display = est_view[[e_prod, "_QTD_ESTOQUE", "_VAL_UNIT_ESTOQ", "_VAL_TOTAL_ESTOQUE"]].copy()
        est_view_display.columns = ["PRODUTO","QUANTIDADE","PREÇO UNITÁRIO","VALOR TOTAL"]
        for col in ["PREÇO UNITÁRIO","VALOR TOTAL"]:
            est_view_display[col] = est_view_display[col].apply(fmt_brl)
        st.dataframe(est_view_display.sort_values("QUANTIDADE", ascending=False))
        st.markdown("---")
        top_val = est_view.sort_values("_VAL_TOTAL_ESTOQUE", ascending=False).head(15)
        fig_e = px.bar(top_val, x=e_prod, y="_VAL_TOTAL_ESTOQUE",
                       color="_VAL_TOTAL_ESTOQUE", color_continuous_scale=["#2ECC71","#27AE60"])
        fig_e.update_layout(plot_bgcolor="#F9F9F9", paper_bgcolor="#F9F9F9", font_color="#2ECC71")
        st.plotly_chart(fig_e, use_container_width=True)

with tab3:
    st.markdown("## Vendas Detalhadas")
    if not vendas_f.empty:
        vendas_show = vendas_f[[v_data, v_prod, "_QTD", "_VAL_UNIT", "_VAL_TOTAL", "_LUCRO"]].copy()
        vendas_show.columns = ["DATA","PRODUTO","QUANTIDADE","PREÇO UNITÁRIO","VALOR TOTAL","LUCRO"]
        for col in ["PREÇO UNITÁRIO","VALOR TOTAL","LUCRO"]:
            vendas_show[col] = vendas_show[col].apply(fmt_brl)
        st.dataframe(vendas_show.sort_values("DATA", ascending=False))
    else:
        st.info("Nenhuma venda encontrada no período/produto filtrado.")
