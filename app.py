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
# Sidebar: Token e File ID
# ======================
st.sidebar.header("OneDrive")
access_token = st.sidebar.text_input("Access Token (OAuth)", type="password")
file_id = st.sidebar.text_input("File ID do Excel (UUID)")

if not access_token or not file_id:
    st.warning("Informe o Access Token e File ID para carregar o Excel.")
    st.stop()

# ======================
# Função para baixar Excel do OneDrive
# ======================
def download_excel(token, file_id):
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{file_id}/content"
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        return BytesIO(r.content)
    else:
        st.error(f"Erro ao baixar o arquivo do OneDrive: {r.status_code} - {r.text}")
        return None

excel_file = download_excel(access_token, file_id)
if excel_file is None:
    st.stop()

# ======================
# Helpers
# ======================
def detect_header(file, sheet_name, look_for="PRODUTO"):
    raw = pd.read_excel(file, sheet_name=sheet_name, header=None)
    header_row = 0
    for i in range(min(len(raw), 12)):
        row = raw.iloc[i].astype(str).str.upper().fillna("")
        if any(look_for.upper() in v for v in row):
            header_row = i
            break
    df = pd.read_excel(file, sheet_name=sheet_name, header=header_row)
    return df

def clean_df(df):
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains("^Unnamed", na=False)]
    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all").reset_index(drop=True)
    return df

def find_col(df, *candidates):
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
# Carregar abas
# ======================
try:
    estoque = clean_df(detect_header(excel_file, "ESTOQUE"))
except Exception:
    st.warning("Aba ESTOQUE não encontrada.")
    estoque = None
try:
    vendas = clean_df(detect_header(excel_file, "VENDAS"))
except Exception:
    st.warning("Aba VENDAS não encontrada.")
    vendas = None
try:
    compras = clean_df(detect_header(excel_file, "COMPRAS"))
except Exception:
    st.warning("Aba COMPRAS não encontrada.")
    compras = None

# ======================
# Mapear colunas
# ======================
e_prod = find_col(estoque, "PRODUTO") if estoque is not None else None
e_qtd = find_col(estoque, "EM ESTOQUE", "QTD", "QUANTIDADE") if estoque is not None else None
e_valor_unit = find_col(estoque, "Valor Venda Sugerido", "VALOR VENDA") if estoque is not None else None

v_data = find_col(vendas, "DATA") if vendas is not None else None
v_prod = find_col(vendas, "PRODUTO") if vendas is not None else None
v_qtd = find_col(vendas, "QTD", "QUANTIDADE") if vendas is not None else None
v_val_unit = find_col(vendas, "VALOR VENDA", "VALOR_VENDA") if vendas is not None else None
v_val_total = find_col(vendas, "VALOR TOTAL", "VALOR_TOTAL", "TOTAL") if vendas is not None else None
v_media_custo = find_col(vendas, "MEDIA CUSTO UNITARIO", "MEDIA C. UNITARIO") if vendas is not None else None
v_lucro = find_col(vendas, "LUCRO") if vendas is not None else None

c_data = find_col(compras, "DATA") if compras is not None else None
c_prod = find_col(compras, "PRODUTO") if compras is not None else None
c_qtd = find_col(compras, "QUANTIDADE", "QTD") if compras is not None else None
c_custo_unit = find_col(compras, "CUSTO UNITÁRIO", "CUSTO UNIT") if compras is not None else None
c_custo_total = find_col(compras, "CUSTO TOTAL", "VALOR TOTAL") if compras is not None else None

# ======================
# Sidebar filtros
# ======================
st.sidebar.header("Filtros")
prod_set = set()
if vendas is not None and v_prod in vendas.columns:
    prod_set.update(vendas[v_prod].dropna().astype(str).unique())
if estoque is not None and e_prod in estoque.columns:
    prod_set.update(estoque[e_prod].dropna().astype(str).unique())
prod_list = sorted([p for p in prod_set if str(p).strip() != ""])
prod_filter = st.sidebar.multiselect("Produtos (filtrar)", options=prod_list, default=prod_list)

# ======================
# Aplicar filtros
# ======================
vendas_f = vendas.copy() if vendas is not None else pd.DataFrame()
if prod_filter and v_prod in (vendas.columns if vendas is not None else []):
    vendas_f = vendas_f[vendas_f[v_prod].astype(str).isin(prod_filter)]

# ======================
# Abas do dashboard
# ======================
tab1, tab2 = st.tabs(["📈 Visão Geral", "📦 Estoque Atual"])

with tab1:
    st.markdown("## Visão Geral — vendas filtradas")
    total_vendido = vendas_f[v_val_total].sum() if v_val_total and v_val_total in vendas_f.columns else 0
    k1, k2 = st.columns(2)
    k1.metric("💰 Vendido", fmt_brl(total_vendido))
    k2.metric("📈 Lucro", "Calculável conforme dados")  # Pode expandir cálculo
    st.markdown("---")
    st.dataframe(vendas_f.head(10))

with tab2:
    st.markdown("## Estoque Atual")
    if estoque is not None and e_prod and e_qtd:
        est_view = estoque.copy()
        est_view["PRODUTO"] = est_view[e_prod].astype(str)
        est_view["QUANTIDADE"] = to_num(est_view[e_qtd])
        st.dataframe(est_view[["PRODUTO", "QUANTIDADE"]].sort_values("QUANTIDADE", ascending=False))
    else:
        st.warning("Estoque não disponível ou colunas faltando.")

st.markdown("---")
st.caption("Dashboard — Preto + Dourado • Streamlit + OneDrive")
