# app.py — Dashboard Loja Importados (Roxo Minimalista - Tema Fixo)
# -----------------------------------------------------------------
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
# CSS (tema fixo - claro/escuro)
# =============================
st.markdown("""
<style>
/* Reset margens internas do Streamlit */
main > div.block-container { padding-top: 10px !important; }
/* Cores fixas para qualquer tema */
:root{
  --bg: #ffffff;
  --accent: #8b5cf6;
  --accent-2: #6d28d9;
  --muted: #444444;
  --card-bg: #ffffff;
  --text-color: #111111;
}
body, .stApp { background: var(--bg) !important; color: var(--text-color) !important; font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; }
.topbar { display:flex; align-items:center; gap:12px; margin-bottom:4px; }
.logo-wrap { width:44px; height:44px; display:flex; align-items:center; justify-content:center; border-radius:10px; background: linear-gradient(135deg,var(--accent),var(--accent-2)); box-shadow: 0 6px 18px rgba(109,40,217,0.12); }
.logo-wrap svg { width:26px; height:26px; }
.title { font-size:20px; font-weight:800; color:var(--accent-2); margin:0; line-height:1; }
.subtitle { margin:0; font-size:12px; color:var(--muted); margin-top:2px; }
.kpi-row { display:flex; gap:10px; align-items:center; margin-bottom:20px; }
.kpi { background:var(--card-bg); border-radius:10px; padding:10px 14px; box-shadow:0 6px 16px rgba(13,12,20,0.04); border-left:6px solid var(--accent); min-width:160px; display:flex; flex-direction:column; justify-content:center; }
.kpi h3 { margin:0; font-size:12px; color:var(--accent-2); font-weight:800; letter-spacing:0.2px; }
.kpi .value { margin-top:6px; font-size:20px; font-weight:900; color:var(--text-color); white-space:nowrap; }
.stTabs { margin-top: 12px !important; }
.stTabs button { background: var(--card-bg) !important; border:1px solid #f0eaff !important; border-radius:12px !important; padding:8px 14px !important; margin-right:8px !important; margin-bottom:8px !important; font-weight:700 !important; color:var(--accent-2) !important; box-shadow:0 3px 10px rgba(0,0,0,0.04) !important; }
.stDataFrame thead th { background:#fbf7ff !important; font-weight:700 !important; }
.stDataFrame, .element-container { font-size:13px; }
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
# HELPERS
# =============================
def parse_money_value(x):
    try: 
        if pd.isna(x): return float("nan")
    except: pass
    s = str(x).strip()
    if s=="" or s.lower() in ("nan","none","-"): return float("nan")
    s = re.sub(r"[^\d\.,\-]","", s)
    if "." in s and "," in s: s = s.replace(".","").replace(",",".")
    elif "," in s and "." not in s: s = s.replace(",",".")
    s = re.sub(r"[^\d\.\-]","", s)
    try: return float(s)
    except: return float("nan")

def parse_money_series(serie):
    return serie.astype(str).map(parse_money_value).astype("float64") if serie is not None else pd.Series(dtype="float64")

def parse_int_series(serie):
    def to_int(x):
        try: 
            if pd.isna(x): return pd.NA
        except: pass
        s = re.sub(r"[^\d\-]","", str(x))
        if s in ("","-","nan"): return pd.NA
        try: return int(float(s))
        except: return pd.NA
    return serie.map(to_int).astype("Int64")

def formatar_reais_sem_centavos(v):
    try: v=float(v)
    except: return "R$ 0"
    return f"R$ {f'{v:,.0f}'.replace(',','.')}" 

def formatar_colunas_moeda(df, cols):
    for c in cols:
        if c in df.columns:
            df[c] = df[c].fillna(0).map(lambda x: formatar_reais_sem_centavos(x))
    return df

def carregar_xlsx_from_url(url):
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return pd.ExcelFile(BytesIO(r.content))

def detectar_linha_cabecalho(df_raw, keywords):
    for i in range(min(len(df_raw),12)):
        linha = " ".join(df_raw.iloc[i].astype(str).str.upper().tolist())
        if any(kw.upper() in linha for kw in keywords): return i
    return None

def limpar_aba_raw(df_raw, nome):
    busca = {
        "ESTOQUE":["PRODUTO","EM ESTOQUE"],
        "VENDAS":["DATA","PRODUTO"],
        "COMPRAS":["DATA","CUSTO"]
    }.get(nome,["PRODUTO"])
    linha = detectar_linha_cabecalho(df_raw, busca)
    if linha is None: return None
    df_tmp = df_raw.copy()
    df_tmp.columns = df_tmp.iloc[linha]
    df = df_tmp.iloc[linha+1:].copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.drop(columns=[c for c in df.columns if str(c).lower() in ("nan","none","")], errors="ignore")
    df = df.loc[:, ~df.isna().all()]
    return df.reset_index(drop=True)

def preparar_tabela_vendas(df):
    if df is None or df.empty: return pd.DataFrame()
    d = df.copy()
    if "DATA" in d.columns:
        d["DATA"] = d["DATA"].dt.strftime("%d/%m/%Y")
    for c in ["VALOR VENDA","VALOR TOTAL","MEDIA CUSTO UNITARIO","LUCRO UNITARIO","QTD"]:
        if c not in d.columns: d[c]=0
    d = formatar_colunas_moeda(d, ["VALOR VENDA","VALOR TOTAL","MEDIA CUSTO UNITARIO","LUCRO UNITARIO"])
    d = d.loc[:, ~d.columns.astype(str).str.contains("^Unnamed|MES_ANO")]
    return d

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
        if cleaned is not None: dfs[aba] = cleaned

# =============================
# Conversores
# =============================
if "ESTOQUE" in dfs:
    df_e = dfs["ESTOQUE"]
    if "Media C. UNITARIO" in df_e.columns: df_e["Media C. UNITARIO"] = parse_money_series(df_e["Media C. UNITARIO"])
    if "Valor Venda Sugerido" in df_e.columns: df_e["Valor Venda Sugerido"] = parse_money_series(df_e["Valor Venda Sugerido"])
    if "EM ESTOQUE" in df_e.columns: df_e["EM ESTOQUE"] = parse_int_series(df_e["EM ESTOQUE"]).fillna(0)
    if "VENDAS" in df_e.columns: df_e["VENDAS"] = parse_int_series(df_e["VENDAS"]).fillna(0)
    dfs["ESTOQUE"]=df_e

if "VENDAS" in dfs:
    df_v = dfs["VENDAS"].copy()
    df_v.columns=[str(c).strip() for c in df_v.columns]
    money_map={
        "VALOR VENDA":["VALOR VENDA","VALOR_VENDA","VALORVENDA"],
        "VALOR TOTAL":["VALOR TOTAL","VALOR_TOTAL","VALORTOTAL"],
        "MEDIA CUSTO UNITARIO":["MEDIA C. UNITARIO","MEDIA CUSTO UNITARIO"],
        "LUCRO UNITARIO":["LUCRO UNITARIO","LUCRO_UNITARIO"]
    }
    for target, vars_ in money_map.items():
        for v in vars_:
            if v in df_v.columns:
                df_v[target] = parse_money_series(df_v[v])
                break
    qtd_cols=[c for c in df_v.columns if c.upper() in ("QTD","QUANTIDADE","QTY")]
    if qtd_cols: df_v["QTD"]=parse_int_series(df_v[qtd_cols[0]]).fillna(0)
    if "DATA" in df_v.columns:
        df_v["DATA"]=pd.to_datetime(df_v["DATA"], errors="coerce")
        df_v["MES_ANO"]=df_v["DATA"].dt.strftime("%Y-%m")
    else: df_v["MES_ANO"]=pd.NA
    if "VALOR TOTAL" not in df_v and "VALOR VENDA" in df_v: df_v["VALOR TOTAL"]=df_v["VALOR VENDA"].fillna(0)*df_v.get("QTD",0).fillna(0)
    if "LUCRO UNITARIO" not in df_v and ("VALOR VENDA" in df_v and "MEDIA CUSTO UNITARIO" in df_v):
        df_v["LUCRO UNITARIO"]=df_v["VALOR VENDA"].fillna(0)-df_v["MEDIA CUSTO UNITARIO"].fillna(0)
    dfs["VENDAS"]=df_v

if "COMPRAS" in dfs:
    df_c = dfs["COMPRAS"]
    qcols=[c for c in df_c.columns if "QUANT" in c.upper()]
    if qcols: df_c["QUANTIDADE"]=parse_int_series(df_c[qcols[0]]).fillna(0)
    ccols=[c for c in df_c.columns if any(k in c.upper() for k in ("CUSTO","UNIT"))]
    if ccols: df_c["CUSTO UNITÁRIO"]=parse_money_series(df_c[ccols[0]]).fillna(0)
    df_c["CUSTO TOTAL (RECALC)"]=df_c.get("QUANTIDADE",0)*df_c.get("CUSTO UNITÁRIO",0)
    if "DATA" in df_c.columns: df_c["MES_ANO"]=df_c["DATA"].dt.strftime("%Y-%m")
    dfs["COMPRAS"]=df_c

# =============================
# Filtro mês
# =============================
meses=["Todos"]
if "VENDAS" in dfs: meses+=sorted(dfs["VENDAS"]["MES_ANO"].dropna().unique().tolist(), reverse=True)
mes_atual=datetime.now().strftime("%Y-%m")
index_padrao=meses.index(mes_atual) if mes_atual in meses else 0
col_filter, col_kpis=st.columns([1,2])
with col_filter: mes_selecionado=st.selectbox("Filtrar por mês (YYYY-MM):", meses, index=index_padrao)
def filtrar_mes_df(df,mes): return df if df.empty or mes=="Todos" else df[df["MES_ANO"]==mes].copy() if "MES_ANO" in df.columns else df
vendas_filtradas=filtrar_mes_df(dfs.get("VENDAS",pd.DataFrame()), mes_selecionado)
compras_filtradas=filtrar_mes_df(dfs.get("COMPRAS",pd.DataFrame()), mes_selecionado)
estoque_df=dfs.get("ESTOQUE",pd.DataFrame())

total_vendido=vendas_filtradas.get("VALOR TOTAL",pd.Series()).fillna(0).sum()
total_lucro=(vendas_filtradas.get("LUCRO UNITARIO",0).fillna(0)*vendas_filtradas.get("QTD",0).fillna(0)).sum()
total_compras=compras_filtradas.get("CUSTO TOTAL (RECALC)", pd.Series()).fillna(0).sum()

with col_kpis:
    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi"><h3>💵 Total Vendido</h3><div class="value">{formatar_reais_sem_centavos(total_vendido)}</div></div>
      <div class="kpi" style="border-left-color:#34d399;"><h3>🧾 Total Lucro</h3><div class="value">{formatar_reais_sem_centavos(total_lucro)}</div></div>
      <div class="kpi" style="border-left-color:#f59e0b;"><h3>💸 Total Compras</h3><div class="value">{formatar_reais_sem_centavos(total_compras)}</div></div>
    </div>
    """, unsafe_allow_html=True)

# =============================
# TABS
# =============================
tabs=st.tabs(["🛒 VENDAS","🏆 TOP10 (VALOR)","🏅 TOP10 (QTD)","📦 ESTOQUE","🔍 PESQUISAR"])

# O restante segue igual ao app que você já tem...
