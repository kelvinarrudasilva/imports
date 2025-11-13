# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO

# ======================
# Config visual (Alto contraste: Preto + Dourado)
# ======================
st.set_page_config(page_title="Painel - Loja Importados", layout="wide")

st.markdown(
    """
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
    """,
    unsafe_allow_html=True,
)

st.markdown("<div class='title'>📊 Painel — Loja Importados</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Tema: Alto contraste — Preto & Dourado • Abas: Visão Geral / Estoque</div>", unsafe_allow_html=True)
st.markdown("---")

# ======================
# Funções auxiliares
# ======================
def to_num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0)

def fmt_brl(x):
    try:
        return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def detect_header(df, look_for="PRODUTO"):
    """Detecta linha de header no df já carregado (Excel)."""
    header_row = None
    for i in range(min(len(df), 12)):
        row = df.iloc[i].astype(str).str.upper().fillna("")
        if any(look_for.upper() in v for v in row):
            header_row = i
            break
    if header_row is None:
        header_row = 0
    df.columns = df.iloc[header_row]
    df = df.drop(range(header_row + 1))
    df = df.reset_index(drop=True)
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
        pattern = str(cand).strip().upper()
        for c in df.columns:
            if pattern in str(c).upper():
                return c
    return None

# ======================
# Baixar Excel do OneDrive
# ======================
st.sidebar.header("OneDrive")
access_token = st.sidebar.text_input("Cole o access_token (OAuth)", type="password")
file_id = st.sidebar.text_input("Cole o File ID do Excel")

EXCEL = None
if access_token and file_id:
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content"
    headers = {"Authorization": f"Bearer {access_token}"}
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        EXCEL = BytesIO(r.content)
        st.sidebar.success("Arquivo baixado com sucesso!")
    else:
        st.sidebar.error(f"Erro ao baixar arquivo: {r.status_code} {r.text}")

if EXCEL is None:
    st.warning("Insira access_token e File ID para baixar o arquivo do OneDrive.")
    st.stop()

# ======================
# Carregar abas
# ======================
def load_sheet(name):
    df = pd.read_excel(EXCEL, sheet_name=name, header=None)
    df = detect_header(df)
    df = clean_df(df)
    return df

try:
    estoque = load_sheet("ESTOQUE")
except:
    estoque = None
try:
    vendas = load_sheet("VENDAS")
except:
    vendas = None
try:
    compras = load_sheet("COMPRAS")
except:
    compras = None

# Mapear colunas principais
e_prod = find_col(estoque, "PRODUTO")
e_qtd = find_col(estoque, "EM ESTOQUE", "QTD", "QUANTIDADE")
e_valor_unit = find_col(estoque, "Valor Venda Sugerido", "VALOR VENDA")

v_data = find_col(vendas, "DATA")
v_prod = find_col(vendas, "PRODUTO")
v_qtd = find_col(vendas, "QTD", "QUANTIDADE")
v_val_unit = find_col(vendas, "VALOR VENDA", "VALOR_VENDA")
v_val_total = find_col(vendas, "VALOR TOTAL", "VALOR_TOTAL", "TOTAL")
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
    vendas[v_data] = pd.to_datetime(vendas[v_data], errors="coerce")
    vendas["_VAL_UNIT"] = to_num(vendas[v_val_unit])
    vendas["_QTD"] = to_num(vendas[v_qtd])
    if v_val_total in vendas.columns:
        vendas["_VAL_TOTAL"] = to_num(vendas[v_val_total])
    else:
        vendas["_VAL_TOTAL"] = vendas["_VAL_UNIT"] * vendas["_QTD"]
    if v_lucro in vendas.columns:
        vendas["_LUCRO"] = to_num(vendas[v_lucro])
    else:
        vendas["_LUCRO"] = (vendas["_VAL_UNIT"] - 0) * vendas["_QTD"]  # sem custo, só exemplo

if estoque is not None:
    estoque["_QTD_ESTOQUE"] = to_num(estoque[e_qtd])
    estoque["_VAL_UNIT_ESTOQ"] = to_num(estoque[e_valor_unit])
    estoque["_VAL_TOTAL_ESTOQUE"] = estoque["_QTD_ESTOQUE"] * estoque["_VAL_UNIT_ESTOQ"]

# ======================
# Filtros Sidebar
# ======================
st.sidebar.header("Filtros")
prod_set = set()
if vendas is not None: prod_set.update(vendas[v_prod].dropna().astype(str).unique())
if estoque is not None: prod_set.update(estoque[e_prod].dropna().astype(str).unique())
prod_list = sorted([p for p in prod_set if str(p).strip() != ""])
prod_filter = st.sidebar.multiselect("Produtos (filtrar)", options=prod_list, default=prod_list)

vendas_f = vendas.copy() if vendas is not None else pd.DataFrame()
if prod_filter:
    vendas_f = vendas_f[vendas_f[v_prod].astype(str).isin(prod_filter)]

# ======================
# Abas
# ======================
tab1, tab2 = st.tabs(["📈 Visão Geral", "📦 Estoque Atual"])

with tab1:
    st.markdown("## Visão Geral — vendas e lucro (filtradas)")
    total_vendido = vendas_f["_VAL_TOTAL"].sum() if "_VAL_TOTAL" in vendas_f.columns else 0
    lucro_total = vendas_f["_LUCRO"].sum() if "_LUCRO" in vendas_f.columns else 0
    valor_estoque = estoque["_VAL_TOTAL_ESTOQUE"].sum() if estoque is not None else 0

    k1, k2, k3 = st.columns(3)
    k1.metric("💰 Vendido", fmt_brl(total_vendido))
    k2.metric("📈 Lucro", fmt_brl(lucro_total))
    k3.metric("📦 Estoque total", fmt_brl(valor_estoque))

    st.markdown("---")
    st.subheader("🏆 Top 10 Produtos por Valor")
    if vendas_f.shape[0] > 0:
        top = vendas_f.groupby(v_prod).agg(QTDE=(" _QTD" if "_QTD" in vendas_f.columns else v_qtd, "sum"),
                                          VALOR=("_VAL_TOTAL", "sum")).reset_index()
        top = top.sort_values("VALOR", ascending=False).head(10)
        if not top.empty:
            fig = px.bar(top, x="VALOR", y=v_prod, orientation="h", text="QTDE",
                         color="VALOR", color_continuous_scale=["#FFD700", "#B8860B"])
            fig.update_traces(texttemplate='%{text:.0f} un', textposition='outside')
            fig.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000", font_color="#FFD700",
                              yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig, use_container_width=True)
            st.table(top.rename(columns={v_prod:"PRODUTO","QTDE":"QUANTIDADE","VALOR":"VALOR TOTAL"}))

with tab2:
    st.markdown("## Estoque Atual")
    if estoque is not None:
        est_view = estoque.copy()
        est_view["PRODUTO"] = est_view[e_prod].astype(str)
        est_view["QUANTIDADE"] = est_view["_QTD_ESTOQUE"].astype(int)
        est_view["VALOR_TOTAL_ESTOQUE"] = est_view["_VAL_TOTAL_ESTOQUE"]
        if prod_filter: est_view = est_view[est_view["PRODUTO"].isin(prod_filter)]
        total_qty = est_view["QUANTIDADE"].sum()
        total_val = est_view["VALOR_TOTAL_ESTOQUE"].sum()
        c1, c2 = st.columns(2)
        c1.metric("📦 Qtde total em estoque", f"{int(total_qty):,}".replace(",", "."))
        c2.metric("💰 Valor total do estoque", fmt_brl(total_val))
        st.dataframe(est_view[["PRODUTO","QUANTIDADE","VALOR_TOTAL_ESTOQUE"]].sort_values("QUANTIDADE", ascending=False))

st.markdown("---")
st.caption("Dashboard — Preto + Dourado • Streamlit | Kelvin")
