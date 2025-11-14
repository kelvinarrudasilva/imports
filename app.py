import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Loja Importados – Dashboard", layout="wide")

# ------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------

GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_ID/export?format=csv"

st.title("📊 Dashboard – Loja Importados")


# ------------------------------------------------------------
# FUNÇÃO PARA CARREGAR PLANILHA
# ------------------------------------------------------------
def carregar_planilha():
    try:
        return pd.read_csv(GOOGLE_SHEET_URL, encoding="utf-8")
    except:
        return pd.read_csv(GOOGLE_SHEET_URL, encoding="latin1")


# ------------------------------------------------------------
# TRATAMENTO DO ARQUIVO
# ------------------------------------------------------------
try:
    df = carregar_planilha()
except Exception as e:
    st.error(f"Erro ao carregar planilha: {e}")
    st.stop()

# limpar colunas
df.columns = [c.strip().upper() for c in df.columns]

# converter DATA
if "DATA" in df.columns:
    df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")


# ------------------------------------------------------------
# FILTROS – MÊS E ANO
# ------------------------------------------------------------

col1, col2 = st.columns(2)

with col1:
    ano_filtro = st.selectbox("Ano", sorted(df["DATA"].dt.year.dropna().unique()), index=0)

with col2:
    mes_filtro = st.selectbox(
        "Mês",
        list(range(1, 13)),
        index=df["DATA"].dt.month.mode().iloc[0] - 1
    )

df_filtrado = df[
    (df["DATA"].dt.year == ano_filtro) &
    (df["DATA"].dt.month == mes_filtro)
]


# ------------------------------------------------------------
# MÉTRICAS GERAIS
# ------------------------------------------------------------
st.subheader("📌 Indicadores Gerais")

total_vendido = df_filtrado["VALOR TOTAL"].sum()
total_lucro = df_filtrado["LUCRO UNITARIO"].sum()
total_qtd = df_filtrado["QTD"].sum()

c1, c2, c3 = st.columns(3)

c1.metric("💰 Total Vendido (R$)", f"R$ {total_vendido:,.2f}")
c2.metric("🏦 Lucro Total (R$)", f"R$ {total_lucro:,.2f}")
c3.metric("📦 Quantidade Vendida", int(total_qtd))


# ------------------------------------------------------------
# ABA DE NAVEGAÇÃO
# ------------------------------------------------------------
aba = st.tabs(["📦 Vendas", "🏆 Top 10 Produtos", "📈 Faturamento", "📦 Consultar Estoque"])


# ------------------------------------------------------------
# 📦 ABA VENDAS
# ------------------------------------------------------------
with aba[0]:

    st.subheader("📦 Vendas do Período Selecionado")

    st.dataframe(df_filtrado, use_container_width=True)


# ------------------------------------------------------------
# 🏆 TOP 10 PRODUTOS
# ------------------------------------------------------------
with aba[1]:

    st.subheader("🏆 Top 10 Produtos Mais Vendidos")

    # Agrupamento geral
    grp = df_filtrado.groupby("PRODUTO").agg(
        QTD_TOTAL=("QTD", "sum"),
        VALOR_TOTAL=("VALOR TOTAL", "sum")
    ).reset_index()

    # Top 10 por valor
    top_valor = grp.sort_values(by="VALOR_TOTAL", ascending=False).head(10)

    # Top 10 por quantidade
    top_qtd = grp.sort_values(by="QTD_TOTAL", ascending=False).head(10)

    colA, colB = st.columns(2)

    # --------- GRÁFICO POR VALOR ---------
    with colA:
        st.write("💵 Top 10 por Valor Vendido")
        fig1 = px.bar(
            top_valor,
            x="PRODUTO",
            y="VALOR_TOTAL",
            text=top_valor["VALOR_TOTAL"].apply(lambda x: f"R$ {x:,.0f}"),
        )
        fig1.update_traces(textposition="inside")
        st.plotly_chart(fig1, use_container_width=True)

    # --------- GRÁFICO POR QUANTIDADE ---------
    with colB:
        st.write("📦 Top 10 por Quantidade Vendida")
        fig2 = px.bar(
            top_qtd,
            x="PRODUTO",
            y="QTD_TOTAL",
            text=top_qtd["QTD_TOTAL"],
        )
        fig2.update_traces(textposition="inside")
        st.plotly_chart(fig2, use_container_width=True)


# ------------------------------------------------------------
# 📈 EVOLUÇÃO DO FATURAMENTO
# ------------------------------------------------------------
with aba[2]:
    st.subheader("📈 Evolução do Faturamento Mensal")

    df_mes = df.copy()
    df_mes["ANO"] = df_mes["DATA"].dt.year
    df_mes["MES"] = df_mes["DATA"].dt.month

    evolucao = df_mes.groupby(["ANO", "MES"])["VALOR TOTAL"].sum().reset_index()

    fig = px.line(evolucao, x="MES", y="VALOR TOTAL", color="ANO", markers=True)
    st.plotly_chart(fig, use_container_width=True)


# ------------------------------------------------------------
# 📦 CONSULTAR ESTOQUE
# ------------------------------------------------------------
with aba[3]:

    st.subheader("📦 Consulta Geral de Estoque")

    if "ESTOQUE" in df.columns:
        st.dataframe(df[["PRODUTO", "ESTOQUE"]].sort_values(by="ESTOQUE", ascending=False), use_container_width=True)
    else:
        st.info("Nenhuma coluna de ESTOQUE encontrada na planilha.")

st.success("Dashboard carregado com sucesso! 🎉")
