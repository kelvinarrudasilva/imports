import streamlit as st
import pandas as pd
import plotly.express as px

# ==============================
# CONFIGURAÇÃO DA PÁGINA
# ==============================
st.set_page_config(
    page_title="Dashboard - Loja Importados",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📊 Dashboard de Desempenho - Loja Importados")
st.markdown("Análise de Estoque, Vendas e Compras em tempo real")

# ==============================
# FUNÇÃO DE LEITURA ROBUSTA
# ==============================
def read_sheet(file, sheet):
    df = None
    # tenta encontrar a primeira linha com "Produto" ou "Data"
    for skip in range(0, 10):
        temp = pd.read_excel(file, sheet_name=sheet, skiprows=skip)
        if any(temp.columns.str.contains("PRODUTO", case=False, na=False)) or \
           any(temp.columns.str.contains("DATA", case=False, na=False)):
            df = temp
            break
    if df is None:
        df = pd.read_excel(file, sheet_name=sheet)

    # remove colunas Unnamed
    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
    df.columns = [c.strip().upper() for c in df.columns]
    return df

# ==============================
# CARREGAR DADOS
# ==============================
@st.cache_data
def load_data():
    file = "LOJA IMPORTADOS.xlsx"
    estoque = read_sheet(file, "ESTOQUE")
    vendas = read_sheet(file, "VENDAS")
    compras = read_sheet(file, "COMPRAS")
    return estoque, vendas, compras

estoque, vendas, compras = load_data()

# ==============================
# TRATAMENTO DE DATAS
# ==============================
for df in [vendas, compras]:
    for col in df.columns:
        if "DATA" in col:
            df[col] = pd.to_datetime(df[col], errors="coerce")

# ==============================
# KPIs PRINCIPAIS
# ==============================
def get_col(df, *possible_names):
    """Tenta encontrar o nome de coluna certo por similaridade"""
    for name in possible_names:
        matches = [c for c in df.columns if name in c]
        if matches:
            return matches[0]
    return None

col_valor = get_col(vendas, "VALOR TOTAL", "VENDA", "VALOR")
col_qtd = get_col(estoque, "QUANTIDADE", "QTD", "QTDE")

total_vendas = vendas[col_valor].sum() if col_valor else 0
total_compras = compras[get_col(compras, "VALOR TOTAL", "COMPRA", "VALOR")].sum() if get_col(compras, "VALOR TOTAL", "COMPRA", "VALOR") else 0
lucro_estimado = total_vendas - total_compras
qtde_estoque = estoque[col_qtd].sum() if col_qtd else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("💰 Total de Vendas", f"R$ {total_vendas:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
col2.metric("🧾 Total de Compras", f"R$ {total_compras:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
col3.metric("📈 Lucro Estimado", f"R$ {lucro_estimado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
col4.metric("📦 Quantidade em Estoque", int(qtde_estoque))

st.markdown("---")

# ==============================
# GRÁFICOS
# ==============================
if col_valor and "DATA" in vendas.columns:
    vendas["MÊS"] = vendas["DATA"].dt.to_period("M").astype(str)
    vendas_mensais = vendas.groupby("MÊS")[col_valor].sum().reset_index()
    fig_vendas = px.bar(vendas_mensais, x="MÊS", y=col_valor, title="📅 Evolução Mensal das Vendas", text_auto=True)
    st.plotly_chart(fig_vendas, use_container_width=True)

if "PRODUTO" in vendas.columns and col_valor:
    top_produtos = vendas.groupby("PRODUTO")[col_valor].sum().nlargest(10).reset_index()
    fig_top = px.bar(top_produtos, x=col_valor, y="PRODUTO", orientation="h", title="🏆 Top 10 Produtos Mais Vendidos", text_auto=True)
    st.plotly_chart(fig_top, use_container_width=True)

if "DATA" in compras.columns:
    col_compras = get_col(compras, "VALOR TOTAL", "COMPRA", "VALOR")
    if col_compras:
        compras["MÊS"] = compras["DATA"].dt.to_period("M").astype(str)
        compras_mensais = compras.groupby("MÊS")[col_compras].sum().reset_index()
        fig_compras = px.line(compras_mensais, x="MÊS", y=col_compras, markers=True, title="📦 Evolução das Compras")
        st.plotly_chart(fig_compras, use_container_width=True)

if col_qtd:
    top_estoque = estoque.sort_values(col_qtd, ascending=False).head(15)
    fig_estoque = px.bar(top_estoque, x="PRODUTO", y=col_qtd, title="📊 Top 15 Itens em Estoque")
    st.plotly_chart(fig_estoque, use_container_width=True)

# ==============================
# DADOS DETALHADOS
# ==============================
with st.expander("📋 Visualizar Dados Detalhados"):
    tab1, tab2, tab3 = st.tabs(["🛒 Vendas", "📦 Compras", "🏷️ Estoque"])
    tab1.dataframe(vendas)
    tab2.dataframe(compras)
    tab3.dataframe(estoque)

st.markdown("---")
st.caption("© 2025 Loja Importados | Dashboard gerado automaticamente com Streamlit + Plotly")
