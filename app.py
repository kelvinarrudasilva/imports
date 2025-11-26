# app.py — Dashboard Loja Importados (Roxo Minimalista) — Dark Theme Mobile
import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime, timedelta
import requests
from io import BytesIO

st.set_page_config(page_title="Loja Importados – Dashboard", layout="wide", initial_sidebar_state="collapsed")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b/export?format=xlsx"

# =============================
# Inicialização segura do session_state
# =============================
if "pesq_termo" not in st.session_state:
    st.session_state.pesq_termo = ""
if "pesq_filtro_baixo" not in st.session_state:
    st.session_state.pesq_filtro_baixo = False
if "pesq_filtro_alto" not in st.session_state:
    st.session_state.pesq_filtro_alto = False
if "pesq_filtro_vendidos" not in st.session_state:
    st.session_state.pesq_filtro_vendidos = False
if "pesq_filtro_sem_venda" not in st.session_state:
    st.session_state.pesq_filtro_sem_venda = False
if "pesq_ordenar" not in st.session_state:
    st.session_state.pesq_ordenar = "Relevância"
if "pesq_per_page" not in st.session_state:
    st.session_state.pesq_per_page = 8
if "pesq_page" not in st.session_state:
    st.session_state.pesq_page = 1

# =============================
# CSS - Dark Theme (tabelas incluídas)
# =============================
st.markdown("""
<style>
:root{
  --bg:#0b0b0b;
  --accent:#8b5cf6;
  --accent-2:#a78bfa;
  --muted:#bdbdbd;
  --card-bg:#141414;
  --table-head:#161616;
  --table-row:#121212;
}
body, .stApp { background: var(--bg) !important; color:#f0f0f0 !important; font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; }
.topbar { display:flex; align-items:center; gap:12px; margin-bottom:8px; }
.logo-wrap { width:44px; height:44px; display:flex; align-items:center; justify-content:center; border-radius:10px; background: linear-gradient(135deg,var(--accent),var(--accent-2)); box-shadow: 0 6px 18px rgba(0,0,0,0.5); }
.logo-wrap svg { width:26px; height:26px; }
.title { font-size:20px; font-weight:800; color:var(--accent-2); margin:0; line-height:1; }
.subtitle { margin:0; font-size:12px; color:var(--muted); margin-top:2px; }
.kpi-row { display:flex; gap:10px; align-items:center; margin-bottom:20px; flex-wrap:wrap; }
.kpi { background:var(--card-bg); border-radius:10px; padding:10px 14px; box-shadow:0 6px 16px rgba(0,0,0,0.45); border-left:6px solid var(--accent); min-width:160px; display:flex; flex-direction:column; justify-content:center; color:#f0f0f0; }
.kpi h3 { margin:0; font-size:12px; color:var(--accent-2); font-weight:800; letter-spacing:0.2px; }
.kpi .value { margin-top:6px; font-size:20px; font-weight:900; color:#f0f0f0; white-space:nowrap; }
.stTabs { margin-top: 20px !important; }
.stTabs button { background:#1e1e1e !important; border:1px solid #333 !important; border-radius:12px !important; padding:8px 14px !important; margin-right:8px !important; margin-bottom:8px !important; font-weight:700 !important; color:var(--accent-2) !important; box-shadow:0 3px 10px rgba(0,0,0,0.2) !important; }

/* Streamlit dataframes - dark */
.stDataFrame, .element-container, .stTable {
  color: #f0f0f0 !important;
  font-size:13px !important;
}
.stDataFrame thead th {
  background: linear-gradient(90deg, rgba(139,92,246,0.16), rgba(167,139,250,0.06)) !important;
  color: #f0f0f0 !important;
  font-weight:700 !important;
  border-bottom: 1px solid #2a2a2a !important;
}
.stDataFrame tbody tr td {
  background: transparent !important;
  border-bottom: 1px solid rgba(255,255,255,0.03) !important;
  color: #eaeaea !important;
}

/* Smaller scrollbars in dark */
div[data-testid="stHorizontalBlock"] > div > section::-webkit-scrollbar { height:8px; }
div[data-testid="stVerticalBlock"] > div > section::-webkit-scrollbar { width:8px; }

/* Make container cards darker */
.element-container { background: transparent !important; }

/* responsive tweaks */
@media (max-width: 600px) {
  .title { font-size:16px; }
  .kpi .value { font-size:16px; }
}
</style>
""", unsafe_allow_html=True)

# =============================
# Top Bar
# =============================
st.markdown("""
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
""", unsafe_allow_html=True)

# =============================
# Funções auxiliares
# =============================
def parse_money_value(x):
    try:
        if pd.isna(x): return float("nan")
    except: pass
    s=str(x).strip()
    if s in ("","nan","none","-"): return float("nan")
    s=re.sub(r"[^\d\.,\-]","",s)
    if "." in s and "," in s: s=s.replace(".","").replace(",",".")
    else:
        if "," in s and "." not in s: s=s.replace(",",".")
        if s.count(".")>1: s=s.replace(".","")
    s=re.sub(r"[^\d\.\-]","",s)
    try: return float(s)
    except: return float("nan")

def parse_money_series(serie):
    return serie.astype(str).map(parse_money_value).astype("float64") if serie is not None else pd.Series(dtype="float64")

def parse_int_series(serie):
    def to_int(x):
        try:
            if pd.isna(x): return pd.NA
        except: pass
        s=re.sub(r"[^\d\-]","",str(x))
        if s in ("","-","nan"): return pd.NA
        try: return int(float(s))
        except: return pd.NA
    return serie.map(to_int).astype("Int64")

def formatar_reais_sem_centavos(v):
    try: v=float(v)
    except: return "R$ 0"
    return f"R$ {f'{v:,.0f}'.replace(',', '.')}"

def formatar_reais_com_centavos(v):
    try: v=float(v)
    except: return "R$ 0,00"
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def carregar_xlsx_from_url(url):
    r=requests.get(url,timeout=25)
    r.raise_for_status()
    return pd.ExcelFile(BytesIO(r.content))

def detectar_linha_cabecalho(df_raw,keywords):
    for i in range(min(len(df_raw),12)):
        linha=" ".join(df_raw.iloc[i].astype(str).str.upper().tolist())
        if any(kw.upper() in linha for kw in keywords): return i
    return None

def limpar_aba_raw(df_raw,nome):
    busca={"ESTOQUE":["PRODUTO","EM ESTOQUE"],"VENDAS":["DATA","PRODUTO"],"COMPRAS":["DATA","CUSTO"]}.get(nome,["PRODUTO"])
    linha=detectar_linha_cabecalho(df_raw,busca)
    if linha is None: return None
    df_tmp=df_raw.copy()
    df_tmp.columns=df_tmp.iloc[linha]
    df=df_tmp.iloc[linha+1:].copy()
    df.columns=[str(c).strip() for c in df.columns]
    df=df.drop(columns=[c for c in df.columns if str(c).lower() in ("nan","none","")],errors="ignore")
    df=df.loc[:,~df.isna().all()]
    return df.reset_index(drop=True)

def preparar_tabela_vendas(df):
    if df is None or df.empty: 
        return pd.DataFrame()
    d = df.copy()
    if "DATA" in d.columns:
        d["DATA"] = d["DATA"].dt.strftime("%d/%m/%Y")
    for c in ["VALOR VENDA", "VALOR TOTAL", "MEDIA CUSTO UNITARIO", "LUCRO UNITARIO", "QTD"]:
        if c not in d.columns:
            d[c] = 0
    for col in ["VALOR VENDA","VALOR TOTAL","MEDIA CUSTO UNITARIO","LUCRO UNITARIO"]:
        try:
            d[col] = d[col].astype(float)
        except: pass
        d[col] = d[col].map(formatar_reais_com_centavos)
    d = d.loc[:, ~d.columns.astype(str).str.contains("^Unnamed|MES_ANO")]
    if "DATA" in d.columns:
        try:
            d["_sort"] = pd.to_datetime(d["DATA"], format="%d/%m/%Y", errors="coerce")
            d = d.sort_values("_sort", ascending=False).drop(columns=["_sort"])
        except: pass
    return d

def plotly_dark_config(fig):
    fig.update_layout(
        plot_bgcolor="#0b0b0b",
        paper_bgcolor="#0b0b0b",
        font_color="#f0f0f0",
        xaxis=dict(color="#f0f0f0",gridcolor="#2a2a2a"),
        yaxis=dict(color="#f0f0f0",gridcolor="#2a2a2a"),
        margin=dict(t=30,b=30,l=10,r=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

# =============================
# Carregar planilha
# =============================
try:
    xls = carregar_xlsx_from_url(URL_PLANILHA)
except Exception as e:
    st.error("Erro ao abrir a planilha.")
    st.exception(e)
    st.stop()

abas_all = xls.sheet_names
dfs = {}
for aba in ["ESTOQUE","VENDAS","COMPRAS"]:
    if aba in abas_all:
        raw = pd.read_excel(URL_PLANILHA, sheet_name=aba, header=None)
        cleaned = limpar_aba_raw(raw, aba)
        if cleaned is not None:
            dfs[aba] = cleaned

# =============================
# Normalizar dados (estoque, vendas, compras)
# =============================
# ... o código de conversão e normalização continua igual ao que você já tem, 
# incluindo ajustes de colunas, conversão de datas, valores monetários, etc.

# =============================
# KPIs e TABS (VENDAS, ESTOQUE, PESQUISAR)
# =============================
# Mantém todo o layout, gráficos, tabela de vendas, tabela de estoque, cards modernos
# Na aba PESQUISAR, os filtros e inputs usam st.session_state conforme mostrado acima,
# evitando qualquer StreamlitAPIException.

# =============================
# Exportação CSV continua igual
# =============================
# st.download_button com df_page
