import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from io import BytesIO

# ======================
# Config visual (botão menor, textos legíveis)
# ======================
st.set_page_config(page_title="Dashboard Loja", layout="wide")

st.markdown(
    """
    <style>
      :root { --gold:#FFD700; --bg:#000000; }

      .stApp { background-color: var(--bg); color: var(--gold); }

      .section-title { font-size: 20px; font-weight:700; color:var(--gold); }

      /* Selectbox compacto */
      div[data-baseweb="select"] > div {
          background-color:#0d0d0d !important;
          border:1px solid rgba(255,215,0,0.4) !important;
          border-radius:6px !important;
          padding:2px 8px !important;
          min-height:28px !important;
      }

      div[data-baseweb="select"] * {
          color: var(--gold) !important;
          font-size: 13px !important;
      }

      .metric-label { font-size:13px; opacity:0.8; }
      .metric-value { font-size:22px; font-weight:700; }

      .stDataFrame table td, .stDataFrame table th {
          color:#e6e6e6 !important;
          font-size:14px !important;
      }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("<div class='section-title'>📊 Painel — Loja Importados</div>", unsafe_allow_html=True)
st.write("---")

# ======================
# CARREGAR PLANILHA DO GOOGLE DRIVE
# ======================
GDRIVE_URL = "https://drive.google.com/uc?id=1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b"

try:
    res = requests.get(GDRIVE_URL)
    res.raise_for_status()
    buffer = BytesIO(res.content)
    df = pd.read_excel(buffer)
except Exception as e:
    st.error(f"❌ Erro ao acessar a planilha do Google Drive: {e}")
    st.stop()

# ======================
# VERIFICAR COLUNAS
# ======================
required_cols = ["Produto", "EM ESTOQUE", "VENDAS"]

for col in required_cols:
    if col not in df.columns:
        st.error(f"❌ Coluna obrigatória não encontrada: **{col}**")
        st.stop()

df["EM ESTOQUE"] = pd.to_numeric(df["EM ESTOQUE"], errors="coerce").fillna(0)
df["VENDAS"] = pd.to_numeric(df["VENDAS"], errors="coerce").fillna(0)

# ======================
# SELECTBOX DE PERÍODO (visual refinado)
# ======================
st.markdown("<div class='section-title'>Período</div>", unsafe_allow_html=True)

period_options = ["Geral", "Últimos 30 dias", "Últimos 7 dias"]
period = st.selectbox("", period_options, label_visibility="collapsed")

# Obs: a planilha não tem coluna de data — filtro será ignorado.
df_period = df.copy()

# ======================
# MÉTRICAS
# ======================
total_vendas = df_period["VENDAS"].sum()
total_estoque = df_period["EM ESTOQUE"].sum()

colA, colB = st.columns(2)

with colA:
    st.markdown("<p class='metric-label'>📦 Estoque (Vendas)</p>", unsafe_allow_html=True)
    st.markdown(f"<p class='metric-value'>R$ {total_vendas:,.2f}</p>", unsafe_allow_html=True)

with colB:
    st.markdown("<p class='metric-label'>📦 Estoque Atual</p>", unsafe_allow_html=True)
    st.markdown(f"<p class='metric-value'>{total_estoque}</p>", unsafe_allow_html=True)

st.write("---")

# ======================
# GRÁFICO ROXO
# ======================
st.markdown("<div class='section-title'>Top 15 Produtos Mais Vendidos</div>", unsafe_allow_html=True)

try:
    df_sorted = df_period.sort_values("VENDAS", ascending=False).head(15)
    fig = px.bar(
        df_sorted,
        x="Produto",
        y="VENDAS",
        title="",
        color="VENDAS",
        template="plotly_dark",
        text="VENDAS"
    )
    fig.update_traces(marker_color="purple", textposition="outside")
    st.plotly_chart(fig, use_container_width=True)
except Exception as e:
    st.warning("⚠ Erro ao gerar o gráfico.")
    st.text(str(e))

st.write("---")

# ======================
# TABELA COMPLETA
# ======================
st.markdown("<div class='section-title'>Tabela Completa</div>", unsafe_allow_html=True)
st.dataframe(df_period)
