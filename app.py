# app.py — Dashboard Loja Importados (Roxo Minimalista) — Corrigido (conversões seguras)
# Versão: correção de astype + homepage com gráficos e insights leves (IA)
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import re
from datetime import datetime, timedelta
import requests
from io import BytesIO

st.set_page_config(page_title="Loja Importados – Dashboard IA", layout="wide", initial_sidebar_state="collapsed")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b/export?format=xlsx"

# ----------------------------
# CSS - Dark Theme
# ----------------------------
st.markdown("""
<style>
:root{
  --bg:#0b0b0b;
  --accent:#8b5cf6;
  --accent-2:#a78bfa;
  --muted:#bdbdbd;
  --card-bg:#141414;
}
body, .stApp { background: var(--bg) !important; color:#f0f0f0 !important; font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; }
.topbar { display:flex; align-items:center; gap:12px; margin-bottom:8px; }
.logo-wrap { width:44px; height:44px; display:flex; align-items:center; justify-content:center; border-radius:10px; background: linear-gradient(135deg,var(--accent),var(--accent-2)); box-shadow: 0 6px 18px rgba(0,0,0,0.5); }
.title { font-size:20px; font-weight:800; color:var(--accent-2); margin:0; line-height:1; }
.subtitle { margin:0; font-size:12px; color:var(--muted); margin-top:2px; }
.kpi-row { display:flex; gap:10px; align-items:center; margin-bottom:20px; flex-wrap:wrap; }
.kpi { background:var(--card-bg); border-radius:10px; padding:10px 14px; box-shadow:0 6px 16px rgba(0,0,0,0.45); border-left:6px solid var(--accent); min-width:160px; display:flex; flex-direction:column; justify-content:center; color:#f0f0f0; }
.kpi h3 { margin:0; font-size:12px; color:var(--accent-2); font-weight:800; letter-spacing:0.2px; }
.kpi .value { margin-top:6px; font-size:20px; font-weight:900; color:#f0f0f0; white-space:nowrap; }
.stTabs { margin-top: 20px !important; }
.stTabs button { background:#1e1e1e !important; border:1px solid #333 !important; border-radius:12px !important; padding:8px 14px !important; margin-right:8px !important; margin-bottom:8px !important; font-weight:700 !important; color:var(--accent-2) !important; box-shadow:0 3px 10px rgba(0,0,0,0.2) !important; }
.stDataFrame, .element-container, .stTable { color: #f0f0f0 !important; font-size:13px !important; }
.stDataFrame thead th { background: linear-gradient(90deg, rgba(139,92,246,0.16), rgba(167,139,250,0.06)) !important; color: #f0f0f0 !important; font-weight:700 !important; border-bottom: 1px solid #2a2a2a !important; }
.stDataFrame tbody tr td { background: transparent !important; border-bottom: 1px solid rgba(255,255,255,0.03) !important; color: #eaeaea !important; }
@media (max-width: 600px) { .title { font-size:16px; } .kpi .value { font-size:16px; } }
</style>
""", unsafe_allow_html=True)

# ----------------------------
# Top bar
# ----------------------------
st.markdown(f"""
<div class="topbar">
  <div class="logo-wrap">
    <svg viewBox="0 0 24 24" fill="none">
      <rect x="3" y="3" width="18" height="18" rx="4" fill="white" fill-opacity="0.06"/>
      <path d="M7 9h10l-1 6H8L7 9z" stroke="white" stroke-opacity="0.95" stroke-width="1.2"/>
      <path d="M9 6l2-2 2 2" stroke="white" stroke-opacity="0.95" stroke-width="1.2"/>
    </svg>
  </div>
  <div>
    <div class="title">Loja Importados — Dashboard IA</div>
    <div class="subtitle">Visão rápida: vendas, lucro, estoque e insights</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ----------------------------
# Helpers
# ----------------------------
def parse_money_value(x):
    try:
        if pd.isna(x): return np.nan
    except: pass
    s = str(x).strip()
    if s in ("","nan","none","-"): return np.nan
    s = re.sub(r"[^\d\.,\-]","",s)
    if "." in s and "," in s:
        s = s.replace(".","").replace(",",".")
    else:
        if "," in s: s = s.replace(",",".")

    s = re.sub(r"[^\d\.\-]","",s)
    try:
        return float(s)
    except:
        return np.nan

def parse_money_series(serie):
    # retorna float64, seguro contra valores sujos
    return pd.to_numeric(serie.astype(str).map(parse_money_value), errors="coerce").astype("float64")

def parse_int_safe(serie):
    return pd.to_numeric(serie.astype(str).str.replace(r"[^\d\-]","", regex=True), errors="coerce").fillna(0).astype(int)

def formatar_reais_sem_centavos(v):
    try: v=float(v)
    except: return "R$ 0"
    return f"R$ {f'{v:,.0f}'.replace(',','.')}" 

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

# ----------------------------
# Carregar planilha
# ----------------------------
try:
    xls = carregar_xlsx_from_url(URL_PLANILHA)
except Exception as e:
    st.error("Erro ao abrir a planilha.")
    st.exception(e)
    st.stop()

abas_all = xls.sheet_names
colunas_esperadas = ["ESTOQUE","VENDAS","COMPRAS"]
dfs = {}
for aba in colunas_esperadas:
    if aba in abas_all:
        raw = pd.read_excel(URL_PLANILHA, sheet_name=aba, header=None)
        cleaned = limpar_aba_raw(raw, aba)
        if cleaned is not None:
            dfs[aba] = cleaned

# ----------------------------
# Conversores e ajustes (ESTOQUE)
# ----------------------------
if "ESTOQUE" in dfs:
    df_e = dfs["ESTOQUE"].copy()

    # garantir nomes: detectar colunas variantes com segurança
    # Coluna custo médio
    if "Media C. UNITARIO" in df_e.columns:
        df_e["Media C. UNITARIO"] = parse_money_series(df_e["Media C. UNITARIO"]).fillna(0)
    else:
        for alt in ["MEDIA C. UNITARIO","MEDIA CUSTO UNITARIO","MEDIA C. UNIT","CUSTO"]:
            if alt in df_e.columns:
                df_e["Media C. UNITARIO"] = parse_money_series(df_e[alt]).fillna(0)
                break
        else:
            df_e["Media C. UNITARIO"] = 0.0

    # Coluna valor venda sugerido
    if "Valor Venda Sugerido" in df_e.columns:
        df_e["Valor Venda Sugerido"] = parse_money_series(df_e["Valor Venda Sugerido"]).fillna(0)
    else:
        for alt in ["VALOR VENDA SUGERIDO","VALOR VENDA","VALOR_VENDA","VENDA"]:
            if alt in df_e.columns:
                df_e["Valor Venda Sugerido"] = parse_money_series(df_e[alt]).fillna(0)
                break
        else:
            df_e["Valor Venda Sugerido"] = 0.0

    # Coluna quantidade em estoque - conversão segura
    if "EM ESTOQUE" in df_e.columns:
        df_e["EM ESTOQUE"] = parse_int_safe(df_e["EM ESTOQUE"]).astype(int)
    else:
        for alt in ["ESTOQUE","QTD","QUANTIDADE"]:
            if alt in df_e.columns:
                df_e["EM ESTOQUE"] = parse_int_safe(df_e[alt]).astype(int)
                break
        else:
            df_e["EM ESTOQUE"] = 0

    # Produto nome
    if "PRODUTO" not in df_e.columns:
        # tenta achar primeira coluna de texto como produto
        str_cols = [c for c in df_e.columns if df_e[c].dtype == object]
        if len(str_cols)>0:
            df_e = df_e.rename(columns={str_cols[0]:"PRODUTO"})
        else:
            df_e["PRODUTO"] = df_e.index.astype(str)

    # calcular totais
    df_e["VALOR_CUSTO_TOTAL"] = df_e["Media C. UNITARIO"].fillna(0) * df_e["EM ESTOQUE"].fillna(0)
    df_e["VALOR_VENDA_TOTAL"] = df_e["Valor Venda Sugerido"].fillna(0) * df_e["EM ESTOQUE"].fillna(0)

    dfs["ESTOQUE"] = df_e

# ----------------------------
# Conversores e ajustes (VENDAS)
# ----------------------------
if "VENDAS" in dfs:
    df_v = dfs["VENDAS"].copy()
    df_v.columns = [str(c).strip() for c in df_v.columns]

    # mapear colunas monetárias / numéricas com segurança
    money_map = {
        "VALOR VENDA":["VALOR VENDA","VALOR_VENDA","VALORVENDA","PRECO"],
        "VALOR TOTAL":["VALOR TOTAL","VALOR_TOTAL","VALORTOTAL"],
        "MEDIA CUSTO UNITARIO":["MEDIA C. UNITARIO","MEDIA CUSTO UNITARIO","MEDIA CUSTO"],
        "LUCRO UNITARIO":["LUCRO UNITARIO","LUCRO_UNITARIO"]
    }
    for target,vars_ in money_map.items():
        assigned = False
        for v in vars_:
            if v in df_v.columns:
                df_v[target] = parse_money_series(df_v[v]).fillna(0)
                assigned = True
                break
        if not assigned:
            df_v[target] = 0.0

    # qtd
    qtd_cols = [c for c in df_v.columns if c.upper() in ("QTD","QUANTIDADE","QTY","QTE")]
    if qtd_cols:
        df_v["QTD"] = parse_int_safe(df_v[qtd_cols[0]]).fillna(0).astype(int)
    else:
        df_v["QTD"] = 0

    # data
    if "DATA" in df_v.columns:
        df_v["DATA"] = pd.to_datetime(df_v["DATA"], errors="coerce")
        df_v["MES_ANO"] = df_v["DATA"].dt.strftime("%Y-%m")
    else:
        df_v["DATA"] = pd.NaT
        df_v["MES_ANO"] = pd.NA

    # garantir VALOR TOTAL
    if "VALOR TOTAL" not in df_v.columns or df_v["VALOR TOTAL"].isna().all():
        df_v["VALOR TOTAL"] = df_v["VALOR VENDA"].fillna(0) * df_v["QTD"].fillna(0)

    # lucro unitário e total
    if "LUCRO UNITARIO" not in df_v.columns or df_v["LUCRO UNITARIO"].isna().all():
        # tenta calcular: preço - custo médio unitário
        if "MEDIA CUSTO UNITARIO" in df_v.columns:
            df_v["LUCRO UNITARIO"] = df_v["VALOR VENDA"].fillna(0) - df_v["MEDIA CUSTO UNITARIO"].fillna(0)
        else:
            df_v["LUCRO UNITARIO"] = 0.0

    df_v["LUCRO TOTAL"] = (df_v["LUCRO UNITARIO"].fillna(0).astype(float) * df_v["QTD"].fillna(0).astype(float)).astype(float)

    # ordenar
    if "DATA" in df_v.columns:
        df_v = df_v.sort_values("DATA", ascending=False).reset_index(drop=True)

    dfs["VENDAS"] = df_v

# ----------------------------
# Conversores e ajustes (COMPRAS)
# ----------------------------
if "COMPRAS" in dfs:
    df_c = dfs["COMPRAS"].copy()
    # quant
    qcols=[c for c in df_c.columns if "QUANT" in c.upper()]
    if qcols:
        df_c["QUANTIDADE"] = parse_int_safe(df_c[qcols[0]]).fillna(0).astype(int)
    else:
        df_c["QUANTIDADE"] = 0
    # custo unitário
    cost_cols=[c for c in df_c.columns if any(k in c.upper() for k in ("CUSTO","UNIT"))]
    if cost_cols:
        df_c["CUSTO UNITÁRIO"] = parse_money_series(df_c[cost_cols[0]]).fillna(0)
    else:
        df_c["CUSTO UNITÁRIO"] = 0.0
    df_c["CUSTO TOTAL (RECALC)"] = df_c["QUANTIDADE"].fillna(0) * df_c["CUSTO UNITÁRIO"].fillna(0)
    if "DATA" in df_c.columns:
        df_c["DATA"] = pd.to_datetime(df_c["DATA"], errors="coerce")
        df_c["MES_ANO"] = df_c["DATA"].dt.strftime("%Y-%m")
    dfs["COMPRAS"] = df_c

# ----------------------------
# INDICADORES DE ESTOQUE (fixos)
# ----------------------------
estoque_df = dfs.get("ESTOQUE", pd.DataFrame()).copy()
if not estoque_df.empty:
    estoque_df["Media C. UNITARIO"] = estoque_df.get("Media C. UNITARIO", 0).fillna(0).astype(float)
    estoque_df["Valor Venda Sugerido"] = estoque_df.get("Valor Venda Sugerido", 0).fillna(0).astype(float)
    estoque_df["EM ESTOQUE"] = estoque_df.get("EM ESTOQUE", 0).fillna(0).astype(int)
    valor_custo_estoque = (estoque_df["Media C. UNITARIO"] * estoque_df["EM ESTOQUE"]).sum()
    valor_venda_estoque = (estoque_df["Valor Venda Sugerido"] * estoque_df["EM ESTOQUE"]).sum()
    quantidade_total_itens = int(estoque_df["EM ESTOQUE"].sum())
else:
    valor_custo_estoque = 0
    valor_venda_estoque = 0
    quantidade_total_itens = 0

# ----------------------------
# Filtro mês (aplica somente em VENDAS/COMPRAS)
# ----------------------------
meses = ["Todos"]
if "VENDAS" in dfs:
    meses += sorted(dfs["VENDAS"]["MES_ANO"].dropna().unique().tolist(), reverse=True)
mes_atual = datetime.now().strftime("%Y-%m")
index_padrao = meses.index(mes_atual) if mes_atual in meses else 0
col_filter, col_kpis = st.columns([1,3])
with col_filter:
    mes_selecionado = st.selectbox("Filtrar por mês (YYYY-MM):", meses, index=index_padrao)

def filtrar_mes_df(df,mes):
    if df is None or df.empty: return df
    if mes=="Todos": return df
    if "MES_ANO" in df.columns:
        return df[df["MES_ANO"]==mes].copy()
    return df

vendas_filtradas = filtrar_mes_df(dfs.get("VENDAS", pd.DataFrame()), mes_selecionado)
if not vendas_filtradas.empty and "DATA" in vendas_filtradas.columns:
    vendas_filtradas = vendas_filtradas.sort_values("DATA", ascending=False).reset_index(drop=True)
compras_filtradas = filtrar_mes_df(dfs.get("COMPRAS", pd.DataFrame()), mes_selecionado)

# ----------------------------
# KPIs (vendas + estoque ao lado)
# ----------------------------
total_vendido = vendas_filtradas.get("VALOR TOTAL", pd.Series()).fillna(0).sum()
total_lucro = vendas_filtradas.get("LUCRO TOTAL", pd.Series()).fillna(0).sum()
total_compras = compras_filtradas.get("CUSTO TOTAL (RECALC)", pd.Series()).fillna(0).sum()

with col_kpis:
    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi"><h3>💵 Total Vendido</h3><div class="value">{formatar_reais_sem_centavos(total_vendido)}</div></div>
      <div class="kpi" style="border-left-color:#34d399;"><h3>🧾 Total Lucro</h3><div class="value">{formatar_reais_sem_centavos(total_lucro)}</div></div>
      <div class="kpi" style="border-left-color:#f59e0b;"><h3>💸 Total Compras</h3><div class="value">{formatar_reais_sem_centavos(total_compras)}</div></div>
      <div class="kpi" style="border-left-color:#8b5cf6;"><h3>📦 Valor Custo Estoque</h3><div class="value">{formatar_reais_sem_centavos(valor_custo_estoque)}</div></div>
      <div class="kpi" style="border-left-color:#a78bfa;"><h3>🏷️ Valor Venda Estoque</h3><div class="value">{formatar_reais_sem_centavos(valor_venda_estoque)}</div></div>
      <div class="kpi" style="border-left-color:#6ee7b7;"><h3>🔢 Qtde Total Itens</h3><div class="value">{quantidade_total_itens}</div></div>
    </div>
    """, unsafe_allow_html=True)

# ----------------------------
# HOME: gráficos e insights iniciais (surpresa)
# ----------------------------
st.markdown("---")
st.header("Painel inicial — visão rápida & sinais")

if not vendas_filtradas.empty:
    # Faturamento mensal últimos 12 meses
    df_month = vendas_filtradas.copy()
    df_month = df_month.dropna(subset=["DATA"])
    df_month["MES"] = df_month["DATA"].dt.to_period("M").dt.to_timestamp()
    last_months = (df_month.groupby("MES")["VALOR TOTAL"].sum().reset_index()
                   .sort_values("MES").tail(12))
    if not last_months.empty:
        fig_rev = px.line(last_months, x="MES", y="VALOR TOTAL", markers=True)
        fig_rev.update_traces(line=dict(width=3), marker=dict(size=6))
        plotly_dark_config(fig_rev)
        st.subheader("📈 Faturamento (últimos 12 meses)")
        st.plotly_chart(fig_rev, use_container_width=True, config=dict(displayModeBar=False))

    # Lucro mensal últimos 12 meses
    last_lucro = (df_month.groupby("MES")["LUCRO TOTAL"].sum().reset_index()
                  .sort_values("MES").tail(12))
    if not last_lucro.empty:
        fig_lucro = px.line(last_lucro, x="MES", y="LUCRO TOTAL", markers=True)
        plotly_dark_config(fig_lucro)
        st.subheader("📊 Lucro (últimos 12 meses)")
        st.plotly_chart(fig_lucro, use_container_width=True, config=dict(displayModeBar=False))

    # Top produtos por lucro (horizontal)
    prod_profit = vendas_filtradas.groupby("PRODUTO", dropna=False).agg(LUCRO_TOTAL_REAL=("LUCRO TOTAL","sum"), QTD_TOTAL=("QTD","sum")).reset_index()
    top_profit = prod_profit.sort_values("LUCRO_TOTAL_REAL", ascending=False).head(8)
    if not top_profit.empty:
        top_profit["LUCRO_LABEL"] = top_profit["LUCRO_TOTAL_REAL"].map(formatar_reais_sem_centavos)
        fig_top = px.bar(top_profit, x="LUCRO_TOTAL_REAL", y="PRODUTO", orientation="h", text="LUCRO_LABEL", height=360, color_discrete_sequence=["#a78bfa"])
        plotly_dark_config(fig_top)
        fig_top.update_traces(textposition="outside")
        st.subheader("💰 Top produtos por lucro")
        st.plotly_chart(fig_top, use_container_width=True, config=dict(displayModeBar=False))

    # Sinal rápido (regra simples)
    st.markdown("### 🔔 Sinais rápidos")
    # tendência: comparar soma últimos 3 meses
    try:
        s = last_months["VALOR TOTAL"].values
        if len(s) >= 3:
            if s[-1] > s[-2] > s[-3]:
                st.success("Tendência: alta nos últimos 3 meses.")
            elif s[-1] < s[-2] < s[-3]:
                st.warning("Tendência: queda nos últimos 3 meses. Analise promoções / preço.")
            else:
                st.info("Tendência: estável / mista.")
    except Exception:
        pass

    # previsão simples: regressão linear sobre os meses (estimativa do próximo mês)
    try:
        ym = last_months.copy().reset_index(drop=True)
        ym = ym.reset_index()  # cria coluna index 0..n
        if len(ym) >= 2:
            X = ym["index"].values
            Y = ym["VALOR TOTAL"].values
            a, b = np.polyfit(X, Y, 1)
            next_idx = len(X)
            pred = a * next_idx + b
            st.markdown(f"**Previsão simples (próximo mês):** {formatar_reais_sem_centavos(max(0,pred))}")
    except Exception:
        pass
else:
    st.info("Sem dados de vendas para gerar painel inicial.")

st.markdown("---")

# ----------------------------
# TABS principais
# ----------------------------
tabs = st.tabs(["🛒 VENDAS","📦 ESTOQUE","🔍 PESQUISAR","🧠 INSIGHTS"])

# ============================
# ABA VENDAS
# ============================
with tabs[0]:
    st.subheader("Vendas — tabela (mais recentes primeiro)")
    dfv = vendas_filtradas.copy()
    if dfv.empty:
        st.info("Sem dados de vendas.")
    else:
        # preparar exibição: formatar colunas monetárias e datas
        dfv_display = dfv.copy()
        if "DATA" in dfv_display.columns:
            dfv_display["DATA"] = dfv_display["DATA"].dt.strftime("%d/%m/%Y")
        for col in ["VALOR VENDA","VALOR TOTAL","MEDIA CUSTO UNITARIO","LUCRO UNITARIO","LUCRO TOTAL"]:
            if col in dfv_display.columns:
                dfv_display[col] = dfv_display[col].fillna(0).map(formatar_reais_com_centavos)
        st.dataframe(dfv_display, use_container_width=True)

# ============================
# ABA ESTOQUE
# ============================
with tabs[1]:
    st.subheader("Estoque — visão detalhada")
    de = estoque_df.copy() if not estoque_df.empty else pd.DataFrame()
    if de.empty:
        st.info("Sem dados de estoque.")
    else:
        de_display = de.copy()
        de_display["Media C. UNITARIO"] = de_display["Media C. UNITARIO"].map(formatar_reais_com_centavos)
        de_display["Valor Venda Sugerido"] = de_display["Valor Venda Sugerido"].map(formatar_reais_com_centavos)
        de_display["VALOR_CUSTO_TOTAL"] = de_display["VALOR_CUSTO_TOTAL"].map(formatar_reais_sem_centavos)
        de_display["VALOR_VENDA_TOTAL"] = de_display["VALOR_VENDA_TOTAL"].map(formatar_reais_sem_centavos)
        st.dataframe(de_display.sort_values("EM ESTOQUE", ascending=False).reset_index(drop=True), use_container_width=True)

# ============================
# ABA PESQUISAR
# ============================
with tabs[2]:
    st.subheader("Pesquisar produtos no estoque")
    termo = st.text_input("Digite parte do nome do produto")
    if termo.strip():
        if estoque_df.empty:
            st.warning("Nenhum dado de estoque disponível.")
        else:
            df_search = estoque_df[estoque_df["PRODUTO"].str.contains(termo, case=False, na=False)]
            if df_search.empty:
                st.warning("Nenhum produto encontrado.")
            else:
                df_search_display = df_search.copy()
                df_search_display["Media C. UNITARIO"] = df_search_display["Media C. UNITARIO"].map(formatar_reais_com_centavos)
                df_search_display["Valor Venda Sugerido"] = df_search_display["Valor Venda Sugerido"].map(formatar_reais_com_centavos)
                st.dataframe(df_search_display.reset_index(drop=True), use_container_width=True)

# ============================
# ABA INSIGHTS (IA leve)
# ============================
with tabs[3]:
    st.subheader("AI Insights — previsões, alertas e recomendações")
    st.markdown("**Configurações rápidas**")
    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        lead_time_days = st.number_input("Lead time (dias)", value=7, min_value=1)
    with c2:
        safety_weeks = st.number_input("Safety stock (semanas)", value=1, min_value=0)
    with c3:
        min_order = st.number_input("Pedido mínimo (unid.)", value=5, min_value=1)

    st.markdown("### 1) Resumo automático")
    try:
        total_sales = int(vendas_filtradas["QTD"].sum()) if not vendas_filtradas.empty else 0
        total_rev = vendas_filtradas["VALOR TOTAL"].sum() if not vendas_filtradas.empty else 0
        top3 = []
        if not vendas_filtradas.empty and "PRODUTO" in vendas_filtradas.columns:
            top3 = vendas_filtradas.groupby("PRODUTO").agg(Q=("QTD","sum")).reset_index().sort_values("Q", ascending=False).head(3)["PRODUTO"].tolist()
        s = f"Total vendido: {formatar_reais_sem_centavos(total_rev)} em {total_sales} unidades."
        if top3:
            s += " Principais: " + ", ".join(top3) + "."
        st.write(s)
    except Exception as e:
        st.write("Resumo indisponível.")
        st.exception(e)

    st.markdown("### 2) Previsão rápida por top produtos (média móvel)")
    # weekly sales build
    def weekly_sales_build(df_v):
        if df_v is None or df_v.empty: return pd.DataFrame()
        tmp = df_v.dropna(subset=["DATA"]).copy()
        tmp["WEEK_START"] = tmp["DATA"].dt.to_period("W").apply(lambda r: r.start_time)
        weekly = tmp.groupby(["PRODUTO","WEEK_START"])["QTD"].sum().reset_index()
        return weekly

    weekly = weekly_sales_build(vendas_filtradas)
    if weekly.empty:
        st.info("Dados insuficientes para previsões.")
    else:
        last_n = st.slider("Semanas para média móvel", 1, 12, 4)
        top_products = vendas_filtradas.groupby("PRODUTO").agg(Q=("QTD","sum")).reset_index().sort_values("Q", ascending=False).head(5)["PRODUTO"].tolist()
        forecasts = []
        for p in top_products:
            w = weekly[weekly["PRODUTO"]==p].sort_values("WEEK_START")
            if w.empty:
                forecasts.append((p,0))
            else:
                avg = float(w.tail(last_n)["QTD"].mean()) if len(w)>=1 else float(w["QTD"].mean())
                forecasts.append((p,int(round(max(0,avg)))))
        if forecasts:
            df_f = pd.DataFrame(forecasts, columns=["PRODUTO","PREVISAO_QTD"])
            st.dataframe(df_f, use_container_width=True)
            figf = px.bar(df_f, x="PRODISAO_QTD" if "PRODISAO_QTD" in df_f.columns else "PREVISAO_QTD", y="PRODUTO", orientation="h")
            # fallback simple plot if labels mismatch:
            try:
                figf = px.bar(df_f, x="PRODUTO", y="PREVISAO_QTD", color_discrete_sequence=["#a78bfa"])
                plotly_dark_config(figf)
                st.plotly_chart(figf, use_container_width=True, config=dict(displayModeBar=False))
            except:
                pass

    st.markdown("### 3) Alertas de reposição (sugestão)")
    def suggest_reorder(est_df, weekly_sales, lead_time_days=7, safety_weeks=1, min_order=5):
        if est_df is None or est_df.empty: return pd.DataFrame()
        avg_week = weekly_sales.groupby("PRODUTO")["QTD"].mean().reset_index().rename(columns={"QTD":"AVG_WEEKLY"})
        out = est_df.copy()
        out = out.merge(avg_week, how="left", on="PRODUTO")
        out["AVG_WEEKLY"] = out["AVG_WEEKLY"].fillna(0)
        out["DEMANDA_LEAD"] = out["AVG_WEEKLY"] * (lead_time_days/7.0)
        out["SAFETY"] = out["AVG_WEEKLY"] * safety_weeks
        out["SUGESTAO"] = np.ceil((out["DEMANDA_LEAD"] + out["SAFETY"]) - out["EM ESTOQUE"])
        out["SUGESTAO"] = out["SUGESTAO"].fillna(0)
        out.loc[out["SUGESTAO"] < min_order, "SUGESTAO"] = np.where(out["SUGESTAO"]>0, min_order, 0)
        out["SUGESTAO"] = out["SUGESTAO"].astype(int)
        out["URGENTE"] = out["SUGESTAO"] > 0
        return out.sort_values("URGENTE", ascending=False)

    reorder = suggest_reorder(estoque_df, weekly, lead_time_days=lead_time_days, safety_weeks=safety_weeks, min_order=min_order)
    if reorder is None or reorder.empty:
        st.info("Sem sugestões de reposição (dados insuficientes).")
    else:
        qlow = reorder[reorder["URGENTE"]]
        if not qlow.empty:
            disp = qlow[["PRODUTO","EM ESTOQUE","AVG_WEEKLY","DEMANDA_LEAD","SAFETY","SUGESTAO"]].copy()
            disp["AVG_WEEKLY"] = disp["AVG_WEEKLY"].map(lambda x: round(float(x),2))
            disp["DEMANDA_LEAD"] = disp["DEMANDA_LEAD"].map(lambda x: round(float(x),2))
            disp["SAFETY"] = disp["SAFETY"].map(lambda x: round(float(x),2))
            st.dataframe(disp.reset_index(drop=True), use_container_width=True)
        else:
            st.info("Nenhum produto requer reposição agora.")

    st.markdown("### 4) Anomalias simples (z-score diário)")
    def detect_anomalies(df_v, z_thresh=3.0):
        if df_v is None or df_v.empty: return pd.DataFrame()
        df = df_v.dropna(subset=["DATA"]).copy()
        df["DATA_DAY"] = df["DATA"].dt.floor("D")
        daily = df.groupby("DATA_DAY")["VALOR TOTAL"].sum().reset_index()
        daily["MEAN"] = daily["VALOR TOTAL"].mean()
        daily["STD"] = daily["VALOR TOTAL"].std(ddof=0) if daily["VALOR TOTAL"].std(ddof=0) != 0 else 0.0
        daily["Z"] = (daily["VALOR TOTAL"] - daily["MEAN"]) / (daily["STD"] + 1e-9)
        anomalies = daily[np.abs(daily["Z"]) >= z_thresh].sort_values("Z", ascending=False)
        return anomalies

    anomalies = detect_anomalies(vendas_filtradas, z_thresh=3.0)
    if anomalies.empty:
        st.info("Nenhuma anomalia diária (z>=3) detectada.")
    else:
        anomalies["VALOR TOTAL FMT"] = anomalies["VALOR TOTAL"].map(formatar_reais_com_centavos)
        st.dataframe(anomalies[["DATA_DAY","VALOR TOTAL FMT","Z"]].rename(columns={"DATA_DAY":"DATA"}).reset_index(drop=True), use_container_width=True)

    st.markdown("### 5) Sugestões de precificação (margem)")
    target_margin_pct = st.slider("Margem alvo (%)", min_value=10, max_value=80, value=30)
    if not estoque_df.empty:
        price_df = estoque_df.copy()
        price_df["CUSTO"] = price_df["Media C. UNITARIO"].fillna(0).astype(float)
        price_df["PRECO_ATUAL"] = price_df["Valor Venda Sugerido"].fillna(0).astype(float)
        price_df["MARGEM_ATUAL_PCT"] = np.where(price_df["PRECO_ATUAL"]>0, (price_df["PRECO_ATUAL"] - price_df["CUSTO"])/price_df["PRECO_ATUAL"]*100, 0)
        denom = (1 - (target_margin_pct/100))
        price_df["PRECO_RECOM"] = np.where(denom>0, price_df["CUSTO"] / denom, price_df["PRECO_ATUAL"])
        price_df["DELTA_PCT"] = np.where(price_df["PRECO_ATUAL"]>0, (price_df["PRECO_RECOM"] - price_df["PRECO_ATUAL"]) / price_df["PRECO_ATUAL"] * 100, 0)
        price_df["AJUSTAR"] = np.abs(price_df["DELTA_PCT"]) > 2.0
        price_df["PRECO_ATUAL_FMT"] = price_df["PRECO_ATUAL"].map(formatar_reais_com_centavos)
        price_df["PRECO_RECOM_FMT"] = price_df["PRECO_RECOM"].map(formatar_reais_com_centavos)
        price_df["MARGEM_ATUAL_PCT"] = price_df["MARGEM_ATUAL_PCT"].map(lambda x: f"{x:.1f}%")
        price_df["DELTA_PCT"] = price_df["DELTA_PCT"].map(lambda x: f"{x:+.1f}%")
        st.dataframe(price_df.sort_values("AJUSTAR",ascending=False)[["PRODUTO","CUSTO","PRECO_ATUAL_FMT","PRECO_RECOM_FMT","MARGEM_ATUAL_PCT","DELTA_PCT","AJUSTAR"]].reset_index(drop=True), use_container_width=True)
    else:
        st.info("Sem dados de estoque para análise de preços.")

    st.markdown("#### Observações")
    st.write("- Módulo IA usa regras e heurísticas simples (sem chamadas externas).")
    st.write("- Previsões e alertas são auxiliares — sempre valide antes de comprar/alterar preços.")

# ----------------------------
# Rodapé
# ----------------------------
st.markdown("""
<div style="margin-top:18px; color:#bdbdbd; font-size:12px;">
  <em>Nota:</em> Valores de estoque (custo & venda) são calculados a partir das colunas <strong>Media C. UNITARIO</strong>, <strong>Valor Venda Sugerido</strong> e <strong>EM ESTOQUE</strong>.  
  O módulo de insights é leve e rule-based; posso evoluir para modelos mais robustos se desejar.
</div>
""", unsafe_allow_html=True)
