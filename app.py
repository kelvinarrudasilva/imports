# ================================================
# app.py – DASHBOARD FINAL COMPLETO (Roxo Minimalista)
# Loja Importados – Vendas / Compras / Estoque
# ================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime
import requests
from io import BytesIO


# --------------------------
# CONFIGURAÇÃO DO APP
# --------------------------
st.set_page_config(page_title="Loja Importados – Dashboard", layout="wide", initial_sidebar_state="collapsed")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b/export?format=xlsx"


# --------------------------
# CSS – THEMA DARK ROXO
# --------------------------
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


# --------------------------
# FUNÇÕES AUXILIARES
# --------------------------
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


# --------------------------
# CARREGAR PLANILHA
# --------------------------
try:
    xls = baixar_arquivo()
except:
    st.error("Erro ao carregar a planilha.")
    st.stop()

dfs = {}
for aba in ["VENDAS","COMPRAS","ESTOQUE"]:
    if aba in xls.sheet_names:
        df = pd.read_excel(xls, aba)
        dfs[aba] = df.copy()


# =====================================================
#        TRATAMENTO DE VENDAS — 100% AUTOMÁTICO
# =====================================================
if "VENDAS" in dfs:
    vendas = dfs["VENDAS"].copy()

    # 1. Detectar automaticamente coluna de DATA
    col_data = None

    for c in vendas.columns:
        nome = c.upper().replace(" ", "")
        if any(x in nome for x in ["DATA","DIA","DT","DATE"]):
            col_data = c
            break

    if col_data is None:
        for c in vendas.columns:
            try:
                teste = pd.to_datetime(vendas[c].head(10), errors="ignore")
                if any(isinstance(x, (datetime, pd.Timestamp)) for x in teste):
                    col_data = c
                    break
            except:
                pass

    if col_data is None:
        st.error(f"❌ Não encontrei coluna de data.\nColunas da aba VENDAS: {list(vendas.columns)}")
        st.stop()

    vendas = vendas.rename(columns={col_data: "DATA"})
    vendas["DATA"] = pd.to_datetime(vendas["DATA"], errors="coerce")


    # 2. Valor total
    col_total = None
    for c in vendas.columns:
        if "TOTAL" in c.upper():
            col_total = c

    if col_total:
        vendas["VALOR TOTAL"] = vendas[col_total].map(limpar_moeda)


    # 3. Valor venda
    col_venda = None
    for c in vendas.columns:
        if "VENDA" in c.upper():
            col_venda = c

    if col_venda:
        vendas["VALOR VENDA"] = vendas[col_venda].map(limpar_moeda)


    # 4. QTD
    col_qtd = None
    for c in vendas.columns:
        nome = c.upper().replace(" ", "")
        if "QTD" in nome or "QUANT" in nome:
            col_qtd = c
            break

    if col_qtd:
        vendas["QTD"] = vendas[col_qtd].fillna(0).astype(float).astype(int)
    else:
        vendas["QTD"] = 0


    # 5. Calcular valor total se não existir
    if "VALOR TOTAL" not in vendas.columns and "VALOR VENDA" in vendas.columns:
        vendas["VALOR TOTAL"] = vendas["VALOR VENDA"] * vendas["QTD"]


    # 6. Criar MES_ANO
    vendas["MES_ANO"] = vendas["DATA"].dt.strftime("%Y-%m")

else:
    vendas = pd.DataFrame()


# =====================================================
#            TRATAMENTO COMPRAS
# =====================================================
if "COMPRAS" in dfs:
    compras = dfs["COMPRAS"].copy()

    # detectar DATA
    col_data = None
    for c in compras.columns:
        nome = c.upper().replace(" ", "")
        if any(x in nome for x in ["DATA","DIA","DT"]):
            col_data = c
            break

    if col_data:
        compras = compras.rename(columns={col_data: "DATA"})
        compras["DATA"] = pd.to_datetime(compras["DATA"], errors="coerce")

    # custo unitário
    col_custo = None
    for c in compras.columns:
        if "CUSTO" in c.upper() and "UNIT" in c.upper():
            col_custo = c

    if col_custo:
        compras["CUSTO UNITARIO"] = compras[col_custo].map(limpar_moeda)

    # quantidade
    col_qtd = None
    for c in compras.columns:
        if "QTD" in c.upper() or "QUANT" in c.upper():
            col_qtd = c

    if col_qtd:
        compras["QUANTIDADE"] = compras[col_qtd].fillna(0).astype(int)
    else:
        compras["QUANTIDADE"] = 0

    compras["CUSTO TOTAL"] = compras["CUSTO UNITARIO"] * compras["QUANTIDADE"]
    compras["MES_ANO"] = compras["DATA"].dt.strftime("%Y-%m")

else:
    compras = pd.DataFrame()


# =====================================================
#            TRATAMENTO ESTOQUE
# =====================================================
if "ESTOQUE" in dfs:
    estoque = dfs["ESTOQUE"].copy()

    col_custo = None
    for c in estoque.columns:
        if "CUSTO" in c.upper():
            col_custo = c
    if col_custo:
        estoque["CUSTO UNIT"] = estoque[col_custo].map(limpar_moeda)

    col_venda = None
    for c in estoque.columns:
        if "VENDA" in c.upper():
            col_venda = c
    if col_venda:
        estoque["PRECO VENDA"] = estoque[col_venda].map(limpar_moeda)

    col_qtd = None
    for c in estoque.columns:
        if "ESTOQUE" in c.upper() or "QTD" in c.upper():
            col_qtd = c

    estoque["EM ESTOQUE"] = estoque[col_qtd].fillna(0).astype(int) if col_qtd else 0

    estoque["VALOR TOTAL CUSTO"] = estoque["CUSTO UNIT"] * estoque["EM ESTOQUE"]
    estoque["VALOR TOTAL VENDA"] = estoque["PRECO VENDA"] * estoque["EM ESTOQUE"]

else:
    estoque = pd.DataFrame()


# =====================================================
#                FILTRO MENSAL
# =====================================================
meses = ["Todos"]
if not vendas.empty:
    meses += sorted(vendas["MES_ANO"].dropna().unique().tolist(), reverse=True)

mes_atual = datetime.now().strftime("%Y-%m")
idx_padrao = meses.index(mes_atual) if mes_atual in meses else 0

mes_escolhido = st.selectbox("Filtrar por mês:", meses, index=idx_padrao)

def filtrar(df):
    if df.empty: return df
    if mes_escolhido == "Todos": return df
    return df[df["MES_ANO"] == mes_escolhido]


vendas_f = filtrar(vendas)
compras_f = filtrar(compras)


# =====================================================
#                KPIs GERAIS
# =====================================================
total_vendas = vendas_f["VALOR TOTAL"].sum() if not vendas_f.empty else 0
total_qtd = vendas_f["QTD"].sum() if not vendas_f.empty else 0
total_compras = compras_f["CUSTO TOTAL"].sum() if not compras_f.empty else 0
valor_estoque = estoque["VALOR TOTAL VENDA"].sum() if not estoque.empty else 0
custo_estoque = estoque["VALOR TOTAL CUSTO"].sum() if not estoque.empty else 0

col1, col2, col3, col4, col5 = st.columns(5)

col1.markdown(f"<div class='kpi-box'><h4>💵 Vendas</h4><h2>{formatar(total_vendas)}</h2></div>", unsafe_allow_html=True)
col2.markdown(f"<div class='kpi-box'><h4>📦 Itens vendidos</h4><h2>{total_qtd}</h2></div>", unsafe_allow_html=True)
col3.markdown(f"<div class='kpi-box'><h4>💸 Compras</h4><h2>{formatar(total_compras)}</h2></div>", unsafe_allow_html=True)
col4.markdown(f"<div class='kpi-box'><h4>🏷 Estoque (Venda)</h4><h2>{formatar(valor_estoque)}</h2></div>", unsafe_allow_html=True)
col5.markdown(f"<div class='kpi-box'><h4>📥 Estoque (Custo)</h4><h2>{formatar(custo_estoque)}</h2></div>", unsafe_allow_html=True)


# =====================================================
#                ABAS PRINCIPAIS
# =====================================================
aba1, aba2, aba3, aba4 = st.tabs(["🛒 VENDAS", "💸 COMPRAS", "📦 ESTOQUE", "🔍 PESQUISAR"])


# -----------------------
# ABA VENDAS
# -----------------------
with aba1:
    st.subheader("📊 Vendas — período selecionado")

    if vendas_f.empty:
        st.info("Nenhuma venda encontrada.")
    else:
        df = vendas_f.copy()

        fig = px.bar(
            df.sort_values("DATA"),
            x="DATA",
            y="VALOR TOTAL",
            text=df["VALOR TOTAL"].apply(formatar),
            color_discrete_sequence=["#8b5cf6"],
            height=380
        )
        fig.update_traces(textposition="inside")
        fig.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.subheader("📄 Tabela de Vendas")
        st.dataframe(df.sort_values("DATA", ascending=False), use_container_width=True)


# -----------------------
# ABA COMPRAS
# -----------------------
with aba2:
    st.subheader("💸 Compras — período selecionado")

    if compras_f.empty:
        st.info("Nenhuma compra encontrada.")
    else:
        df = compras_f.copy()

        fig = px.bar(
            df.sort_values("DATA"),
            x="DATA",
            y="CUSTO TOTAL",
            text=df["CUSTO TOTAL"].apply(formatar),
            color_discrete_sequence=["#8b5cf6"],
            height=380
        )
        fig.update_traces(textposition="inside")
        fig.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.subheader("📄 Tabela de Compras")
        st.dataframe(df.sort_values("DATA", ascending=False), use_container_width=True)


# -----------------------
# ABA ESTOQUE
# -----------------------
with aba3:
    st.subheader("📦 Estoque Atual")

    if estoque.empty:
        st.info("Nenhum item encontrado.")
    else:
        df = estoque.copy().sort_values("EM ESTOQUE", ascending=False)

        fig = px.bar(
            df.head(25),
            x="PRODUTO",
            y="EM ESTOQUE",
            text="EM ESTOQUE",
            color_discrete_sequence=["#8b5cf6"],
            height=380
        )
        fig.update_traces(textposition="inside")
        fig.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b")
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.subheader("📄 Tabela completa")
        st.dataframe(df, use_container_width=True)


# -----------------------
# ABA PESQUISAR
# -----------------------
with aba4:
    st.subheader("🔍 Buscar produto no estoque")

    termo = st.text_input("Digite parte do nome:")

    if termo.strip():
        df = (
            estoque[
                estoque["PRODUTO"]
                .astype(str)
                .str.contains(termo, case=False, na=False)
            ]
            if "PRODUTO" in estoque.columns
            else pd.DataFrame()
        )

        if df.empty:
            st.warning("Nenhum produto encontrado.")
        else:
            st.dataframe(df.reset_index(drop=True), use_container_width=True)
