# app.py - Versão Final com Detecção Automática da Coluna de Data (100% Estável)
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import requests
from io import BytesIO

# ============================
# CONFIGURAÇÃO DO APLICATIVO
# ============================
st.set_page_config(page_title="Painel - Loja Importados", layout="wide")

# ============================
# ESTILO PERSONALIZADO (Preto + Dourado)
# ============================
st.markdown(
    """
    <style>
        body, .stApp { background-color: #000!important; }

        .stMarkdown, .stText, .stDataFrame, div, span, p, label {
            color: #f0f0f0 !important;
            font-family: 'Segoe UI', sans-serif;
        }

        .minimal-selectbox label {
            font-size: 14px !important;
            color: #d4af37 !important;
            font-weight: 600;
        }

        .minimal-selectbox .stSelectbox div[data-baseweb="select"] {
            background: transparent!important;
            border: 1px solid #d4af37!important;
            border-radius: 8px!important;
            color: #fff!important;
        }

        .minimal-selectbox .stSelectbox:hover div[data-baseweb="select"] {
            border-color: #f5d76e!important;
        }

        .kpi-card {
            background-color: #111;
            border: 1px solid #333;
            padding: 20px;
            border-radius: 14px;
            text-align: center;
            box-shadow: 0px 0px 8px rgba(212,175,55,0.25);
        }
        .kpi-title { font-size: 14px; color: #d4af37; }
        .kpi-value { font-size: 28px; font-weight: bold; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ============================
# FUNÇÃO PARA BAIXAR PLANILHA DO GOOGLE DRIVE
# ============================
def carregar_planilha(url):
    try:
        dados = requests.get(url).content
        return pd.read_excel(BytesIO(dados))
    except:
        st.error("❌ Erro ao carregar a planilha do Google Drive.")
        return None

# URL DIRETA DO DRIVE
URL_DRIVE = "https://drive.google.com/uc?id=1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b"
df = carregar_planilha(URL_DRIVE)

if df is None:
    st.stop()

# ============================
# AJUSTES INICIAIS
# ============================
for col in df.columns:
    if isinstance(df[col].dtype, object):
        df[col] = df[col].astype(str)

# ============================
# DETECÇÃO AUTOMÁTICA DA COLUNA DE DATA
# ============================
possiveis_datas = ["DATA", "Data", "data", "DATA VENDA", "DIA", "VENDA DATA", "DT", "DATE"]

col_data = None
for c in df.columns:
    if c.strip().upper() in [x.upper() for x in possiveis_datas]:
        col_data = c
        break

if col_data is None:
    st.error("❌ Nenhuma coluna de data encontrada na planilha.")
    st.write("Colunas disponíveis:", df.columns.tolist())
    st.stop()

# Converter col_data para datetime
try:
    df[col_data] = pd.to_datetime(df[col_data], errors="coerce")
except:
    st.error("❌ Não foi possível converter a coluna de data.")
    st.stop()

# ============================
# BARRA SUPERIOR + SELECTOR MINIMALISTA C1
# ============================
colA, colB, colC = st.columns([1.2, 2, 1])

with colA:
    st.markdown("### 🛍️ Painel de Vendas — Loja Importados")

with colB:
    st.write("")
    st.write("")
    st.markdown("<div class='minimal-selectbox'>📅 <b>Período</b></div>", unsafe_allow_html=True)

with colC:
    meses = df[col_data].dt.strftime("%m/%Y").dropna().unique()
    meses = sorted(meses, key=lambda x: datetime.strptime(x, "%m/%Y"))
    mes_selecionado = st.selectbox("", meses, label_visibility="collapsed")

mes_dt = datetime.strptime(mes_selecionado, "%m/%Y")
df_mes = df[(df[col_data].dt.month == mes_dt.month) & (df[col_data].dt.year == mes_dt.year)]

# ============================
# KPIs
# ============================
col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"<div class='kpi-card'><div class='kpi-title'>Vendas no mês</div><div class='kpi-value'>{len(df_mes)}</div></div>", unsafe_allow_html=True)

with col2:
    total = df_mes["VALOR"].astype(float).sum() if "VALOR" in df_mes.columns else 0
    st.markdown(f"<div class='kpi-card'><div class='kpi-title'>Faturamento</div><div class='kpi-value'>R$ {total:,.2f}</div></div>", unsafe_allow_html=True)

with col3:
    lucro = df_mes["LUCRO"].astype(float).sum() if "LUCRO" in df_mes.columns else 0
    st.markdown(f"<div class='kpi-card'><div class='kpi-title'>Lucro Obtido</div><div class='kpi-value'>R$ {lucro:,.2f}</div></div>", unsafe_allow_html=True)

# ============================
# GRÁFICO DE PRODUTOS MAIS VENDIDOS
# ============================
st.subheader("📦 Produtos Mais Vendidos — Mês Selecionado")

if "QUANTIDADE" in df_mes.columns:
    df_rank = df_mes.groupby("PRODUTO")["QUANTIDADE"].sum().reset_index()
    df_rank = df_rank.sort_values(by="QUANTIDADE", ascending=False)

    fig = px.bar(df_rank, x="PRODUTO", y="QUANTIDADE", title="Ranking de Vendas", text_auto=True)
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("A planilha não possui coluna QUANTIDADE.")

# ============================
# TABELA DE VENDAS DO MÊS (Nova Últimas Vendas)
# ============================
st.subheader("📋 Vendas do Mês — Lista Completa")
st.dataframe(df_mes, use_container_width=True)

# ============================
# ESTOQUE (somente consulta)
# ============================
st.subheader("📦 Estoque (Consulta)")

if "ESTOQUE" in df.columns:
    estoque_df = df[["PRODUTO", "ESTOQUE"]].drop_duplicates()
    st.dataframe(estoque_df, use_container_width=True)
else:
    st.info("A planilha não possui coluna ESTOQUE.")
