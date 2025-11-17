# app.py — Dashboard Loja Importados (Roxo Minimalista) — Dark Theme Mobile
# COMPLETO — Tabelas totalmente dark + Top 5 em gráfico de pizza

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
# CSS — DARK COMPLETO (tabelas 100% escuras)
# =============================
st.markdown("""
<style>
:root{
  --bg:#0b0b0b;
  --accent:#8b5cf6;
  --accent-2:#a78bfa;
  --muted:#bdbdbd;
  --card-bg:#141414;
  --table-bg:#111;
  --table-head:#202020;
  --table-row:#181818;
}
body, .stApp { background: var(--bg) !important; color:#f0f0f0 !important; font-family: Inter, system-ui, -apple-system; }

/* Tabelas completamente escuras */
.stDataFrame, .stTable, .dataframe {
    background: var(--table-bg) !important;
    color: #f0f0f0 !important;
}

.stDataFrame thead th, .dataframe thead th {
    background: var(--table-head) !important;
    color: #fff !important;
    font-weight:700 !important;
    border-bottom:1px solid #333 !important;
}

.stDataFrame tbody tr td, .dataframe tbody tr td {
    background: var(--table-row) !important;
    color:#eaeaea !important;
    border-bottom:1px solid rgba(255,255,255,0.06) !important;
}

/* Scrollbars escuros */
::-webkit-scrollbar { width: 8px; height:8px; }
::-webkit-scrollbar-track { background:#111; }
::-webkit-scrollbar-thumb { background:#333; border-radius:10px; }

/* KPIs / Estética geral */
.topbar { display:flex; gap:12px; margin-bottom:8px; align-items:center; }
.logo-wrap { width:44px; height:44px; display:flex; align-items:center; justify-content:center; border-radius:10px; background: linear-gradient(135deg,var(--accent),var(--accent-2)); box-shadow:0 6px 18px rgba(0,0,0,0.5); }
.logo-wrap svg { width:26px; height:26px; }
.title { font-size:20px; font-weight:800; color:var(--accent-2); margin:0; }
.subtitle { font-size:12px; color:var(--muted); margin:0; margin-top:2px; }
.kpi-row { display:flex; gap:10px; flex-wrap:wrap; margin-bottom:20px; }
.kpi { background:var(--card-bg); border-radius:10px; padding:10px 14px; box-shadow:0 6px 16px rgba(0,0,0,0.45); border-left:6px solid var(--accent); min-width:160px; }
.kpi h3 { margin:0; font-size:12px; color:var(--accent-2); font-weight:800; }
.kpi .value { margin-top:6px; font-size:20px; font-weight:900; }
.stTabs button { background:#1e1e1e !important; border:1px solid #333 !important; border-radius:12px !important; padding:8px 14px !important; margin-right:8px !important; color:var(--accent-2) !important; font-weight:700 !important; }
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
# Helper functions
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

def parse_money_series(s):
    return s.astype(str).map(parse_money_value).astype(float)

def parse_int_series(s):
    def conv(x):
        try:
            if pd.isna(x): return 0
        except: pass
        s=re.sub(r"[^\d]","",str(x))
        if s=="": return 0
        try: return int(s)
        except: return 0
    return s.map(conv)

def formatar_reais_sem_centavos(v):
    try: v=float(v)
    except: return "R$ 0"
    return f"R$ {f'{v:,.0f}'.replace(',','.')}"

# =============================
# Carregar Planilha
# =============================
def carregar_xlsx_from_url(url):
    r=requests.get(url, timeout=30)
    r.raise_for_status()
    return pd.ExcelFile(BytesIO(r.content))

try:
    xls = carregar_xlsx_from_url(URL_PLANILHA)
except Exception as e:
    st.error("Erro ao carregar planilha.")
    st.exception(e)
    st.stop()

# =============================
# Ler Abas
# =============================
dfs = {}
for aba in ["ESTOQUE","VENDAS","COMPRAS"]:
    if aba in xls.sheet_names:
        df = pd.read_excel(URL_PLANILHA, sheet_name=aba)
        dfs[aba] = df

# =============================
# Tratamento Estoque
# =============================
if "ESTOQUE" in dfs:
    e = dfs["ESTOQUE"].copy()
    e = e.rename(columns={c:str(c).strip() for c in e.columns})

    if "Media C. UNITARIO" in e: e["Media C. UNITARIO"] = parse_money_series(e["Media C. UNITARIO"]).fillna(0)
    if "Valor Venda Sugerido" in e: e["Valor Venda Sugerido"] = parse_money_series(e["Valor Venda Sugerido"]).fillna(0)
    if "EM ESTOQUE" in e: e["EM ESTOQUE"] = parse_int_series(e["EM ESTOQUE"]).fillna(0)

    dfs["ESTOQUE"] = e
else:
    e = pd.DataFrame()

# =============================
# Tratamento Vendas
# =============================
if "VENDAS" in dfs:
    v = dfs["VENDAS"].copy()
    v = v.rename(columns={c:str(c).strip() for c in v.columns})

    for col in ["VALOR VENDA","VALOR TOTAL","MEDIA CUSTO UNITARIO","LUCRO UNITARIO"]:
        if col in v: v[col] = parse_money_series(v[col])

    if "QTD" in v: v["QTD"] = parse_int_series(v["QTD"]).fillna(0)

    if "DATA" in v:
        v["DATA"]=pd.to_datetime(v["DATA"],errors="coerce")
        v["MES_ANO"] = v["DATA"].dt.strftime("%Y-%m")

    dfs["VENDAS"] = v
else:
    v = pd.DataFrame()

# =============================
# Tratamento Compras
# =============================
if "COMPRAS" in dfs:
    c = dfs["COMPRAS"].copy()
    if "QUANTIDADE" in c: c["QUANTIDADE"] = parse_int_series(c["QUANTIDADE"]).fillna(0)
    for col in c.columns:
        if "CUSTO" in col.upper():
            c[col] = parse_money_series(c[col]).fillna(0)
    dfs["COMPRAS"] = c
else:
    c = pd.DataFrame()

# =============================
# KPIs de Estoque (NÃO afetados pelo filtro)
# =============================
if not e.empty:
    valor_custo = (e["Media C. UNITARIO"] * e["EM ESTOQUE"]).sum()
    valor_venda = (e["Valor Venda Sugerido"] * e["EM ESTOQUE"]).sum()
    total_itens = int(e["EM ESTOQUE"].sum())
    top5 = e.sort_values("EM ESTOQUE", ascending=False).head(5)
else:
    valor_custo = valor_venda = total_itens = 0
    top5 = pd.DataFrame()

# =============================
# Filtro Mês (VENDAS/COMPRAS)
# =============================
meses = ["Todos"] + sorted(v.get("MES_ANO", pd.Series()).dropna().unique(), reverse=True)
atual = datetime.now().strftime("%Y-%m")
index_pad = meses.index(atual) if atual in meses else 0

col_f, col_k = st.columns([1,3])

with col_f:
    mes_sel = st.selectbox("Filtrar por mês", meses, index=index_pad)

def filtrar(df):
    if df is None or df.empty or mes_sel=="Todos": return df
    if "MES_ANO" not in df: return df
    return df[df["MES_ANO"]==mes_sel]

v_f = filtrar(v)
c_f = filtrar(c)

# =============================
# KPIs Gerais
# =============================
vend = v_f.get("VALOR TOTAL", pd.Series()).fillna(0).sum()
lucro = ((v_f.get("LUCRO UNITARIO",0)*v_f.get("QTD",0))).sum()
compr = c_f.get(c_f.columns[c_f.columns.str.contains("CUSTO")][0], pd.Series()).sum() if not c_f.empty else 0

with col_k:
    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi"><h3>💵 Total Vendido</h3><div class="value">{formatar_reais_sem_centavos(vend)}</div></div>
      <div class="kpi" style="border-left-color:#34d399;"><h3>🧾 Total Lucro</h3><div class="value">{formatar_reais_sem_centavos(lucro)}</div></div>
      <div class="kpi" style="border-left-color:#f59e0b;"><h3>💸 Total Compras</h3><div class="value">{formatar_reais_sem_centavos(compr)}</div></div>

      <div class="kpi" style="border-left-color:#8b5cf6;"><h3>📦 Custo Estoque</h3><div class="value">{formatar_reais_sem_centavos(valor_custo)}</div></div>
      <div class="kpi" style="border-left-color:#a78bfa;"><h3>🏷️ Venda Estoque</h3><div class="value">{formatar_reais_sem_centavos(valor_venda)}</div></div>
      <div class="kpi" style="border-left-color:#6ee7b7;"><h3>🔢 Total Itens</h3><div class="value">{total_itens}</div></div>
    </div>
    """, unsafe_allow_html=True)

# =============================
# TOP 5 — Pizza Colorida
# =============================
st.markdown("### 🥧 Top 5 Itens com mais estoque")
if top5.empty:
    st.info("Nenhum dado.")
else:
    fig_pie = px.pie(top5, names="PRODUTO", values="EM ESTOQUE", hole=0.35)
    fig_pie.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b", font_color="#fff")
    st.plotly_chart(fig_pie, use_container_width=True)

# =============================
# TABS — VENDAS / TOP10 / ESTOQUE / PESQUISA
# =============================
t1, t2, t3, t4, t5 = st.tabs(["🛒 VENDAS","🏆 TOP10 (VALOR)","🏅 TOP10 (QTD)","📦 ESTOQUE","🔍 PESQUISAR"])

with t1:
    st.subheader("Vendas — período selecionado")
    if v_f.empty:
        st.info("Sem dados.")
    else:
        st.dataframe(v_f, use_container_width=True)

with t2:
    st.subheader("Top 10 por Valor")
    if v_f.empty:
        st.info("Sem dados.")
    else:
        g = v_f.groupby("PRODUTO").agg(TOTAL=("VALOR TOTAL","sum"))\
                .sort_values("TOTAL", ascending=False).head(10)
        fig = px.bar(g, x=g.index, y="TOTAL", color_discrete_sequence=["#8b5cf6"])
        fig.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b", font_color="#fff")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(g, use_container_width=True)

with t3:
    st.subheader("Top 10 por Quantidade")
    if v_f.empty:
        st.info("Sem dados.")
    else:
        g = v_f.groupby("PRODUTO").agg(QTD=("QTD","sum"))\
                .sort_values("QTD", ascending=False).head(10)
        fig = px.bar(g, x=g.index, y="QTD", color_discrete_sequence=["#8b5cf6"])
        fig.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b", font_color="#fff")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(g, use_container_width=True)

with t4:
    st.subheader("Estoque Atual")
    if e.empty:
        st.info("Sem estoque.")
    else:
        st.dataframe(e, use_container_width=True)

with t5:
    st.subheader("Pesquisar produto")
    txt = st.text_input("Digite parte do nome")
    if txt.strip():
        r = e[e["PRODUTO"].str.contains(txt, case=False, na=False)]
        if r.empty:
            st.warning("Nenhum encontrado.")
        else:
            st.dataframe(r, use_container_width=True)
