# app.py — Dashboard Loja Importados (Dark Roxo Minimalista) — PATCH FINAL 2025

import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime, timedelta
import requests
from io import BytesIO

st.set_page_config(page_title="Loja Importados – Dashboard", layout="wide", initial_sidebar_state="collapsed")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b/export?format=xlsx"


# ======================================================
# CSS — DARK TOTAL PARA TODAS TABELAS
# ======================================================
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

/* Tabelas dark */
.stDataFrame, .stTable, .dataframe {
    background: var(--table-bg) !important;
    color: #f0f0f0 !important;
}
.stDataFrame thead th, .dataframe thead th {
    background: var(--table-head) !important;
    color: #fff !important;
    font-weight:700 !important;
}
.stDataFrame tbody td, .dataframe tbody td {
    background: var(--table-row) !important;
    color:#eaeaea !important;
    border-bottom:1px solid rgba(255,255,255,0.08) !important;
}
</style>
""", unsafe_allow_html=True)



# ======================================================
# LOAD PLANILHA — PATCH FINAL
# ======================================================
def carregar_xlsx_from_url(url):
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return BytesIO(r.content)

try:
    xls = carregar_xlsx_from_url(URL_PLANILHA)
except Exception as e:
    st.error("Erro ao carregar planilha.")
    st.exception(e)
    st.stop()



# ======================================================
# HELPERS
# ======================================================
def parse_money_value(x):
    try:
        if pd.isna(x): return float("nan")
    except: pass
    s=str(x).strip()
    if s in ("","nan","none","-"): return float("nan")
    s=re.sub(r"[^\d\.,\-]","",s)
    if "." in s and "," in s:
        s=s.replace(".","").replace(",",".")
    else:
        if "," in s: s=s.replace(",",".")
    try: return float(s)
    except: return float("nan")

def parse_money_series(s):
    return s.astype(str).map(parse_money_value).astype(float)

def parse_int_series(s):
    def safe(x):
        try:
            if pd.isna(x): return 0
        except: pass
        x=re.sub(r"[^\d]","",str(x))
        return int(x) if x else 0
    return s.map(safe)

def formatar_reais_sem_centavos(v):
    try: v=float(v)
    except: return "R$ 0"
    return "R$ " + f"{v:,.0f}".replace(",", ".")



# ======================================================
# LER ABAS
# ======================================================
dfs = {}
for aba in ["ESTOQUE","VENDAS","COMPRAS"]:
    try:
        df = pd.read_excel(xls, sheet_name=aba)
        dfs[aba] = df
    except:
        dfs[aba] = pd.DataFrame()



# ======================================================
# TRATAMENTO ESTOQUE — BLINDADO
# ======================================================
e = dfs.get("ESTOQUE", pd.DataFrame()).copy()

if not e.empty:
    e = e.rename(columns={c:str(c).strip() for c in e.columns})

    # Tratamento blindado
    e["Media C. UNITARIO"] = parse_money_series(e.get("Media C. UNITARIO", pd.Series([0]*len(e))))
    e["Valor Venda Sugerido"] = parse_money_series(e.get("Valor Venda Sugerido", pd.Series([0]*len(e))))
    e["EM ESTOQUE"] = parse_int_series(e.get("EM ESTOQUE", pd.Series([0]*len(e))))

dfs["ESTOQUE"] = e



# ======================================================
# TRATAMENTO VENDAS
# ======================================================
v = dfs.get("VENDAS", pd.DataFrame()).copy()
if not v.empty:
    v = v.rename(columns={c:str(c).strip() for c in v.columns})
    for col in ["VALOR VENDA","VALOR TOTAL","MEDIA CUSTO UNITARIO","LUCRO UNITARIO"]:
        if col in v:
            v[col] = parse_money_series(v[col])
    if "QTD" in v:
        v["QTD"] = parse_int_series(v["QTD"])
    if "DATA" in v:
        v["DATA"] = pd.to_datetime(v["DATA"], errors="coerce")
        v["MES_ANO"] = v["DATA"].dt.strftime("%Y-%m")
dfs["VENDAS"] = v



# ======================================================
# TRATAMENTO COMPRAS
# ======================================================
c = dfs.get("COMPRAS", pd.DataFrame()).copy()
if not c.empty:
    for col in c.columns:
        if "CUSTO" in col.upper():
            c[col] = parse_money_series(c[col])
    if "QUANTIDADE" in c:
        c["QUANTIDADE"] = parse_int_series(c["QUANTIDADE"])
dfs["COMPRAS"] = c



# ======================================================
# KPIs ESTOQUE — BLINDADO
# ======================================================
media_custo = e.get("Media C. UNITARIO", pd.Series([0]*len(e))).fillna(0)
venda_sugerida = e.get("Valor Venda Sugerido", pd.Series([0]*len(e))).fillna(0)
estoque_qtd = e.get("EM ESTOQUE", pd.Series([0]*len(e))).fillna(0)

valor_custo = (media_custo * estoque_qtd).sum()
valor_venda = (venda_sugerida * estoque_qtd).sum()
total_itens = int(estoque_qtd.sum())

top5 = e.sort_values("EM ESTOQUE", ascending=False).head(5)



# ======================================================
# FILTRO MÊS
# ======================================================
meses = ["Todos"] + sorted(v.get("MES_ANO", pd.Series()).dropna().unique(), reverse=True)
mes_atual = datetime.now().strftime("%Y-%m")
index_padrao = meses.index(mes_atual) if mes_atual in meses else 0

col_f, col_k = st.columns([1,3])
with col_f:
    mes_sel = st.selectbox("Filtrar por mês:", meses, index=index_padrao)

def filtrar(df):
    if df.empty or mes_sel=="Todos": return df
    return df[df.get("MES_ANO") == mes_sel]

v_f = filtrar(v)
c_f = filtrar(c)



# ======================================================
# KPIs GERAIS
# ======================================================
total_vendido = v_f.get("VALOR TOTAL", pd.Series([0])).sum()
total_lucro = (v_f.get("LUCRO UNITARIO",0) * v_f.get("QTD",0)).sum()

if not c_f.empty:
    col_custo = [x for x in c_f.columns if "CUSTO" in x.upper()]
    total_compras = c_f[col_custo[0]].sum() if col_custo else 0
else:
    total_compras = 0


# Exibição
with col_k:
    st.metric("💵 Total Vendido", formatar_reais_sem_centavos(total_vendido))
    st.metric("🧾 Total Lucro", formatar_reais_sem_centavos(total_lucro))
    st.metric("💸 Total Compras", formatar_reais_sem_centavos(total_compras))
    st.metric("📦 Custo Estoque", formatar_reais_sem_centavos(valor_custo))
    st.metric("🏷️ Venda Estoque", formatar_reais_sem_centavos(valor_venda))
    st.metric("🔢 Total Itens", total_itens)



# ======================================================
# TOP 5 — GRÁFICO DE PIZZA
# ======================================================
st.subheader("🥧 Top 5 itens com maior estoque")
if top5.empty:
    st.info("Sem dados.")
else:
    fig = px.pie(top5, names="PRODUTO", values="EM ESTOQUE", hole=0.35)
    fig.update_layout(paper_bgcolor="#0b0b0b", plot_bgcolor="#0b0b0b", font_color="#fff")
    st.plotly_chart(fig, use_container_width=True)



# ======================================================
# TABS
# ======================================================
t1, t2, t3, t4 = st.tabs(["🛒 VENDAS", "🏆 TOP10 (VALOR)", "🏅 TOP10 (QTD)", "📦 ESTOQUE"])


with t1:
    st.subheader("Vendas — período filtrado")
    st.dataframe(v_f, use_container_width=True)


with t2:
    st.subheader("Top 10 por Valor")
    if v_f.empty:
        st.info("Sem dados.")
    else:
        g = v_f.groupby("PRODUTO")["VALOR TOTAL"].sum().sort_values(ascending=False).head(10)
        fig2 = px.bar(g, x=g.index, y=g.values, color_discrete_sequence=["#8b5cf6"])
        fig2.update_layout(paper_bgcolor="#0b0b0b", font_color="#fff")
        st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(g, use_container_width=True)


with t3:
    st.subheader("Top 10 por Quantidade")
    if v_f.empty:
        st.info("Sem dados.")
    else:
        g = v_f.groupby("PRODUTO")["QTD"].sum().sort_values(ascending=False).head(10)
        fig3 = px.bar(g, x=g.index, y=g.values, color_discrete_sequence=["#8b5cf6"])
        fig3.update_layout(paper_bgcolor="#0b0b0b", font_color="#fff")
        st.plotly_chart(fig3, use_container_width=True)
        st.dataframe(g, use_container_width=True)


with t4:
    st.subheader("Estoque Completo")
    st.dataframe(e, use_container_width=True)
