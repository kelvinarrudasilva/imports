# Novo app.py melhorado com maior contraste, visibilidade aprimorada
# Ajustado conforme solicitado: Top10 mais visível, botão de mês reduzido,
# visão geral com Últimas Vendas Resumidas, barras com quantidade dentro,
# e troca de temas (Dark, Claro e Tema Premium)

import streamlit as st
import pandas as pd
import plotly.express as px

# ==========================
# CONFIGURAÇÕES DE TEMA
# ==========================
temas = {
    "Dark": {
        "bg": "#0D0D0D",
        "card": "#1A1A1A",
        "text": "white",
        "accent": "#00BFFF"
    },
    "Claro": {
        "bg": "#F5F5F5",
        "card": "white",
        "text": "#000000",
        "accent": "#0077CC"
    },
    "Premium": {
        "bg": "#111827",
        "card": "#1F2937",
        "text": "#F3F4F6",
        "accent": "#10B981"  # Verde elegante
    }
}

if "tema" not in st.session_state:
    st.session_state.tema = "Premium"

# SELECTOR
selected_tema = st.sidebar.selectbox("Tema", list(temas.keys()), index=list(temas.keys()).index(st.session_state.tema))
st.session_state.tema = selected_tema
TEMA = temas[selected_tema]

# APLICAÇÃO DE ESTILO GLOBAL
st.markdown(f"""
<style>
body {{ background-color: {TEMA['bg']}; color: {TEMA['text']}; }}
.block-container {{ background-color: {TEMA['bg']}; }}
.metric, .stMetric {{ color: {TEMA['text']} !important; }}
.card {{ background-color: {TEMA['card']}; padding: 18px; border-radius: 12px; margin-bottom: 12px; }}
h2,h3,h4,h5,h6,p,span,div {{ color: {TEMA['text']} !important; }}
</style>
""", unsafe_allow_html=True)

# ==========================
# CARREGAMENTO
# ==========================
def load_df(path):
    try:
        return pd.read_excel(path)
    except:
        return pd.read_csv(path)

vendas = load_df("vendas.csv")
estoque = load_df("estoque.csv")

# NORMALIZAÇÃO
vendas.columns = vendas.columns.str.upper().str.strip()
estoque.columns = estoque.columns.str.upper().str.strip()

# --------------------------
# Página 1 — VISÃO GERAL
# --------------------------
def pagina_visao_geral():
    st.title("📊 Visão Geral — Painel de Vendas e Estoque")

    # Filtro mês reduzido
    vendas["DATA"] = pd.to_datetime(vendas["DATA"], errors="coerce")
    vendas["ANO_MES"] = vendas["DATA"].dt.strftime("%b/%Y")

    meses = vendas["ANO_MES"].dropna().unique()
    mes_select = st.selectbox("", meses, index=len(meses)-1)
    vendas_mes = vendas[vendas["ANO_MES"] == mes_select]

    # KPIs
    col1, col2, col3 = st.columns(3)
    with col1: st.metric("Vendas Totais", f"R$ {vendas_mes['VALOR TOTAL'].sum():,.2f}")
    with col2: st.metric("Lucro do Mês", f"R$ {vendas_mes['LUCRO'].sum():,.2f}")
    with col3: st.metric("Qtd Vendida", int(vendas_mes["QUANTIDADE"].sum()))

    st.subheader("📌 Últimas Vendas (Resumido)")
    ult = vendas.sort_values("DATA", ascending=False).head(12)[["DATA", "PRODUTO", "QUANTIDADE", "VALOR TOTAL"]]
    st.dataframe(ult, use_container_width=True)

    st.subheader("🔥 Top 10 Produtos Mais Vendidos")
    top10 = vendas.groupby("PRODUTO")["QUANTIDADE"].sum().sort_values(ascending=False).head(10)
    fig = px.bar(top10, orientation='h', text=top10.values)
    fig.update_traces(textposition='inside')
    fig.update_layout(height=480, plot_bgcolor=TEMA['card'], paper_bgcolor=TEMA['bg'], font_color=TEMA['text'])
    st.plotly_chart(fig, use_container_width=True)

# --------------------------
# Página 2 — ESTOQUE
# --------------------------
def pagina_estoque():
    st.title("📦 Estoque Atual — Quantidade, Custo e Valor de Venda")

    # Conversões
    estoque["QTD"] = pd.to_numeric(estoque.get("QUANTIDADE", 0), errors='coerce').fillna(0)
    estoque["PRECO_CUSTO"] = pd.to_numeric(estoque.get("CUSTO", 0), errors='coerce').fillna(0)
    estoque["PRECO_VENDA"] = pd.to_numeric(estoque.get("PRECO", 0), errors='coerce').fillna(0)

    estoque["TOTAL_CUSTO"] = estoque["QTD"] * estoque["PRECO_CUSTO"]
    estoque["TOTAL_VENDA"] = estoque["QTD"] * estoque["PRECO_VENDA"]

    # KPIs resumo estoque
    col1, col2 = st.columns(2)
    with col1: st.metric("Valor total em estoque (Custo)", f"R$ {estoque['TOTAL_CUSTO'].sum():,.2f}")
    with col2: st.metric("Valor total em estoque (Venda)", f"R$ {estoque['TOTAL_VENDA'].sum():,.2f}")

    st.subheader("📊 Estoque Atual — Quantidade por Produto")
    fig2 = px.bar(
        estoque.sort_values("QTD", ascending=False),
        x="PRODUTO", y="QTD", text="QTD"
    )
    fig2.update_traces(textposition='inside')
    fig2.update_layout(height=520, plot_bgcolor=TEMA['card'], paper_bgcolor=TEMA['bg'], font_color=TEMA['text'])
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("📋 Tabela completa do estoque")
    st.dataframe(estoque, use_container_width=True)

# --------------------------
# MENU
# --------------------------
aba = st.sidebar.radio("Navegação", ["Visão Geral", "Estoque"])
if aba == "Visão Geral":
    pagina_visao_geral()
elif aba == "Estoque":
    pagina_estoque()
