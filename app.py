import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re

st.set_page_config(page_title="Estoque & Vendas", layout="wide")

# ==========================
#  CSS
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
#  FUNÇÕES
# ==========================

def clean_number(x):
    if pd.isna(x): 
        return 0
    x = str(x)
    x = re.sub(r"[^0-9\-,\.]", "", x)
    x = x.replace(",", ".")
    if x == "" or x == "-":
        return 0
    try:
        return float(x)
    except:
        return 0


def carregar_excel_google_drive(url):
    try:
        df_dict = pd.read_excel(url, sheet_name=None, engine="openpyxl")
        return df_dict
    except Exception as e:
        st.error(f"Erro ao carregar arquivo: {e}")
        return None


def find_sheet(name_list, target):
    for name in name_list:
        if target in name.upper():
            return name
    return None


# ==========================
#  URL FIXA DO ARQUIVO
# ==========================
url = "https://drive.google.com/uc?id=1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b"

planilhas = carregar_excel_google_drive(url)
if planilhas is None:
    st.stop()

# ==========================
#  DETECTAR SHEETS
# ==========================
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
#  PADRONIZAR VENDAS
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
        vendas[novo] = None


# ==========================
#  CONVERTER DATA
# ==========================
try:
    vendas["_DATA"] = pd.to_datetime(vendas["_DATA"], format="%d/%m/%Y")
except:
    st.error("Erro ao converter DATA. Verifique o formato da planilha.")
    st.stop()

vendas["_PERIODO"] = vendas["_DATA"].dt.strftime("%Y-%m")


# ==========================
#  LIMPAR NÚMEROS
# ==========================
vendas["_QTD"] = vendas["_QTD"].apply(clean_number).astype(int)
vendas["_VALOR_TOTAL"] = vendas["_VALOR_TOTAL"].apply(clean_number)
vendas["_LUCRO"] = vendas["_LUCRO"].apply(clean_number)


# ==========================
#  FILTRO DE PERÍODO
# ==========================
st.header("Gerenciamento de Estoque & Vendas")

periodos = ["Geral"] + sorted(vendas["_PERIODO"].unique())
periodo_escolhido = st.radio("Período", periodos, horizontal=True)

df = vendas.copy()

if periodo_escolhido != "Geral":
    df = df[df["_PERIODO"] == periodo_escolhido]

# ==========================
#  MÉTRICAS
# ==========================
vendido = df["_VALOR_TOTAL"].sum()
quantidade = df["_QTD"].sum()
lucro = df["_LUCRO"].sum()

col1, col2, col3 = st.columns(3)
col1.metric("💰 Vendido", f"R$ {vendido:,.2f}".replace(",", "."))
col2.metric("📈 Quantidade", quantidade)
col3.metric("💸 Lucro", f"R$ {lucro:,.2f}".replace(",", "."))

# ==========================
#  RELATÓRIO
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

df_saida = vendas[[c for c in colunas_saida if c in vendas.columns]]

st.dataframe(df_saida, use_container_width=True)

# ==========================
#  TOP PRODUTOS
# ==========================

st.subheader("🏆 Top 10 Produtos Mais Vendidos")

top = (
    vendas.groupby("PRODUTO")["_QTD"]
    .sum()
    .sort_values(ascending=False)
    .head(10)
    .reset_index()
)

fig = px.bar(top, x="PRODUTO", y="_QTD", title="Top 10 Produtos")
st.plotly_chart(fig, use_container_width=True)
