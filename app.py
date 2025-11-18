# ================================================
# app.py — Versão FINAL 100% compatível com sua planilha
# -----------------------------------------------
# - Detecta automaticamente a linha do cabeçalho
# - Remove Unnamed sem erros
# - Detecta DATA mesmo se vier com nomes diferentes
# - Top 5 Geral (QTD e VALOR)
# - Sem abas TOP10
# - Layout 3 confirmado
# ================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime, timedelta
import requests
from io import BytesIO

st.set_page_config(page_title="Loja Importados – Dashboard", layout="wide")

# -----------------------------
# CONFIG
# -----------------------------
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b/export?format=xlsx"

# -----------------------------
# CSS
# -----------------------------
st.markdown("""
<style>
:root{
  --bg:#0b0b0b; --card:#141414; --accent:#8b5cf6; --accent2:#a78bfa; --text:#f2f2f2;
}
body, .stApp { background:var(--bg) !important; color:var(--text) !important; }
.kpi-box{ background:var(--card); padding:14px; border-radius:12px; border-left:5px solid var(--accent); box-shadow:0 5px 14px rgba(0,0,0,0.35); }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# HELPERS
# -----------------------------
def baixar_xlsx(url):
    r = requests.get(url, timeout=25)
    r.raise_for_status()
    return BytesIO(r.content)

def detectar_header(df_raw, keywords=None):
    if keywords is None:
        keywords = ["DATA", "PRODUTO", "QTD"]

    for i in range(min(12, len(df_raw))):
        linha = " ".join(str(x).upper().strip() for x in df_raw.iloc[i].tolist())
        if any(kw in linha for kw in keywords):
            return i

    return 1  # fallback seguro (a sua planilha usa linha 2 = índice 1)

def limpar_header(df_raw):
    header_idx = detectar_header(df_raw, ["DATA", "PRODUTO", "QTD", "VENDA", "VALOR"])
    cols = df_raw.iloc[header_idx].fillna("").astype(str).str.strip()

    df = df_raw.iloc[header_idx + 1:].copy().reset_index(drop=True)
    df.columns = cols

    # remover Unnamed de forma segura
    df = df.loc[:, [c for c in df.columns if c.strip() != "" and not c.upper().startswith("UNNAMED")]]

    return df

def limpar_moeda(x):
    if pd.isna(x): return 0
    s = str(x).replace("R$","").replace(".","").replace(",",".")
    s = re.sub(r"[^0-9.\-]", "", s)
    try: return float(s)
    except: return 0

def formatar(v):
    try: v = float(v)
    except: return "R$ 0"
    return f"R$ {v:,.0f}".replace(",", ".")

def dark(fig):
    fig.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b", font_color="#f2f2f2")
    return fig

def detectar_col(df, palavras):
    for c in df.columns:
        nome = c.upper().replace(" ", "")
        for p in palavras:
            if p.upper().replace(" ", "") in nome:
                return c
    return None

def detectar_col_data_por_conteudo(df):
    for c in df.columns:
        try:
            if pd.to_datetime(df[c], errors="coerce").notna().sum() > 0:
                return c
        except:
            pass
    return None

# -----------------------------
# CARREGAR PLANILHA
# -----------------------------
try:
    file = baixar_xlsx(URL_PLANILHA)
    xls = pd.ExcelFile(file)
except:
    st.error("Erro ao carregar a planilha.")
    st.stop()

# -----------------------------
# LIMPAR ABAS
# -----------------------------
def carregar_aba(nome):
    if nome not in xls.sheet_names:
        return pd.DataFrame()
    raw = pd.read_excel(file, sheet_name=nome, header=None)
    return limpar_header(raw)

vendas = carregar_aba("VENDAS")
compras = carregar_aba("COMPRAS")
estoque = carregar_aba("ESTOQUE")

# -----------------------------
# NORMALIZAR VENDAS
# -----------------------------
# DATA
col_data = detectar_col(vendas, ["DATA", "DIA", "DT"])
if not col_data:
    col_data = detectar_col_data_por_conteudo(vendas)

if col_data:
    vendas = vendas.rename(columns={col_data: "DATA"})
else:
    vendas["DATA"] = pd.NaT

vendas["DATA"] = pd.to_datetime(vendas["DATA"], errors="coerce")

# PRODUTO
col_prod = detectar_col(vendas, ["PRODUTO", "ITEM", "NOME", "DESC"])
if col_prod:
    vendas = vendas.rename(columns={col_prod: "PRODUTO"})
else:
    vendas["PRODUTO"] = "SEM_PRODUTO"

# QTD
col_qtd = detectar_col(vendas, ["QTD", "QUANT"])
if col_qtd:
    vendas = vendas.rename(columns={col_qtd: "QTD"})
    vendas["QTD"] = pd.to_numeric(vendas["QTD"], errors="coerce").fillna(0).astype(int)
else:
    vendas["QTD"] = 0

# VALORES
col_total = detectar_col(vendas, ["VALOR TOTAL", "TOTAL", "VALORTOTAL"])
col_unit = detectar_col(vendas, ["VALOR VENDA", "PRECO", "UNIT", "VENDA"])

if col_total:
    vendas = vendas.rename(columns={col_total: "VALOR TOTAL"})
    vendas["VALOR TOTAL"] = vendas["VALOR TOTAL"].map(limpar_moeda)
elif col_unit:
    vendas = vendas.rename(columns={col_unit: "VALOR VENDA"})
    vendas["VALOR VENDA"] = vendas["VALOR VENDA"].map(limpar_moeda)
    vendas["VALOR TOTAL"] = vendas["VALOR VENDA"] * vendas["QTD"]
else:
    vendas["VALOR TOTAL"] = 0.0

# MES_ANO
vendas["MES_ANO"] = vendas["DATA"].dt.strftime("%Y-%m")

# -----------------------------
# NORMALIZAR COMPRAS
# -----------------------------
if not compras.empty:

    col_d = detectar_col(compras, ["DATA"])
    if col_d:
        compras = compras.rename(columns={col_d: "DATA"})
        compras["DATA"] = pd.to_datetime(compras["DATA"], errors="coerce")

    col_q = detectar_col(compras, ["QTD", "QUANT"])
    if col_q:
        compras = compras.rename(columns={col_q: "QTD"})
        compras["QTD"] = pd.to_numeric(compras["QTD"], errors="coerce").fillna(0).astype(int)
    else:
        compras["QTD"] = 0

    col_c = detectar_col(compras, ["CUSTO", "VALOR", "PRECO"])
    if col_c:
        compras = compras.rename(columns={col_c: "CUSTO"})
        compras["CUSTO"] = compras["CUSTO"].map(limpar_moeda)
    else:
        compras["CUSTO"] = 0

    compras["CUSTO TOTAL"] = compras["QTD"] * compras["CUSTO"]

    compras["MES_ANO"] = compras["DATA"].dt.strftime("%Y-%m")

# -----------------------------
# NORMALIZAR ESTOQUE
# -----------------------------
if not estoque.empty:

    col_p = detectar_col(estoque, ["PRODUTO", "ITEM", "NOME"])
    if col_p:
        estoque = estoque.rename(columns={col_p: "PRODUTO"})

    col_qe = detectar_col(estoque, ["EM ESTOQUE", "ESTOQUE"])
    if col_qe:
        estoque = estoque.rename(columns={col_qe: "EM_ESTOQUE"})
        estoque["EM_ESTOQUE"] = pd.to_numeric(estoque["EM_ESTOQUE"], errors="coerce").fillna(0).astype(int)
    else:
        estoque["EM_ESTOQUE"] = 0

    col_ce = detectar_col(estoque, ["CUSTO", "MEDIA"])
    if col_ce:
        estoque = estoque.rename(columns={col_ce: "CUSTO_UNIT"})
        estoque["CUSTO_UNIT"] = estoque["CUSTO_UNIT"].map(limpar_moeda)
    else:
        estoque["CUSTO_UNIT"] = 0

    col_ve = detectar_col(estoque, ["VENDA", "SUGERIDO", "PRECO"])
    if col_ve:
        estoque = estoque.rename(columns={col_ve: "PRECO_VENDA"})
        estoque["PRECO_VENDA"] = estoque["PRECO_VENDA"].map(limpar_moeda)
    else:
        estoque["PRECO_VENDA"] = 0

    estoque["VALOR_CUSTO_TOTAL"] = estoque["CUSTO_UNIT"] * estoque["EM_ESTOQUE"]
    estoque["VALOR_VENDA_TOTAL"] = estoque["PRECO_VENDA"] * estoque["EM_ESTOQUE"]

# -----------------------------
# FILTRO MÊS
# -----------------------------
meses = ["Todos"] + sorted(vendas["MES_ANO"].dropna().unique().tolist(), reverse=True)
mes_atual = datetime.now().strftime("%Y-%m")
idx = meses.index(mes_atual) if mes_atual in meses else 0
mes = st.selectbox("Filtrar por mês:", meses, index=idx)

def filtrar(df):
    if df.empty or mes == "Todos": return df
    return df[df["MES_ANO"] == mes]

vendas_f = filtrar(vendas)
compras_f = filtrar(compras)

# -----------------------------
# KPIs
# -----------------------------
k_vendas = vendas_f["VALOR TOTAL"].sum()
k_qtd = vendas_f["QTD"].sum()
k_compras = compras_f["CUSTO TOTAL"].sum() if not compras_f.empty else 0
k_est_venda = estoque["VALOR_VENDA_TOTAL"].sum() if not estoque.empty else 0
k_est_custo = estoque["VALOR_CUSTO_TOTAL"].sum() if not estoque.empty else 0

c1,c2,c3,c4,c5 = st.columns(5)
c1.markdown(f"<div class='kpi-box'><h4>💵 Vendas</h4><h2>{formatar(k_vendas)}</h2></div>", unsafe_allow_html=True)
c2.markdown(f"<div class='kpi-box'><h4>📦 Quantidade</h4><h2>{k_qtd}</h2></div>", unsafe_allow_html=True)
c3.markdown(f"<div class='kpi-box'><h4>💸 Compras</h4><h2>{formatar(k_compras)}</h2></div>", unsafe_allow_html=True)
c4.markdown(f"<div class='kpi-box'><h4>🏷 Estoque Venda</h4><h2>{formatar(k_est_venda)}</h2></div>", unsafe_allow_html=True)
c5.markdown(f"<div class='kpi-box'><h4>📥 Estoque Custo</h4><h2>{formatar(k_est_custo)}</h2></div>", unsafe_allow_html=True)

# -----------------------------
# ABAS
# -----------------------------
tab1, tab2, tab3 = st.tabs(["🛒 VENDAS", "📦 ESTOQUE", "🔍 PESQUISAR"])

# -------------------------------------------------
# 🛒 ABA VENDAS — LAYOUT 3
# -------------------------------------------------
with tab1:

    # 🔥 Top5 por Quantidade (GERAL)
    st.subheader("🔥 Top 5 Produtos Mais Vendidos — Quantidade (Geral)")
    top5_qtd = vendas.groupby("PRODUTO", dropna=False)["QTD"].sum().reset_index().sort_values("QTD", ascending=False).head(5)

    if not top5_qtd.empty:
        fig = px.bar(top5_qtd, x="QTD", y="PRODUTO", orientation="h", text="QTD",
                     color_discrete_sequence=["#8b5cf6"], height=360)
        fig.update_traces(textposition="inside")
        st.plotly_chart(dark(fig), use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Nenhum dado disponível para Top 5 (Quantidade).")

    st.markdown("---")

    # 💰 Top5 por Valor (GERAL)
    st.subheader("💰 Top 5 Produtos Mais Vendidos — Valor (Geral)")
    top5_val = vendas.groupby("PRODUTO", dropna=False)["VALOR TOTAL"].sum().reset_index().sort_values("VALOR TOTAL", ascending=False).head(5)

    if not top5_val.empty:
        top5_val["LABEL"] = top5_val["VALOR TOTAL"].apply(formatar)
        fig2 = px.bar(top5_val, x="VALOR TOTAL", y="PRODUTO", orientation="h", text="LABEL",
                      color_discrete_sequence=["#8b5cf6"], height=360)
        fig2.update_traces(textposition="inside")
        st.plotly_chart(dark(fig2), use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Nenhum dado disponível para Top 5 (Valor).")

    st.markdown("---")

    # 📅 FATURAMENTO SEMANAL (MÊS SELECIONADO)
    st.subheader("📅 Faturamento Semanal — Mês Selecionado")
    df = vendas_f.dropna(subset=["DATA"])

    if not df.empty:
        df["SEMANA"] = df["DATA"].dt.isocalendar().week
        df["ANO"] = df["DATA"].dt.year

        sem = df.groupby(["ANO","SEMANA"])["VALOR TOTAL"].sum().reset_index()

        def intervalo(r):
            try:
                ini = datetime.fromisocalendar(int(r["ANO"]), int(r["SEMANA"]), 1)
                fim = ini + timedelta(days=6)
                return f"{ini.strftime('%d/%m')} → {fim.strftime('%d/%m')}"
            except:
                return "N/A"

        sem["INTERVALO"] = sem.apply(intervalo, axis=1)
        sem["LABEL"] = sem["VALOR TOTAL"].apply(formatar)

        fig3 = px.bar(sem, x="INTERVALO", y="VALOR TOTAL", text="LABEL",
                       color_discrete_sequence=["#8b5cf6"], height=360)
        fig3.update_traces(textposition="inside")
        st.plotly_chart(dark(fig3), use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Sem dados para gerar o gráfico semanal.")

    st.markdown("---")

    # 📄 Tabela do Mês
    st.subheader("📄 Tabela de Vendas — Mês Selecionado")
    if vendas_f.empty:
        st.info("Nenhuma venda no mês selecionado.")
    else:
        cols_show = [c for c in ["DATA","PRODUTO","QTD","VALOR VENDA","VALOR TOTAL"] if c in vendas_f.columns]
        st.dataframe(vendas_f[cols_show].sort_values("DATA", ascending=False).reset_index(drop=True), 
                     use_container_width=True)

# -------------------------------------------------
# 📦 ABA ESTOQUE
# -------------------------------------------------
with tab2:
    st.subheader("📦 Estoque Atual")
    if estoque.empty:
        st.info("Nenhum item no estoque.")
    else:
        st.dataframe(estoque, use_container_width=True)

# -------------------------------------------------
# 🔍 ABA PESQUISAR
# -------------------------------------------------
with tab3:
    st.subheader("🔍 Pesquisar no Estoque")
    termo = st.text_input("Digite parte do nome:")
    if termo:
        res = estoque[estoque["PRODUTO"].astype(str).str.contains(termo, case=False, na=False)]
        st.dataframe(res if not res.empty else pd.DataFrame(), use_container_width=True)
