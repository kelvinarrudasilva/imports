# ============================================
#  app.py — Dashboard Loja Importados (v. HOME IA)
#  Kelvin Edition — Dark Purple Vision
# ============================================

import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime, timedelta
import numpy as np
import requests
from io import BytesIO

# -------------------------------------------------
# CONFIG INICIAL
# -------------------------------------------------
st.set_page_config(
    page_title="Loja Importados – Dashboard IA",
    layout="wide",
    initial_sidebar_state="collapsed"
)

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b/export?format=xlsx"

# -------------------------------------------------
# CSS — Dark Theme
# -------------------------------------------------
st.markdown("""
<style>
:root {
  --bg: #0b0b0b;
  --accent: #8b5cf6;
  --accent-2: #a78bfa;
  --muted: #bdbdbd;
  --card-bg: #141414;
}
body, .stApp { background: var(--bg) !important; color: #f0f0f0 !important; }

/* KPIs */
.kpi-row { display:flex; gap:12px; flex-wrap:wrap; margin-top:20px; }
.kpi {
  background: var(--card-bg); padding:14px 18px; border-radius:12px;
  box-shadow:0 6px 16px rgba(0,0,0,0.45); border-left:6px solid var(--accent);
  min-width:170px;
}
.kpi h3 { margin:0; font-size:12px; color:var(--accent-2); }
.kpi .value { margin-top:6px; font-size:22px; font-weight:900; }

/* TABS */
.stTabs button {
  background:#1e1e1e !important; border:1px solid #333 !important;
  border-radius:12px !important; padding:8px 14px !important;
  font-weight:700 !important; color:var(--accent-2) !important;
  margin-right:8px !important;
}

/* Dataframe */
.dataframe, .stDataFrame { color:white !important; }
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------
# FUNÇÕES AUXILIARES
# -------------------------------------------------
def parse_money_value(x):
    try:
        if pd.isna(x): return float("nan")
    except: pass
    s = str(x).strip()
    s = re.sub(r"[^\d\.,\-]", "", s)
    if "." in s and "," in s: s = s.replace(".","").replace(",",".")
    else:
        if "," in s: s = s.replace(",",".")
    try: return float(s)
    except: return float("nan")

def parse_money_series(s):
    return s.astype(str).map(parse_money_value)

def formatar_reais_com_centavos(v):
    try: v=float(v)
    except: return "R$ 0,00"
    s=f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def formatar_reais_sem_centavos(v):
    try: v=float(v)
    except: return "R$ 0"
    s=f"{v:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def carregar_xlsx_from_url(url):
    r=requests.get(url, timeout=25)
    r.raise_for_status()
    return pd.ExcelFile(BytesIO(r.content))

def detectar_linha_cabecalho(df_raw, keywords):
    for i in range(12):
        linha = " ".join(df_raw.iloc[i].astype(str).str.upper().tolist())
        if any(k.upper() in linha for k in keywords):
            return i
    return None

def limpar_aba_raw(df_raw, nome):
    busca = {"ESTOQUE":["PRODUTO","ESTOQUE"],"VENDAS":["DATA","PRODUTO"],"COMPRAS":["DATA","CUSTO"]}.get(nome,["PRODUTO"])
    linha = detectar_linha_cabecalho(df_raw, busca)
    if linha is None: return None
    tmp = df_raw.copy()
    tmp.columns = tmp.iloc[linha]
    df = tmp.iloc[linha+1:].copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.astype(str).str.contains("Unnamed")]
    return df.reset_index(drop=True)

# -------------------------------------------------
# CARREGAR PLANILHA
# -------------------------------------------------
try:
    xls = carregar_xlsx_from_url(URL_PLANILHA)
except:
    st.error("Não foi possível carregar a planilha.")
    st.stop()

abas = xls.sheet_names
dfs = {}

for aba in ["ESTOQUE","VENDAS","COMPRAS"]:
    if aba in abas:
        raw = pd.read_excel(URL_PLANILHA, sheet_name=aba, header=None)
        dfs[aba] = limpar_aba_raw(raw, aba)

# -------------------------------------------------
# AJUSTAR ESTOQUE
# -------------------------------------------------
if "ESTOQUE" in dfs and dfs["ESTOQUE"] is not None:
    df_e = dfs["ESTOQUE"].copy()

    # Normalização
    col_map = {
        "Media C. UNITARIO": ["Media C. UNITARIO","MEDIA CUSTO UNITARIO","CUSTO"],
        "Valor Venda Sugerido": ["Valor Venda Sugerido","VALOR VENDA","VENDA"],
        "EM ESTOQUE": ["EM ESTOQUE","ESTOQUE","QTD"]
    }

    for target, opts in col_map.items():
        for op in opts:
            if op in df_e.columns:
                df_e[target] = parse_money_series(df_e[op]) if "VALOR" in target.upper() or "C." in target else df_e[op].astype(int)
                break

    if "PRODUTO" not in df_e.columns:
        df_e.rename(columns={df_e.columns[0]:"PRODUTO"}, inplace=True)

    # cálculos totais
    df_e["VALOR_CUSTO_TOTAL"] = df_e["Media C. UNITARIO"] * df_e["EM ESTOQUE"]
    df_e["VALOR_VENDA_TOTAL"] = df_e["Valor Venda Sugerido"] * df_e["EM ESTOQUE"]

    dfs["ESTOQUE"] = df_e

# -------------------------------------------------
# AJUSTAR VENDAS
# -------------------------------------------------
if "VENDAS" in dfs and dfs["VENDAS"] is not None:
    df_v = dfs["VENDAS"].copy()

    colmap = {
        "VALOR VENDA":["VALOR VENDA","VALOR_VENDA"],
        "VALOR TOTAL":["VALOR TOTAL","VALOR_TOTAL"],
        "MEDIA CUSTO UNITARIO":["MEDIA CUSTO UNITARIO","MEDIA C. UNITARIO"],
        "LUCRO UNITARIO":["LUCRO UNITARIO","LUCRO_UNITARIO"],
        "QTD":["QTD","QUANTIDADE"]
    }

    for t,opts in colmap.items():
        for op in opts:
            if op in df_v.columns:
                if "VALOR" in t or "CUSTO" in t or "LUCRO" in t:
                    df_v[t] = parse_money_series(df_v[op])
                else:
                    df_v[t] = pd.to_numeric(df_v[op], errors="coerce").fillna(0).astype(int)
                break

    if "DATA" in df_v.columns:
        df_v["DATA"] = pd.to_datetime(df_v["DATA"], errors="coerce")
        df_v["MES_ANO"] = df_v["DATA"].dt.strftime("%Y-%m")

    if "VALOR TOTAL" not in df_v.columns:
        df_v["VALOR TOTAL"] = df_v["VALOR VENDA"] * df_v["QTD"]

    if "LUCRO UNITARIO" in df_v.columns:
        df_v["LUCRO TOTAL"] = df_v["LUCRO UNITARIO"] * df_v["QTD"]

    df_v = df_v.sort_values("DATA", ascending=False)

    dfs["VENDAS"] = df_v

# -------------------------------------------------
# CRIAR PÁGINA INICIAL (IA + GRÁFICOS)
# -------------------------------------------------
st.title("📊 Painel Geral — Inteligência Comercial")

df_v = dfs.get("VENDAS", pd.DataFrame())

if not df_v.empty:

    colA, colB, colC = st.columns(3)

    total_vendido = df_v["VALOR TOTAL"].sum()
    total_lucro = df_v.get("LUCRO TOTAL", pd.Series()).sum()
    vendas_qtd = df_v["QTD"].sum()

    with colA:
        st.markdown(f"""
        <div class='kpi'><h3>Total Vendido</h3>
        <div class='value'>{formatar_reais_sem_centavos(total_vendido)}</div></div>
        """, unsafe_allow_html=True)

    with colB:
        st.markdown(f"""
        <div class='kpi'><h3>Lucro Total</h3>
        <div class='value'>{formatar_reais_sem_centavos(total_lucro)}</div></div>
        """, unsafe_allow_html=True)

    with colC:
        st.markdown(f"""
        <div class='kpi'><h3>Itens Vendidos</h3>
        <div class='value'>{vendas_qtd}</div></div>
        """, unsafe_allow_html=True)

    # ===============================
    st.markdown("## 📈 Faturamento — últimos 12 meses")
    df_m = df_v.copy()
    df_m["MES"] = df_m["DATA"].dt.to_period("M")
    df_m_sum = df_m.groupby("MES")["VALOR TOTAL"].sum().reset_index()
    df_m_sum["MES"] = df_m_sum["MES"].astype(str)

    fig = px.line(df_m_sum, x="MES", y="VALOR TOTAL")
    fig.update_layout(paper_bgcolor="#0b0b0b", plot_bgcolor="#0b0b0b", font_color="white")
    st.plotly_chart(fig, use_container_width=True)

    # ===============================
    st.markdown("## 💡 Insight Automático (IA)")

    # IA ANALÍTICA SIMPLES
    tendencia = ""
    if len(df_m_sum) >= 3:
        ult3 = df_m_sum["VALOR TOTAL"].tail(3).tolist()
        if ult3[2] > ult3[1] > ult3[0]:
            tendencia = "📈 Seu faturamento está em clara tendência de alta. Bom ritmo!"
        elif ult3[2] < ult3[1] < ult3[0]:
            tendencia = "📉 Faturamento em queda contínua — vale revisar campanhas e estoque."
        else:
            tendencia = "⚖️ Variação mista — o mercado está oscilando. Acompanhe de perto."

    st.info(tendencia)

    # ===============================
    st.markdown("## 🔮 Previsão Simples — Próximos 30 dias")

    try:
        # regressão linear simples
        Y = df_m_sum["VALOR TOTAL"].values
        X = np.arange(len(Y))
        coef = np.polyfit(X, Y, 1)
        prox = coef[0] * (len(Y)+1) + coef[1]
        prox = max(0, prox)

        st.success(f"📌 Faturamento previsto para o próximo período: **{formatar_reais_com_centavos(prox)}**")
    except:
        st.warning("Dados insuficientes para previsão.")

# -------------------------------------------------
# TABS
# -------------------------------------------------
tabs = st.tabs(["📄 VENDAS","📦 ESTOQUE","🔍 BUSCA"])

# -------------------------------------------------
# ABA VENDAS
# -------------------------------------------------
with tabs[0]:
    st.subheader("Tabela de Vendas (com Lucro Total formatado)")
    if df_v.empty:
        st.info("Sem dados.")
    else:
        df_temp = df_v.copy()
        df_temp["DATA"] = df_temp["DATA"].dt.strftime("%d/%m/%Y")
        df_temp["VALOR VENDA"] = df_temp["VALOR VENDA"].map(formatar_reais_com_centavos)
        df_temp["VALOR TOTAL"] = df_temp["VALOR TOTAL"].map(formatar_reais_com_centavos)
        df_temp["MEDIA CUSTO UNITARIO"] = df_temp["MEDIA CUSTO UNITARIO"].map(formatar_reais_com_centavos)
        df_temp["LUCRO UNITARIO"] = df_temp["LUCRO UNITARIO"].map(formatar_reais_com_centavos)
        df_temp["LUCRO TOTAL"] = df_temp["LUCRO TOTAL"].map(formatar_reais_com_centavos)
        st.dataframe(df_temp, use_container_width=True)

# -------------------------------------------------
# ABA ESTOQUE
# -------------------------------------------------
with tabs[1]:
    df_e = dfs.get("ESTOQUE", pd.DataFrame())
    st.subheader("Estoque")
    if df_e.empty:
        st.info("Sem dados.")
    else:
        df_temp = df_e.copy()
        df_temp["CUSTO"] = df_temp["Media C. UNITARIO"].map(formatar_reais_com_centavos)
        df_temp["VENDA"] = df_temp["Valor Venda Sugerido"].map(formatar_reais_com_centavos)
        df_temp["VALOR_CUSTO_TOTAL"] = df_temp["VALOR_CUSTO_TOTAL"].map(formatar_reais_com_centavos)
        df_temp["VALOR_VENDA_TOTAL"] = df_temp["VALOR_VENDA_TOTAL"].map(formatar_reais_com_centavos)
        st.dataframe(df_temp, use_container_width=True)

# -------------------------------------------------
# ABA BUSCA
# -------------------------------------------------
with tabs[2]:
    termo = st.text_input("Buscar produto:")
    if termo:
        df_e = dfs.get("ESTOQUE", pd.DataFrame())
        df_s = df_e[df_e["PRODUTO"].str.contains(termo, case=False, na=False)]
        st.dataframe(df_s, use_container_width=True)
