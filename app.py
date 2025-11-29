# app.py — Dashboard Loja Importados (Roxo Minimalista) — Dark Theme Mobile
import streamlit as st

# ================================================
# 🔄 BOTÃO FLUTUANTE PREMIUM (ROXO NEON + ANIMAÇÃO)
# ================================================
st.markdown("""
<style>

.refresh-btn {
    position: fixed;
    bottom: 26px;
    right: 26px;
    z-index: 9999;

    background: linear-gradient(135deg, #a855f7, #7c3aed);
    color: white;
    border-radius: 50%;
    width: 68px;
    height: 68px;
    display: flex;
    align-items: center;
    justify-content: center;

    font-size: 32px;
    cursor: pointer;

    box-shadow: 0 0 25px rgba(168, 85, 247, 0.65);
    transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.refresh-btn:hover {
    transform: scale(1.15) rotate(190deg);
    box-shadow: 0 0 40px rgba(168, 85, 247, 0.95);
}

.refresh-btn:active {
    transform: scale(0.92);
}
</style>

<div class="refresh-btn" onclick="triggerRefresh()">
    🔄
</div>

<script>
function triggerRefresh() {
    window.parent.postMessage({isStreamlitMessage: true, type: "streamlit:setComponentValue", value: "refresh_now"}, "*");
}
</script>
""", unsafe_allow_html=True)

# Listener
if "refresh_now" in st.session_state and st.session_state["refresh_now"]:
    st.session_state["refresh_now"] = False
    st.rerun()


import pandas as pd
import plotly.express as px
import re
from datetime import datetime, timedelta
import requests
from io import BytesIO

st.set_page_config(page_title="Loja Importados – Dashboard", layout="wide", initial_sidebar_state="collapsed")



# --- Cálculo GLOBAL de Produtos Encalhados (limpo) ---
def compute_encalhados_global(dfs, limit=10):
    import pandas as _pd
    estoque = dfs.get("ESTOQUE", _pd.DataFrame()).copy()
    vendas = dfs.get("VENDAS", _pd.DataFrame()).copy()
    compras = dfs.get("COMPRAS", _pd.DataFrame()).copy()

    if not compras.empty:
        compras["DATA"] = _pd.to_datetime(compras["DATA"], errors="coerce")
    if not vendas.empty:
        vendas["DATA"] = _pd.to_datetime(vendas["DATA"], errors="coerce")

    if estoque.empty:
        return [], _pd.DataFrame()

    # última venda
    if not vendas.empty and "PRODUTO" in vendas.columns:
        last_sale = vendas.groupby("PRODUTO")["DATA"].max().reset_index().rename(columns={"DATA": "ULT_VENDA"})
    else:
        last_sale = _pd.DataFrame(columns=["PRODUTO", "ULT_VENDA"])

    # última compra
    if not compras.empty and "PRODUTO" in compras.columns:
        last_buy = compras.groupby("PRODUTO")["DATA"].max().reset_index().rename(columns={"DATA": "ULT_COMPRA"})
    else:
        last_buy = _pd.DataFrame(columns=["PRODUTO", "ULT_COMPRA"])

    enc = estoque.merge(last_sale, how="left", on="PRODUTO").merge(last_buy, how="left", on="PRODUTO")
    enc = enc[enc.get("EM ESTOQUE", 0) > 0].copy()

    today = _pd.Timestamp.now()
    enc["DIAS_PARADO"] = enc.apply(
        lambda row: (today - row["ULT_VENDA"]).days if _pd.notna(row["ULT_VENDA"])
        else (today - row["ULT_COMPRA"]).days if _pd.notna(row["ULT_COMPRA"])
        else 9999, axis=1
    )

    enc_sorted = enc.sort_values("DIAS_PARADO", ascending=False).head(limit)
    return enc_sorted["PRODUTO"].tolist(), enc_sorted


# --- Cálculo GLOBAL Top 5 mais vendidos ---
def compute_top5_global(dfs):
    import pandas as _pd
    vendas = dfs.get("VENDAS", _pd.DataFrame()).copy()
    if vendas.empty or "PRODUTO" not in vendas.columns:
        return []
    if "QTD" not in vendas.columns:
        for c in vendas.columns:
            if c.upper() in ("QTD","QUANTIDADE","QTY"):
                vendas["QTD"] = vendas[c]
                break
    vendas["QTD"] = vendas.get("QTD", 0).fillna(0).astype(int)
    top = vendas.groupby("PRODUTO")["QTD"].sum().sort_values(ascending=False).head(5)
    return list(top.index)


# --- Cálculo GLOBAL Top 5 mais vendidos ---
def compute_top5_global(dfs):
    import pandas as _pd
    vendas = dfs.get("VENDAS", _pd.DataFrame()).copy()
    if vendas.empty or "PRODUTO" not in vendas.columns:
        return []
    if "QTD" not in vendas.columns:
        # try to infer a quantity column
        for c in vendas.columns:
            if c.upper() in ("QTD","QUANTIDADE","QTY"):
                vendas["QTD"] = vendas[c]
                break
    vendas["QTD"] = vendas.get("QTD", 0).fillna(0).astype(int)
    top = vendas.groupby("PRODUTO")["QTD"].sum().sort_values(ascending=False).head(5)
    return top.index.tolist()

    _top5_list_global = []
    import pandas as _pd
    estoque_all = dfs.get("ESTOQUE", _pd.DataFrame()).copy()
    vendas_all = dfs.get("VENDAS", _pd.DataFrame()).copy()
    compras_all = dfs.get("COMPRAS", _pd.DataFrame()).copy()

    if not compras_all.empty:
        compras_all["DATA"] = _pd.to_datetime(compras_all["DATA"], errors="coerce")
    if not vendas_all.empty:
        vendas_all["DATA"] = _pd.to_datetime(vendas_all["DATA"], errors="coerce")

    if estoque_all.empty:
        return [], _pd.DataFrame()

    # last sale
    if not vendas_all.empty and "PRODUTO" in vendas_all.columns:
        last_sale = vendas_all.groupby("PRODUTO")["DATA"].max().reset_index().rename(columns={"DATA":"ULT_VENDA"})
    else:
        last_sale = _pd.DataFrame(columns=["PRODUTO","ULT_VENDA"])
    # last buy
    if not compras_all.empty and "PRODUTO" in compras_all.columns:
        last_buy = compras_all.groupby("PRODUTO")["DATA"].max().reset_index().rename(columns={"DATA":"ULT_COMPRA"})
    else:
        last_buy = _pd.DataFrame(columns=["PRODUTO","ULT_COMPRA"])

    enc = estoque_all.merge(last_sale, how="left", on="PRODUTO").merge(last_buy, how="left", on="PRODUTO")
    enc = enc[enc.get("EM ESTOQUE", 0) > 0].copy()

    today = _pd.Timestamp.now()

    def calc_days(row):
        if _pd.notna(row.get("ULT_VENDA")):
            return (today - row["ULT_VENDA"]).days
        if _pd.notna(row.get("ULT_COMPRA")):
            return (today - row["ULT_COMPRA"]).days
        return 9999

    enc["DIAS_PARADO"] = enc.apply(calc_days, axis=1)
    enc_sorted = enc.sort_values("DIAS_PARADO", ascending=False).head(limit)
    enc_list = enc_sorted["PRODUTO"].tolist()
    return enc_list, enc_sorted

# compute once and show alert
try:
    _enc_list_global, _enc_df_global = compute_encalhados_global(dfs, limit=10)
    if len(_enc_list_global) > 0:
        st.warning(f"❄️ Produtos encalhados detectados: {len(_enc_list_global)} — vá em VENDAS > Produtos encalhados para ver a lista.")
except Exception:
    _enc_list_global, _enc_df_global = [], None


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

.badge{
    padding:4px 8px;
    border-radius:8px;
    font-size:12px;
    display:inline-block;
    font-weight:700;
    letter-spacing:0.3px;
    animation:fadeIn 0.6s ease;
}

.low{
    background:rgba(255,0,0,0.25);
    color:#ffb4b4;
    box-shadow:0 0 8px rgba(255,0,0,0.35);
}
.hot{
    background:rgba(150,0,255,0.25);
    color:#e0b0ff;
    box-shadow:0 0 8px rgba(150,0,255,0.35);
}
.zero{
    background:rgba(255,255,255,0.1);
    color:#fff;
    box-shadow:0 0 8px rgba(255,255,255,0.15);
}

@keyframes fadeIn{
    from{opacity:0; transform:translateY(4px);}
    to{opacity:1; transform:translateY(0);}
}

.avatar{
    width:64px;height:64px;border-radius:14px;
    background:linear-gradient(120deg,#a78bfa,#ec4899,#06b6d4);
    background-size:300% 300%;
    animation:neonMove 6s ease infinite;
    display:flex;align-items:center;justify-content:center;
    color:white;font-weight:900;font-size:22px;
    box-shadow:0 4px 14px rgba(0,0,0,0.5);
}
@keyframes neonMove{
    0%{background-position:0% 50%;}
    50%{background-position:100% 50%;}
    100%{background-position:0% 50%;}
}

@keyframes pulseRed{0%{opacity:.7;}50%{opacity:1;}100%{opacity:.7;}}
@keyframes pulseOrange{0%{opacity:.7;}50%{opacity:1;}100%{opacity:.7;}}
@keyframes pulsePurple{0%{opacity:.7;}50%{opacity:1;}100%{opacity:.7;}}
@keyframes pulseGreen{0%{opacity:.7;}50%{opacity:1;}100%{opacity:.7;}}

.card-ecom:hover{
    transform:translateY(-2px);
    transition:.2s;
    box-shadow:0 8px 20px rgba(0,0,0,0.35);
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

# =============================
# Preparar tabela vendas
# =============================
def preparar_tabela_vendas(df):
    if df is None or df.empty: 
        return pd.DataFrame()

    d = df.copy()

    # DATA
    if "DATA" in d.columns:
        d["DATA"] = d["DATA"].dt.strftime("%d/%m/%Y")

    # Criar colunas caso não existam
    for c in ["VALOR VENDA", "VALOR TOTAL", "MEDIA CUSTO UNITARIO", "LUCRO UNITARIO", "QTD"]:
        if c not in d.columns:
            d[c] = 0

    # FORMATAR MOEDAS COM CENTAVOS
    try:
        d["VALOR VENDA"] = d["VALOR VENDA"].astype(float)
    except:
        pass
    try:
        d["VALOR TOTAL"] = d["VALOR TOTAL"].astype(float)
    except:
        pass
    try:
        d["MEDIA CUSTO UNITARIO"] = d["MEDIA CUSTO UNITARIO"].astype(float)
    except:
        pass
    try:
        d["LUCRO UNITARIO"] = d["LUCRO UNITARIO"].astype(float)
    except:
        pass

    d["VALOR VENDA"] = d["VALOR VENDA"].map(formatar_reais_com_centavos)
    d["VALOR TOTAL"] = d["VALOR TOTAL"].map(formatar_reais_com_centavos)
    d["MEDIA CUSTO UNITARIO"] = d["MEDIA CUSTO UNITARIO"].map(formatar_reais_com_centavos)
    d["LUCRO UNITARIO"] = d["LUCRO UNITARIO"].map(formatar_reais_com_centavos)

    # Remover colunas lixo
    d = d.loc[:, ~d.columns.astype(str).str.contains("^Unnamed|MES_ANO")]

    # Ordenação: mais recente primeiro
    if "DATA" in d.columns:
        try:
            d["_sort"] = pd.to_datetime(d["DATA"], format="%d/%m/%Y", errors="coerce")
            d = d.sort_values("_sort", ascending=False).drop(columns=["_sort"])
        except:
            pass

    
    # ensure raw values for lucro calculation
    try:
        d["VALOR VENDA_RAW"] = parse_money_series(df["VALOR VENDA"]).fillna(0)
    except:
        d["VALOR VENDA_RAW"] = pd.to_numeric(df["VALOR VENDA"], errors="coerce").fillna(0)

    try:
        d["CUSTO_RAW"] = parse_money_series(df["MEDIA CUSTO UNITARIO"]).fillna(0)
    except:
        d["CUSTO_RAW"] = pd.to_numeric(df["MEDIA CUSTO UNITARIO"], errors="coerce").fillna(0)

    # calculate lucro total
    try:
        d["LUCRO TOTAL"] = (d["VALOR VENDA_RAW"] - d["CUSTO_RAW"]) * d["QTD"]
    except:
        d["LUCRO TOTAL"] = 0

    # format lucro total
    try:
        d["LUCRO TOTAL"] = d["LUCRO TOTAL"].map(formatar_reais_com_centavos)
    except:
        d["LUCRO TOTAL"] = d["LUCRO TOTAL"].apply(lambda x: f"R$ {x:,.2f}".replace(',', 'X').replace('.', ',').replace('X','.') )

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
# === Inicializações corretas ===
try:
    _top5_list_global = compute_top5_global(dfs)
except Exception:
    _top5_list_global = []

try:
    _enc_list_global, _enc_df_global = compute_encalhados_global(dfs, limit=10)
except Exception:
    _enc_list_global, _enc_df_global = [], None



# =============================
# Conversores e ajustes
# =============================
# Normaliza colunas de estoque
if "ESTOQUE" in dfs:
    df_e = dfs["ESTOQUE"].copy()
    if "Media C. UNITARIO" in df_e.columns:
        df_e["Media C. UNITARIO"] = parse_money_series(df_e["Media C. UNITARIO"]).fillna(0)
    else:
        for alt in ["MEDIA C. UNITARIO","MEDIA CUSTO UNITARIO","MEDIA C. UNIT"]:
            if alt in df_e.columns:
                df_e["Media C. UNITARIO"] = parse_money_series(df_e[alt]).fillna(0)
                break
    if "Valor Venda Sugerido" in df_e.columns:
        df_e["Valor Venda Sugerido"] = parse_money_series(df_e["Valor Venda Sugerido"]).fillna(0)
    else:
        for alt in ["VALOR VENDA SUGERIDO","VALOR VENDA","VALOR_VENDA"]:
            if alt in df_e.columns:
                df_e["Valor Venda Sugerido"] = parse_money_series(df_e[alt]).fillna(0)
                break
    if "EM ESTOQUE" in df_e.columns:
        df_e["EM ESTOQUE"] = parse_int_series(df_e["EM ESTOQUE"]).fillna(0).astype(int)
    else:
        for alt in ["ESTOQUE","QTD","QUANTIDADE"]:
            if alt in df_e.columns:
                df_e["EM ESTOQUE"] = parse_int_series(df_e[alt]).fillna(0).astype(int)
                break
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
# TABS (AGORA APENAS 3)
# =============================
tabs = st.tabs(["🛒 VENDAS", "📦 ESTOQUE", "🔍 PESQUISAR"])

# =============================
# VENDAS
# =============================
with tabs[0]:

    st.subheader("Vendas — período selecionado")

    if vendas_filtradas.empty:
        st.info("Sem dados de vendas.")
    else:
        df_sem=vendas_filtradas.copy()
        df_sem["DATA"]=pd.to_datetime(df_sem["DATA"], errors="coerce")
        df_sem=df_sem.sort_values("DATA", ascending=False).reset_index(drop=True)
        df_sem["SEMANA"]=df_sem["DATA"].dt.isocalendar().week
        df_sem["ANO"]=df_sem["DATA"].dt.year

        def semana_intervalo(row):
            try:
                inicio=datetime.fromisocalendar(int(row["ANO"]), int(row["SEMANA"]), 1)
                fim=inicio+timedelta(days=6)
                return f"{inicio.strftime('%d/%m')} → {fim.strftime('%d/%m')}"
            except:
                return "N/A"

        df_sem_group=df_sem.groupby(["ANO","SEMANA"], dropna=False)["VALOR TOTAL"].sum().reset_index()

        if not df_sem_group.empty:
            df_sem_group["INTERVALO"]=df_sem_group.apply(semana_intervalo, axis=1)
            df_sem_group["LABEL"]=df_sem_group["VALOR TOTAL"].apply(formatar_reais_com_centavos)

            st.markdown("### 📊 Faturamento Semanal do Mês")

            fig_sem=px.bar(
                df_sem_group,
                x="INTERVALO",
                y="VALOR TOTAL",
                text="LABEL",
                color_discrete_sequence=["#8b5cf6"],
                height=380
            )
            plotly_dark_config(fig_sem)
            fig_sem.update_traces(textposition="inside", textfont_size=12)
            st.plotly_chart(fig_sem, use_container_width=True, config=dict(displayModeBar=False))

        st.markdown("### 📄 Tabela de Vendas (mais recentes primeiro)")
        tabela_vendas_exib=preparar_tabela_vendas(df_sem)
        st.dataframe(tabela_vendas_exib, use_container_width=True)

        # ---------------------
        # TOP 5 PRODUTOS BOMBANDO (por quantidade vendida)
        # ---------------------
        try:
            vendas_all = dfs.get("VENDAS", pd.DataFrame()).copy()
            if not vendas_all.empty and "PRODUTO" in vendas_all.columns:
                top5 = vendas_all.groupby("PRODUTO")["QTD"].sum().reset_index().sort_values("QTD", ascending=False).head(5)
                if not top5.empty:
                    st.markdown("""### 🔥 Top 5 — Produtos bombando (por unidades vendidas)
""", unsafe_allow_html=True)
                    # render as small table
                    top5["QTD"] = top5["QTD"].astype(int)
                    st.table(top5.rename(columns={"PRODUTO":"Produto","QTD":"Unidades"}))
        except Exception:
            pass

        
        # ---------------------
        # PRODUTOS ENCALHADOS — lógica profissional (global)
        # ---------------------
        try:
            estoque_all = dfs.get("ESTOQUE", pd.DataFrame()).copy()
            vendas_all = dfs.get("VENDAS", pd.DataFrame()).copy()
            compras_all = dfs.get("COMPRAS", pd.DataFrame()).copy()

            if not compras_all.empty:
                compras_all["DATA"] = pd.to_datetime(compras_all["DATA"], errors="coerce")

            if not vendas_all.empty:
                vendas_all["DATA"] = pd.to_datetime(vendas_all["DATA"], errors="coerce")

            if not estoque_all.empty:
                estoque_all = estoque_all.copy()

                # Última venda
                if not vendas_all.empty:
                    last_sale = vendas_all.groupby("PRODUTO")["DATA"].max().reset_index().rename(columns={"DATA":"ULT_VENDA"})
                else:
                    last_sale = pd.DataFrame(columns=["PRODUTO","ULT_VENDA"])

                # Última compra
                if not compras_all.empty:
                    last_buy = compras_all.groupby("PRODUTO")["DATA"].max().reset_index().rename(columns={"DATA":"ULT_COMPRA"})
                else:
                    last_buy = pd.DataFrame(columns=["PRODUTO","ULT_COMPRA"])

                enc = estoque_all.merge(last_sale, how="left", on="PRODUTO").merge(last_buy, how="left", on="PRODUTO")

                # Consider only products with estoque > 0
                enc = enc[enc["EM ESTOQUE"] > 0].copy()

                # Calculate days stopped
                today = pd.Timestamp.now()

                def calc_days(row):
                    if pd.notna(row["ULT_VENDA"]):
                        return (today - row["ULT_VENDA"]).days
                    if pd.notna(row["ULT_COMPRA"]):
                        return (today - row["ULT_COMPRA"]).days
                    return 9999  # extreme case

                enc["DIAS_PARADO"] = enc.apply(calc_days, axis=1)

                enc = enc.sort_values("DIAS_PARADO", ascending=False).head(10)

                if not enc.empty:
                    enc_display = enc[["PRODUTO","EM ESTOQUE","ULT_VENDA","ULT_COMPRA","DIAS_PARADO"]].copy()
                    enc_display["ULT_VENDA"] = enc_display["ULT_VENDA"].dt.strftime("%d/%m/%Y").fillna("—")
                    enc_display["ULT_COMPRA"] = enc_display["ULT_COMPRA"].dt.strftime("%d/%m/%Y").fillna("—")

                    st.markdown("### ❄️ Produtos encalhados (global) — baseado em última venda / compra e estoque atual")
                    st.table(enc_display.rename(columns={
                        "PRODUTO":"Produto",
                        "EM ESTOQUE":"Estoque",
                        "ULT_VENDA":"Última venda",
                        "ULT_COMPRA":"Última compra",
                        "DIAS_PARADO":"Dias parado"
                    }))
        except Exception as e:
            st.write("Erro encalhados:", e)




# =============================
# ESTOQUE
# =============================
with tabs[1]:

    if estoque_df.empty:
        st.info("Sem dados de estoque.")
    else:
        estoque_display=estoque_df.copy()
        estoque_display["VALOR_CUSTO_TOTAL_RAW"]=(estoque_display["Media C. UNITARIO"] * estoque_display["EM ESTOQUE"]).fillna(0)
        estoque_display["VALOR_VENDA_TOTAL_RAW"]=(estoque_display["Valor Venda Sugerido"] * estoque_display["EM ESTOQUE"]).fillna(0)

        st.markdown("### 🥧 Distribuição de estoque — fatias com quantidade")

        top_for_pie=estoque_display.sort_values("EM ESTOQUE", ascending=False).head(10)

        if not top_for_pie.empty:
            fig_pie=px.pie(
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
                title={"text": "Top itens por quantidade em estoque", "y":0.96, "x":0.5, "xanchor":"center"},
                showlegend=False,
                margin=dict(t=60,b=10,l=10,r=10)
            )
            plotly_dark_config(fig_pie)
            st.plotly_chart(fig_pie, use_container_width=True, config=dict(displayModeBar=False))
        else:
            st.info("Sem itens para gerar o gráfico.")

        estoque_clas=estoque_display.copy()
        estoque_clas["CUSTO_UNITARIO_FMT"]=estoque_clas["Media C. UNITARIO"].map(formatar_reais_com_centavos)
        estoque_clas["VENDA_SUGERIDA_FMT"]=estoque_clas["Valor Venda Sugerido"].map(formatar_reais_com_centavos)
        estoque_clas["VALOR_TOTAL_CUSTO_FMT"]=estoque_clas["VALOR_CUSTO_TOTAL_RAW"].map(formatar_reais_sem_centavos)
        estoque_clas["VALOR_TOTAL_VENDA_FMT"]=estoque_clas["VALOR_VENDA_TOTAL_RAW"].map(formatar_reais_sem_centavos)

        display_df=estoque_clas[[
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

        display_df=display_df.sort_values("EM ESTOQUE", ascending=False).reset_index(drop=True)

        st.markdown("### 📋 Estoque — visão detalhada")
        st.dataframe(display_df, use_container_width=True)







# =============================
# PESQUISAR (MODERNIZADA — FINAL CORRIGIDO)
# =============================
# =============================
# PESQUISAR — E-COMMERCE COMPLETO
# =============================

with tabs[2]:
    # ===== Modernized E-commerce Search / Grid =====
    st.markdown("""
    <style>
    /* glass + neon aesthetic for cards */
    .search-topbar { display:flex; gap:12px; align-items:center; margin-bottom:12px; }
    .glass-card { background: rgba(255,255,255,0.03); border-radius:14px; padding:10px; backdrop-filter: blur(6px) saturate(120%); -webkit-backdrop-filter: blur(6px); border:1px solid rgba(255,255,255,0.04); box-shadow: 0 6px 24px rgba(0,0,0,0.6); }
    .neon-btn { padding:8px 12px; border-radius:10px; border:1px solid rgba(167,139,250,0.12); font-weight:700; }
    .card-grid-ecom { display:grid; grid-template-columns: repeat(3,1fr); gap:16px; margin-top:12px; }
    @media(max-width:1200px){ .card-grid-ecom{grid-template-columns:repeat(2,1fr);} }
    @media(max-width:720px){ .card-grid-ecom{grid-template-columns:1fr;} }

    .card-ecom{
        background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01));
        border-radius:12px;
        padding:14px;
        border:1px solid rgba(167,139,250,0.06);
        display:flex;
        gap:12px;
        align-items:center;
        transition: transform .18s ease, box-shadow .18s ease;
        backdrop-filter: blur(4px);
    }
    .card-ecom:hover{ transform: translateY(-6px); box-shadow: 0 18px 40px rgba(139,92,246,0.12); }
    .avatar{ width:64px;height:64px;border-radius:14px; display:flex;align-items:center;justify-content:center; color:white;font-weight:900;font-size:22px; flex-shrink:0; }
    .avatar.neon{ background: linear-gradient(135deg,#8b5cf6,#ec4899); box-shadow: 0 6px 18px rgba(139,92,246,0.12); }
    .card-title{font-weight:900;font-size:15px;margin-bottom:4px;color:#fff;}
    .card-meta{font-size:12px;color:#cfcfe0;margin-bottom:6px;}
    .card-prices{display:flex;gap:10px;margin-bottom:6px;align-items:baseline;}
    .card-price{color:#a78bfa;font-weight:900;}
    .card-cost{color:#bdbdbd;font-weight:700;font-size:13px;}
    .badge{padding:4px 8px;border-radius:8px;font-size:12px;margin-right:6px;display:inline-block;}
    .low{background:rgba(255,69,96,0.12);color:#ffb4b4;border:1px solid rgba(255,69,96,0.06);}
    .hot{background:rgba(139,92,246,0.12);color:#e9d5ff;border:1px solid rgba(139,92,246,0.06);}
    .zero{background:rgba(255,255,255,0.04);color:#fff;border:1px solid rgba(255,255,255,0.03);}
    .small-muted { font-size:11px; color: #bdbdbd; margin-top:4px; }

    .controls { display:flex; gap:8px; align-items:center; flex-wrap:wrap; }
    .muted { color:#cfcfe0; font-size:13px; }

    </style>
    """, unsafe_allow_html=True)

    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    col_a, col_b = st.columns([3,2])
    with col_a:
        termo = st.text_input("🔎 Buscar produto", value="", placeholder="Digite o nome do produto...")
    with col_b:
        # modern controls row
        cols = st.columns([1,1,1,1])
        with cols[0]:
            itens_pagina = st.selectbox("Itens/pg", [6,9,12,24,36,48,60,100,200], index=2)
        with cols[1]:
            ordenar = st.selectbox("Ordenar por", [
                "Nome A–Z","Nome Z–A","Menor preço","Maior preço",
                "Mais vendidos","Maior estoque","Última compra (recente)","Última compra (antiga)"
            ], index=0)
        with cols[2]:
            grid_cols = st.selectbox("Colunas", [2,3,4], index=1)
        with cols[3]:
            ver_tudo = st.checkbox("Ver tudo (sem paginação)", value=False)
    st.markdown("</div>", unsafe_allow_html=True)

    # filtros avançados
    filtro_baixo = st.checkbox("⚠️ Baixo estoque (≤3)", value=False)
    filtro_alto = st.checkbox("📦 Alto estoque (≥20)", value=False)
    filtro_vendidos = st.checkbox("🔥 Com vendas", value=False)
    filtro_sem_venda = st.checkbox("❄️ Sem vendas", value=False)

    # build df copy
    df = estoque_df.copy()
    vendas_df = dfs.get("VENDAS", pd.DataFrame()).copy()
    if not vendas_df.empty and "QTD" in vendas_df.columns:
        vend = vendas_df.groupby("PRODUTO")["QTD"].sum().reset_index().rename(columns={"QTD":"TOTAL_QTD"})
        df = df.merge(vend,how="left",on="PRODUTO").fillna({"TOTAL_QTD":0})
    else:
        df["TOTAL_QTD"]=0

    # ultima compra map
    compras_df = dfs.get("COMPRAS", pd.DataFrame()).copy()
    ultima_compra = {}
    if not compras_df.empty and "DATA" in compras_df.columns and "PRODUTO" in compras_df.columns:
        compras_df = compras_df.dropna(subset=["PRODUTO"])
        compras_df["DATA"] = pd.to_datetime(compras_df["DATA"], errors="coerce")
        tmp = compras_df.groupby("PRODUTO")["DATA"].max().reset_index()
        ultima_compra = dict(zip(tmp["PRODUTO"], tmp["DATA"].dt.strftime("%d/%m/%Y")))

    # apply search & filters
    if termo and termo.strip():
        df = df[df["PRODUTO"].str.contains(termo, case=False, na=False)]
    if filtro_baixo:
        df = df[df["EM ESTOQUE"]<=3]
    if filtro_alto:
        df = df[df["EM ESTOQUE"]>=20]
    if filtro_vendidos:
        df = df[df["TOTAL_QTD"]>0]
    if filtro_sem_venda:
        df = df[df["TOTAL_QTD"]==0]

    # formatting
    df["CUSTO_FMT"] = df.get("Media C. UNITARIO", 0).map(formatar_reais_com_centavos)
    df["VENDA_FMT"] = df.get("Valor Venda Sugerido", 0).map(formatar_reais_com_centavos)

    # sorting
    if ordenar == "Nome A–Z":
        df = df.sort_values("PRODUTO", ascending=True)
    elif ordenar == "Nome Z–A":
        df = df.sort_values("PRODUTO", ascending=False)
    elif ordenar == "Menor preço":
        df = df.sort_values("Valor Venda Sugerido", ascending=True)
    elif ordenar == "Maior preço":
        df = df.sort_values("Valor Venda Sugerido", ascending=False)
    elif ordenar == "Mais vendidos":
        if "TOTAL_QTD" in df.columns:
            df = df.sort_values("TOTAL_QTD", ascending=False)
    elif ordenar == "Maior estoque":
        df = df.sort_values("EM ESTOQUE", ascending=False)
    elif ordenar == "Última compra (recente)":
        # ensure we have compras dataframe parsed
        if not compras_df.empty:
            tmp2 = compras_df.groupby("PRODUTO")["DATA"].max().reset_index()
            tmp2.columns = ["PRODUTO","ULT_COMPRA_RAW"]
            df = df.merge(tmp2, how="left", on="PRODUTO")
            df["ULT_COMPRA_RAW"] = pd.to_datetime(df["ULT_COMPRA_RAW"], errors="coerce")
            df = df.sort_values("ULT_COMPRA_RAW", ascending=False).drop(columns=["ULT_COMPRA_RAW"])
    elif ordenar == "Última compra (antiga)":
        if not compras_df.empty:
            tmp2 = compras_df.groupby("PRODUTO")["DATA"].max().reset_index()
            tmp2.columns = ["PRODUTO","ULT_COMPRA_RAW"]
            df = df.merge(tmp2, how="left", on="PRODUTO")
            df["ULT_COMPRA_RAW"] = pd.to_datetime(df["ULT_COMPRA_RAW"], errors="coerce")
            df = df.sort_values("ULT_COMPRA_RAW", ascending=True).drop(columns=["ULT_COMPRA_RAW"])

    total = len(df)

    # pagination
    if ver_tudo:
        itens_pagina = total if total>0 else 1
    else:
        itens_pagina = int(itens_pagina)

    total_paginas = max(1, (total + itens_pagina - 1)//itens_pagina)

    if "pagina" not in st.session_state:
        st.session_state["pagina"] = 1
    # clamp page
    st.session_state["pagina"] = max(1, min(st.session_state["pagina"], total_paginas))

    coln1, coln2, coln3 = st.columns([1,2,1])
    with coln1:
        if st.button("⬅️ Voltar"):
            st.session_state["pagina"] = max(1, st.session_state["pagina"]-1)
    with coln2:
        st.markdown(f"**Página {st.session_state['pagina']} de {total_paginas} — {total} resultados**")
    with coln3:
        if st.button("Avançar ➡️"):
            st.session_state["pagina"] = min(total_paginas, st.session_state["pagina"]+1)

    pagina = st.session_state["pagina"]
    inicio = (pagina-1)*itens_pagina
    fim = inicio + itens_pagina
    df_page = df.iloc[inicio:fim].reset_index(drop=True)

    # render grid with selected columns layout
    # inject dynamic grid style
    st.markdown(f"<style>.card-grid-ecom{{grid-template-columns: repeat({grid_cols},1fr);}}</style>", unsafe_allow_html=True)
    st.markdown("<div class='card-grid-ecom'>", unsafe_allow_html=True)

    for _, r in df_page.iterrows():
        nome = r.get("PRODUTO","")
        estoque = int(r.get("EM ESTOQUE",0)) if pd.notna(r.get("EM ESTOQUE",0)) else 0
        venda = r.get("VENDA_FMT","R$ 0")
        custo = r.get("CUSTO_FMT","R$ 0")
        vendidos = int(r.get("TOTAL_QTD",0)) if pd.notna(r.get("TOTAL_QTD",0)) else 0

        iniciais = "".join([p[0].upper() for p in str(nome).split()[:2] if p]) or "—"

        badges = []
        if estoque<=3: badges.append(f"<span class='badge low'>⚠️ Baixo</span>")
        if vendidos>=15: badges.append(f"<span class='badge hot'>🔥 Saindo</span>")
        if nome in ultima_compra and vendidos==0:
            vendas_produto = vendas_df[vendas_df['PRODUTO']==nome] if not vendas_df.empty else pd.DataFrame()
            if vendas_produto.empty: badges.append("<span class='badge slow'>❄️ Sem vendas</span>")
        try:
            if nome in _enc_list_global:
                badges.append("<span class='badge zero'>🐌 Encalhado</span>")
        except Exception:
            pass
        try:
            if nome in _top5_list_global:
                badges.append("<span class='badge hot'>🥇 Campeão</span>")
        except Exception:
            pass

        badges_html = " ".join(badges)
        ultima = ultima_compra.get(nome,"—")

        enc_style = ""
        try:
            if nome in _enc_list_global:
                enc_style="style='border-left:6px solid #ef4444; animation:pulseRed 2s infinite;'"
            elif nome in _top5_list_global:
                enc_style="style='border-left:6px solid #22c55e;'"
        except Exception:
            pass

        dias_sem_venda = ""
        try:
            vendas_prod = vendas_df[vendas_df["PRODUTO"]==nome] if not vendas_df.empty else pd.DataFrame()
            if not vendas_prod.empty:
                last = vendas_prod["DATA"].max()
                if pd.notna(last) and estoque>0:
                    delta = (pd.Timestamp.now() - last).days
                    if delta>=60:
                        cor="#ef4444"; icone="⛔"; pulse="pulseRed"
                    elif delta>=30:
                        cor="#f59e0b"; icone="⚠️"; pulse="pulseOrange"
                    elif delta>=7:
                        cor="#a78bfa"; icone="🕒"; pulse="pulsePurple"
                    else:
                        cor="#22c55e"; icone="✅"; pulse="pulseGreen"
                    dias_sem_venda = f"<div style='font-size:11px;margin-top:2px;color:{cor};animation:{pulse} 2s infinite;'>{icone} Dias sem vender: <b>{delta}</b></div>"
        except Exception:
            pass

        avatar_html = f"<div class='avatar neon'>{iniciais}</div>"
        card_html = (
            f"<div class='card-ecom' {enc_style}>"
            f"{avatar_html}"
            f"<div style='flex:1;'>"
            f"<div class='card-title'>{nome}</div>"
            f"<div class='card-meta'>Estoque: <b>{estoque}</b> • Vendidos: <b>{vendidos}</b></div>"
            f"<div class='card-prices'><div class='card-price'>{venda}</div><div class='card-cost'>{custo}</div></div>"
            f"<div style='font-size:11px;color:#9ca3af;margin-top:4px;'>🕒 Última compra: <b>{ultima}</b></div>"
            f"{dias_sem_venda}"
            f"<div style='margin-top:6px;'>{badges_html}</div>"
            f"</div>"
            f"</div>"
        )
        st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

