# ================================================
# app.py – DASHBOARD FINAL (Roxo Minimalista)
# Loja Importados – Vendas / Compras / Estoque
# ================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime
import requests
from io import BytesIO

# ------------------------------------------------
# CONFIG DO APP
# ------------------------------------------------
st.set_page_config(page_title="Loja Importados – Dashboard", layout="wide", initial_sidebar_state="collapsed")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b/export?format=xlsx"

# ------------------------------------------------
# CSS DARK LINDO
# ------------------------------------------------
st.markdown("""
<style>
:root{
  --bg:#0b0b0b;
  --card:#141414;
  --accent:#8b5cf6;
  --accent2:#a78bfa;
  --text:#f2f2f2;
}
body, .stApp { background:var(--bg) !important; color:var(--text); font-family: Inter; }
h1,h2,h3,h4 { color: var(--accent2) !important; }

.kpi-box{
  background:var(--card);
  padding:14px 18px;
  border-radius:14px;
  border-left:5px solid var(--accent);
  box-shadow:0 4px 14px rgba(0,0,0,0.45);
}

.dataframe tbody tr td{
  color:white !important;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------
# FUNÇÕES
# ------------------------------------------------
def limpar_moeda(x):
    if pd.isna(x): return 0
    s=str(x).replace("R$","").replace(".","").replace(",",".")
    s=re.sub(r"[^0-9.\-]","",s)
    try: return float(s)
    except: return 0

def formatar(v):
    try: v=float(v)
    except: return "R$ 0"
    s=f"{v:,.0f}".replace(",",".")
    return f"R$ {s}"

def baixar_arquivo():
    r=requests.get(URL_PLANILHA,timeout=20)
    r.raise_for_status()
    return pd.ExcelFile(BytesIO(r.content))

# ------------------------------------------------
# CARREGAR PLANILHA
# ------------------------------------------------
try:
    xls = baixar_arquivo()
except:
    st.error("Erro ao carregar planilha.")
    st.stop()

dfs = {}
for aba in ["VENDAS","COMPRAS","ESTOQUE"]:
    if aba in xls.sheet_names:
        dfs[aba] = pd.read_excel(xls, aba)

# ------------------------------------------------
# TRATAMENTO VENDAS (ROBUSTO)
# ------------------------------------------------
if "VENDAS" in dfs:
    vendas = dfs["VENDAS"].copy()

    # DETECTA COLUNA DATA POR NOME OU POR TIPO
    col_data = None
    for c in vendas.columns:
        if any(x in c.upper() for x in ["DATA","DIA","DT","DATE"]):
            col_data = c
            break

    if col_data is None:
        for c in vendas.columns:
            try:
                tmp = pd.to_datetime(vendas[c], errors="ignore")
                if any(isinstance(v, (datetime, pd.Timestamp)) for v in tmp):
                    col_data = c
                    break
            except:
                pass

    if col_data is None:
        st.error(f"Não encontrei coluna com data. Colunas: {list(vendas.columns)}")
        st.stop()

    vendas = vendas.rename(columns={col_data:"DATA"})
    vendas["DATA"] = pd.to_datetime(vendas["DATA"], errors="coerce")

    # VALOR TOTAL
    col_total = None
    for c in vendas.columns:
        if "TOTAL" in c.upper():
            col_total = c
            break

    if col_total:
        vendas["VALOR TOTAL"] = vendas[col_total].map(limpar_moeda)

    # VALOR VENDA
    col_venda = None
    for c in vendas.columns:
        if "VENDA" in c.upper():
            col_venda = c
            break

    if col_venda:
        vendas["VALOR VENDA"] = vendas[col_venda].map(limpar_moeda)

    # QTD
    col_qtd = None
    for c in vendas.columns:
        if "QTD" in c.upper() or "QUANT" in c.upper():
            col_qtd = c
            break

    vendas["QTD"] = vendas[col_qtd].fillna(0).astype(int) if col_qtd else 0

    # calcula total se não tem
    if "VALOR TOTAL" not in vendas:
        vendas["VALOR TOTAL"] = vendas["VALOR VENDA"] * vendas["QTD"]

    vendas["MES_ANO"] = vendas["DATA"].dt.strftime("%Y-%m")
else:
    vendas = pd.DataFrame()

# ------------------------------------------------
# TRATAMENTO COMPRAS (ROBUSTO)
# ------------------------------------------------
if "COMPRAS" in dfs:
    compras = dfs["COMPRAS"].copy()

    # DATA
    col_data = None
    for c in compras.columns:
        if any(x in c.upper() for x in ["DATA","DIA","DT"]):
            col_data = c
            break

    if col_data:
        compras = compras.rename(columns={col_data:"DATA"})
        compras["DATA"] = pd.to_datetime(compras["DATA"], errors="coerce")

    # DETECTAR CUSTO UNITÁRIO
    col_custo = None
    for c in compras.columns:
        nome = c.upper().replace(" ","")
        if any(x in nome for x in ["CUSTO","UNIT","PRECO","VALOR"]):
            col_custo = c
            break

    if col_custo:
        compras["CUSTO_UNIT"] = compras[col_custo].map(limpar_moeda)
    else:
        compras["CUSTO_UNIT"] = 0

    # QUANTIDADE
    col_qtd = None
    for c in compras.columns:
        if "QTD" in c.upper() or "QUANT" in c.upper():
            col_qtd = c
            break

    compras["QUANTIDADE"] = compras[col_qtd].fillna(0).astype(int) if col_qtd else 0

    compras["CUSTO TOTAL"] = compras["CUSTO_UNIT"] * compras["QUANTIDADE"]
    compras["MES_ANO"] = compras["DATA"].dt.strftime("%Y-%m") if "DATA" in compras else "N/A"

else:
    compras = pd.DataFrame()

# ------------------------------------------------
# TRATAMENTO ESTOQUE
# ------------------------------------------------
if "ESTOQUE" in dfs:
    estoque = dfs["ESTOQUE"].copy()

    # custo
    col_custo = None
    for c in estoque.columns:
        if "CUSTO" in c.upper():
            col_custo = c
            break
    estoque["CUSTO_UNIT"] = estoque[col_custo].map(limpar_moeda) if col_custo else 0

    # venda
    col_venda = None
    for c in estoque.columns:
        if "VENDA" in c.upper():
            col_venda = c
            break
    estoque["PRECO_VENDA"] = estoque[col_venda].map(limpar_moeda) if col_venda else 0

    # estoque
    col_qtd = None
    for c in estoque.columns:
        if any(x in c.upper() for x in ["ESTOQUE","QTD","QUANT"]):
            col_qtd = c
            break
    estoque["EM_ESTOQUE"] = estoque[col_qtd].fillna(0).astype(int) if col_qtd else 0

    estoque["VALOR_CUSTO_TOTAL"] = estoque["CUSTO_UNIT"] * estoque["EM_ESTOQUE"]
    estoque["VALOR_VENDA_TOTAL"] = estoque["PRECO_VENDA"] * estoque["EM_ESTOQUE"]
else:
    estoque = pd.DataFrame()

# ------------------------------------------------
# FILTRO MENSAL
# ------------------------------------------------
meses = ["Todos"]
if not vendas.empty:
    meses += sorted(vendas["MES_ANO"].dropna().unique(), reverse=True)

mes_padrao = datetime.now().strftime("%Y-%m")
idx = meses.index(mes_padrao) if mes_padrao in meses else 0

mes = st.selectbox("Filtrar por mês:", meses, index=idx)

def filtrar(df):
    if df.empty or mes == "Todos": return df
    return df[df["MES_ANO"] == mes]

vendas_f = filtrar(vendas)
compras_f = filtrar(compras)

# ------------------------------------------------
# KPIs
# ------------------------------------------------
kpi_vendas = vendas_f["VALOR TOTAL"].sum()
kpi_qtd = vendas_f["QTD"].sum()
kpi_compras = compras_f["CUSTO TOTAL"].sum()
kpi_est_venda = estoque["VALOR_VENDA_TOTAL"].sum()
kpi_est_custo = estoque["VALOR_CUSTO_TOTAL"].sum()

col1,col2,col3,col4,col5 = st.columns(5)

col1.markdown(f"<div class='kpi-box'><h4>💵 Vendas</h4><h2>{formatar(kpi_vendas)}</h2></div>", unsafe_allow_html=True)
col2.markdown(f"<div class='kpi-box'><h4>📦 Itens Vendidos</h4><h2>{kpi_qtd}</h2></div>", unsafe_allow_html=True)
col3.markdown(f"<div class='kpi-box'><h4>💸 Compras</h4><h2>{formatar(kpi_compras)}</h2></div>", unsafe_allow_html=True)
col4.markdown(f"<div class='kpi-box'><h4>🏷 Estoque (Venda)</h4><h2>{formatar(kpi_est_venda)}</h2></div>", unsafe_allow_html=True)
col5.markdown(f"<div class='kpi-box'><h4>📥 Estoque (Custo)</h4><h2>{formatar(kpi_est_custo)}</h2></div>", unsafe_allow_html=True)

# ------------------------------------------------
# ABAS
# ------------------------------------------------
aba1,aba2,aba3,aba4=st.tabs(["🛒 VENDAS","💸 COMPRAS","📦 ESTOQUE","🔍 PESQUISAR"])

# ---------------- VENDAS ----------------
with aba1:
    st.subheader("📊 Vendas do período")
    if vendas_f.empty:
        st.info("Nenhuma venda.")
    else:
        fig = px.bar(
            vendas_f.sort_values("DATA"),
            x="DATA", y="VALOR TOTAL",
            text=vendas_f["VALOR TOTAL"].apply(formatar),
            color_discrete_sequence=["#8b5cf6"],
            height=380
        )
        fig.update_traces(textposition="inside")
        fig.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Tabela de Vendas")
        st.dataframe(vendas_f.sort_values("DATA", ascending=False), use_container_width=True)

# ---------------- COMPRAS ----------------
with aba2:
    st.subheader("💸 Compras do período")
    if compras_f.empty:
        st.info("Nenhuma compra.")
    else:
        fig = px.bar(
            compras_f.sort_values("DATA"),
            x="DATA", y="CUSTO TOTAL",
            text=compras_f["CUSTO TOTAL"].apply(formatar),
            color_discrete_sequence=["#8b5cf6"],
            height=380
        )
        fig.update_traces(textposition="inside")
        fig.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Tabela de Compras")
        st.dataframe(compras_f.sort_values("DATA", ascending=False), use_container_width=True)

# ---------------- ESTOQUE ----------------
with aba3:
    st.subheader("📦 Estoque Atual")
    if estoque.empty:
        st.info("Nenhum item.")
    else:
        df = estoque.sort_values("EM_ESTOQUE", ascending=False)

        fig = px.bar(
            df.head(25),
            x="PRODUTO", y="EM_ESTOQUE",
            text="EM_ESTOQUE",
            color_discrete_sequence=["#8b5cf6"],
            height=380
        )
        fig.update_traces(textposition="inside")
        fig.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b")
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(df, use_container_width=True)

# ---------------- PESQUISAR ----------------
with aba4:
    termo = st.text_input("Buscar produto:")
    if termo:
        df = estoque[estoque["PRODUTO"].astype(str).str.contains(termo, case=False, na=False)]
        if df.empty:
            st.warning("Nenhum item encontrado.")
        else:
            st.dataframe(df.reset_index(drop=True), use_container_width=True)
