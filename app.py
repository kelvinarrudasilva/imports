# app.py — Loja Importados (roxo moderno) — CORRIGIDO (tratamento seguro de % e demais colunas)
import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime
import requests
from io import BytesIO

st.set_page_config(page_title="Loja Importados – Dashboard", layout="wide")

# --- link padrão (mantive seu link) ---
URL_PLANILHA_DEFAULT = "https://docs.google.com/spreadsheets/d/1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b/export?format=xlsx"

# =============================
# Estilo (roxo, abas brancas, KPIs grandes)
# =============================
st.markdown("""
<style>
:root {
  --bg: #f7f2ff;
  --accent: #8b5cf6;
  --accent-dark: #6d28d9;
  --text: #1a1a1a;
}
body, .stApp { background: var(--bg) !important; }

/* KPIs */
.kpi { background: white; padding: 24px; border-radius:18px; box-shadow:0 6px 18px rgba(0,0,0,0.08); border-left:8px solid var(--accent); margin-bottom:18px; }
.kpi h3 { margin:0; font-size:20px; font-weight:800; color:var(--accent-dark); }
.kpi span { display:block; margin-top:8px; font-size:36px; font-weight:900; color:var(--text); }

/* Tabs */
.stTabs button { background:white !important; border:2px solid #efe6ff !important; border-radius:14px !important; padding:12px 20px !important; margin-right:12px !important; margin-bottom:12px !important; font-weight:700 !important; color:var(--accent-dark) !important; box-shadow:0 2px 6px rgba(0,0,0,0.06) !important; }
.stTabs button:hover { border-color:var(--accent) !important; box-shadow:0 4px 10px rgba(0,0,0,0.10) !important; }

/* Buttons */
.stButton>button { background:var(--accent) !important; color:white !important; padding:10px 22px !important; border-radius:12px !important; font-weight:700 !important; }

/* Table header */
.stDataFrame thead th { background:#f6f0ff !important; font-weight:700 !important; }

/* Mobile */
@media (max-width:768px) {
  .kpi span { font-size:30px; }
  .stTabs button { width:100% !important; text-align:center; }
}
</style>
""", unsafe_allow_html=True)

st.title("📊 Loja Importados — Dashboard (Roxo) — Corrigido")

# =============================
# Utilitários
# =============================
def parse_money_value(x):
    try:
        if pd.isna(x): return float("nan")
    except:
        pass
    s = str(x).strip()
    if s == "" or s.lower() in ("nan","none","-"):
        return float("nan")
    s = re.sub(r"[^\d\.,\-]", "", s)
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
    return serie.astype(str).map(parse_money_value).astype("float64")

def parse_int_series(serie):
    def to_int(x):
        try:
            if pd.isna(x): return pd.NA
        except:
            pass
        s = re.sub(r"[^\d\-]", "", str(x))
        if s in ("", "-", "nan"): return pd.NA
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
# Funções de leitura/limpeza
# =============================
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
    drop_cols = [c for c in df.columns if str(c).strip().lower() in ("nan","none","")]
    df = df.drop(columns=drop_cols, errors="ignore")
    df = df.loc[:, ~df.isna().all()]
    df = df.reset_index(drop=True)
    return df

def carregar_xlsx_from_url(url):
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return pd.ExcelFile(BytesIO(resp.content))

# =============================
# URL input
# =============================
url_input = st.text_input("URL da planilha do Google Drive (ou deixe vazio para usar a fixa):", value="")
URL_PLANILHA = url_input.strip() if url_input.strip() else URL_PLANILHA_DEFAULT

# =============================
# Ler e limpar abas
# =============================
try:
    xls = carregar_xlsx_from_url(URL_PLANILHA)
except Exception as e:
    st.error("Erro ao baixar/abrir a planilha. Verifique o link e permissões.")
    st.exception(e)
    st.stop()

abas_all = [a for a in xls.sheet_names]
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
# Conversões por aba
# =============================
# Estoque
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

# Vendas
if "VENDAS" in dfs:
    df_v = dfs["VENDAS"]
    df_v.columns = [str(c).strip() for c in df_v.columns]
    money_cols = [c for c in ["VALOR VENDA","VALOR TOTAL","MEDIA CUSTO UNITARIO","LUCRO UNITARIO"] if c in df_v.columns]
    for c in money_cols:
        df_v[c] = parse_money_series(df_v[c])
    if "QTD" in df_v.columns:
        df_v["QTD"] = parse_int_series(df_v["QTD"]).fillna(0)
    if "DATA" in df_v.columns:
        df_v["DATA"] = pd.to_datetime(df_v["DATA"], errors="coerce")
        df_v["MES_ANO"] = df_v["DATA"].dt.strftime("%Y-%m")
    else:
        df_v["MES_ANO"] = pd.NA
    # derivar VALOR TOTAL, LUCRO UNITARIO e % se necessário
    if "VALOR TOTAL" not in df_v.columns and "VALOR VENDA" in df_v.columns:
        df_v["VALOR TOTAL"] = df_v["VALOR VENDA"].fillna(0) * df_v.get("QTD", 0).fillna(0)
    if "LUCRO UNITARIO" not in df_v.columns and ("VALOR VENDA" in df_v.columns and "MEDIA CUSTO UNITARIO" in df_v.columns):
        df_v["LUCRO UNITARIO"] = df_v["VALOR VENDA"].fillna(0) - df_v["MEDIA CUSTO UNITARIO"].fillna(0)
    if "% DE LUCRO SOBRE CUSTO" not in df_v.columns and ("VALOR VENDA" in df_v.columns and "MEDIA CUSTO UNITARIO" in df_v.columns):
        custo = df_v["MEDIA CUSTO UNITARIO"].replace({0: pd.NA})
        df_v["% DE LUCRO SOBRE CUSTO"] = ((df_v["VALOR VENDA"] - df_v["MEDIA CUSTO UNITARIO"]) / custo * 100).round(2).fillna(0)
    for col in ["VALOR VENDA","VALOR TOTAL","LUCRO UNITARIO","QTD","MEDIA CUSTO UNITARIO"]:
        if col not in df_v.columns:
            df_v[col] = 0
    dfs["VENDAS"] = df_v

# Compras
if "COMPRAS" in dfs:
    df_c = dfs["COMPRAS"]
    if "QUANTIDADE" in df_c.columns:
        df_c["QUANTIDADE"] = parse_int_series(df_c["QUANTIDADE"]).fillna(0)
    if "CUSTO UNITÁRIO" in df_c.columns:
        df_c["CUSTO UNITÁRIO"] = parse_money_series(df_c["CUSTO UNITÁRIO"]).fillna(0)
    df_c["CUSTO TOTAL (RECALC)"] = df_c.get("QUANTIDADE",0).fillna(0) * df_c.get("CUSTO UNITÁRIO",0).fillna(0)
    if "DATA" in df_c.columns:
        df_c["DATA"] = pd.to_datetime(df_c["DATA"], errors="coerce")
        df_c["MES_ANO"] = df_c["DATA"].dt.strftime("%Y-%m")
    dfs["COMPRAS"] = df_c

# =============================
# filtro por mês
# =============================
meses = []
if "VENDAS" in dfs:
    meses = sorted(dfs["VENDAS"]["MES_ANO"].dropna().unique().tolist(), reverse=True)
mes_opcoes = ["Todos"] + meses
mes_atual = datetime.now().strftime("%Y-%m")
index_padrao = mes_opcoes.index(mes_atual) if mes_atual in mes_opcoes else 0
mes_selecionado = st.selectbox("Filtrar por mês (YYYY-MM):", mes_opcoes, index=index_padrao)

def filtrar_mes_df(df):
    if df is None or df.empty: return df
    if mes_selecionado == "Todos": return df
    if "MES_ANO" in df.columns:
        return df[df["MES_ANO"] == mes_selecionado].copy()
    return df

vendas_filtradas = filtrar_mes_df(dfs.get("VENDAS", pd.DataFrame()))
compras_filtradas = filtrar_mes_df(dfs.get("COMPRAS", pd.DataFrame()))
estoque_df = dfs.get("ESTOQUE", pd.DataFrame())

if vendas_filtradas is not None and not vendas_filtradas.empty and "DATA" in vendas_filtradas.columns:
    vendas_filtradas = vendas_filtradas.sort_values("DATA", ascending=False)
if compras_filtradas is not None and not compras_filtradas.empty and "DATA" in compras_filtradas.columns:
    compras_filtradas = compras_filtradas.sort_values("DATA", ascending=False)

# =============================
# KPIs
# =============================
total_vendido = vendas_filtradas["VALOR TOTAL"].fillna(0).sum() if vendas_filtradas is not None and "VALOR TOTAL" in vendas_filtradas else 0
total_lucro = (vendas_filtradas["LUCRO UNITARIO"].fillna(0) * vendas_filtradas["QTD"].fillna(0)).sum() if vendas_filtradas is not None and "LUCRO UNITARIO" in vendas_filtradas else 0
total_compras = compras_filtradas["CUSTO TOTAL (RECALC)"].fillna(0).sum() if compras_filtradas is not None and "CUSTO TOTAL (RECALC)" in compras_filtradas else 0

k1,k2,k3 = st.columns(3)
k1.markdown(f'<div class="kpi"><h3>💵 Total Vendido</h3><span>{formatar_reais_sem_centavos(total_vendido)}</span></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="kpi"><h3>🧾 Total Lucro</h3><span>{formatar_reais_sem_centavos(total_lucro)}</span></div>', unsafe_allow_html=True)
k3.markdown(f'<div class="kpi"><h3>💸 Total Compras</h3><span>{formatar_reais_sem_centavos(total_compras)}</span></div>', unsafe_allow_html=True)

# =============================
# abas e tabelas
# =============================
tabs = st.tabs(["🛒 VENDAS","🏆 TOP10 (VALOR)","🏅 TOP10 (QTD)","📦 ESTOQUE","🔍 PESQUISAR"])

def preparar_tabela_vendas(df):
    if df is None or df.empty:
        return pd.DataFrame()
    df_show = df.copy()
    if "DATA" in df_show.columns:
        df_show["DATA"] = df_show["DATA"].dt.strftime("%d/%m/%Y")
    # garantir colunas existentes
    for col in ["VALOR VENDA","VALOR TOTAL","MEDIA CUSTO UNITARIO","LUCRO UNITARIO","% DE LUCRO SOBRE CUSTO","QTD"]:
        if col not in df_show.columns:
            df_show[col] = 0
    # formatar monetários
    df_show = formatar_colunas_moeda(df_show, ["VALOR VENDA","VALOR TOTAL","MEDIA CUSTO UNITARIO","LUCRO UNITARIO"])
    # formatar % de lucro com conversão segura
    if "% DE LUCRO SOBRE CUSTO" in df_show.columns:
        # converte para numérico (coerce erros), preenche 0 e formata
        pct = pd.to_numeric(df_show["% DE LUCRO SOBRE CUSTO"], errors="coerce").fillna(0)
        df_show["% DE LUCRO SOBRE CUSTO"] = pct.map(lambda x: f"{float(x):.2f}%")
    return df_show

with tabs[0]:
    st.subheader("VENDAS (período selecionado)")
    if vendas_filtradas is None or vendas_filtradas.empty:
        st.info("Sem dados de vendas para o período selecionado.")
    else:
        st.dataframe(preparar_tabela_vendas(vendas_filtradas), use_container_width=True)

# Top10 valor
with tabs[1]:
    st.subheader("Top 10 — por VALOR")
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

# Top10 qtd
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

# Estoque
with tabs[3]:
    st.subheader("Consulta do ESTOQUE")
    if estoque_df is None or estoque_df.empty:
        st.info("Aba ESTOQUE não encontrada ou vazia.")
    else:
        df_e = estoque_df.copy()
        if "EM ESTOQUE" in df_e.columns:
            df_e["EM ESTOQUE"] = pd.to_numeric(df_e["EM ESTOQUE"], errors="coerce").fillna(0).astype(int)
            df_e = df_e.sort_values("EM ESTOQUE", ascending=False)
        df_e = formatar_colunas_moeda(df_e, ["Media C. UNITARIO","Valor Venda Sugerido"])
        st.dataframe(df_e.reset_index(drop=True), use_container_width=True)

# Pesquisar
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
