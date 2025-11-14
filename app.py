# app.py
# Código completo ajustado com validação automática e prevenção de erros

import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime
from io import BytesIO

# ======================
# CONFIG VISUAL
# ======================
st.set_page_config(page_title="Painel - Loja Importados", layout="wide")

st.markdown(
    """
    <style>
      :root { --gold:#FFD700; }
      body, .stApp { background-color: #000; color: white; }
      .stMetric { background: #111; padding: 20px; border-radius: 12px; border: 1px solid var(--gold); }
      h1, h2, h3 { color: var(--gold); }
    </style>
    """,
    unsafe_allow_html=True,
)

# ======================
# FUNÇÃO CORRIGIR CABEÇALHOS
# ======================
def limpar_colunas(df):
    cols = []
    for c in df.columns:
        if not isinstance(c, str):
            c = str(c)
        cols.append(c.strip().upper().replace(" ", "_").replace("-", "_"))
    df.columns = cols
    return df

# ======================
# VALIDADOR AUTOMÁTICO
# ======================
def validar(df, esperado, nome_aba):
    erros = []
    corr = {}

    df_cols = [c.strip().upper() for c in df.columns]
    esp_cols = [e.strip().upper() for e in esperado]

    for col_esp in esp_cols:
        if col_esp not in df_cols:
            parecido = None
            for c in df_cols:
                if col_esp.replace("_", "") in c.replace("_", ""):
                    parecido = c
            if parecido:
                corr[parecido] = col_esp
            else:
                erros.append(col_esp)

    # Aplicar correções
    for errado, certo in corr.items():
        df.rename(columns={errado: certo}, inplace=True)

    df = limpar_colunas(df)

    return df, erros

# ======================
# COLUNAS ESPERADAS
# ======================
colunas_esperadas = {
    "ESTOQUE": ["CODIGO", "NOME", "CUSTO", "VENDA", "STATUS"],
    "VENDAS": ["DATA", "CODIGO", "CLIENTE", "VALOR"],
}

# ======================
# SIDEBAR
# ======================
st.sidebar.title("📂 Importar Planilha")
arquivo = st.sidebar.file_uploader("Envie um Excel", type=["xlsx"])

if not arquivo:
    st.warning("Envie a planilha para iniciar.")
    st.stop()

try:
    excel = pd.ExcelFile(arquivo)
except Exception as e:
    st.error("Erro ao ler arquivo: " + str(e))
    st.stop()

abas = excel.sheet_names

st.sidebar.subheader("Selecione uma aba para visualizar")
aba_escolhida = st.sidebar.selectbox("Aba", abas)

df = excel.parse(aba_escolhida)

# ======================
# LIMPAR E VALIDAR
# ======================
df = limpar_colunas(df)

if aba_escolhida.upper() in colunas_esperadas:
    df, erros = validar(df, colunas_esperadas[aba_escolhida.upper()], aba_escolhida)

    if erros:
        st.error(f"⛔ Colunas faltando em **{aba_escolhida}**: {erros}")
    else:
        st.success(f"✔ Aba {aba_escolhida} validada e corrigida automaticamente!")

# ======================
# MOSTRAR DATAFRAME
# ======================
st.subheader(f"📌 Dados da aba: {aba_escolhida}")
st.dataframe(df, use_container_width=True)

# ======================
# GRÁFICOS AUTOMÁTICOS
# ======================
if "VENDA" in df.columns:
    fig = px.histogram(df, x="VENDA", title="Distribuição Valores de Venda")
    st.plotly_chart(fig, use_container_width=True)

if "STATUS" in df.columns:
    fig2 = px.pie(df, names="STATUS", title="Status do Estoque")
    st.plotly_chart(fig2, use_container_width=True)

# ======================
# DOWNLOAD DO DF CORRIGIDO
# ======================
buffer = BytesIO()
with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
    df.to_excel(writer, index=False, sheet_name=aba_escolhida)

st.download_button(
    label="⬇ Baixar aba corrigida",
    data=buffer.getvalue(),
    file_name=f"{aba_escolhida}_corrigida.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# ======================
# DASHBOARD
# Link fixo da planilha Google Drive
URL_PLANILHA = "https://drive.google.com/uc?export=download&id=1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b"

# ======================
st.header("📊 Dashboard - Visão Geral")

# =============== MÉTRICAS ===============
col1, col2, col3 = st.columns(3)
try:
    total_estoque = estoque_df["EM ESTOQUE"].sum()
    col1.metric("Total em Estoque", f"{total_estoque:,.0f}")
except:
    col1.metric("Total em Estoque", "Erro")

try:
    total_vendas = vendas_df["VALOR TOTAL"].sum()
    col2.metric("Faturamento Total", f"R$ {total_vendas:,.2f}")
except:
    col2.metric("Faturamento Total", "Erro")

try:
    lucro_total = vendas_df["LUCRO UNITARIO"].sum()
    col3.metric("Lucro Total", f"R$ {lucro_total:,.2f}")
except:
    col3.metric("Lucro Total", "Erro")

# =============== VENDAS POR PRODUTO ===============
st.subheader("📦 Vendas por Produto")
try:
    vendas_produto = vendas_df.groupby("PRODUTO")["VALOR TOTAL"].sum().reset_index()
    fig1 = px.bar(vendas_produto, x="PRODUTO", y="VALOR TOTAL", title="Vendas por Produto")
    st.plotly_chart(fig1, use_container_width=True)
except:
    st.error("Erro ao gerar gráfico de vendas por produto.")

# =============== ESTOQUE DOS MAIS VENDIDOS ===============
st.subheader("🔥 Produtos Mais Vendidos")
try:
    qtd_vendida = vendas_df.groupby("PRODUTO")["QTD"].sum().reset_index()
    top = qtd_vendida.sort_values("QTD", ascending=False).head(10)
    fig2 = px.bar(top, x="PRODUTO", y="QTD", title="Top 10 mais vendidos")
    st.plotly_chart(fig2, use_container_width=True)
except:
    st.error("Erro ao gerar gráfico de top produtos.")

# =============== EVOLUÇÃO DO FATURAMENTO ===============
st.subheader("📈 Evolução do Faturamento")
try:
    vendas_df["DATA"] = pd.to_datetime(vendas_df["DATA"], errors="coerce")
    fat_diario = vendas_df.groupby("DATA")["VALOR TOTAL"].sum().reset_index()
    fig3 = px.line(fat_diario, x="DATA", y="VALOR TOTAL", title="Faturamento ao longo do tempo")
    st.plotly_chart(fig3, use_container_width=True)
except:
    st.error("Erro ao gerar gráfico de evolução do faturamento.")

