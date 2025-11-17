# app.py — Dashboard Loja Importados (Dark Roxo Final)
# 100% funcional — Tabelas Dark, Pizza Top5, Sem erros de cache, Planilha carregando certo.

import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime
import requests
from io import BytesIO

# ----------------------------
# CONFIGURAÇÃO DA PÁGINA
# ----------------------------
st.set_page_config(
    page_title="Loja Importados – Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed"
)

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b/export?format=xlsx"

# ----------------------------
# CSS DARK COMPLETO
# ----------------------------
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
body, .stApp { background: var(--bg) !important; color:#f0f0f0 !important; font-family: Inter, system-ui; }

/* Tabelas DARK 100% */
.stDataFrame, .stTable, .dataframe { background: var(--table-bg) !important; color: #f0f0f0 !important; }
.stDataFrame thead th, .dataframe thead th {
    background: var(--table-head) !important; color:#fff !important; font-weight:700 !important;
}
.stDataFrame tbody tr td, .dataframe tbody tr td {
    background: var(--table-row) !important; color:#eaeaea !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 8px; height:8px; }
::-webkit-scrollbar-track { background:#111; }
::-webkit-scrollbar-thumb { background:#333; }

/* KPIs / Estética */
.topbar { display:flex; gap:12px; margin-bottom:8px; align-items:center; }
.logo-wrap { width:44px; height:44px; display:flex; align-items:center; justify-content:center;
  border-radius:10px; background: linear-gradient(135deg,var(--accent),var(--accent-2));
}
.title { font-size:20px; font-weight:800; color:var(--accent-2); }
.subtitle { font-size:12px; color:var(--muted); margin-top:2px; }

.kpi-row { display:flex; gap:10px; flex-wrap:wrap; margin-bottom:20px; }
.kpi { background:var(--card-bg); border-radius:10px; padding:10px 14px; border-left:6px solid var(--accent); }
.kpi h3 { margin:0; font-size:12px; color:var(--accent-2); font-weight:800; }
.kpi .value { margin-top:6px; font-size:20px; font-weight:900; }

.stTabs button {
    background:#1e1e1e !important; border:1px solid #333 !important;
    border-radius:12px !important; padding:8px 14px !important; margin-right:8px !important;
    color:var(--accent-2) !important; font-weight:700 !important;
}
</style>
""", unsafe_allow_html=True)


# ----------------------------
# TOP BAR
# ----------------------------
st.markdown("""
<div class="topbar">
  <div class="logo-wrap">
    <svg viewBox="0 0 24 24" fill="none"><rect x="3" y="3" width="18" height="18"
    rx="4" fill="white" fill-opacity="0.06"/>
    <path d="M7 9h10l-1 6H8L7 9z" stroke="white" stroke-width="1.2"/>
    <path d="M9 6l2-2 2 2" stroke="white" stroke-width="1.2"/></svg>
  </div>
  <div>
    <div class="title">Loja Importados — Dashboard</div>
    <div class="subtitle">Visão rápida de vendas e estoque</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ----------------------------
# FUNÇÕES AUXILIARES
# ----------------------------
def parse_money(x):
    s = str(x)
    s = re.sub(r"[^\d\.,-]", "", s)
    if "." in s and "," in s: s = s.replace(".", "").replace(",", ".")
    elif "," in s: s = s.replace(",", ".")
    try: return float(s)
    except: return 0.0

def parse_money_series(s):
    return s.astype(str).map(parse_money)

def parse_int_series(s):
    return s.astype(str).str.replace(r"\D", "", regex=True).replace("", 0).astype(int)

def formatar(v):
    try: v = float(v)
    except: return "R$ 0"
    return "R$ " + f"{v:,.0f}".replace(",", ".")
    

# ----------------------------
# CARREGAR PLANILHA — sem erro de cache
# ----------------------------
def carregar_planilha(url):
    r = requests.get(url)
    r.raise_for_status()
    return BytesIO(r.content)  # <— sem retornar ExcelFile (evita erro)

try:
    buffer = carregar_planilha(URL_PLANILHA)
    xls = pd.ExcelFile(buffer)
except Exception as e:
    st.error("Erro ao carregar planilha.")
    st.exception(e)
    st.stop()


# ----------------------------
# LER ABAS
# ----------------------------
dfs = {}
for aba in ["ESTOQUE", "VENDAS", "COMPRAS"]:
    if aba in xls.sheet_names:
        dfs[aba] = pd.read_excel(xls, sheet_name=aba)


# ----------------------------
# TRATAMENTO — ESTOQUE
# ----------------------------
if "ESTOQUE" in dfs:
    e = dfs["ESTOQUE"].copy()
    e.columns = e.columns.str.strip()

    if "Media C. UNITARIO" in e: e["Media C. UNITARIO"] = parse_money_series(e["Media C. UNITARIO"])
    if "Valor Venda Sugerido" in e: e["Valor Venda Sugerido"] = parse_money_series(e["Valor Venda Sugerido"])
    if "EM ESTOQUE" in e: e["EM ESTOQUE"] = parse_int_series(e["EM ESTOQUE"])

else:
    e = pd.DataFrame()


# ----------------------------
# TRATAMENTO — VENDAS
# ----------------------------
if "VENDAS" in dfs:
    v = dfs["VENDAS"].copy()
    v.columns = v.columns.str.strip()

    for col in ["VALOR VENDA", "VALOR TOTAL", "MEDIA CUSTO UNITARIO", "LUCRO UNITARIO"]:
        if col in v:
            v[col] = parse_money_series(v[col])

    if "QTD" in v: v["QTD"] = parse_int_series(v["QTD"])

    if "DATA" in v:
        v["DATA"] = pd.to_datetime(v["DATA"], errors="coerce")
        v["MES_ANO"] = v["DATA"].dt.strftime("%Y-%m")

else:
    v = pd.DataFrame()


# ----------------------------
# TRATAMENTO — COMPRAS
# ----------------------------
if "COMPRAS" in dfs:
    c = dfs["COMPRAS"].copy()
    c.columns = c.columns.str.strip()

    if "QUANTIDADE" in c:
        c["QUANTIDADE"] = parse_int_series(c["QUANTIDADE"])

    for col in c.columns:
        if "CUSTO" in col.upper():
            c[col] = parse_money_series(c[col])

else:
    c = pd.DataFrame()


# ----------------------------
# KPIs ESTOQUE
# ----------------------------
if not e.empty:
    valor_custo = (e["Media C. UNITARIO"] * e["EM ESTOQUE"]).sum()
    valor_venda = (e["Valor Venda Sugerido"] * e["EM ESTOQUE"]).sum()
    total_itens = int(e["EM ESTOQUE"].sum())
    top5 = e.sort_values("EM ESTOQUE", ascending=False).head(5)
else:
    valor_custo = valor_venda = total_itens = 0
    top5 = pd.DataFrame()


# ----------------------------
# FILTRO MÊS
# ----------------------------
meses = ["Todos"] + sorted(v.get("MES_ANO", pd.Series()).dropna().unique(), reverse=True)
mes_atual = datetime.now().strftime("%Y-%m")
index_padrao = meses.index(mes_atual) if mes_atual in meses else 0

col_f, col_k = st.columns([1, 3])

with col_f:
    mes_sel = st.selectbox("Filtrar por mês", meses, index=index_padrao)

def filtrar(df):
    if df.empty or mes_sel == "Todos":
        return df
    if "MES_ANO" not in df:
        return df
    return df[df["MES_ANO"] == mes_sel]

v_f = filtrar(v)
c_f = filtrar(c)


# ----------------------------
# KPIs GERAIS
# ----------------------------
vendas_totais = v_f.get("VALOR TOTAL", pd.Series()).sum()
lucro_total = (v_f.get("LUCRO UNITARIO", 0) * v_f.get("QTD", 0)).sum()

col_compra = [col for col in c_f.columns if "CUSTO" in col.upper()]
compras_totais = c_f[col_compra[0]].sum() if c_f.shape[0] > 0 and len(col_compra) > 0 else 0

with col_k:
    st.markdown(f"""
    <div class='kpi-row'>
      <div class='kpi'><h3>💵 Total Vendido</h3><div class='value'>{formatar(vendas_totais)}</div></div>
      <div class='kpi'><h3>🧾 Total Lucro</h3><div class='value'>{formatar(lucro_total)}</div></div>
      <div class='kpi'><h3>💸 Gastos Compras</h3><div class='value'>{formatar(compras_totais)}</div></div>

      <div class='kpi'><h3>📦 Custo Estoque</h3><div class='value'>{formatar(valor_custo)}</div></div>
      <div class='kpi'><h3>🏷️ Venda Estoque</h3><div class='value'>{formatar(valor_venda)}</div></div>
      <div class='kpi'><h3>🔢 Total Itens</h3><div class='value'>{total_itens}</div></div>
    </div>
    """, unsafe_allow_html=True)


# ----------------------------
# TOP 5 – GRÁFICO PIZZA
# ----------------------------
st.markdown("### 🥧 Top 5 itens com maior estoque")

if top5.empty:
    st.info("Nenhum item encontrado.")
else:
    fig_pie = px.pie(
        top5,
        names="PRODUTO",
        values="EM ESTOQUE",
        hole=0.35
    )
    fig_pie.update_layout(
        plot_bgcolor="#0b0b0b",
        paper_bgcolor="#0b0b0b",
        font_color="#fff"
    )
    st.plotly_chart(fig_pie, use_container_width=True)


# ----------------------------
# TABS PRINCIPAIS
# ----------------------------
t1, t2, t3, t4, t5 = st.tabs([
    "🛒 VENDAS",
    "🏆 TOP10 (VALOR)",
    "🏅 TOP10 (QTD)",
    "📦 ESTOQUE",
    "🔍 PESQUISAR"
])


# ----------------------------
# TAB 1 — VENDAS
# ----------------------------
with t1:
    st.subheader("Vendas no período")
    if v_f.empty:
        st.info("Nenhuma venda registrada.")
    else:
        st.dataframe(v_f, use_container_width=True)


# ----------------------------
# TAB 2 — TOP10 VALOR
# ----------------------------
with t2:
    st.subheader("Top 10 por valor vendido")
    if v_f.empty:
        st.info("Nada encontrado.")
    else:
        g = v_f.groupby("PRODUTO").agg(TOTAL=("VALOR TOTAL", "sum"))
        g = g.sort_values("TOTAL", ascending=False).head(10)

        fig = px.bar(g, x=g.index, y="TOTAL", color_discrete_sequence=["#8b5cf6"])
        fig.update_layout(
            plot_bgcolor="#0b0b0b",
            paper_bgcolor="#0b0b0b",
            font_color="#fff"
        )

        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(g, use_container_width=True)


# ----------------------------
# TAB 3 — TOP10 QTD
# ----------------------------
with t3:
    st.subheader("Top 10 por quantidade vendida")
    if v_f.empty:
        st.info("Nada encontrado.")
    else:
        g = v_f.groupby("PRODUTO").agg(QTD=("QTD", "sum"))
        g = g.sort_values("QTD", ascending=False).head(10)

        fig = px.bar(g, x=g.index, y="QTD", color_discrete_sequence=["#8b5cf6"])
        fig.update_layout(
            plot_bgcolor="#0b0b0b",
            paper_bgcolor="#0b0b0b",
            font_color="#fff"
        )

        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(g, use_container_width=True)


# ----------------------------
# TAB 4 — ESTOQUE
# ----------------------------
with t4:
    st.subheader("Estoque atual")
    if e.empty:
        st.info("Nenhum item no estoque.")
    else:
        st.dataframe(e, use_container_width=True)


# ----------------------------
# TAB 5 — PESQUISAR
# ----------------------------
with t5:
    st.subheader("Pesquisar produto no estoque")
    termo = st.text_input("Digite o nome ou parte dele:")
    if termo.strip():
        res = e[e["PRODUTO"].str.contains(termo, case=False, na=False)]
        if res.empty:
            st.warning("Nenhum produto encontrado.")
        else:
            st.dataframe(res, use_container_width=True)
