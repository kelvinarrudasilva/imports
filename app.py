# app.py — Dashboard Loja Importados (Roxo Minimalista) — Dark Theme Mobile
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import re
from datetime import datetime, timedelta
import requests
from io import BytesIO
import unicodedata
import difflib
import numpy as np

# ---------------------------
# Config
# ---------------------------
st.set_page_config(page_title="Loja Importados – Dashboard", layout="wide", initial_sidebar_state="collapsed")

URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b/export?format=xlsx"

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
# Helpers
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
    return f"R$ {f'{v:,.0f}'.replace(',','.')}" 

def formatar_reais_com_centavos(v):
    try: v=float(v)
    except: return "R$ 0,00"
    s = f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"

def formatar_colunas_moeda(df, cols):
    for c in cols:
        if c in df.columns: df[c]=df[c].fillna(0).map(lambda x: formatar_reais_sem_centavos(x))
    return df

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
    if df is None or df.empty: return pd.DataFrame()
    d=df.copy()
    if "DATA" in d.columns: d["DATA"]=d["DATA"].dt.strftime("%d/%m/%Y")
    for c in ["VALOR VENDA","VALOR TOTAL","MEDIA CUSTO UNITARIO","LUCRO UNITARIO","QTD"]:
        if c not in d.columns: d[c]=0
    d=formatar_colunas_moeda(d,["VALOR VENDA","VALOR TOTAL","MEDIA CUSTO UNITARIO","LUCRO UNITARIO"])
    d=d.loc[:,~d.columns.astype(str).str.contains("^Unnamed|MES_ANO")]
    if "DATA" in d.columns:
        try:
            d["_sort"] = pd.to_datetime(d["DATA"].str.replace("/","-"), format="%d-%m-%Y", errors="coerce")
            d = d.sort_values("_sort", ascending=False).drop(columns=["_sort"])
        except:
            pass
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
colunas_esperadas = ["ESTOQUE","VENDAS","COMPRAS"]
dfs = {}
for aba in colunas_esperadas:
    if aba in abas_all:
        raw = pd.read_excel(URL_PLANILHA, sheet_name=aba, header=None)
        cleaned = limpar_aba_raw(raw, aba)
        if cleaned is not None:
            dfs[aba] = cleaned

# =============================
# Conversores e ajustes
# =============================
# Normaliza colunas de estoque
if "ESTOQUE" in dfs:
    df_e = dfs["ESTOQUE"].copy()
    # coluna media custo
    if "Media C. UNITARIO" in df_e.columns:
        df_e["Media C. UNITARIO"] = parse_money_series(df_e["Media C. UNITARIO"]).fillna(0)
    else:
        for alt in ["MEDIA C. UNITARIO","MEDIA CUSTO UNITARIO","MEDIA C. UNIT"]:
            if alt in df_e.columns:
                df_e["Media C. UNITARIO"] = parse_money_series(df_e[alt]).fillna(0)
                break
    # valor venda sugerido
    if "Valor Venda Sugerido" in df_e.columns:
        df_e["Valor Venda Sugerido"] = parse_money_series(df_e["Valor Venda Sugerido"]).fillna(0)
    else:
        for alt in ["VALOR VENDA SUGERIDO","VALOR VENDA","VALOR_VENDA"]:
            if alt in df_e.columns:
                df_e["Valor Venda Sugerido"] = parse_money_series(df_e[alt]).fillna(0)
                break
    # estoque qty
    if "EM ESTOQUE" in df_e.columns:
        df_e["EM ESTOQUE"] = parse_int_series(df_e["EM ESTOQUE"]).fillna(0).astype(int)
    else:
        for alt in ["ESTOQUE","QTD","QUANTIDADE"]:
            if alt in df_e.columns:
                df_e["EM ESTOQUE"] = parse_int_series(df_e[alt]).fillna(0).astype(int)
                break
    # produto column fallback
    if "PRODUTO" not in df_e.columns:
        for c in df_e.columns:
            if df_e[c].dtype == object:
                df_e = df_e.rename(columns={c:"PRODUTO"})
                break
    dfs["ESTOQUE"] = df_e

# VENDAS
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
    if qtd_cols:
        df_v["QTD"]=parse_int_series(df_v[qtd_cols[0]]).fillna(0).astype(int)
    else:
        # se não existir QTD, tente inferir 1 por linha
        df_v["QTD"] = 1
    if "DATA" in df_v.columns:
        df_v["DATA"]=pd.to_datetime(df_v["DATA"],errors="coerce")
        df_v["MES_ANO"]=df_v["DATA"].dt.strftime("%Y-%m")
    else:
        df_v["MES_ANO"]=pd.NA
    if "VALOR TOTAL" not in df_v and "VALOR VENDA" in df_v:
        df_v["VALOR TOTAL"]=df_v["VALOR VENDA"].fillna(0)*df_v.get("QTD",0).fillna(0)
    if "LUCRO UNITARIO" not in df_v and ("VALOR VENDA" in df_v and "MEDIA CUSTO UNITARIO" in df_v):
        df_v["LUCRO UNITARIO"]=df_v["VALOR VENDA"].fillna(0)-df_v["MEDIA CUSTO UNITARIO"].fillna(0)
    # garantir ordenação: mais recente primeiro
    if "DATA" in df_v.columns:
        df_v = df_v.sort_values("DATA", ascending=False).reset_index(drop=True)
    dfs["VENDAS"] = df_v

# COMPRAS
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

# =============================
# INDICADORES DE ESTOQUE (NÃO AFETADOS PELO FILTRO)
# =============================
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

# =============================
# Filtro mês (aplica somente em VENDAS/COMPRAS)
# =============================
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

# =============================
# KPIs (vendas + estoque ao lado)
# =============================
total_vendido = vendas_filtradas.get("VALOR TOTAL", pd.Series()).fillna(0).sum()
total_lucro = (vendas_filtradas.get("LUCRO UNITARIO", 0).fillna(0) * vendas_filtradas.get("QTD", 0).fillna(0)).sum()
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

# =============================
# TABS
# =============================
tabs = st.tabs(["🛒 VENDAS","🏆 TOP10 VENDAS (VALOR)","🏅 TOP10 VENDAS (QTD)","📦 ESTOQUE","🔍 PESQUISAR"])

# =============================
# VENDAS — com Top3 gráfico + linha de tendência + previsão
# =============================
with tabs[0]:
    st.subheader("Vendas — período selecionado")

    if vendas_filtradas.empty:
        st.info("Sem dados de vendas.")
    else:
        df_sem = vendas_filtradas.copy()
        df_sem["DATA"] = pd.to_datetime(df_sem.get("DATA", pd.NaT), errors="coerce")
        df_sem = df_sem.sort_values("DATA", ascending=False).reset_index(drop=True)

        # --- gráfico Top3 últimos 6 meses (horizontal bar com % e tooltip) ---
        st.markdown("### 🏆 Top 3 — últimos 6 meses (resumo)")
        limite = datetime.now() - timedelta(days=180)
        df6 = df_sem[df_sem["DATA"] >= limite].copy()

        if df6.empty:
            st.info("Sem vendas nos últimos 6 meses.")
        else:
            agg = df6.groupby("PRODUTO", dropna=False).agg(
                QTD_TOTAL = ("QTD","sum"),
                VALOR_TOTAL = ("VALOR TOTAL","sum"),
                LUCRO_TOTAL = (lambda d: "LUCRO UNITARIO" in df6.columns and "QTD" in df6.columns, "sum") # dummy, adjusted below
            ).reset_index()

            # safer: compute lucro total properly if available
            if "LUCRO UNITARIO" in df6.columns:
                lucro_agg = df6.groupby("PRODUTO", dropna=False).apply(lambda g: (g.get("LUCRO UNITARIO",0).fillna(0)*(g.get("QTD",0).fillna(0))).sum()).reset_index(name="LUCRO_TOTAL")
                agg = agg.drop(columns=[c for c in ["LUCRO_TOTAL"] if c in agg.columns], errors="ignore").merge(lucro_agg, on="PRODUTO", how="left")
            else:
                agg["LUCRO_TOTAL"] = 0

            agg = agg.sort_values("QTD_TOTAL", ascending=False).reset_index(drop=True)
            top3 = agg.head(3).copy()
            total_qtd_period = agg["QTD_TOTAL"].sum()
            if total_qtd_period == 0:
                top3["PCT"] = 0
            else:
                top3["PCT"] = (top3["QTD_TOTAL"] / total_qtd_period) * 100

            # abrevia nomes longos
            def abbreviate(name, max_len=20):
                if not isinstance(name, str): return ""
                return name if len(name) <= max_len else name[:max_len].rstrip() + "…"

            top3["PRODUTO_ABV"] = top3["PRODUTO"].apply(abbreviate)

            # horizontal bar
            fig_h = px.bar(
                top3,
                x="QTD_TOTAL",
                y="PRODUTO_ABV",
                orientation="h",
                text="QTD_TOTAL",
                hover_data={"PRODUTO":True, "VALOR_TOTAL":":.2f", "LUCRO_TOTAL":":.2f", "PCT":":.1f"},
                height=300
            )
            fig_h.update_layout(margin=dict(l=40, r=10, t=30, b=30))
            fig_h.update_traces(textposition="outside")
            plotly_dark_config(fig_h)
            st.plotly_chart(fig_h, use_container_width=True, config=dict(displayModeBar=False))

            # small summary row (percent + totals)
            col1, col2, col3 = st.columns([2,2,2])
            col1.metric("Top3 Qtd (soma)", int(top3["QTD_TOTAL"].sum()))
            col2.metric("Participação Top3", f"{top3['PCT'].sum():.1f}%")
            col3.metric("Período", f"Últimos 6 meses")

            # --- linha de tendência mensal por produto (últimos 6 meses) + previsão simples ---
            st.markdown("### 📈 Tendência mensal (últimos 6 meses) — + previsão para próximo mês")
            # prepare monthly series for each of top3 products
            meses_range = pd.date_range(end=datetime.now(), periods=6, freq='M').to_series().dt.to_period('M').astype(str).tolist()
            # We'll build a df with columns: MES (YYYY-MM), PRODUTO, QTD
            df6["MES"] = df6["DATA"].dt.to_period('M').astype(str)
            monthly = df6.groupby(["PRODUTO","MES"], dropna=False).agg(QTD=("QTD","sum"), VALOR=("VALOR TOTAL","sum")).reset_index()

            # ensure months exist for each product
            prod_lines = []
            predictions = []
            for prod in top3["PRODUTO"].tolist():
                row = {"PRODUTO": prod}
                s = monthly[monthly["PRODUTO"]==prod].set_index("MES").reindex(meses_range).fillna(0).reset_index()
                s.rename(columns={"index":"MES"}, inplace=True)
                s["MES_ORD"] = range(len(s))  # 0..5
                x = s["MES_ORD"].values
                y = s["QTD"].values.astype(float)
                # linear fit if variance exists
                pred_next = 0
                slope = 0
                intercept = 0
                if len(x) >= 2 and y.sum() > 0:
                    try:
                        coeffs = np.polyfit(x, y, 1)
                        slope, intercept = coeffs[0], coeffs[1]
                        pred_next = max(0, int(np.round(np.polyval(coeffs, len(x)))))
                    except Exception:
                        pred_next = int(round(float(y[-1]) if len(y)>0 else 0))
                else:
                    pred_next = int(round(float(y[-1]) if len(y)>0 else 0))
                # store prediction
                predictions.append({
                    "PRODUTO": prod,
                    "PRED_NEXT_QTD": int(pred_next),
                    "SLOPE": float(slope),
                    "LAST_QTD": int(y[-1]) if len(y)>0 else 0
                })
                s["PRODUTO"] = prod
                prod_lines.append(s[["MES","PRODUTO","QTD"]])

            pred_df = pd.DataFrame(predictions).sort_values("PRED_NEXT_QTD", ascending=False).reset_index(drop=True)
            # plot lines
            fig_lines = go.Figure()
            for s in prod_lines:
                prod_name = s["PRODUTO"].iloc[0]
                abv = abbreviate(prod_name, max_len=16)
                fig_lines.add_trace(go.Scatter(
                    x=s["MES"],
                    y=s["QTD"],
                    mode="lines+markers",
                    name=abv,
                    hovertemplate="%{y} unidades<br>%{x}<extra></extra>"
                ))
                # add predicted point (dashed)
                last_mes = s["MES"].iloc[-1]
                pred_row = pred_df[pred_df["PRODUTO"]==prod_name]
                if not pred_row.empty:
                    pred_q = int(pred_row["PRED_NEXT_QTD"].iloc[0])
                    fig_lines.add_trace(go.Scatter(
                        x=[ "Próx" ],
                        y=[ pred_q ],
                        mode="markers",
                        marker=dict(symbol="diamond", size=10),
                        name=f"{abv} (prev)",
                        hovertemplate=f"{pred_q} unidades (prev.)<extra></extra>",
                        showlegend=False
                    ))
            fig_lines.update_layout(height=380, margin=dict(t=30,b=30,l=10,r=10))
            plotly_dark_config(fig_lines)
            st.plotly_chart(fig_lines, use_container_width=True, config=dict(displayModeBar=False))

            # --- tabela preditiva resumida ---
            st.markdown("### 🔮 Previsão rápida e tendência")
            if not pred_df.empty:
                pred_df_display = pred_df.copy()
                # add arrow for slope
                def slope_arrow(s):
                    if s > 0.5: return "⬆ Forte"
                    if s > 0.05: return "⬆"
                    if s < -0.5: return "⬇ Forte"
                    if s < -0.05: return "⬇"
                    return "→ Estável"
                pred_df_display["TENDÊNCIA"] = pred_df_display["SLOPE"].map(slope_arrow)
                pred_df_display = pred_df_display.rename(columns={"PRED_NEXT_QTD":"Prev Próx Mês (QTD)","LAST_QTD":"Últ. Mês QTD"})
                st.dataframe(pred_df_display[["PRODUTO","Últ. Mês QTD","Prev Próx Mês (QTD)","TENDÊNCIA"]].reset_index(drop=True), use_container_width=True)
            else:
                st.info("Sem dados para previsão.")

        # --- continua com tabela de vendas mais abaixo (mantido) ---
        st.markdown("### 📄 Tabela de Vendas (mais recentes primeiro)")
        tabela_vendas_exib = preparar_tabela_vendas(df_sem)
        st.dataframe(tabela_vendas_exib, use_container_width=True)

# =============================
# TOP10 VALOR
# =============================
with tabs[1]:
    st.subheader("Top 10 — por VALOR (R$)")
    if vendas_filtradas.empty:
        st.info("Sem dados.")
    else:
        dfv = vendas_filtradas.copy()
        top_val = dfv.groupby("PRODUTO", dropna=False).agg(VALOR_TOTAL=("VALOR TOTAL","sum"), QTD_TOTAL=("QTD","sum")).reset_index().sort_values("VALOR_TOTAL", ascending=False).head(10)
        top_val["VALOR_TOTAL_LABEL"] = top_val["VALOR_TOTAL"].apply(formatar_reais_sem_centavos)
        fig_top_val = px.bar(top_val, x="PRODUTO", y="VALOR_TOTAL", text="VALOR_TOTAL_LABEL", color_discrete_sequence=["#8b5cf6"], height=380)
        plotly_dark_config(fig_top_val)
        fig_top_val.update_traces(textposition="inside", textfont_size=12)
        st.plotly_chart(fig_top_val, use_container_width=True, config=dict(displayModeBar=False))
        st.markdown("### 📄 Tabela Top 10 por VALOR")
        top_val_display = top_val.copy()
        top_val_display["VALOR_TOTAL"] = top_val_display["VALOR_TOTAL"].map(formatar_reais_sem_centavos)
        st.dataframe(top_val_display[["PRODUTO","VALOR_TOTAL","QTD_TOTAL"]], use_container_width=True)

# =============================
# TOP10 QTD
# =============================
with tabs[2]:
    st.subheader("Top 10 — por QUANTIDADE")
    if vendas_filtradas.empty:
        st.info("Sem dados.")
    else:
        dfv = vendas_filtradas.copy()
        top_qtd = dfv.groupby("PRODUTO", dropna=False).agg(QTD_TOTAL=("QTD","sum"), VALOR_TOTAL=("VALOR TOTAL","sum")).reset_index().sort_values("QTD_TOTAL", ascending=False).head(10)
        top_qtd["QTD_TOTAL_LABEL"] = top_qtd["QTD_TOTAL"].astype(str)
        fig_top_qtd = px.bar(top_qtd, x="PRODUTO", y="QTD_TOTAL", text="QTD_TOTAL_LABEL", color_discrete_sequence=["#8b5cf6"], height=380)
        plotly_dark_config(fig_top_qtd)
        fig_top_qtd.update_traces(textposition="inside", textfont_size=12)
        st.plotly_chart(fig_top_qtd, use_container_width=True, config=dict(displayModeBar=False))
        st.markdown("### 📄 Tabela Top 10 por QUANTIDADE")
        top_qtd_display = top_qtd.copy()
        top_qtd_display["VALOR_TOTAL"] = top_qtd_display["VALOR_TOTAL"].map(formatar_reais_sem_centavos)
        st.dataframe(top_qtd_display[["PRODUTO","QTD_TOTAL","VALOR_TOTAL"]], use_container_width=True)

# =============================
# ESTOQUE
# =============================
with tabs[3]:
    if estoque_df.empty:
        st.info("Sem dados de estoque.")
    else:
        estoque_display = estoque_df.copy()
        estoque_display["VALOR_CUSTO_TOTAL_RAW"] = (estoque_display["Media C. UNITARIO"] * estoque_display["EM ESTOQUE"]).fillna(0)
        estoque_display["VALOR_VENDA_TOTAL_RAW"] = (estoque_display["Valor Venda Sugerido"] * estoque_display["EM ESTOQUE"]).fillna(0)

        st.markdown("### 🥧 Distribuição de estoque — fatias com quantidade")
        top_for_pie = estoque_display.sort_values("EM ESTOQUE", ascending=False).head(10)
        if not top_for_pie.empty:
            fig_pie = px.pie(
                top_for_pie,
                names="PRODUTO",
                values="EM ESTOQUE",
                hole=0.40
            )
            fig_pie.update_traces(
                textinfo="label+value",
                textposition="inside",
                pull=[0.05 if i == 0 else 0 for i in range(len(top_for_pie))],
                marker=dict(line=dict(color="#0b0b0b", width=1))
            )
            fig_pie.update_layout(
                title={"text":"Top itens por quantidade em estoque","y":0.96,"x":0.5,"xanchor":"center","yanchor":"top"},
                showlegend=False,
                margin=dict(t=60,b=10,l=10,r=10)
            )
            plotly_dark_config(fig_pie)
            st.plotly_chart(fig_pie, use_container_width=True, config=dict(displayModeBar=False, responsive=True))
        else:
            st.info("Sem itens para gerar o gráfico.")

        # tabela de estoque
        estoque_clas = estoque_display.copy()
        estoque_clas["CUSTO_UNITARIO_FMT"] = estoque_clas["Media C. UNITARIO"].map(formatar_reais_com_centavos)
        estoque_clas["VENDA_SUGERIDA_FMT"] = estoque_clas["Valor Venda Sugerido"].map(formatar_reais_com_centavos)
        estoque_clas["VALOR_TOTAL_CUSTO_FMT"] = estoque_clas["VALOR_CUSTO_TOTAL_RAW"].map(formatar_reais_sem_centavos)
        estoque_clas["VALOR_TOTAL_VENDA_FMT"] = estoque_clas["VALOR_VENDA_TOTAL_RAW"].map(formatar_reais_sem_centavos)

        display_df = estoque_clas[[
            "PRODUTO",
            "EM ESTOQUE",
            "CUSTO_UNITARIO_FMT",
            "VENDA_SUGERIDA_FMT",
            "VALOR_TOTAL_CUSTO_FMT",
            "VALOR_TOTAL_VENDA_FMT"
        ]].rename(columns={
            "CUSTO_UNITARIO_FMT":"CUSTO UNITÁRIO",
            "VENDA_SUGERIDA_FMT":"VENDA SUGERIDA",
            "VALOR_TOTAL_CUSTO_FMT":"VALOR TOTAL CUSTO",
            "VALOR_TOTAL_VENDA_FMT":"VALOR TOTAL VENDA"
        })

        display_df = display_df.sort_values("EM ESTOQUE", ascending=False).reset_index(drop=True)
        st.markdown("### 📋 Estoque — visão detalhada")
        st.dataframe(display_df, use_container_width=True)

# =============================
# PESQUISAR (sensível equilibrado) — sem libs externas
# =============================
def normalizar(texto):
    if not isinstance(texto, str):
        return ""
    texto = unicodedata.normalize("NFD", texto)
    texto = texto.encode("ascii", "ignore").decode("utf-8")
    return texto.lower().strip()

def gerar_ngrams(texto, tamanho=3):
    if len(texto) < tamanho:
        return [texto]
    return [texto[i:i+tamanho] for i in range(len(texto)-tamanho+1)]

with tabs[4]:
    st.subheader("Pesquisar produtos")

    termo = st.text_input(
        "Digite parte do nome do produto",
        placeholder="Ex: cabo usb, fonte, carregador, fan..."
    )

    if termo.strip():
        if estoque_df.empty:
            st.warning("Nenhum dado de estoque disponível para busca.")
        else:
            termo_norm = normalizar(termo)
            tokens = termo_norm.split()

            estoque_df["_search"] = estoque_df["PRODUTO"].apply(normalizar)

            resultados = []

            for i, row in estoque_df.iterrows():
                nome = row["_search"]

                score_final = 0

                # 1) CONTÉM DIRETO
                if termo_norm in nome:
                    score_final = 1.0

                # 2) TODOS OS TOKENS PRESENTES
                elif all(tok in nome for tok in tokens):
                    score_final = 0.90

                # 3) PELO MENOS UM TOKEN PRESENTE
                elif any(tok in nome for tok in tokens):
                    score_final = 0.70

                else:
                    # 4) SIMILARIDADE GLOBAL
                    sim_global = difflib.SequenceMatcher(None, termo_norm, nome).ratio()

                    # 5) SIMILARIDADE PARCIAL — um pouco mais rígida agora
                    ngrams_nome = gerar_ngrams(nome)
                    melhor_parcial = max(
                        difflib.SequenceMatcher(None, termo_norm, ng).ratio()
                        for ng in ngrams_nome
                    )

                    score_final = max(sim_global * 0.8, melhor_parcial * 0.6)

                # LIMIAR MAIS RESTRITO AGORA
                if score_final >= 0.45:
                    resultados.append((i, score_final))

            if not resultados:
                st.warning("Nenhum produto encontrado.")
            else:
                resultados = sorted(resultados, key=lambda x: x[1], reverse=True)

                df_search = estoque_df.loc[[i for i, s in resultados]].copy()
                df_search.drop(columns=["_search"], inplace=True)

                if "Media C. UNITARIO" in df_search.columns:
                    df_search["Media C. UNITARIO"] = df_search["Media C. UNITARIO"].map(formatar_reais_com_centavos)
                if "Valor Venda Sugerido" in df_search.columns:
                    df_search["Valor Venda Sugerido"] = df_search["Valor Venda Sugerido"].map(formatar_reais_com_centavos)

                st.dataframe(df_search.reset_index(drop=True), use_container_width=True)

# =============================
# Rodapé simples
# =============================
st.markdown("""
<div style="margin-top:18px; color:#bdbdbd; font-size:12px;">
  <em>Nota:</em> Valores de estoque (custo & venda) são calculados a partir das colunas <strong>Media C. UNITARIO</strong>, <strong>Valor Venda Sugerido</strong> e <strong>EM ESTOQUE</strong> — estes indicadores não são afetados pelo filtro de mês.
</div>
""", unsafe_allow_html=True)
