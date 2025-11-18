# ================================================
# app.py – DASHBOARD FINAL (Roxo Minimalista)
# Loja Importados – Vendas / Compras / Estoque
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
st.set_page_config(page_title="Loja Importados – Dashboard", layout="wide", initial_sidebar_state="collapsed")

# PLANILHA
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
    s = str(x).replace("R$","").replace(".","").replace(",",".")
    s = re.sub(r"[^0-9.\-]","",s)
    try: return float(s)
    except: return 0

def formatar_reais(v):
    try: v = float(v)
    except: return "R$ 0"
    s = f"{v:,.0f}".replace(",",".")
    return f"R$ {s}"

def baixar_arquivo():
    r = requests.get(URL_PLANILHA, timeout=20)
    r.raise_for_status()
    return pd.ExcelFile(BytesIO(r.content))

def dark_layout(fig):
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
    xls = baixar_arquivo()
except:
    st.error("Erro ao carregar a planilha.")
    st.stop()

dfs = {}
for aba in ["VENDAS","COMPRAS","ESTOQUE"]:
    if aba in xls.sheet_names:
        dfs[aba] = pd.read_excel(xls, aba)

# =====================================================
#        TRATAMENTO DE VENDAS — AUTOMÁTICO
# =====================================================
if "VENDAS" in dfs:
    vendas = dfs["VENDAS"].copy()

    # Detectar DATA
    col_data = None
    for c in vendas.columns:
        if any(x in c.upper() for x in ["DATA","DT","DIA"]):
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
        st.error(f"Não encontrei coluna de DATA. Colunas: {list(vendas.columns)}")
        st.stop()

    vendas = vendas.rename(columns={col_data:"DATA"})
    vendas["DATA"] = pd.to_datetime(vendas["DATA"], errors="coerce")

    # VALOR TOTAL
    col_total = None
    for c in vendas.columns:
        if "TOTAL" in c.upper():
            col_total = c
    if col_total:
        vendas["VALOR TOTAL"] = vendas[col_total].map(limpar_moeda)

    # VALOR VENDA
    col_venda_valor = None
    for c in vendas.columns:
        if "VENDA" in c.upper():
            col_venda_valor = c
    if col_venda_valor:
        vendas["VALOR VENDA"] = vendas[col_venda_valor].map(limpar_moeda)

    # QTD
    col_qtd = None
    for c in vendas.columns:
        if any(x in c.upper() for x in ["QTD","QUANT"]):
            col_qtd = c
    vendas["QTD"] = vendas[col_qtd].fillna(0).astype(int) if col_qtd else 0

    # calcula total
    if "VALOR TOTAL" not in vendas:
        vendas["VALOR TOTAL"] = vendas["VALOR VENDA"] * vendas["QTD"]

    vendas["MES_ANO"] = vendas["DATA"].dt.strftime("%Y-%m")

else:
    vendas = pd.DataFrame()

# =====================================================
#            TRATAMENTO COMPRAS
# =====================================================
if "COMPRAS" in dfs:
    compras = dfs["COMPRAS"].copy()

    # DATA
    col_data = None
    for c in compras.columns:
        if any(x in c.upper() for x in ["DATA","DT"]):
            col_data = c
    if col_data:
        compras = compras.rename(columns={col_data:"DATA"})
        compras["DATA"] = pd.to_datetime(compras["DATA"], errors="coerce")

    # custo
    col_custo = None
    for c in compras.columns:
        if any(x in c.upper() for x in ["CUSTO","VALOR","PRECO","UNIT"]):
            col_custo = c
            break

    compras["CUSTO_UNIT"] = compras[col_custo].map(limpar_moeda) if col_custo else 0

    # qtd
    col_qtd = None
    for c in compras.columns:
        if "QTD" in c.upper() or "QUANT" in c.upper():
            col_qtd = c
    compras["QUANTIDADE"] = compras[col_qtd].fillna(0).astype(int) if col_qtd else 0

    compras["CUSTO TOTAL"] = compras["CUSTO_UNIT"] * compras["QUANTIDADE"]
    compras["MES_ANO"] = compras["DATA"].dt.strftime("%Y-%m") if "DATA" in compras else "N/A"
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
    estoque["CUSTO_UNIT"] = estoque[col_custo].map(limpar_moeda) if col_custo else 0

    col_preco = None
    for c in estoque.columns:
        if "VENDA" in c.upper():
            col_preco = c
    estoque["PRECO_VENDA"] = estoque[col_preco].map(limpar_moeda) if col_preco else 0

    col_qtd = None
    for c in estoque.columns:
        if any(x in c.upper() for x in ["ESTOQUE","QTD","QUANT"]):
            col_qtd = c
    estoque["EM_ESTOQUE"] = estoque[col_qtd].fillna(0).astype(int) if col_qtd else 0

    estoque["VALOR_CUSTO_TOTAL"] = estoque["CUSTO_UNIT"] * estoque["EM_ESTOQUE"]
    estoque["VALOR_VENDA_TOTAL"] = estoque["PRECO_VENDA"] * estoque["EM_ESTOQUE"]
else:
    estoque = pd.DataFrame()

# =====================================================
#                FILTRO MENSAL
# =====================================================
meses = ["Todos"]
if not vendas.empty:
    meses += sorted(vendas["MES_ANO"].dropna().unique(), reverse=True)

mes_atual = datetime.now().strftime("%Y-%m")
idx = meses.index(mes_atual) if mes_atual in meses else 0

mes = st.selectbox("Filtrar por mês:", meses, index=idx)

def filtrar(df):
    if df.empty or mes == "Todos": return df
    return df[df["MES_ANO"] == mes]

vendas_f = filtrar(vendas)
compras_f = filtrar(compras)

# =====================================================
#                KPIs
# =====================================================
kpi_vendas = vendas_f["VALOR TOTAL"].sum()
kpi_qtd = vendas_f["QTD"].sum()
kpi_compras = compras_f["CUSTO TOTAL"].sum()
kpi_est_venda = estoque["VALOR_VENDA_TOTAL"].sum()
kpi_est_custo = estoque["VALOR_CUSTO_TOTAL"].sum()

col1,col2,col3,col4,col5 = st.columns(5)

col1.markdown(f"<div class='kpi-box'><h4>💵 Vendas</h4><h2>{formatar_reais(kpi_vendas)}</h2></div>", unsafe_allow_html=True)
col2.markdown(f"<div class='kpi-box'><h4>📦 Itens Vendidos</h4><h2>{kpi_qtd}</h2></div>", unsafe_allow_html=True)
col3.markdown(f"<div class='kpi-box'><h4>💸 Compras</h4><h2>{formatar_reais(kpi_compras)}</h2></div>", unsafe_allow_html=True)
col4.markdown(f"<div class='kpi-box'><h4>🏷 Estoque (Venda)</h4><h2>{formatar_reais(kpi_est_venda)}</h2></div>", unsafe_allow_html=True)
col5.markdown(f"<div class='kpi-box'><h4>📥 Estoque (Custo)</h4><h2>{formatar_reais(kpi_est_custo)}</h2></div>", unsafe_allow_html=True)

# =====================================================
#                ABAS (SEM TOP10)
# =====================================================
tabs = st.tabs(["🛒 VENDAS", "📦 ESTOQUE", "🔍 PESQUISAR"])

# =====================================================
#                ABA VENDAS
# =====================================================
with tabs[0]:

    st.subheader("📊 Vendas — período selecionado")

    if vendas_f.empty:
        st.info("Nenhuma venda encontrada.")
    else:

        # ------------------------------------------------
        # TOP 5 PRODUTOS MAIS VENDIDOS (ÚLTIMOS 90 DIAS)
        # ------------------------------------------------
        st.markdown("### 🏆 Top 5 produtos mais vendidos (últimos meses)")

        df_hist = vendas.copy()
        df_hist = df_hist[df_hist["DATA"] >= (datetime.now() - timedelta(days=90))]

        top5 = (
            df_hist.groupby("PRODUTO")["QTD"]
            .sum()
            .reset_index()
            .sort_values("QTD", ascending=False)
            .head(5)
        )

        if not top5.empty:

            fig_top5 = px.bar(
                top5,
                x="QTD",
                y="PRODUTO",
                orientation="h",
                text="QTD",
                color_discrete_sequence=["#8b5cf6"],
                height=380
            )
            fig_top5.update_traces(textposition="inside", insidetextanchor="middle")
            dark_layout(fig_top5)
            st.plotly_chart(fig_top5, use_container_width=True, config={"displayModeBar": False})

        else:
            st.info("Não há histórico suficiente para o cálculo.")

        # ------------------------------------------------
        # GRÁFICO FATURAMENTO SEMANAL
        # ------------------------------------------------
        st.markdown("### 📅 Faturamento Semanal")

        df_sem = vendas_f.copy()
        df_sem["DATA"] = pd.to_datetime(df_sem["DATA"], errors="coerce")
        df_sem["SEMANA"] = df_sem["DATA"].dt.isocalendar().week
        df_sem["ANO"] = df_sem["DATA"].dt.year

        def intervalo_sem(row):
            try:
                ini = datetime.fromisocalendar(int(row["ANO"]), int(row["SEMANA"]), 1)
                fim = ini + timedelta(days=6)
                return f"{ini.strftime('%d/%m')} → {fim.strftime('%d/%m')}"
            except:
                return "N/A"

        df_week = df_sem.groupby(["ANO","SEMANA"])["VALOR TOTAL"].sum().reset_index()
        df_week["INTERVALO"] = df_week.apply(intervalo_sem, axis=1)
        df_week["LABEL"] = df_week["VALOR TOTAL"].apply(formatar_reais)

        fig_sem = px.bar(
            df_week,
            x="INTERVALO",
            y="VALOR TOTAL",
            text="LABEL",
            color_discrete_sequence=["#8b5cf6"],
            height=380
        )
        fig_sem.update_traces(textposition="inside")
        dark_layout(fig_sem)
        st.plotly_chart(fig_sem, use_container_width=True, config={"displayModeBar": False})

        # ------------------------------------------------
        # TABELA DE VENDAS
        # ------------------------------------------------
        st.markdown("### 📄 Tabela de Vendas")
        st.dataframe(vendas_f.sort_values("DATA", ascending=False), use_container_width=True)

# =====================================================
#                ABA ESTOQUE
# =====================================================
with tabs[1]:

    st.subheader("📦 Estoque Atual")

    if estoque.empty:
        st.info("Nenhum item no estoque.")
    else:
        df = estoque.sort_values("EM_ESTOQUE", ascending=False)

        fig = px.bar(
            df.head(25),
            x="PRODUTO",
            y="EM_ESTOQUE",
            text="EM_ESTOQUE",
            color_discrete_sequence=["#8b5cf6"],
            height=380
        )
        fig.update_traces(textposition="inside")
        dark_layout(fig)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

        st.dataframe(df, use_container_width=True)

# =====================================================
#                ABA PESQUISAR
# =====================================================
with tabs[2]:

    st.subheader("🔍 Buscar produto no estoque")

    termo = st.text_input("Digite parte do nome:")

    if termo:
        df = estoque[estoque["PRODUTO"].astype(str).str.contains(termo, case=False, na=False)]

        if df.empty:
            st.warning("Nenhum produto encontrado.")
        else:
            st.dataframe(df.reset_index(drop=True), use_container_width=True)
