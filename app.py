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

st.markdown(
    """
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
    """,
    unsafe_allow_html=True,
)

st.markdown("<div class='title'>📊 Painel — Loja Importados</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Tema: Claro & Verde • Abas: Visão Geral / Estoque</div>", unsafe_allow_html=True)
st.markdown("---")

# ======================
# Util helpers
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
    st.error(f"Arquivo '{EXCEL}' não encontrado no diretório do app.")
    st.stop()

xls = pd.ExcelFile(EXCEL)
available = set([s.upper() for s in xls.sheet_names])
needed = {"ESTOQUE", "VENDAS", "COMPRAS"}
found = needed.intersection(available)
st.sidebar.markdown("### Fonte")
st.sidebar.write("Abas encontradas:", list(xls.sheet_names))
st.sidebar.markdown("---")

def load_sheet(name):
    if name not in available:
        return None, f"Aba '{name}' não encontrada"
    df, hdr = detect_header(EXCEL, name)
    df = clean_df(df)
    return df, None

estoque, err_e = load_sheet("ESTOQUE")
vendas, err_v = load_sheet("VENDAS")
compras, err_c = load_sheet("COMPRAS")

if err_e: st.warning(err_e)
if err_v: st.warning(err_v)
if err_c: st.warning(err_c)

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
v_media_custo = find_col(vendas, "MEDIA CUSTO UNITARIO", "MEDIA C. UNITARIO")
v_lucro = find_col(vendas, "LUCRO")

c_data = find_col(compras, "DATA")
c_prod = find_col(compras, "PRODUTO")
c_qtd = find_col(compras, "QUANTIDADE", "QTD")
c_custo_unit = find_col(compras, "CUSTO UNITÁRIO", "CUSTO UNIT")
c_custo_total = find_col(compras, "CUSTO TOTAL", "VALOR TOTAL")

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

    # lucro
    if v_lucro in vendas.columns:
        vendas["_LUCRO"] = to_num(vendas[v_lucro])
    else:
        if v_media_custo in vendas.columns:
            vendas["_CUSTO_UNIT"] = to_num(vendas[v_media_custo])
        else:
            vendas["_CUSTO_UNIT"] = 0
        if v_prod in vendas.columns and e_prod in estoque.columns:
            mapa = estoque[[e_prod, e_valor_unit]].dropna()
            mapa_dict = mapa.set_index(e_prod)[e_valor_unit].to_dict()
            vendas["_CUSTO_UNIT"] = vendas[v_prod].astype(str).str.strip().map(mapa_dict).fillna(0)
        vendas["_LUCRO"] = (vendas["_VAL_UNIT"].fillna(0) - vendas["_CUSTO_UNIT"].fillna(0)) * vendas["_QTD"].fillna(0)

if compras is not None:
    if c_data in compras.columns: compras[c_data] = pd.to_datetime(compras[c_data], errors="coerce")
    if c_custo_total in compras.columns: compras["_CUSTO_TOTAL"] = to_num(compras[c_custo_total])
    if c_custo_unit in compras.columns: compras["_CUSTO_UNIT"] = to_num(compras[c_custo_unit])
    if c_qtd in compras.columns: compras["_QTD"] = to_num(compras[c_qtd])

if estoque is not None:
    if e_qtd in estoque.columns: estoque["_QTD_ESTOQUE"] = to_num(estoque[e_qtd])
    if e_valor_unit in estoque.columns: estoque["_VAL_UNIT_ESTOQ"] = to_num(estoque[e_valor_unit])
    if "_QTD_ESTOQUE" in estoque.columns and "_VAL_UNIT_ESTOQ" in estoque.columns:
        estoque["_VAL_TOTAL_ESTOQUE"] = estoque["_QTD_ESTOQUE"] * estoque["_VAL_UNIT_ESTOQ"]
    else:
        estoque["_VAL_TOTAL_ESTOQUE"] = 0

# ======================
# Sidebar filtros
# ======================
st.sidebar.header("Filtros")
if vendas is not None and v_data in vendas.columns:
    min_date = vendas[v_data].min().date() if pd.notna(vendas[v_data].min()) else None
    max_date = vendas[v_data].max().date() if pd.notna(vendas[v_data].max()) else None
    date_range = st.sidebar.date_input("Período (Vendas)", value=(min_date, max_date))
else:
    date_range = None

prod_set = set()
if vendas is not None and v_prod in vendas.columns: prod_set.update(vendas[v_prod].dropna().astype(str).unique())
if estoque is not None and e_prod in estoque.columns: prod_set.update(estoque[e_prod].dropna().astype(str).unique())
prod_list = sorted([p for p in prod_set if str(p).strip() != ""])
prod_filter = st.sidebar.multiselect("Produtos (filtrar)", options=prod_list, default=prod_list)

# aplicar filtros
vendas_f = vendas.copy() if vendas is not None else pd.DataFrame()
if date_range and isinstance(date_range, (list, tuple)) and len(date_range) == 2 and v_data in vendas.columns:
    d_from, d_to = date_range
    vendas_f = vendas_f[(vendas_f[v_data].dt.date >= d_from) & (vendas_f[v_data].dt.date <= d_to)]

if prod_filter:
    vendas_f = vendas_f[vendas_f[v_prod].astype(str).isin(prod_filter)]

# ======================
# Abas
# ======================
tab1, tab2 = st.tabs(["📈 Visão Geral", "📦 Estoque Atual"])

with tab1:
    st.markdown("## Visão Geral — Vendas e Lucro")
    total_vendido = vendas_f["_VAL_TOTAL"].sum() if "_VAL_TOTAL" in vendas_f.columns else 0
    lucro_total = vendas_f["_LUCRO"].sum() if "_LUCRO" in vendas_f.columns else 0
    valor_estoque = estoque["_VAL_TOTAL_ESTOQUE"].sum() if estoque is not None else 0

    k1, k2, k3 = st.columns(3)
    k1.markdown(f"<div class='kpi'><div class='kpi-label'>💰 Vendido</div><div class='kpi-value'>{fmt_brl(total_vendido)}</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi'><div class='kpi-label'>📈 Lucro</div><div class='kpi-value'>{fmt_brl(lucro_total)}</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='kpi'><div class='kpi-label'>📦 Estoque</div><div class='kpi-value'>{fmt_brl(valor_estoque)}</div></div>", unsafe_allow_html=True)

    st.markdown("---")
    
    # Top 10 produtos
    st.subheader("🏆 Top 10 Produtos Mais Vendidos")
    if not vendas_f.empty and v_prod in vendas_f.columns:
        qtd_col = "_QTD" if "_QTD" in vendas_f.columns else None
        val_col = "_VAL_TOTAL" if "_VAL_TOTAL" in vendas_f.columns else None
        if qtd_col or val_col:
            agg_dict = {}
            if qtd_col: agg_dict["QUANTIDADE"] = (qtd_col, "sum")
            if val_col: agg_dict["VALOR_TOTAL"] = (val_col, "sum")
            top = vendas_f.groupby(v_prod).agg(**agg_dict).reset_index()
            if "VALOR_TOTAL" in top.columns:
                top = top.sort_values("VALOR_TOTAL", ascending=False).head(10)
            else:
                top = top.sort_values("QUANTIDADE", ascending=False).head(10)
            st.dataframe(top)
        else:
            st.info("Nenhuma coluna de quantidade ou valor disponível.")
    else:
        st.info("Nenhuma venda no período/produtos filtrados.")

with tab2:
    st.markdown("## Estoque Atual")
    if estoque is not None and e_prod in estoque.columns and "_QTD_ESTOQUE" in estoque.columns:
        est_view = estoque.copy()
        est_view["PRODUTO"] = est_view[e_prod].astype(str)
        est_view["QUANTIDADE"] = est_view["_QTD_ESTOQUE"].astype(int)
        est_view["VALOR_TOTAL_ESTOQUE"] = est_view["_VAL_TOTAL_ESTOQUE"]
        if prod_filter: est_view = est_view[est_view["PRODUTO"].isin(prod_filter)]

        total_qty = est_view["QUANTIDADE"].sum()
        total_val = est_view["VALOR_TOTAL_ESTOQUE"].sum()
        c1, c2 = st.columns(2)
        c1.metric("📦 Qtde em estoque", f"{int(total_qty):,}".replace(",", "."))
        c2.metric("💰 Valor total do estoque", fmt_brl(total_val))

        st.markdown("---")
        st.subheader("Tabela de Estoque")
        st.dataframe(est_view[["PRODUTO","QUANTIDADE","VALOR_TOTAL_ESTOQUE"]].sort_values("QUANTIDADE", ascending=False))
    else:
        st.warning("Aba ESTOQUE ou colunas essenciais não encontradas.")

st.markdown("---")
st.caption("Dashboard — Tema: Claro + Verde. Desenvolvido em Streamlit.")
