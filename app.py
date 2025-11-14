import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re

st.set_page_config(page_title="Estoque & Vendas", layout="wide")

# ==========================
#   CONFIG PADRÃO
# ==========================

st.markdown("""
<style>
.small-btn button {
    padding: 0.25rem 0.6rem !important;
    font-size: 0.75rem !important;
    border-radius: 6px !important;
}
.metric-card {
    padding: 14px;
    background: #f5f5f5;
    border-radius: 12px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

# ==========================
#   FUNÇÃO CARREGAR EXCEL
# ==========================

def carregar_excel_google_drive(url):
    if "id=" in url:
        file_id = url.split("id=")[-1]
    else:
        file_id = url

    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"

    try:
        df_dict = pd.read_excel(download_url, sheet_name=None, engine="openpyxl")
        return df_dict
    except Exception as e:
        st.error(f"Erro ao carregar Google Drive: {e}")
        return None


# ==========================
#   LEITURA DA PLANILHA
# ==========================

st.header("Gerenciamento de Estoque & Vendas")

url = st.text_input("URL/ID do Arquivo no Google Drive:")

if not url:
    st.stop()

planilhas = carregar_excel_google_drive(url)
if planilhas is None:
    st.stop()

# ==========================
#   MAPEAR SHEETS
# ==========================

def find_sheet(name_list, target):
    for name in name_list:
        if target in name.upper():
            return name
    return None

sheet_names_upper = [s.upper() for s in list(planilhas.keys())]

sheet_estoque = find_sheet(sheet_names_upper, "ESTOQUE")
sheet_vendas = find_sheet(sheet_names_upper, "VENDAS")

if sheet_vendas is None:
    st.error("Aba VENDAS não encontrada.")
    st.stop()

if sheet_estoque is None:
    st.error("Aba ESTOQUE não encontrada.")
    st.stop()

vendas = planilhas[sheet_vendas]
estoque = planilhas[sheet_estoque]

# ==========================
#   PADRONIZAR COLUNAS
# ==========================

vendas.columns = vendas.columns.str.strip().str.upper()

mapa_vendas = {
    "_DATA": "DATA",
    "_PRODUTO": "PRODUTO",
    "_QTD": "QTD",
    "_VALOR_VENDA": "VALOR VENDA",
    "_VALOR_TOTAL": "VALOR TOTAL",
    "_CUSTO_MEDIO": "MEDIA CUSTO UNITARIO",
    "_LUCRO": "LUCRO UNITARIO",
    "_MAKEUP": "MAKEUP",
    "_LUCRO_PERC": "% DE LUCRO SOBRE CUSTO",
    "_STATUS": "STATUS",
    "_CLIENTE": "CLIENTE",
    "_OBS": "OBS"
}

for novo, antigo in mapa_vendas.items():
    if antigo in vendas.columns:
        vendas[novo] = vendas[antigo]
    else:
        vendas[novo] = None  # Caso falte algo, não quebra

# Converte DATA
try:
    vendas["_DATA"] = pd.to_datetime(vendas["_DATA"], format="%d/%m/%Y")
except:
    st.error("Coluna DATA tem formato inválido.")
    st.stop()

# Criar período
vendas["_PERIODO"] = vendas["_DATA"].dt.strftime("%Y-%m")

# ==========================
#   PERÍODO
# ==========================

periodos = ["Geral"] + sorted(vendas["_PERIODO"].unique())
periodo_escolhido = st.radio("Período", periodos, horizontal=True)

df = vendas.copy()

if periodo_escolhido != "Geral":
    df = df[df["_PERIODO"] == periodo_escolhido]

# ==========================
#   MÉTRICAS
# ==========================

vendido = df["_VALOR_TOTAL"].replace("R$ ", "", regex=True)
vendido = vendido.replace(",", ".", regex=False).astype(float).sum()

quantidade = df["_QTD"].astype(int).sum()

lucro = df["_LUCRO"].replace("R$ ", "", regex=True)
lucro = lucro.replace(",", ".", regex=False).astype(float).sum()

col1, col2, col3 = st.columns(3)
col1.metric("💰 Vendido", f"R$ {vendido:,.2f}".replace(",", "."))
col2.metric("📈 Quantidade", quantidade)
col3.metric("💸 Lucro", f"R$ {lucro:,.2f}".replace(",", "."))

# ==========================
#   RELATÓRIO DE VENDAS
# ==========================

st.subheader("📋 Vendas do Período")

colunas_saida = [
    "DATA",
    "PRODUTO",
    "QTD",
    "VALOR VENDA",
    "VALOR TOTAL",
    "MEDIA CUSTO UNITARIO",
    "LUCRO UNITARIO",
    "MAKEUP",
    "% DE LUCRO SOBRE CUSTO",
    "STATUS",
    "CLIENTE",
    "OBS"
]

df_saida = vendas.copy()
df_saida = df_saida[[c for c in colunas_saida if c in vendas.columns]]

st.dataframe(df_saida, use_container_width=True)

# ==========================
#   GRÁFICO DE TOP PRODUTOS
# ==========================

st.subheader("🏆 Top 10 Produtos Mais Vendidos")

top = (
    vendas.groupby("PRODUTO")["QTD"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
    .reset_index()
)

fig = px.bar(top, x="PRODUTO", y="QTD", title="Top 10 Produtos Mais Vendidos")
st.plotly_chart(fig, use_container_width=True)
