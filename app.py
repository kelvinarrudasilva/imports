# app.py — Loja Importados — Minimalista (roxo) + logo pequena + KPIs compactas + parser % robusto (2 casas)
import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime
import requests
from io import BytesIO

st.set_page_config(page_title="Loja Importados – Dashboard", layout="wide", initial_sidebar_state="collapsed")

# ----------------------------
# Config / Link fixo (não pede URL)
# ----------------------------
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b/export?format=xlsx"

# =============================
# CSS / Estilo minimalista
# =============================
st.markdown(
    """
    <style>
    :root{
      --bg: #ffffff;
      --accent: #8b5cf6;
      --accent-2: #6d28d9;
      --muted: #666666;
      --card-bg: #ffffff;
    }
    body, .stApp { background: var(--bg) !important; color: #111; font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial; }

    /* Top bar: logo + title */
    .topbar { display:flex; align-items:center; gap:12px; margin-bottom:8px; }
    .logo-wrap { width:44px; height:44px; display:flex; align-items:center; justify-content:center; border-radius:10px; background: linear-gradient(135deg,var(--accent),var(--accent-2)); box-shadow: 0 6px 18px rgba(109,40,217,0.12); }
    .logo-wrap svg { width:26px; height:26px; }
    .title { font-size:20px; font-weight:800; color:var(--accent-2); margin:0; line-height:1; }

    /* small subtitle */
    .subtitle { margin:0; font-size:12px; color:var(--muted); margin-top:2px; }

    /* filter + KPIs area */
    .controls { display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-bottom:10px; }

    /* KPI cards compact */
    .kpi-row { display:flex; gap:10px; align-items:center; }
    .kpi { background:var(--card-bg); border-radius:10px; padding:10px 14px; box-shadow:0 6px 16px rgba(13,12,20,0.04); border-left:6px solid var(--accent); min-width:160px; display:flex; flex-direction:column; justify-content:center; }
    .kpi h3 { margin:0; font-size:12px; color:var(--accent-2); font-weight:800; letter-spacing:0.2px; }
    .kpi .value { margin-top:6px; font-size:20px; font-weight:900; color:#111; white-space:nowrap; }

    /* ensure no line-break inside KPI container */
    .kpi, .kpi .value { white-space:nowrap; }

    /* Tabs: white style, spaced */
    .stTabs button { background: white !important; border:1px solid #f0eaff !important; border-radius:12px !important; padding:8px 14px !important; margin-right:8px !important; margin-bottom:8px !important; font-weight:700 !important; color:var(--accent-2) !important; box-shadow:0 3px 10px rgba(0,0,0,0.04) !important; }

    /* DataFrame header slight */
    .stDataFrame thead th { background:#fbf7ff !important; font-weight:700 !important; }

    /* make table font slightly smaller to fit mobile */
    .stDataFrame, .element-container { font-size:13px; }

    /* responsiveness */
    @media (max-width: 720px) {
      .kpi { min-width: 120px; padding:10px; }
      .title { font-size:18px; }
      .kpi .value { font-size:18px; }
      .controls { flex-direction:column; align-items:stretch; gap:8px; }
      .kpi-row { width:100%; justify-content:space-between; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================
# Top bar with small logo (option A) + title
# =============================
st.markdown(
    """
    <div class="topbar">
      <div class="logo-wrap">
        <!-- simple shopping/bolt icon SVG -->
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <rect x="3" y="3" width="18" height="18" rx="4" fill="white" fill-opacity="0.06"/>
          <path d="M7 9h10l-1 6H8L7 9z" stroke="white" stroke-opacity="0.95" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="M9 6l2-2 2 2" stroke="white" stroke-opacity="0.95" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <div>
        <div class="title">Loja Importados — Dashboard</div>
        <div class="subtitle">Visão rápida de vendas e estoque</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ----------------------------
# Helpers: parsing/formatting
# ----------------------------
def parse_money_value(x):
    try:
        if pd.isna(x):
            return float("nan")
    except:
        pass
    s = str(x).strip()
    if s == "" or s.lower() in ("nan","none","-"):
        return float("nan")
    # keep digits, comma, dot, minus
    s = re.sub(r"[^\d\.,\-]", "", s)
    # handle Brazilian formatting heuristics
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        if "," in s and "." not in s:
            s = s.replace(",", ".")
        if s.count(".") > 1:
            s = s.replace(".", "")
    s = re.sub(r"[^\d\.\-]", "", s)
    try:
        return float(s)
    except:
        return float("nan")

def parse_money_series(serie):
    if serie is None:
        return pd.Series(dtype="float64")
    return serie.astype(str).map(parse_money_value).astype("float64")

def parse_int_series(serie):
    def to_int(x):
        try:
            if pd.isna(x):
                return pd.NA
        except:
            pass
        s = re.sub(r"[^\d\-]", "", str(x))
        if s in ("", "-", "nan"):
            return pd.NA
        try:
            return int(float(s))
        except:
            return pd.NA
    return serie.map(to_int).astype("Int64")

def formatar_reais_sem_centavos(v):
    try:
        v = float(v)
    except:
        return "R$ 0"
    s = f"{v:,.0f}".replace(",", ".")
    return f"R$ {s}"

def formatar_colunas_moeda(df, col_list):
    for c in col_list:
        if c in df.columns:
            df[c] = df[c].fillna(0).map(lambda x: formatar_reais_sem_centavos(x))
    return df

# =============================
# carregar XLSX via requests (Google-export link)
# =============================
def carregar_xlsx_from_url(url):
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return pd.ExcelFile(BytesIO(resp.content))

# =============================
# Ler planilha e detectar abas
# =============================
try:
    xls = carregar_xlsx_from_url(URL_PLANILHA)
except Exception as e:
    st.error("Erro ao baixar/abrir a planilha. Verifique o link fixo e permissões.")
    st.exception(e)
    st.stop()

abas_all = [a for a in xls.sheet_names]

def detectar_linha_cabecalho(df_raw, keywords):
    for i in range(min(len(df_raw), 12)):
        linha = " ".join(df_raw.iloc[i].astype(str).str.upper().tolist())
        for kw in keywords:
            if kw.upper() in linha:
                return i
    return None

def limpar_aba_raw(df_raw, nome_aba):
    busca_map = {
        "ESTOQUE": ["PRODUTO", "EM ESTOQUE"],
        "VENDAS": ["DATA", "PRODUTO", "VALOR"],
        "COMPRAS": ["DATA", "PRODUTO", "CUSTO"]
    }
    keywords = busca_map.get(nome_aba, ["PRODUTO"])
    linha = detectar_linha_cabecalho(df_raw, keywords)
    if linha is None:
        return None
    df_tmp = df_raw.copy()
    df_tmp.columns = df_tmp.iloc[linha]
    df = df_tmp.iloc[linha+1:].copy()
    df.columns = [str(c).strip() for c in df.columns]
    # drop empty-name cols
    drop_cols = [c for c in df.columns if str(c).strip().lower() in ("nan","none","")]
    df = df.drop(columns=drop_cols, errors="ignore")
    df = df.loc[:, ~df.isna().all()]
    df = df.reset_index(drop=True)
    return df

colunas_esperadas = ["ESTOQUE","VENDAS","COMPRAS"]
dfs = {}
for aba in colunas_esperadas:
    if aba in abas_all:
        raw = pd.read_excel(URL_PLANILHA, sheet_name=aba, header=None)
        cleaned = limpar_aba_raw(raw, aba)
        if cleaned is not None:
            dfs[aba] = cleaned
        else:
            st.warning(f"Aba {aba} — cabeçalho não identificado (pulei).")

# =============================
# Conversões por aba (seguras)
# =============================
if "ESTOQUE" in dfs:
    df_e = dfs["ESTOQUE"]
    if "Media C. UNITARIO" in df_e.columns:
        df_e["Media C. UNITARIO"] = parse_money_series(df_e["Media C. UNITARIO"])
    if "Valor Venda Sugerido" in df_e.columns:
        df_e["Valor Venda Sugerido"] = parse_money_series(df_e["Valor Venda Sugerido"])
    if "EM ESTOQUE" in df_e.columns:
        df_e["EM ESTOQUE"] = parse_int_series(df_e["EM ESTOQUE"]).fillna(0)
    if "VENDAS" in df_e.columns:
        df_e["VENDAS"] = parse_int_series(df_e["VENDAS"]).fillna(0)
    dfs["ESTOQUE"] = df_e

if "VENDAS" in dfs:
    df_v = dfs["VENDAS"].copy()
    df_v.columns = [str(c).strip() for c in df_v.columns]
    # normalize names: some sheets use slight variations; keep original names but try to detect alternatives
    # parse money columns if present
    money_candidates = {
        "VALOR VENDA": ["VALOR VENDA", "VALOR_VENDA", "VALORVENDA"],
        "VALOR TOTAL": ["VALOR TOTAL","VALOR_TOTAL","VALORTOTAL"],
        "MEDIA CUSTO UNITARIO": ["MEDIA C. UNITARIO","MEDIA CUSTO UNITARIO","MEDIA_CUSTO_UNITARIO","MEDIA CUSTO UNITARIO"],
        "LUCRO UNITARIO": ["LUCRO UNITARIO","LUCRO_UNITARIO"]
    }
    for target, variants in money_candidates.items():
        for v in variants:
            if v in df_v.columns:
                df_v[target] = parse_money_series(df_v[v])
                break

    # ensure QTD
    possible_qtd = [c for c in df_v.columns if c.upper() in ("QTD","QUANTIDADE","QTY")]
    if possible_qtd:
        df_v["QTD"] = parse_int_series(df_v[possible_qtd[0]]).fillna(0)
    # dates
    if "DATA" in df_v.columns:
        df_v["DATA"] = pd.to_datetime(df_v["DATA"], errors="coerce")
        df_v["MES_ANO"] = df_v["DATA"].dt.strftime("%Y-%m")
    else:
        df_v["MES_ANO"] = pd.NA

    # derive VALOR TOTAL if missing
    if "VALOR TOTAL" not in df_v.columns and "VALOR VENDA" in df_v.columns:
        df_v["VALOR TOTAL"] = df_v["VALOR VENDA"].fillna(0) * df_v.get("QTD", 0).fillna(0)
    # derive LUCRO UNITARIO if missing
    if "LUCRO UNITARIO" not in df_v.columns and ("VALOR VENDA" in df_v.columns and "MEDIA CUSTO UNITARIO" in df_v.columns):
        df_v["LUCRO UNITARIO"] = df_v["VALOR VENDA"].fillna(0) - df_v["MEDIA CUSTO UNITARIO"].fillna(0)

    # if % DE LUCRO SOBRE CUSTO exists in sheet, we'll parse it later (string with emoji etc)
    dfs["VENDAS"] = df_v

if "COMPRAS" in dfs:
    df_c = dfs["COMPRAS"]
    # try standard column names for parsing
    qty_cols = [c for c in df_c.columns if "QUANT" in str(c).upper()]
    if qty_cols:
        df_c["QUANTIDADE"] = parse_int_series(df_c[qty_cols[0]]).fillna(0)
    cost_cols = [c for c in df_c.columns if any(k in str(c).upper() for k in ("CUSTO","UNIT"))]
    if cost_cols:
        df_c["CUSTO UNITÁRIO"] = parse_money_series(df_c[cost_cols[0]]).fillna(0)
    df_c["CUSTO TOTAL (RECALC)"] = df_c.get("QUANTIDADE",0).fillna(0) * df_c.get("CUSTO UNITÁRIO",0).fillna(0)
    if "DATA" in df_c.columns:
        df_c["DATA"] = pd.to_datetime(df_c["DATA"], errors="coerce")
        df_c["MES_ANO"] = df_c["DATA"].dt.strftime("%Y-%m")
    dfs["COMPRAS"] = df_c

# =============================
# filtro por mês UI
# =============================
meses = []
if "VENDAS" in dfs:
    meses = sorted(dfs["VENDAS"]["MES_ANO"].dropna().unique().tolist(), reverse=True)
mes_opcoes = ["Todos"] + meses
mes_atual = datetime.now().strftime("%Y-%m")
index_padrao = mes_opcoes.index(mes_atual) if mes_atual in mes_opcoes else 0

# controls row: month filter + KPIs
col_filter, col_kpis = st.columns([1,2], gap="small")
with col_filter:
    mes_selecionado = st.selectbox("Filtrar por mês (YYYY-MM):", mes_opcoes, index=index_padrao)

# helper to filter month
def filtrar_mes_df(df, mes):
    if df is None or df.empty:
        return df
    if mes == "Todos":
        return df
    if "MES_ANO" in df.columns:
        return df[df["MES_ANO"] == mes].copy()
    return df

vendas_filtradas = filtrar_mes_df(dfs.get("VENDAS", pd.DataFrame()), mes_selecionado)
compras_filtradas = filtrar_mes_df(dfs.get("COMPRAS", pd.DataFrame()), mes_selecionado)
estoque_df = dfs.get("ESTOQUE", pd.DataFrame())

# compute KPIs (compact, right after filter)
total_vendido = vendas_filtradas["VALOR TOTAL"].fillna(0).sum() if vendas_filtradas is not None and "VALOR TOTAL" in vendas_filtradas else 0
total_lucro = (vendas_filtradas["LUCRO UNITARIO"].fillna(0) * vendas_filtradas["QTD"].fillna(0)).sum() if vendas_filtradas is not None and "LUCRO UNITARIO" in vendas_filtradas else 0
total_compras = compras_filtradas["CUSTO TOTAL (RECALC)"].fillna(0).sum() if compras_filtradas is not None and "CUSTO TOTAL (RECALC)" in compras_filtradas else 0

with col_kpis:
    st.markdown(
        f"""
        <div class="kpi-row">
          <div class="kpi"><h3>💵 Total Vendido</h3><div class="value">{formatar_reais_sem_centavos(total_vendido)}</div></div>
          <div class="kpi" style="border-left-color:#34d399;"><h3>🧾 Total Lucro</h3><div class="value">{formatar_reais_sem_centavos(total_lucro)}</div></div>
          <div class="kpi" style="border-left-color:#f59e0b;"><h3>💸 Total Compras</h3><div class="value">{formatar_reais_sem_centavos(total_compras)}</div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# =============================
# preparar exibição das tabelas
# =============================
def preparar_tabela_vendas(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df_show = df.copy()

    # format date
    if "DATA" in df_show.columns:
        df_show["DATA"] = df_show["DATA"].dt.strftime("%d/%m/%Y")

    # ensure common columns exist (avoid KeyError later)
    for col in ["VALOR VENDA","VALOR TOTAL","MEDIA CUSTO UNITARIO","LUCRO UNITARIO","% DE LUCRO SOBRE CUSTO","QTD"]:
        if col not in df_show.columns:
            df_show[col] = 0

    # format monetary columns (safe)
    df_show = formatar_colunas_moeda(df_show, ["VALOR VENDA","VALOR TOTAL","MEDIA CUSTO UNITARIO","LUCRO UNITARIO"])

    # parse "% DE LUCRO SOBRE CUSTO" — this column can contain "294% ✅" or "0"
    if "% DE LUCRO SOBRE CUSTO" in df_show.columns:
        raw = df_show["% DE LUCRO SOBRE CUSTO"].astype(str)
        # remove emojis and any non numeric / comma / dot / minus characters
        cleaned = (
            raw
            .str.replace(r"[^0-9,.\-]", "", regex=True)   # keep digits, comma, dot, minus
            .str.replace(",", ".", regex=False)
            .str.strip()
        )
        pct = pd.to_numeric(cleaned, errors="coerce").fillna(0)  # now numeric, e.g. 294 -> 294.0
        # format with two decimals and percent sign (as user requested "0.00%")
        df_show["% DE LUCRO SOBRE CUSTO"] = pct.map(lambda x: f"{float(x):.2f}%")

    # remove any 'Unnamed' or fully-empty columns just in case
    df_show = df_show.loc[:, ~df_show.columns.astype(str).str.contains("^Unnamed")]
    df_show = df_show.loc[:, ~df_show.columns.isnull()]

    return df_show

# =============================
# Tabs and content
# =============================
tabs = st.tabs(["🛒 VENDAS","🏆 TOP10 (VALOR)","🏅 TOP10 (QTD)","📦 ESTOQUE","🔍 PESQUISAR"])

with tabs[0]:
    st.subheader("Vendas — período selecionado")
    if vendas_filtradas is None or vendas_filtradas.empty:
        st.info("Sem dados de vendas para o período selecionado.")
    else:
        st.dataframe(preparar_tabela_vendas(vendas_filtradas), use_container_width=True)

with tabs[1]:
    st.subheader("Top 10 — por VALOR (R$)")
    if vendas_filtradas is None or vendas_filtradas.empty:
        st.info("Sem dados.")
    else:
        dfv = vendas_filtradas.copy()
        if "VALOR TOTAL" not in dfv.columns and "VALOR VENDA" in dfv.columns:
            dfv["VALOR TOTAL"] = dfv["VALOR VENDA"].fillna(0) * dfv.get("QTD",0).fillna(0)
        top_val = dfv.groupby("PRODUTO", dropna=False).agg(VALOR_TOTAL=("VALOR TOTAL","sum"), QTD_TOTAL=("QTD","sum")).reset_index().sort_values("VALOR_TOTAL", ascending=False).head(10)
        top_val["VALOR_TOTAL_LABEL"] = top_val["VALOR_TOTAL"].apply(formatar_reais_sem_centavos)
        fig = px.bar(top_val, x="PRODUTO", y="VALOR_TOTAL", text="VALOR_TOTAL_LABEL", hover_data=["QTD_TOTAL"], color_discrete_sequence=["#8b5cf6"])
        fig.update_traces(textposition="inside")
        fig.update_layout(margin=dict(t=30,b=30,l=10,r=10), xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
        display_top = top_val.copy()
        display_top["VALOR_TOTAL"] = display_top["VALOR_TOTAL"].map(formatar_reais_sem_centavos)
        st.dataframe(display_top.drop(columns=["VALOR_TOTAL_LABEL"]), use_container_width=True)

with tabs[2]:
    st.subheader("Top 10 — por QUANTIDADE")
    if vendas_filtradas is None or vendas_filtradas.empty:
        st.info("Sem dados.")
    else:
        dfq = vendas_filtradas.copy()
        if "QTD" not in dfq.columns:
            dfq["QTD"] = 0
        top_q = dfq.groupby("PRODUTO", dropna=False)["QTD"].sum().reset_index().sort_values("QTD", ascending=False).head(10)
        fig2 = px.bar(top_q, x="PRODUTO", y="QTD", text="QTD", color_discrete_sequence=["#6d28d9"])
        fig2.update_traces(textposition="inside")
        fig2.update_layout(margin=dict(t=30,b=30,l=10,r=10), xaxis_tickangle=-45)
        st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(top_q, use_container_width=True)

with tabs[3]:
    st.subheader("Consulta do Estoque")
    if estoque_df is None or estoque_df.empty:
        st.info("Aba ESTOQUE não encontrada ou vazia.")
    else:
        df_e = estoque_df.copy()
        if "EM ESTOQUE" in df_e.columns:
            df_e["EM ESTOQUE"] = pd.to_numeric(df_e["EM ESTOQUE"], errors="coerce").fillna(0).astype(int)
            df_e = df_e.sort_values("EM ESTOQUE", ascending=False)
        df_e = formatar_colunas_moeda(df_e, ["Media C. UNITARIO","Valor Venda Sugerido"])
        st.dataframe(df_e.reset_index(drop=True), use_container_width=True)

with tabs[4]:
    st.subheader("Pesquisar produto no Estoque")
    termo = st.text_input("Digite o nome do produto (busca em ESTOQUE):")
    if termo:
        if estoque_df is None or estoque_df.empty:
            st.info("Aba Estoque vazia ou não existe.")
        else:
            df_s = estoque_df[estoque_df["PRODUTO"].str.contains(termo, case=False, na=False)].copy()
            if df_s.empty:
                st.info("Nenhum produto encontrado.")
            else:
                df_s = formatar_colunas_moeda(df_s, ["Media C. UNITARIO","Valor Venda Sugerido"])
                st.dataframe(df_s.reset_index(drop=True), use_container_width=True)

st.success("✅ Dashboard carregado com sucesso!")
