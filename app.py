
# app_updated.py — Loja Importados — Dashboard (com glassmorphism, icon animado, sparkline mini-gráfico, skeleton)
import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime, timedelta
import requests
from io import BytesIO
import time
import base64
import math

st.set_page_config(page_title="Loja Importados – Dashboard (Premium)", layout="wide", initial_sidebar_state="collapsed")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b/export?format=xlsx"

# ---------------------
# CSS (dark + glass + skeleton + animations)
# ---------------------
st.markdown(r"""
<style>
:root{
  --bg:#0b0b0b;
  --accent:#8b5cf6;
  --accent-2:#a78bfa;
  --muted:#bdbdbd;
  --card-bg:#141414;
  --glass: rgba(255,255,255,0.04);
}
body, .stApp { background: var(--bg) !important; color:#f0f0f0 !important; font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; }

/* Card grid */
.card-grid-ecom {
    display: grid;
    grid-template-columns: repeat(3,1fr);
    gap:16px;
}
@media(max-width:1200px){ .card-grid-ecom{grid-template-columns:repeat(2,1fr);} }
@media(max-width:720px){ .card-grid-ecom{grid-template-columns:1fr;} }

/* Card */
.card-ecom{
    background: linear-gradient(180deg, rgba(20,20,20,0.7), rgba(16,16,16,0.6));
    border-radius:12px;
    padding:14px;
    border:1px solid rgba(255,255,255,0.04);
    display:flex;
    gap:12px;
    align-items:flex-start;
    min-height:98px;
    position:relative;
    overflow:hidden;
}
.avatar{
    width:64px;height:64px;border-radius:14px;
    background:linear-gradient(135deg,var(--accent),#ec4899);
    display:flex;align-items:center;justify-content:center;
    color:white;font-weight:900;font-size:22px;
    box-shadow:0 6px 18px rgba(0,0,0,0.55);
    flex-shrink:0;
}

/* Title/meta */
.card-title{font-weight:900;font-size:16px;margin-bottom:6px;color:#fff;}
.card-meta{font-size:13px;color:#ccc;margin-bottom:6px;}
.card-prices{display:flex;gap:12px;margin-bottom:6px;}
.card-price{color:var(--accent-2);font-weight:900;}
.card-cost{color:#999;font-weight:700;}
.badge{padding:4px 8px;border-radius:8px;font-size:12px;}
.low{background:#4b0000;color:#fff;}
.hot{background:#3b0050;color:#fff;}
.zero{background:#2f2f2f;color:#fff;}

/* Glassmorphism box for last purchase */
.glass-last {
  display:inline-block;
  padding:6px 10px;
  border-radius:10px;
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
  font-size:13px;
  color:#eaeaea;
  margin-bottom:6px;
  box-shadow: 0 4px 18px rgba(0,0,0,0.45);
}

/* Animated icon */
.icon-anim {
  display:inline-block;
  vertical-align:middle;
  margin-right:8px;
  transform-origin:center;
  animation: floatIcon 1.6s ease-in-out infinite;
}
@keyframes floatIcon {
  0% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-6px) rotate(-6deg); }
  100% { transform: translateY(0) rotate(0deg); }
}

/* small sparkline container */
.sparkline {
  width:110px;
  height:34px;
  display:inline-block;
  vertical-align:middle;
}

/* skeleton */
.skeleton-card{
  background: linear-gradient(90deg, rgba(255,255,255,0.03), rgba(255,255,255,0.02));
  border-radius:12px;
  padding:14px;
  min-height:98px;
  display:flex;
  gap:12px;
  align-items:center;
}
.skeleton-rect {
  height:12px;
  width:100%;
  background: linear-gradient(90deg, rgba(255,255,255,0.02), rgba(255,255,255,0.06), rgba(255,255,255,0.02));
  border-radius:6px;
  animation: shimmer 1.2s infinite linear;
  background-size: 200% 100%;
}
.skeleton-circle {
  width:64px;height:64px;border-radius:12px;
  background: linear-gradient(90deg, rgba(255,255,255,0.02), rgba(255,255,255,0.06), rgba(255,255,255,0.02));
  animation: shimmer 1.2s infinite linear;
}
@keyframes shimmer {
  0% { background-position: -150% 0; }
  100% { background-position: 150% 0; }
}
</style>
""", unsafe_allow_html=True)

# ---------------------
# Helpers (copied / adapted)
# ---------------------
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

def limpar_aba_raw(df_raw,nome):
    busca={"ESTOQUE":["PRODUTO","EM ESTOQUE"],"VENDAS":["DATA","PRODUTO"],"COMPRAS":["DATA","CUSTO"]}.get(nome,["PRODUTO"])
    for i in range(min(len(df_raw),12)):
        linha=" ".join(df_raw.iloc[i].astype(str).str.upper().tolist())
        if any(kw.upper() in linha for kw in busca):
            header_idx = i
            break
    else:
        return None
    df_tmp=df_raw.copy()
    df_tmp.columns=df_tmp.iloc[header_idx]
    df=df_tmp.iloc[header_idx+1:].copy()
    df.columns=[str(c).strip() for c in df.columns]
    df=df.drop(columns=[c for c in df.columns if str(c).lower() in ("nan","none","")],errors="ignore")
    df=df.loc[:,~df.isna().all()]
    return df.reset_index(drop=True)

# ---------------------
# Carregar planilha (com spinner)
# ---------------------
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

# ---------------------
# Normalizações (estoque, vendas, compras)
# ---------------------
if "ESTOQUE" in dfs:
    df_e = dfs["ESTOQUE"].copy()
    # custo médio
    for alt in ["Media C. UNITARIO","MEDIA C. UNITARIO","MEDIA CUSTO UNITARIO","MEDIA C. UNIT"]:
        if alt in df_e.columns:
            df_e["Media C. UNITARIO"] = parse_money_series(df_e[alt]).fillna(0)
            break
    # valor venda sugerido
    for alt in ["Valor Venda Sugerido","VALOR VENDA SUGERIDO","VALOR VENDA","VALOR_VENDA"]:
        if alt in df_e.columns:
            df_e["Valor Venda Sugerido"] = parse_money_series(df_e[alt]).fillna(0)
            break
    # estoque
    for alt in ["EM ESTOQUE","ESTOQUE","QTD","QUANTIDADE"]:
        if alt in df_e.columns:
            df_e["EM ESTOQUE"] = parse_int_series(df_e[alt]).fillna(0).astype(int)
            break
    if "PRODUTO" not in df_e.columns:
        for c in df_e.columns:
            if df_e[c].dtype == object:
                df_e = df_e.rename(columns={c:"PRODUTO"})
                break
    dfs["ESTOQUE"] = df_e

if "VENDAS" in dfs:
    df_v = dfs["VENDAS"].copy()
    df_v.columns = [str(c).strip() for c in df_v.columns]
    money_map={"VALOR VENDA":["VALOR VENDA","VALOR_VENDA","VALORVENDA"],
               "VALOR TOTAL":["VALOR TOTAL","VALOR_TOTAL","VALORTOTAL"],
               "MEDIA CUSTO UNITARIO":["MEDIA C. UNITARIO","MEDIA CUSTO UNITARIO","MEDIA CUSTO"],
               "LUCRO UNITARIO":["LUCRO UNITARIO","LUCRO_UNITARIO"]}
    for target,vars_ in money_map.items():
        for v in vars_:
            if v in df_v.columns:
                df_v[target]=parse_money_series(df_v[v])
                break
    qtd_cols=[c for c in df_v.columns if c.upper() in ("QTD","QUANTIDADE","QTY")]
    if qtd_cols: df_v["QTD"]=parse_int_series(df_v[qtd_cols[0]]).fillna(0).astype(int)
    if "DATA" in df_v.columns:
        df_v["DATA"]=pd.to_datetime(df_v["DATA"],errors="coerce")
        df_v["MES_ANO"]=df_v["DATA"].dt.strftime("%Y-%m")
    else:
        df_v["MES_ANO"]=pd.NA
    if "VALOR TOTAL" not in df_v and "VALOR VENDA" in df_v:
        df_v["VALOR TOTAL"]=df_v["VALOR VENDA"].fillna(0)*df_v.get("QTD",0).fillna(0)
    if "LUCRO UNITARIO" not in df_v and ("VALOR VENDA" in df_v and "MEDIA CUSTO UNITARIO" in df_v):
        df_v["LUCRO UNITARIO"]=df_v["VALOR VENDA"].fillna(0)-df_v["MEDIA CUSTO UNITARIO"].fillna(0)
    if "DATA" in df_v.columns:
        df_v = df_v.sort_values("DATA", ascending=False).reset_index(drop=True)
    dfs["VENDAS"] = df_v

if "COMPRAS" in dfs:
    df_c = dfs["COMPRAS"].copy()
    qcols=[c for c in df_c.columns if "QUANT" in c.upper()]
    if qcols: df_c["QUANTIDADE"]=parse_int_series(df_c[qcols[0]]).fillna(0).astype(int)
    ccols=[c for c in df_c.columns if any(k in c.upper() for k in ("CUSTO","UNIT"))]
    if ccols: df_c["CUSTO UNITÁRIO"]=parse_money_series(df_c[ccols[0]]).fillna(0)
    df_c["CUSTO TOTAL (RECALC)"]=df_c.get("QUANTIDADE",0)*df_c.get("CUSTO UNITÁRIO",0)
    if "DATA" in df_c.columns:
        df_c["DATA"]=pd.to_datetime(df_c["DATA"],errors="coerce")
        df_c["MES_ANO"]=df_c["DATA"].dt.strftime("%Y-%m")
    dfs["COMPRAS"]=df_c

# ---------------------
# Indicadores
# ---------------------
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

# ---------------------
# Filtros e vendas/compras filtradas
# ---------------------
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
    return df[df["MES_ANO"]==mes].copy() if "MES_ANO" in df.columns else df

vendas_filtradas = filtrar_mes_df(dfs.get("VENDAS", pd.DataFrame()), mes_selecionado)
if not vendas_filtradas.empty and "DATA" in vendas_filtradas.columns:
    vendas_filtradas = vendas_filtradas.sort_values("DATA", ascending=False).reset_index(drop=True)
compras_filtradas = filtrar_mes_df(dfs.get("COMPRAS", pd.DataFrame()), mes_selecionado)

total_vendido = vendas_filtradas.get("VALOR TOTAL", pd.Series()).fillna(0).sum()
total_lucro = (vendas_filtradas.get("LUCRO UNITARIO", 0).fillna(0) * vendas_filtradas.get("QTD", 0).fillna(0)).sum()
total_compras = compras_filtradas.get("CUSTO TOTAL (RECALC)", pd.Series()).fillna(0).sum()

with col_kpis:
    st.markdown(f"""
    <div style="display:flex; gap:10px; align-items:center; margin-bottom:20px; flex-wrap:wrap">
      <div style="background:var(--card-bg); border-radius:10px; padding:10px 14px; border-left:6px solid var(--accent); min-width:160px;">
        <h3 style="margin:0; font-size:12px; color:var(--accent-2);">💵 Total Vendido</h3>
        <div style="margin-top:6px; font-size:20px; font-weight:900;">{formatar_reais_sem_centavos(total_vendido)}</div>
      </div>
      <div style="background:var(--card-bg); border-radius:10px; padding:10px 14px; border-left:6px solid #34d399; min-width:160px;">
        <h3 style="margin:0; font-size:12px; color:#34d399;">🧾 Total Lucro</h3>
        <div style="margin-top:6px; font-size:20px; font-weight:900;">{formatar_reais_sem_centavos(total_lucro)}</div>
      </div>
      <div style="background:var(--card-bg); border-radius:10px; padding:10px 14px; border-left:6px solid #f59e0b; min-width:160px;">
        <h3 style="margin:0; font-size:12px; color:#f59e0b;">💸 Total Compras</h3>
        <div style="margin-top:6px; font-size:20px; font-weight:900;">{formatar_reais_sem_centavos(total_compras)}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

# ---------------------
# Tabs
# ---------------------
tabs = st.tabs(["🛒 VENDAS", "📦 ESTOQUE", "🔍 PESQUISAR"])

# VENDAS & ESTOQUE same as before (keeping app concise)...
with tabs[0]:
    st.subheader("Vendas — período selecionado")
    if vendas_filtradas.empty:
        st.info("Sem dados de vendas.")
    else:
        df_sem=vendas_filtradas.copy()
        df_sem["DATA"]=pd.to_datetime(df_sem["DATA"], errors="coerce")
        df_sem=df_sem.sort_values("DATA", ascending=False).reset_index(drop=True)
        st.markdown("### 📄 Tabela de Vendas (mais recentes primeiro)")
        st.dataframe(df_sem.head(200), use_container_width=True)

with tabs[1]:
    if estoque_df.empty:
        st.info("Sem dados de estoque.")
    else:
        st.markdown("### 📋 Estoque — visão detalhada")
        st.dataframe(estoque_df.head(200), use_container_width=True)

# ---------------------
# PESQUISAR — com skeleton -> cards glass -> animated icon -> sparkline
# ---------------------
with tabs[2]:
    st.markdown("### 🔍 Buscar produtos — Modo E-commerce (Premium)")
    termo = st.text_input("Buscar","",placeholder="Nome do produto...")
    filtro_baixo = st.checkbox("⚠️ Baixo estoque (≤3)")
    filtro_alto = st.checkbox("📦 Alto estoque (≥20)")
    filtro_vendidos = st.checkbox("🔥 Com vendas")
    filtro_sem_venda = st.checkbox("❄️ Sem vendas")

    df = estoque_df.copy()
    vendas_df = dfs.get("VENDAS", pd.DataFrame()).copy()
    if not vendas_df.empty and "QTD" in vendas_df.columns:
        vend = vendas_df.groupby("PRODUTO")["QTD"].sum().reset_index().rename(columns={"QTD":"TOTAL_QTD"})
        df = df.merge(vend,how="left",on="PRODUTO").fillna({"TOTAL_QTD":0})
    else:
        df["TOTAL_QTD"]=0

    if termo.strip():
        df = df[df["PRODUTO"].str.contains(termo,case=False,na=False)]
    if filtro_baixo:
        df = df[df["EM ESTOQUE"]<=3]
    if filtro_alto:
        df = df[df["EM ESTOQUE"]>=20]
    if filtro_vendidos:
        df = df[df["TOTAL_QTD"]>0]
    if filtro_sem_venda:
        df = df[df["TOTAL_QTD"]==0]

    df["CUSTO_FMT"]=df["Media C. UNITARIO"].map(formatar_reais_com_centavos)
    df["VENDA_FMT"]=df["Valor Venda Sugerido"].map(formatar_reais_com_centavos)

    itens_pagina = st.selectbox("Itens por página:", [6,9,12], index=0)
    total = len(df)
    total_paginas = max(1, (total + itens_pagina - 1)//itens_pagina)

    if "pagina" not in st.session_state:
        st.session_state["pagina"]=1

    colp1, colp2, colp3 = st.columns([1,1,1])
    with colp1:
        if st.button("⬅️ Voltar"):
            st.session_state['pagina'] = max(1, st.session_state['pagina']-1)
    with colp2:
        st.write(f"Página **{st.session_state['pagina']}** de **{total_paginas}**")
    with colp3:
        if st.button("Avançar ➡️"):
            st.session_state['pagina'] = min(total_paginas, st.session_state['pagina']+1)

    pagina = st.session_state["pagina"]
    inicio = (pagina-1)*itens_pagina
    fim = inicio + itens_pagina
    df_page = df.iloc[inicio:fim]

    st.markdown(f"**{total} resultados encontrados**")

    # Build purchases helper (history + last purchase)
    compras_df = dfs.get("COMPRAS", pd.DataFrame()).copy()
    ultima_compra = None
    historico_compras = {}
    if not compras_df.empty:
        if "DATA" in compras_df.columns:
            compras_df["DATA"] = pd.to_datetime(compras_df["DATA"], errors="coerce")
            compras_df = compras_df.dropna(subset=["DATA"])
        if "PRODUTO" not in compras_df.columns:
            for c in compras_df.columns:
                if compras_df[c].dtype == object:
                    compras_df = compras_df.rename(columns={c:"PRODUTO"})
                    break
        # normalize columns (QUANTIDADE and CUSTO UNITÁRIO)
        qcols=[c for c in compras_df.columns if "QUANT" in c.upper()]
        if qcols: compras_df["QUANTIDADE"] = parse_int_series(compras_df[qcols[0]]).fillna(0).astype(int)
        ccols=[c for c in compras_df.columns if any(k in c.upper() for k in ("CUSTO","UNIT"))]
        if ccols: compras_df["CUSTO UNITÁRIO"] = parse_money_series(compras_df[ccols[0]]).fillna(0)
        compras_df = compras_df.sort_values("DATA", ascending=False)
        ultima_compra = compras_df.groupby("PRODUTO").first()[["DATA","QUANTIDADE","CUSTO UNITÁRIO"]]
        # historico: last 8 purchases per product (date,qtd)
        for prod, g in compras_df.groupby("PRODUTO"):
            hist = g.sort_values("DATA").tail(8)
            vals = list(zip(hist["DATA"].dt.strftime("%Y-%m-%d").tolist(), hist.get("QUANTIDADE", pd.Series([0]*len(hist))).tolist()))
            historico_compras[prod] = vals

    # Skeleton loading (quick UX polish)
    placeholder = st.empty()
    with placeholder.container():
        st.markdown("<div style='display:grid; grid-template-columns: repeat(3,1fr); gap:16px;'>", unsafe_allow_html=True)
        for i in range(itens_pagina):
            st.markdown("""
            <div class='skeleton-card'>
              <div class='skeleton-circle'></div>
              <div style='flex:1; min-width:120px;'>
                <div style='height:14px; width:45%; margin-bottom:8px;' class='skeleton-rect'></div>
                <div style='height:10px; width:70%; margin-bottom:6px;' class='skeleton-rect'></div>
                <div style='height:10px; width:50%; margin-bottom:6px;' class='skeleton-rect'></div>
              </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    # small pause to let skeleton show
    time.sleep(0.35)
    placeholder.empty()

    # Render cards
    st.markdown("<div class='card-grid-ecom'>", unsafe_allow_html=True)
    for _, r in df_page.iterrows():
        nome = r["PRODUTO"]
        estoque = int(r["EM ESTOQUE"])
        venda = r["VENDA_FMT"]
        custo = r["CUSTO_FMT"]
        vendidos = int(r["TOTAL_QTD"])

        partes = str(nome).split()
        iniciais = "".join([p[0].upper() for p in partes[:2]])

        # last purchase
        if ultima_compra is not None and nome in ultima_compra.index:
            uc = ultima_compra.loc[nome]
            data_compra = pd.to_datetime(uc["DATA"]).strftime("%d/%m/%Y") if not pd.isna(uc["DATA"]) else "N/A"
            qtd_compra = int(uc["QUANTIDADE"]) if not pd.isna(uc["QUANTIDADE"]) else 0
            custo_compra = formatar_reais_com_centavos(uc["CUSTO UNITÁRIO"]) if not pd.isna(uc["CUSTO UNITÁRIO"]) else "R$ 0,00"
            texto_ultima = f"<span class='glass-last'><span class='icon-anim'>🧾</span>Última compra: <b>{data_compra}</b> • {qtd_compra} un • {custo_compra}</span>"
        else:
            texto_ultima = "<span class='glass-last'><span class='icon-anim'>🧾</span><i>Nunca comprado</i></span>"

        # sparkline mini-graph (SVG)
        spark_html = ""
        hist = historico_compras.get(nome, [])
        if hist:
            # build simple sparkline from quantities
            vals = [v for (_, v) in hist]
            # normalize to 0-1
            mx = max(vals) if max(vals) != 0 else 1
            points = []
            w = 110
            h = 34
            step = w / max(1, (len(vals)-1))
            for i, vv in enumerate(vals):
                x = i * step
                y = h - (vv/mx) * (h-4) - 2
                points.append(f"{x:.1f},{y:.1f}")
            poly = " ".join(points)
            # small circles for last point
            last_x = (len(vals)-1)*step
            last_y = h - (vals[-1]/mx) * (h-4) - 2
            spark_html = f"<svg class='sparkline' viewBox='0 0 {w} {h}' preserveAspectRatio='none'><polyline points='{poly}' fill='none' stroke='#a78bfa' stroke-width='2' stroke-linecap='round' stroke-linejoin='round' /></svg>"
        else:
            spark_html = "<div style='width:110px;height:34px;display:inline-block;'></div>"

        badges=[]
        if estoque<=3: badges.append("<span class='badge low'>⚠️ Baixo</span>")
        if vendidos>=15: badges.append("<span class='badge hot'>🔥 Saindo</span>")
        if vendidos==0: badges.append("<span class='badge zero'>❄️ Sem vendas</span>")
        badges_html=" ".join(badges)

        html = f"""
<div class='card-ecom'>
  <div class='avatar'>{iniciais}</div>
  <div style='flex:1;'>
    <div class='card-title'>{nome}</div>
    <div class='card-meta'>Estoque: <b>{estoque}</b> • Vendidos: <b>{vendidos}</b></div>
    <div style='display:flex; gap:10px; align-items:center; margin-bottom:8px;'>
      {texto_ultima}
      {spark_html}
    </div>
    <div class='card-prices'>
      <div class='card-price'>{venda}</div>
      <div class='card-cost'>{custo}</div>
    </div>
    <div style='margin-top:6px'>{badges_html}</div>
  </div>
</div>
"""
        st.markdown(html, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

# End of file
