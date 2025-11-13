import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# ==============================
# ⚙️ CONFIGURAÇÃO INICIAL
# ==============================
st.set_page_config(page_title="Painel Power BI - Loja Importados", layout="wide")

st.markdown(
    """
    <style>
        body {background-color: #0e0e0e; color: #FFD700;}
        .stMarkdown h1, h2, h3, h4 {color: #FFD700;}
        .block-container {padding-top: 1rem;}
        .stDataFrame {background-color: #1a1a1a !important; color: #FFD700 !important;}
        [data-testid="stMetricValue"] {color: #FFD700 !important;}
        [data-testid="stMetricLabel"] {color: #CCCCCC !important;}
    </style>
    """,
    unsafe_allow_html=True
)

st.title("📊 Painel Gerencial - Loja Importados")

# ==============================
# 📂 FUNÇÃO PARA LEITURA E LIMPEZA
# ==============================
def detect_header(path, sheet_name):
    temp = pd.read_excel(path, sheet_name=sheet_name, header=None)
    for i in range(len(temp)):
        if "PRODUTO" in str(temp.iloc[i].values).upper():
            df = pd.read_excel(path, sheet_name=sheet_name, header=i)
            return df
    return pd.read_excel(path, sheet_name=sheet_name)

def limpar(df):
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    return df

def money_format(x):
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# ==============================
# 📁 LEITURA DO ARQUIVO
# ==============================
file_path = "LOJA IMPORTADOS.xlsx"

if not Path(file_path).exists():
    st.error("❌ O arquivo 'LOJA IMPORTADOS.xlsx' não foi encontrado.")
    st.stop()

abas = {"ESTOQUE": None, "VENDAS": None, "COMPRAS": None}
xls = pd.ExcelFile(file_path)
for aba in abas.keys():
    if aba in xls.sheet_names:
        abas[aba] = limpar(detect_header(file_path, aba))
    else:
        st.warning(f"⚠️ Aba '{aba}' não encontrada.")

estoque, vendas, compras = abas["ESTOQUE"], abas["VENDAS"], abas["COMPRAS"]

if estoque is None or vendas is None or compras is None:
    st.error("❌ Não foi possível carregar todas as abas necessárias.")
    st.stop()

# ==============================
# 💰 CÁLCULOS PRINCIPAIS
# ==============================
try:
    vendas["VALOR TOTAL"] = pd.to_numeric(vendas["VALOR TOTAL"], errors="coerce")
    vendas["LUCRO"] = pd.to_numeric(vendas["LUCRO"], errors="coerce")
    compras["CUSTO TOTAL"] = pd.to_numeric(compras["CUSTO TOTAL"], errors="coerce")
    estoque["EM ESTOQUE"] = pd.to_numeric(estoque["EM ESTOQUE"], errors="coerce")
except Exception as e:
    st.error(f"Erro ao converter colunas numéricas: {e}")

total_vendas = vendas["VALOR TOTAL"].sum(skipna=True)
total_compras = compras["CUSTO TOTAL"].sum(skipna=True)
lucro_real = vendas["LUCRO"].sum(skipna=True)
qtd_estoque = estoque["EM ESTOQUE"].sum(skipna=True)

# ==============================
# 📊 EXIBIÇÃO DE KPIs
# ==============================
col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Total de Vendas", money_format(total_vendas))
col2.metric("🧾 Total de Compras", money_format(total_compras))
col3.metric("📈 Lucro Total", money_format(lucro_real))
col4.metric("📦 Quantidade em Estoque", f"{int(qtd_estoque)} unid.")

st.markdown("---")

# ==============================
# 🎯 FILTROS
# ==============================
produtos = sorted(vendas["PRODUTO"].dropna().unique())
filtro_produto = st.multiselect("🔍 Filtrar por Produto:", produtos, default=produtos)

vendas_filtradas = vendas[vendas["PRODUTO"].isin(filtro_produto)]

# ==============================
# 📈 GRÁFICOS
# ==============================
st.subheader("💵 Vendas por Produto")
graf_vendas = vendas_filtradas.groupby("PRODUTO", as_index=False)["VALOR TOTAL"].sum()
fig_vendas = px.bar(
    graf_vendas,
    x="PRODUTO",
    y="VALOR TOTAL",
    title="Ranking de Vendas",
    color="VALOR TOTAL",
    color_continuous_scale=["#FFD700", "#8B8000"],
)
fig_vendas.update_layout(
    paper_bgcolor="#0e0e0e",
    plot_bgcolor="#0e0e0e",
    font_color="#FFD700",
)
st.plotly_chart(fig_vendas, use_container_width=True)

st.subheader("📉 Lucro por Produto")
graf_lucro = vendas_filtradas.groupby("PRODUTO", as_index=False)["LUCRO"].sum()
fig_lucro = px.bar(
    graf_lucro,
    x="PRODUTO",
    y="LUCRO",
    title="Lucro Real por Produto",
    color="LUCRO",
    color_continuous_scale=["#FFD700", "#8B8000"],
)
fig_lucro.update_layout(
    paper_bgcolor="#0e0e0e",
    plot_bgcolor="#0e0e0e",
    font_color="#FFD700",
)
st.plotly_chart(fig_lucro, use_container_width=True)

st.subheader("📦 Estoque Atual")
fig_estoque = px.bar(
    estoque,
    x="PRODUTO",
    y="EM ESTOQUE",
    title="Produtos em Estoque",
    color="EM ESTOQUE",
    color_continuous_scale=["#FFD700", "#8B8000"],
)
fig_estoque.update_layout(
    paper_bgcolor="#0e0e0e",
    plot_bgcolor="#0e0e0e",
    font_color="#FFD700",
)
st.plotly_chart(fig_estoque, use_container_width=True)

# ==============================
# ✅ RODAPÉ
# ==============================
st.markdown("---")
st.caption("📊 Painel desenvolvido em Streamlit | Tema: Dark Gold Elegance 🖤💛")
