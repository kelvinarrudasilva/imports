# app.py — Dashboard Loja Importados (Roxo Minimalista) — Dark Theme Mobile
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
# CSS
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
body, .stApp { background: var(--bg) !important; color:#f0f0f0 !important; font-family: Inter, system-ui; }

.topbar { display:flex; align-items:center; gap:12px; margin-bottom:8px; }
.logo-wrap { width:44px; height:44px; display:flex; align-items:center; justify-content:center; border-radius:10px; background: linear-gradient(135deg,var(--accent),var(--accent-2)); box-shadow: 0 6px 18px rgba(0,0,0,0.5); }

.title { font-size:20px; font-weight:800; color:var(--accent-2); margin:0; }
.subtitle { margin:0; font-size:12px; color:var(--muted); }

.kpi-row { display:flex; gap:10px; flex-wrap:wrap; }
.kpi { background:#141414; border-radius:10px; padding:10px 14px; border-left:6px solid var(--accent); min-width:160px; }

.kpi h3 { margin:0; font-size:12px; color:var(--accent-2); font-weight:800; }
.kpi .value { margin-top:6px; font-size:20px; font-weight:900; }

.stTabs button {
  background:#1e1e1e !important; border-radius:12px !important;
  padding:8px 14px !important; margin-right:8px !important;
  font-weight:700 !important; color:var(--accent-2) !important;
  border:1px solid #333 !important; box-shadow:0 3px 10px rgba(0,0,0,0.2);
}

/* Cards de busca (vai ser usado depois) */
.search-card { background:#141414; padding:16px; border-radius:14px;
               border:1px solid rgba(255,255,255,0.04);
               box-shadow:0 6px 18px rgba(0,0,0,0.6); }

.search-card:hover { transform: translateY(-4px); transition:0.12s; }

/* GRID – PC = 2 colunas | Mobile = 1 */
.card-grid { 
  display:grid; 
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); 
  gap:18px; 
  margin-top:16px;
}

/* Mobile tweak */
@media (max-width: 600px) {
  .card-grid { grid-template-columns: 1fr; }
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
# HELPERS
# =============================
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
        if "," in s and "." not in s:
            s=s.replace(",",".")
    s=re.sub(r"[^\d\.\-]","",s)
    try: return float(s)
    except: return float("nan")

def parse_money_series(serie):
    return serie.astype(str).map(parse_money_value).astype("float64")

def parse_int_series(serie):
    def to_int(x):
        try:
            if pd.isna(x): return pd.NA
        except: pass
        s=re.sub(r"[^\d]","",str(x))
        return int(s) if s.isdigit() else pd.NA
    return serie.map(to_int).astype("Int64")


def formatar_reais_sem_centavos(v):
    try: v=float(v)
    except: return "R$ 0"
    return f"R$ {f'{v:,.0f}'.replace(',', '.')}"

def formatar_reais_com_centavos(v):
    try: v=float(v)
    except: return "R$ 0,00"
    s=f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {s}"


# =============================
# Carregar planilha
# =============================
def carregar_xlsx_from_url(url):
    r=requests.get(url,timeout=20)
    r.raise_for_status()
    return pd.ExcelFile(BytesIO(r.content))

try:
    xls = carregar_xlsx_from_url(URL_PLANILHA)
except:
    st.error("Erro ao carregar arquivo.")
    st.stop()


# =============================
# Limpeza inicial
# =============================
def detectar_linha_cabecalho(df_raw,keywords):
    for i in range(12):
        linha=" ".join(df_raw.iloc[i].astype(str).str.upper().tolist())
        if any(k.upper() in linha for k in keywords):
            return i
    return None

def limpar_aba_raw(df_raw,nome):
    busca={"ESTOQUE":["PRODUTO","ESTOQUE"], "VENDAS":["DATA","PRODUTO"], "COMPRAS":["CUSTO","DATA"]}.get(nome, ["PRODUTO"])
    pos=detectar_linha_cabecalho(df_raw, busca)
    if pos is None: return None
    df=df_raw.copy()
    df.columns=df.iloc[pos]
    df=df.iloc[pos+1:]
    df=df.loc[:,~df.columns.astype(str).str.contains("Unnamed")]
    return df.reset_index(drop=True)


dfs={}
for aba in ["ESTOQUE","VENDAS","COMPRAS"]:
    try:
        raw=pd.read_excel(URL_PLANILHA, sheet_name=aba, header=None)
        dfs[aba]=limpar_aba_raw(raw, aba)
    except:
        pass


# =============================
# Ajustar ESTOQUE
# =============================
df_e = dfs.get("ESTOQUE", pd.DataFrame()).copy()

if not df_e.empty:
    # nomes padrão
    df_e.columns=[str(c).strip() for c in df_e.columns]

    # custo
    custo_cols=["Media C. UNITARIO","CUSTO","CUSTO UNIT","MEDIA CUSTO UNITARIO"]
    for c in custo_cols:
        if c in df_e.columns:
            df_e["Media C. UNITARIO"]=parse_money_series(df_e[c])
            break
    df_e["Media C. UNITARIO"]=df_e.get("Media C. UNITARIO",0).fillna(0)

    # venda
    venda_cols=["Valor Venda Sugerido","VALOR VENDA","VENDA","PRECO"]
    for c in venda_cols:
        if c in df_e.columns:
            df_e["Valor Venda Sugerido"]=parse_money_series(df_e[c])
            break
    df_e["Valor Venda Sugerido"]=df_e.get("Valor Venda Sugerido",0).fillna(0)

    # estoque
    qtd_cols=["EM ESTOQUE","ESTOQUE","QTD"]
    for c in qtd_cols:
        if c in df_e.columns:
            df_e["EM ESTOQUE"]=parse_int_series(df_e[c]).fillna(0).astype(int)
            break

    if "PRODUTO" not in df_e.columns:
        # pega a primeira coluna texto
        for c in df_e.columns:
            if df_e[c].dtype==object:
                df_e=df_e.rename(columns={c:"PRODUTO"})
                break

    dfs["ESTOQUE"]=df_e

# =============================
# Ajustar VENDAS
# =============================
df_v = dfs.get("VENDAS", pd.DataFrame()).copy()

if not df_v.empty:
    df_v.columns=[str(c).strip() for c in df_v.columns]

    money_map={"VALOR VENDA":["VALOR VENDA","VENDA"], "VALOR TOTAL":["VALOR TOTAL"]}
    for target,vars_ in money_map.items():
        for v in vars_:
            if v in df_v.columns:
                df_v[target]=parse_money_series(df_v[v])
                break

    if "QTD" in df_v.columns:
        df_v["QTD"]=parse_int_series(df_v["QTD"]).fillna(0).astype(int)

    df_v["DATA"]=pd.to_datetime(df_v.get("DATA"), errors="coerce")
    df_v["MES_ANO"]=df_v["DATA"].dt.strftime("%Y-%m")

    df_v=df_v.sort_values("DATA", ascending=False).reset_index(drop=True)
    dfs["VENDAS"]=df_v

# =============================
# KPIs e filtros
# =============================
estoque_df=df_e.copy()

valor_custo_estoque=(estoque_df["Media C. UNITARIO"]*estoque_df["EM ESTOQUE"]).sum()
valor_venda_estoque=(estoque_df["Valor Venda Sugerido"]*estoque_df["EM ESTOQUE"]).sum()
quantidade_total_itens=int(estoque_df["EM ESTOQUE"].sum())

# Filtro de mês
meses=["Todos"]
if not df_v.empty:
    meses+=sorted(df_v["MES_ANO"].dropna().unique(), reverse=True)

mes_atual=datetime.now().strftime("%Y-%m")
index_padrao=meses.index(mes_atual) if mes_atual in meses else 0

col_f, col_k=st.columns([1,3])
with col_f:
    mes_selecionado=st.selectbox("Filtrar por mês (YYYY-MM):", meses, index=index_padrao)

def filtrar_mes(df,mes):
    if df.empty or mes=="Todos": return df
    return df[df["MES_ANO"]==mes].copy()

vendas_filtradas=filtrar_mes(df_v, mes_selecionado)
compras_filtradas=dfs.get("COMPRAS", pd.DataFrame()).copy()

total_vendido=vendas_filtradas.get("VALOR TOTAL",0).sum()
total_lucro=0
try:
    total_lucro=(vendas_filtradas["VALOR VENDA"]-vendas_filtradas["VALOR TOTAL"]).sum()
except:
    pass
total_compras=compras_filtradas.get("CUSTO TOTAL",0).sum()

# KPIs
with col_k:
    st.markdown(f"""
    <div class="kpi-row">
      <div class="kpi"><h3>💵 Total Vendido</h3><div class="value">{formatar_reais_sem_centavos(total_vendido)}</div></div>
      <div class="kpi" style="border-left-color:#34d399;"><h3>🧾 Lucro</h3><div class="value">{formatar_reais_sem_centavos(total_lucro)}</div></div>
      <div class="kpi" style="border-left-color:#f59e0b;"><h3>💸 Compras</h3><div class="value">{formatar_reais_sem_centavos(total_compras)}</div></div>
      <div class="kpi" style="border-left-color:#8b5cf6;"><h3>📦 Custo Estoque</h3><div class="value">{formatar_reais_sem_centavos(valor_custo_estoque)}</div></div>
      <div class="kpi" style="border-left-color:#a78bfa;"><h3>🏷️ Venda Estoque</h3><div class="value">{formatar_reais_sem_centavos(valor_venda_estoque)}</div></div>
      <div class="kpi" style="border-left-color:#6ee7b7;"><h3>🔢 Total Itens</h3><div class="value">{quantidade_total_itens}</div></div>
    </div>
    """, unsafe_allow_html=True)

# =============================
# TABS
# =============================
tabs = st.tabs(["🛒 VENDAS","📦 ESTOQUE","🔍 PESQUISAR"])

# =============================
# TAB: VENDAS
# =============================
with tabs[0]:
    st.subheader("Vendas — período selecionado")
    if vendas_filtradas.empty:
        st.info("Sem dados.")
    else:
        df_temp=vendas_filtradas.copy()
        df_temp["DATA"]=pd.to_datetime(df_temp["DATA"], errors="coerce")
        df_temp=df_temp.sort_values("DATA", ascending=False).reset_index(drop=True)

        st.dataframe(df_temp, use_container_width=True)

# =============================
# TAB: ESTOQUE
# =============================
with tabs[1]:
    st.subheader("📋 Estoque — visão detalhada")

    if estoque_df.empty:
        st.info("Sem dados de estoque.")
    else:
        df_show=estoque_df.copy()
        df_show["CUSTO"]=df_show["Media C. UNITARIO"].map(formatar_reais_com_centavos)
        df_show["VENDA"]=df_show["Valor Venda Sugerido"].map(formatar_reais_com_centavos)

        st.dataframe(df_show[["PRODUTO","EM ESTOQUE","CUSTO","VENDA"]], use_container_width=True)

# ============================================================
# AQUI TERMINA O BLOCO 1
# ============================================================


# =============================
# TAB: PESQUISAR (TOTALMENTE REFEITA)
# =============================
with tabs[2]:

    st.subheader("🔍 Pesquisar produtos — visão moderna")

    st.markdown("""
    <style>
    /* grid de cards — 2 colunas no PC, 1 no mobile */
    .card-grid {
        display:grid;
        grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
        gap:18px;
        margin-top:14px;
    }
    @media (max-width: 600px) {
        .card-grid { grid-template-columns: 1fr; }
    }

    .search-card {
        background:#141414;
        padding:16px;
        border-radius:14px;
        border:1px solid rgba(255,255,255,0.05);
        box-shadow:0 6px 18px rgba(0,0,0,0.55);
        transition:transform .12s ease;
    }
    .search-card:hover {
        transform: translateY(-6px);
        border-color: rgba(167,139,250,0.25);
    }

    .search-title {
        font-size:16px;
        font-weight:800;
        color:#a78bfa;
        margin-bottom:6px;
    }

    .meta {
        font-size:13px;
        color:#d4d4d4;
        line-height:1.5;
    }

    /* badges simplificados: só estoque e saída */
    .badge {
        background:#222;
        padding:4px 8px;
        border-radius:8px;
        font-size:12px;
        margin-right:6px;
        border:1px solid #333;
        color:#eee;
    }
    .low { background:#4b0000; border-color:#ff5b5b; }
    .hot { background:#2b0030; border-color:#c77dff; }
    .zero { background:#2f2f2f; border-color:#666; }

    </style>
    """, unsafe_allow_html=True)

    # ===========================
    # Campo de busca
    # ===========================
    col_s1, col_s2 = st.columns([3,1])
    with col_s1:
        termo = st.text_input("Procurar produto", placeholder="Digite o nome ou parte dele...")
    with col_s2:
        limpar = st.button("Limpar")

    if limpar:
        termo = ""
        st.experimental_rerun()

    # ===========================
    # Filtros rápidos
    # ===========================
    f1, f2, f3 = st.columns(3)
    filtro_baixo = f1.checkbox("⚠️ Estoque baixo (≤ 3)")
    filtro_alto = f2.checkbox("📦 Estoque alto (≥ 20)")
    filtro_vendidos = f3.checkbox("🔥 Com vendas")

    # ordenar
    ordenar = st.selectbox("Ordenar por:", 
                           ["Relevância","Nome A–Z","Estoque (maior→menor)","Preço (maior→menor)"])

    # pagination
    colp1, colp2 = st.columns([1,1])
    per_page = colp1.selectbox("Itens por página", [6,8,10,12], index=1)
    page = colp2.number_input("Página", min_value=1, value=1, step=1)

    df_src = estoque_df.copy()

    if df_src.empty:
        st.info("Sem dados de estoque.")
    else:
        # unificar vendas p/ badge de movimento
        df_v_ag = df_v.groupby("PRODUTO", dropna=False)["QTD"].sum().reset_index()
        df_v_ag = df_v_ag.rename(columns={"QTD":"TOTAL_VENDAS"})

        df = df_src.merge(df_v_ag, how="left", on="PRODUTO").fillna({"TOTAL_VENDAS":0})

        # BUSCA
        if termo.strip():
            df = df[df["PRODUTO"].str.contains(termo, case=False, na=False)]

        # FILTROS
        if filtro_baixo:
            df = df[df["EM ESTOQUE"] <= 3]

        if filtro_alto:
            df = df[df["EM ESTOQUE"] >= 20]

        if filtro_vendidos:
            df = df[df["TOTAL_VENDAS"] > 0]

        # ORDENAR
        if ordenar == "Nome A–Z":
            df = df.sort_values("PRODUTO")
        elif ordenar == "Estoque (maior→menor)":
            df = df.sort_values("EM ESTOQUE", ascending=False)
        elif ordenar == "Preço (maior→menor)":
            df = df.sort_values("Valor Venda Sugerido", ascending=False)
        else:
            df = df.sort_values(["TOTAL_VENDAS","EM ESTOQUE"], ascending=[False,False])

        # PAGINAÇÃO
        total_itens = len(df)
        total_pages = max(1, (total_itens + per_page - 1) // per_page)
        page = min(page, total_pages)
        start = (page - 1) * per_page
        df_page = df.iloc[start:start+per_page]

        st.markdown(f"**Resultados:** {total_itens} itens — página {page}/{total_pages}")

        if df_page.empty:
            st.info("Nenhum produto encontrado.")
        else:
            st.markdown("<div class='card-grid'>", unsafe_allow_html=True)

            for _, r in df_page.iterrows():
                nome = r["PRODUTO"]
                estoque = int(r["EM ESTOQUE"])
                preco = formatar_reais_com_centavos(r["Valor Venda Sugerido"])
                custo = formatar_reais_com_centavos(r["Media C. UNITARIO"])
                vendidos = int(r["TOTAL_VENDAS"])

                # BADGES — apenas 3 tipos
                badges = []
                if estoque <= 3:
                    badges.append("<span class='badge low'>⚠️ Baixo estoque</span>")
                if vendidos >= 15:
                    badges.append("<span class='badge hot'>🔥 Saindo muito</span>")
                if vendidos == 0:
                    badges.append("<span class='badge zero'>❄️ Sem vendas</span>")

                st.markdown(f"""
                <div class='search-card'>
                    <div class='search-title'>{nome}</div>
                    <div>{" ".join(badges)}</div>
                    <div class='meta'>
                        Estoque: <b>{estoque}</b><br>
                        Preço: <b>{preco}</b><br>
                        Custo: <b>{custo}</b><br>
                        Vendidos: <b>{vendidos}</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)

        # EXPORTAÇÃO CSV
        csv = df_page[["PRODUTO","EM ESTOQUE","Valor Venda Sugerido","Media C. UNITARIO","TOTAL_VENDAS"]] \
                .rename(columns={
                    "Valor Venda Sugerido":"PRECO_VENDA",
                    "Media C. UNITARIO":"CUSTO_UNITARIO"
                }) \
                .to_csv(index=False).encode("utf-8")

        st.download_button("📥 Exportar esta página (CSV)",
                           data=csv,
                           file_name=f"pesquisa_pagina_{page}.csv",
                           mime="text/csv")


# =============================
# Rodapé
# =============================
st.markdown("""
<div style='margin-top:20px; font-size:12px; color:#aaa;'>
  <em>Dashboard Loja Importados — Valores calculados a partir do estoque atual.</em>
</div>
""", unsafe_allow_html=True)
