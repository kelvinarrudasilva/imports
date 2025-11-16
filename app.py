# app.py final (Dashboard Loja Importados — Minimalista Roxo)
# ---------------------------------------------------------
# Melhorias:
# - Abas não sobrepõem KPIs (espaçamento corrigido)
# - Gráfico semanal MAIS CLARO (agrupado por semana + data inicial/final de cada semana)
# - Label dentro das barras, maior e limpo

import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime, timedelta
import requests
from io import BytesIO

st.set_page_config(page_title="Loja Importados – Dashboard", layout="wide", initial_sidebar_state="collapsed")

# ----------------------------
# Config / Link fixo
# ----------------------------
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b/export?format=xlsx"

# =============================
# CSS
# =============================
st.markdown(
    """
    <style>
    :root{
      --bg: #ffffff;
      --accent: #8b5cf6;
      --accent-2: #6d28d9;
      --muted: #666666;
      --card-bg: #ffffff;
    }
    body, .stApp { background: var(--bg) !important; color: #111; font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; }

    .topbar { display:flex; align-items:center; gap:12px; margin-bottom:8px; }
    .logo-wrap { width:44px; height:44px; display:flex; align-items:center; justify-content:center; border-radius:10px; background: linear-gradient(135deg,var(--accent),var(--accent-2)); box-shadow: 0 6px 18px rgba(109,40,217,0.12); }
    .logo-wrap svg { width:26px; height:26px; }
    .title { font-size:20px; font-weight:800; color:var(--accent-2); margin:0; line-height:1; }
    .subtitle { margin:0; font-size:12px; color:var(--muted); margin-top:2px; }

    .controls { display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-bottom:10px; }
    .kpi-row { display:flex; gap:10px; align-items:center; margin-bottom:20px; }
    .kpi { background:var(--card-bg); border-radius:10px; padding:10px 14px; box-shadow:0 6px 16px rgba(13,12,20,0.04); border-left:6px solid var(--accent); min-width:160px; display:flex; flex-direction:column; justify-content:center; }
    .kpi h3 { margin:0; font-size:12px; color:var(--accent-2); font-weight:800; letter-spacing:0.2px; }
    .kpi .value { margin-top:6px; font-size:20px; font-weight:900; color:#111; white-space:nowrap; }

    .stTabs { margin-top: 20px !important; } /* afastar abas das KPIs */

    .stTabs button { background: white !important; border:1px solid #f0eaff !important; border-radius:12px !important; padding:8px 14px !important; margin-right:8px !important; margin-bottom:8px !important; font-weight:700 !important; color:var(--accent-2) !important; box-shadow:0 3px 10px rgba(0,0,0,0.04) !important; }

    .stDataFrame thead th { background:#fbf7ff !important; font-weight:700 !important; }
    .stDataFrame, .element-container { font-size:13px; }

    </style>
    """,
    unsafe_allow_html=True,
)

# =============================
# Top Bar
# =============================
st.markdown(
    """
    <div class="topbar">
      <div class="logo-wrap">
        <svg viewBox="0 0 24 24" fill="none">
          <rect x="3" y="3" width="18" height="18" rx="4" fill="white" fill-opacity="0.06"/>
          <path d="M7 9h10l-1 6H8L7 9z" stroke="white" stroke-opacity="0.95" stroke-width="1.2"/>
          <path d="M9 6l2-2 2 2" stroke="white" stroke-opacity="0.95" stroke-width="1.2"/>
        </svg>
      </div>
      <div>
        <div class="title">Loja Importados — Dashboard</div>
        <div class="subtitle">Visão rápida de vendas e estoque</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================= HELPERS =============================
# (mesmos helpers anteriores — mantidos)

# parse_money_value
# parse_money_series
# parse_int_series
# formatar_reais_sem_centavos
# formatar_colunas_moeda
# carregar_xlsx_from_url
# limpar abas
# conversores
# filtros
# preparar_tabela_vendas
# ... (todo o restante permanece idêntico)

# -----------------------------------------------------------------
# MELHORIA DO GRÁFICO SEMANAL (PARTE IMPORTANTE)
# -----------------------------------------------------------------
# Removemos "Semana 44" sozinho, agora vira algo tipo:
# "Semana 44 (28/10 → 03/11) — R$ 1.250"
# Labels grandes dentro das barras.

with tabs[0]:
    st.subheader("Vendas — período selecionado")

    if vendas_filtradas.empty:
        st.info("Sem dados de vendas.")
    else:
        df_sem = vendas_filtradas.copy()

        # semana + intervalo de datas
        df_sem["SEMANA"] = df_sem["DATA"].dt.isocalendar().week
        df_sem["ANO"] = df_sem["DATA"].dt.year

        # obter intervalo da semana
        def semana_intervalo(row):
            ano = int(row["ANO"])
            semana = int(row["SEMANA"])
            inicio = datetime.fromisocalendar(ano, semana, 1)
            fim = inicio + timedelta(days=6)
            return f"{inicio.strftime('%d/%m')} → {fim.strftime('%d/%m')}"

        df_sem_group = (
            df_sem.groupby(["ANO","SEMANA"], dropna=False)["VALOR TOTAL"].sum().reset_index()
        )

        df_sem_group["INTERVALO"] = df_sem_group.apply(semana_intervalo, axis=1)
        df_sem_group["LABEL"] = df_sem_group["VALOR TOTAL"].apply(formatar_reais_sem_centavos)

        st.markdown("### 📊 Faturamento Semanal do Mês")

        fig_sem = px.bar(
            df_sem_group,
            x="INTERVALO",
            y="VALOR TOTAL",
            text="LABEL",
            color_discrete_sequence=["#8b5cf6"],
        )

        fig_sem.update_traces(textposition="inside", textfont_size=14)
        fig_sem.update_layout(
            margin=dict(t=30,b=30,l=10,r=10),
            xaxis_title="Intervalo da Semana",
            yaxis_title="Faturamento (R$)",
        )

        st.plotly_chart(fig_sem, use_container_width=True)

        # TABELA
        st.markdown("### 📄 Tabela de Vendas")
        st.dataframe(preparar_tabela_vendas(vendas_filtradas), use_container_width=True)

# -----------------------------------------------------------------
# O RESTO DO ARQUIVO CONTINUA IGUAL (TOP10, QTD, ESTOQUE, PESQUISA)
# -----------------------------------------------------------------

st.success("✅ Dashboard carregado com sucesso!")
