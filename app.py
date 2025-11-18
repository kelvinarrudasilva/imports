# ================================================
# app.py – VERSÃO FINAL E À PROVA DE ERROS
# Loja Importados – Dashboard Dark Roxo
# ================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime, timedelta
import requests
from io import BytesIO

# ------------------------------------------------
# CONFIG DO APP
# ------------------------------------------------
st.set_page_config(page_title="Loja Importados – Dashboard", layout="wide")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b/export?format=xlsx"

# ------------------------------------------------
# CSS DARK
# ------------------------------------------------
st.markdown("""
<style>
:root {
  --bg:#0b0b0b;
  --card:#141414;
  --accent:#8b5cf6;
  --accent2:#a78bfa;
  --text:#f2f2f2;
}
body, .stApp { background: var(--bg); color: var(--text); font-family: Inter; }
.kpi-box {
  background: var(--card);
  padding: 14px 18px;
  border-radius: 14px;
  border-left: 5px solid var(--accent);
  box-shadow: 0 4px 14px rgba(0,0,0,0.45);
}
.dataframe tbody tr td { color: white !important; }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------
# FUNÇÕES
# ------------------------------------------------
def limpar_moeda(x):
    if pd.isna(x): return 0
    s = str(x)
    s = s.replace("R$","").replace(".","").replace(",",".")
    s = re.sub(r"[^0-9.\-]","",s)
    try: return float(s)
    except: return 0

def formatar(v):
    try: v=float(v)
    except: return "R$ 0"
    return "R$ {:,.0f}".format(v).replace(",",".")    

def baixar():
    r = requests.get(URL_PLANILHA, timeout=20)
    r.raise_for_status()
    return pd.ExcelFile(BytesIO(r.content))

def dark(fig):
    fig.update_layout(
        plot_bgcolor="#0b0b0b",
        paper_bgcolor="#0b0b0b",
        font_color="#f2f2f2"
    )
    return fig

# ------------------------------------------------
# CARREGAR PLANILHA
# ------------------------------------------------
try:
    xls = baixar()
except:
    st.error("Erro ao carregar a planilha.")
    st.stop()

dfs = {}
for name in ["VENDAS","COMPRAS","ESTOQUE"]:
    if name in xls.sheet_names:
        dfs[name] = pd.read_excel(xls, name)

# =====================================================
# TRATAMENTO VENDAS (100% seguro)
# =====================================================
if "VENDAS" in dfs:
    vendas = dfs["VENDAS"].copy()

    # ----- Detectar coluna de DATA -----
    col_data = None
    for c in vendas.columns:
        if any(x in c.upper() for x in ["DATA", "DIA", "DT"]):
            col_data = c
            break

    if col_data is None:
        for c in vendas.columns:
            try:
                tmp = pd.to_datetime(vendas[c], errors="ignore")
                if any(isinstance(v, (pd.Timestamp, datetime)) for v in tmp):
                    col_data = c
                    break
            except:
                pass

    if col_data is None:
        st.error(f"Não encontrei coluna de data em VENDAS. Colunas: {list(vendas.columns)}")
        st.stop()

    vendas.rename(columns={col_data:"DATA"}, inplace=True)
    vendas["DATA"] = pd.to_datetime(vendas["DATA"], errors="coerce")

    # ----- Detectar QTD -----
    col_qtd = None
    for c in vendas.columns:
        if any(x in c.upper() for x in ["QTD","QUANT"]):
            col_qtd = c

    vendas["QTD"] = vendas[col_qtd].fillna(0).astype(int) if col_qtd else 0

    # ----- Detectar valor total ou unitário -----
    col_total = None
    col_unit = None

    for c in vendas.columns:
        nome = c.upper().replace(" ","")
        if "TOTAL" in nome:
            col_total = c
        if any(x in nome for x in ["VALOR","PRECO","UNIT"]):
            col_unit = c

    # Criar coluna VALOR TOTAL segura
    if col_total:
        vendas["VALOR TOTAL"] = vendas[col_total].map(limpar_moeda)
    elif col_unit:
        vendas["VALOR TOTAL"] = vendas[col_unit].map(limpar_moeda) * vendas["QTD"]
    else:
        vendas["VALOR TOTAL"] = 0

    vendas["MES_ANO"] = vendas["DATA"].dt.strftime("%Y-%m")
else:
    vendas = pd.DataFrame()

# =====================================================
# COMPRAS
# =====================================================
if "COMPRAS" in dfs:
    compras = dfs["COMPRAS"].copy()

    # detectar data
    col_data = None
    for c in compras.columns:
        if any(x in c.upper() for x in ["DATA","DT"]):
            col_data = c
    if col_data:
        compras.rename(columns={col_data:"DATA"}, inplace=True)
        compras["DATA"] = pd.to_datetime(compras["DATA"], errors="coerce")

    # detectar custo unitário
    col_custo = None
    for c in compras.columns:
        if any(x in c.upper() for x in ["CUSTO","PRECO","VALOR","UNIT"]):
            col_custo = c
            break

    compras["CUSTO_UNIT"] = compras[col_custo].map(limpar_moeda) if col_custo else 0

    # detectar quantidade
    col_qtd = None
    for c in compras.columns:
        if any(x in c.upper() for x in ["QTD","QUANT"]):
            col_qtd = c

    compras["QUANTIDADE"] = compras[col_qtd].fillna(0).astype(int) if col_qtd else 0

    compras["CUSTO TOTAL"] = compras["CUSTO_UNIT"] * compras["QUANTIDADE"]

    if "DATA" in compras:
        compras["MES_ANO"] = compras["DATA"].dt.strftime("%Y-%m")
    else:
        compras["MES_ANO"] = "N/A"
else:
    compras = pd.DataFrame()

# =====================================================
# ESTOQUE
# =====================================================
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

    # qtd
    col_qtd = None
    for c in estoque.columns:
        if any(x in c.upper() for x in ["QTD","ESTOQUE","QUANT"]):
            col_qtd = c
            break
    estoque["EM_ESTOQUE"] = estoque[col_qtd].fillna(0).astype(int) if col_qtd else 0

    estoque["VALOR_CUSTO_TOTAL"] = estoque["CUSTO_UNIT"] * estoque["EM_ESTOQUE"]
    estoque["VALOR_VENDA_TOTAL"] = estoque["PRECO_VENDA"] * estoque["EM_ESTOQUE"]
else:
    estoque = pd.DataFrame()

# =====================================================
# FILTRO MENSAL
# =====================================================
meses = ["Todos"]
if not vendas.empty:
    meses += sorted(vendas["MES_ANO"].unique(), reverse=True)

mes_atual = datetime.now().strftime("%Y-%m")
idx = meses.index(mes_atual) if mes_atual in meses else 0

mes = st.selectbox("Filtrar por mês:", meses, index=idx)

def filtrar(df):
    if df.empty or mes == "Todos":
        return df
    return df[df["MES_ANO"] == mes]

vendas_f = filtrar(vendas)
compras_f = filtrar(compras)

# =====================================================
# KPIs
# =====================================================
k1 = vendas_f["VALOR TOTAL"].sum()
k2 = vendas_f["QTD"].sum()
k3 = compras_f["CUSTO TOTAL"].sum()
k4 = estoque["VALOR_VENDA_TOTAL"].sum()
k5 = estoque["VALOR_CUSTO_TOTAL"].sum()

col1,col2,col3,col4,col5 = st.columns(5)
col1.markdown(f"<div class='kpi-box'><h4>💵 Vendas</h4><h2>{formatar(k1)}</h2></div>", unsafe_allow_html=True)
col2.markdown(f"<div class='kpi-box'><h4>📦 QTD Vendida</h4><h2>{k2}</h2></div>", unsafe_allow_html=True)
col3.markdown(f"<div class='kpi-box'><h4>💸 Compras</h4><h2>{formatar(k3)}</h2></div>", unsafe_allow_html=True)
col4.markdown(f"<div class='kpi-box'><h4>🏷 Estoque Venda</h4><h2>{formatar(k4)}</h2></div>", unsafe_allow_html=True)
col5.markdown(f"<div class='kpi-box'><h4>📥 Estoque Custo</h4><h2>{formatar(k5)}</h2></div>", unsafe_allow_html=True)

# =====================================================
# ABAS
# =====================================================
aba1, aba2, aba3 = st.tabs(["🛒 VENDAS", "📦 ESTOQUE", "🔍 PESQUISAR"])

# =====================================================
# ABA VENDAS
# =====================================================
with aba1:

    st.subheader("🏆 Top 5 Produtos Mais Vendidos (últimos 90 dias)")

    df_hist = vendas[vendas["DATA"] >= (datetime.now() - timedelta(days=90))]
    top5 = df_hist.groupby("PRODUTO")["QTD"].sum().reset_index().sort_values("QTD", ascending=False).head(5)

    if not top5.empty:
        fig = px.bar(
            top5,
            x="QTD", y="PRODUTO",
            orientation="h",
            text="QTD",
            color_discrete_sequence=["#8b5cf6"],
            height=380
        )
        fig.update_traces(textposition="inside")
        st.plotly_chart(dark(fig), use_container_width=True)

    st.subheader("📅 Faturamento Semanal")

    df_sem = vendas_f.copy()
    df_sem["SEMANA"] = df_sem["DATA"].dt.isocalendar().week
    df_sem["ANO"] = df_sem["DATA"].dt.year

    def intervalo(row):
        ini = datetime.fromisocalendar(row["ANO"], row["SEMANA"], 1)
        fim = ini + timedelta(days=6)
        return f"{ini.strftime('%d/%m')} → {fim.strftime('%d/%m')}"

    df_week = df_sem.groupby(["ANO","SEMANA"])["VALOR TOTAL"].sum().reset_index()
    df_week["INT"] = df_week.apply(intervalo, axis=1)

    fig2 = px.bar(
        df_week,
        x="INT", y="VALOR TOTAL",
        text=df_week["VALOR TOTAL"].apply(formatar),
        color_discrete_sequence=["#8b5cf6"],
        height=380
    )
    fig2.update_traces(textposition="inside")
    st.plotly_chart(dark(fig2), use_container_width=True)

    st.subheader("📄 Tabela de Vendas")
    st.dataframe(vendas_f.sort_values("DATA", ascending=False), use_container_width=True)

# =====================================================
# ABA ESTOQUE
# =====================================================
with aba2:

    st.subheader("📦 Estoque Atual")

    if estoque.empty:
        st.info("Sem itens.")
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
        st.plotly_chart(dark(fig), use_container_width=True)

        st.dataframe(df, use_container_width=True)

# =====================================================
# ABA PESQUISAR
# =====================================================
with aba3:

    st.subheader("🔍 Buscar no Estoque")

    termo = st.text_input("Nome do produto:")

    if termo:
        df = estoque[estoque["PRODUTO"].astype(str).str.contains(termo, case=False, na=False)]
        st.dataframe(df if not df.empty else pd.DataFrame({"Resultado":[]}))
