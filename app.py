import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Loja", layout="wide")

# =====================================================================
# NORMALIZAÇÃO SIMPLES
# =====================================================================
def norm(text):
    if not isinstance(text, str):
        return ""
    return text.strip().upper()

# =====================================================================
# UPLOAD DO EXCEL
# =====================================================================
st.title("📦 Dashboard de Estoque e Vendas")

excel_file = st.file_uploader("Envie o arquivo Excel", type=["xlsx"])
if not excel_file:
    st.stop()

xls = pd.ExcelFile(excel_file)

# =====================================================================
# ABAS QUE DEVEM EXISTIR (EXATAMENTE ISTO)
# =====================================================================
NEEDED = ["ESTOQUE", "VENDAS", "COMPRAS"]

# Mapeia abas reais encontradas
sheet_map = {norm(name): name for name in xls.sheet_names}

# Debug na tela
st.write("Abas encontradas:", xls.sheet_names)
st.write("Mapeamento:", sheet_map)

# Verificar e carregar cada aba
missing = [aba for aba in NEEDED if aba not in sheet_map]
if missing:
    st.error(f"As abas obrigatórias estão faltando: {missing}")
    st.stop()

SHEET_ESTOQUE = sheet_map["ESTOQUE"]
SHEET_VENDAS = sheet_map["VENDAS"]
SHEET_COMPRAS = sheet_map["COMPRAS"]

# Carregar dataframes
df_estoque = pd.read_excel(excel_file, sheet_name=SHEET_ESTOQUE)
df_vendas = pd.read_excel(excel_file, sheet_name=SHEET_VENDAS)
df_compras = pd.read_excel(excel_file, sheet_name=SHEET_COMPRAS)

# =====================================================================
# NORMALIZAR COLUNAS
# =====================================================================
df_estoque.columns = [norm(c) for c in df_estoque.columns]
df_vendas.columns = [norm(c) for c in df_vendas.columns]

# Debug
st.write("📄 Colunas VENDAS:", df_vendas.columns.tolist())
st.write("📄 Colunas ESTOQUE:", df_estoque.columns.tolist())

# =====================================================================
# CAMPOS OBRIGATÓRIOS PARA VENDAS
# =====================================================================
REQUIRED_VENDAS = ["DATA", "PRODUTO", "QTD", "VALOR VENDA", "VALOR TOTAL"]

req_norm = [norm(c) for c in REQUIRED_VENDAS]

missing_cols = [c for c in req_norm if c not in df_vendas.columns]
if missing_cols:
    st.error(f"As colunas obrigatórias estão faltando na aba VENDAS: {missing_cols}")
    st.stop()

# Converter datas
df_vendas["DATA"] = pd.to_datetime(df_vendas["DATA"], errors="coerce")

# =====================================================================
# FILTRO DE PERÍODO
# =====================================================================
st.subheader("📅 Período")

min_date = df_vendas["DATA"].min()
max_date = df_vendas["DATA"].max()

periodo = st.date_input("Selecione o período", (min_date, max_date))
inicio, fim = periodo

df_filtrado = df_vendas[
    (df_vendas["DATA"] >= pd.to_datetime(inicio)) &
    (df_vendas["DATA"] <= pd.to_datetime(fim))
]

# =====================================================================
# MÉTRICAS
# =====================================================================
st.subheader("📊 Resumo do Período")

valor_vendido = df_filtrado["VALOR TOTAL"].sum()
quantidade_total = df_filtrado["QTD"].sum()

col1, col2 = st.columns(2)
col1.metric("💰 Valor Vendido", f"R$ {valor_vendido:,.2f}".replace(",", "."))
col2.metric("📈 Quantidade Vendida", int(quantidade_total))

# =====================================================================
# LISTAGEM DE VENDAS
# =====================================================================
st.subheader("📋 Vendas do Período")

if df_filtrado.empty:
    st.warning("Nenhuma venda encontrada neste período.")
else:
    st.dataframe(df_filtrado)

# =====================================================================
# TOP PRODUTOS
# =====================================================================
st.subheader("🏆 Top Produtos Mais Vendidos")

if not df_filtrado.empty:
    top = (
        df_filtrado.groupby("PRODUTO")["QTD"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .reset_index()
    )

    fig = px.bar(top, x="PRODUTO", y="QTD", title="Top 10 Produtos Mais Vendidos")
    fig.update_traces(marker_color="purple")
    st.plotly_chart(fig)
else:
    st.info("Sem vendas para exibir ranking.")

# =====================================================================
# ESTOQUE
# =====================================================================
st.subheader("📦 Estoque Atual")

if df_estoque.empty:
    st.warning("Estoque vazio.")
else:
    st.dataframe(df_estoque)

