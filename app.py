# app.py — Tema Roxo Moderno + Botões com Espaço + Abas Brancas + KPIs Grandes
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import re
import requests
from io import BytesIO

st.set_page_config(page_title="Painel - Loja Importados", layout="wide")

# =============================
# ESTILO (tema roxo + abas modernas + espaçamento)
# =============================
st.markdown(
    """
    <style>
      :root {
        --bg: #f7f2ff;
        --accent: #8b5cf6;
        --accent-dark: #6d28d9;
        --text: #1a1a1a;
      }

      body, .stApp { background: var(--bg) !important; }

      /* ======= KPIs Estilizadas ======= */
      .kpi {
        background: white;
        padding: 26px 26px;
        border-radius: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.10);
        border-left: 7px solid var(--accent);
        margin-bottom: 20px;
      }
      .kpi h3 {
        margin:0;
        font-size:22px;
        font-weight:800;
        color: var(--accent-dark);
      }
      .kpi span {
        font-size:38px;
        font-weight:900;
        color: var(--text);
        display:block;
        margin-top:10px;
      }

      /* ======= Abas Modernas (brancas, sem fundo cinza) ======= */
      .stTabs button {
        background: white !important;
        border: 2px solid #e3d7ff !important;
        border-radius: 14px !important;
        padding: 12px 20px !important;
        margin-right: 12px !important;
        margin-bottom: 14px !important;
        font-weight:700 !important;
        color: var(--accent-dark) !important;
        box-shadow: 0 3px 8px rgba(0,0,0,0.07) !important;
      }

      .stTabs button:hover {
        border-color: var(--accent) !important;
        box-shadow: 0 5px 12px rgba(0,0,0,0.12) !important;
      }

      /* ======= Botões gerais ======= */
      .stButton>button {
        background: var(--accent) !important;
        color: white !important;
        padding: 12px 26px !important;
        border-radius: 12px !important;
        font-size:16px !important;
        font-weight:700 !important;
        margin-top:10px;
      }

      /* ======= Responsividade ======= */
      @media (max-width: 768px) {
        .kpi span { font-size:32px; }
        .kpi h3 { font-size:20px; }
        .stTabs button { font-size:15px !important; width:100%; text-align:center; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================
# Funções auxiliares
# =============================
def format_moeda(valor):
    try:
        return f"R$ {int(valor):,}".replace(",", ".")
    except:
        return valor

# =============================
# Carregar arquivo direto do Google Drive
# =============================
def carregar_planilha(url):
    file_id = re.findall(r"/d/(.*?)/", url)[0]
    download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
    resposta = requests.get(download_url)
    file = BytesIO(resposta.content)
    return pd.read_excel(file)

# =============================
# Interface
# =============================
st.title("📦 Painel Loja Importados — Tema Roxo Moderno")

url_planilha = st.text_input("URL da planilha do Google Drive:")

if url_planilha:
    try:
        df = carregar_planilha(url_planilha)
        st.success("Planilha carregada com sucesso!")
    except:
        st.error("Erro ao carregar. Verifique o link e se o arquivo está público.")
        st.stop()

    # =============================
    # KPIs
    # =============================
    col1, col2, col3 = st.columns(3)

    with col1:
        total_itens = len(df)
        st.markdown(f"<div class='kpi'><h3>Total de Registros</h3><span>{total_itens}</span></div>", unsafe_allow_html=True)

    with col2:
        if "VALOR VENDIDO" in df.columns:
            total_vendas = df["VALOR VENDIDO"].sum()
            st.markdown(f"<div class='kpi'><h3>Total Vendido</h3><span>{format_moeda(total_vendas)}</span></div>", unsafe_allow_html=True)

    with col3:
        if "CUSTO" in df.columns:
            total_custo = df["CUSTO"].sum()
            st.markdown(f"<div class='kpi'><h3>Total em Custos</h3><span>{format_moeda(total_custo)}</span></div>", unsafe_allow_html=True)

    # =============================
    # Abas (bonitas e modernas)
    # =============================
    aba1, aba2 = st.tabs(["📊 Gráficos", "📄 Tabela"])

    with aba1:
        if "DATA" in df.columns:
            df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")
            df_mes = df.groupby(df["DATA"].dt.to_period("M")).size().reset_index(name="Qtd")

            fig = px.bar(
                df_mes,
                x="DATA",
                y="Qtd",
                title="Movimentação por Mês",
                color_discrete_sequence=["#8b5cf6"],
            )
            fig.update_layout(margin=dict(t=40, b=30))
            st.plotly_chart(fig, use_container_width=True)

    with aba2:
        df_formatado = df.copy()
        for col in df_formatado.columns:
            if "VALOR" in col.upper() or "CUSTO" in col.upper():
                df_formatado[col] = df_formatado[col].apply(format_moeda)

        st.dataframe(df_formatado, use_container_width=True)

else:
    st.info("Insira o link da planilha para continuar.")
