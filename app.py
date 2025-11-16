# app.py — Dashboard Loja Importados final (visual moderno, KPIs grandes, abas brancas espaçadas)
import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime

st.set_page_config(page_title="Loja Importados – Dashboard", layout="wide")

# ----------------------------
# LINK FIXO PLANILHA
# ----------------------------
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b/export?format=xlsx"

# ----------------------------
# VISUAL — Tema Moderno / Abas Brancas / KPIs Grandes
# ----------------------------
st.markdown("""
<style>

:root {
    --azul: #1aa3ff;
    --azul-escuro: #0066cc;
    --roxinho: #8b5cf6;
}

/* Fundo */
body, .stApp { background:#ffffff !important; color:#111; }

/* ---------------------- */
/*        KPIs           */
/* ---------------------- */

.kpi {
    padding:22px;
    border-radius:16px;
    color:white;
    text-align:center;
    box-shadow:0 3px 10px rgba(0,0,0,0.10);
    margin-bottom:18px;
}

.kpi h3 {
    margin:0;
    font-size:20px;
    font-weight:800;
}

.kpi span {
    margin-top:10px;
    font-size:34px;
    font-weight:900;
    display:block;
}

.kpi-vendas {
    background: linear-gradient(135deg, #4facfe, #00f2fe);
}

.kpi-lucro {
    background: linear-gradient(135deg, #34e89e, #0f3443);
}

.kpi-compras {
    background: linear-gradient(135deg, #f6d365, #fda085);
    color:#222;
}

/* ---------------------- */
/*       ABAS NOVAS       */
/* ---------------------- */

.stTabs button {
    background:white !important;
    color: var(--azul-escuro) !important;
    border-radius:14px !important;
    padding:12px 22px !important;
    margin-right:12px !important;
    margin-bottom:12px !important;
    font-weight:700 !important;
    border:1px solid #e5e5e5 !important;
    box-shadow:0 2px 6px rgba(0,0,0,0.08) !important;
}

.stTabs button:hover {
    border-color: var(--azul) !important;
    box-shadow:0 4px 10px rgba(0,0,0,0.12) !important;
}

/* ---------------------- */
/* DataFrame topo suave   */
/* ---------------------- */
.stDataFrame thead th { background-color:#f5faff !important; }

/* ---------------------- */
/* Responsividade mobile  */
/* ---------------------- */
@media (max-width: 720px) {
    .kpi span { font-size:28px; }
    .kpi h3 { font-size:16px; }
    .stTabs button { width:100%; text-align:center; }
}

</style>
""", unsafe_allow_html=True)


st.title("📊 Loja Importados — Dashboard")

# ----------------------------
# FUNÇÕES DE PARSE E FORMATAÇÃO
# ----------------------------
def parse_money_value(x):
    try:
        if pd.isna(x):
            return float("nan")
    except:
        pass
    s = str(x).strip()
    if s == "" or s.lower() == "nan":
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
        return float(s) if s not in ("", ".", "-") else float("nan")
    except:
        return float("nan")

def parse_money_series(serie):
    return serie.astype(str).map(lambda x: parse_money_value(x)).astype("float64")

def parse_int_series(serie):
    def to_int(x):
        try:
            if pd.isna(x):
                return pd.NA
        except:
            pass
        s = str(x)
        s = re.sub(r"[^\d\-]", "", s)
        if s in ["", "-", "nan"]:
            return pd.NA
        try:
            return int(float(s))
        except:
            return pd.NA
    return serie.map(to_int).astype("Int64")

# Reais sem centavos
def formatar_reais_sem_centavos(valor):
    try:
        if pd.isna(valor): return "R$ 0"
    except:
        pass
    try:
        v = float(valor)
    except:
        return str(valor)
    s = f"{v:,.0f}".replace(",", ".")
    return f"R$ {s}"

def formatar_valor_reais(df, colunas):
    for c in colunas:
        if c in df.columns:
            df[c] = df[c].fillna(0.0).map(formatar_reais_sem_centavos)
    return df

# ----------------------------
# DETECTAR CABEÇALHO / LIMPEZA
# ----------------------------
def detectar_linha_cabecalho(df_raw, chave):
    for i in range(len(df_raw)):
        if chave in " ".join(df_raw.iloc[i].astype(str).str.upper().tolist()):
            return i
    return None

def limpar_aba_raw(df_raw, nome_aba):
    busca = "PRODUTO" if nome_aba not in ("VENDAS","COMPRAS") else "DATA"
    linha = detectar_linha_cabecalho(df_raw, busca)
    if linha is None: return None
    df_raw.columns = df_raw.iloc[linha]
    df = df_raw.iloc[linha+1:].copy()
    df = df.loc[:, ~df.columns.astype(str).str.contains("Unnamed")]
    df.columns = [str(c).strip() for c in df.columns]
    return df.reset_index(drop=True)

# ----------------------------
# CARREGAR PLANILHA
# ----------------------------
try:
    xls = pd.ExcelFile(URL_PLANILHA)
except Exception as e:
    st.error("Erro ao carregar planilha.")
    st.code(str(e))
    st.stop()

abas_all = [a for a in xls.sheet_names if a.upper()!="EXCELENTEJOAO"]

colunas_esperadas = {
    "ESTOQUE": ["PRODUTO","EM ESTOQUE","COMPRAS","Media C. UNITARIO","Valor Venda Sugerido","VENDAS"],
    "VENDAS": ["DATA","PRODUTO","QTD","VALOR VENDA","VALOR TOTAL","MEDIA CUSTO UNITARIO","LUCRO UNITARIO","MAKEUP","% DE LUCRO SOBRE CUSTO","STATUS","CLIENTE","OBS"],
    "COMPRAS":["DATA","PRODUTO","STATUS","QUANTIDADE","CUSTO UNITÁRIO","CUSTO TOTAL"]
}

dfs = {}
for aba in colunas_esperadas:
    if aba not in abas_all: continue
    bruto = pd.read_excel(URL_PLANILHA, sheet_name=aba, header=None)
    limpo = limpar_aba_raw(bruto, aba)
    if limpo is None:
        st.warning(f"Aba {aba} inválida — pulando.")
        continue
    dfs[aba] = limpo

# ----------------------------
# CONVERSÃO
# ----------------------------
if "ESTOQUE" in dfs:
    df_e = dfs["ESTOQUE"]
    df_e["Media C. UNITARIO"] = parse_money_series(df_e["Media C. UNITARIO"])
    df_e["Valor Venda Sugerido"] = parse_money_series(df_e["Valor Venda Sugerido"])
    df_e["EM ESTOQUE"] = parse_int_series(df_e["EM ESTOQUE"]).fillna(0)
    df_e["VENDAS"] = parse_int_series(df_e["VENDAS"]).fillna(0)
    dfs["ESTOQUE"] = df_e

if "VENDAS" in dfs:
    df_v = dfs["VENDAS"]
    df_v["VALOR VENDA"] = parse_money_series(df_v["VALOR VENDA"])
    df_v["VALOR TOTAL"] = parse_money_series(df_v["VALOR TOTAL"])
    df_v["MEDIA CUSTO UNITARIO"] = parse_money_series(df_v["MEDIA CUSTO UNITARIO"])
    df_v["LUCRO UNITARIO"] = parse_money_series(df_v["LUCRO UNITARIO"])
    df_v["QTD"] = parse_int_series(df_v["QTD"]).fillna(0)
    df_v["DATA"] = pd.to_datetime(df_v["DATA"], errors="coerce")
    df_v["MES_ANO"] = df_v["DATA"].dt.strftime("%Y-%m")
    dfs["VENDAS"] = df_v

if "COMPRAS" in dfs:
    df_c = dfs["COMPRAS"]
    df_c["QUANTIDADE"] = parse_int_series(df_c["QUANTIDADE"]).fillna(0)
    df_c["CUSTO UNITÁRIO"] = parse_money_series(df_c["CUSTO UNITÁRIO"])
    df_c["CUSTO TOTAL (RECALC)"] = df_c["QUANTIDADE"] * df_c["CUSTO UNITÁRIO"]
    df_c["DATA"] = pd.to_datetime(df_c["DATA"], errors="coerce")
    df_c["MES_ANO"] = df_c["DATA"].dt.strftime("%Y-%m")
    dfs["COMPRAS"] = df_c

# ----------------------------
# FILTRO
# ----------------------------
meses_venda = sorted(dfs["VENDAS"]["MES_ANO"].dropna().unique(), reverse=True)
mes_opcoes = ["Todos"] + meses_venda
mes_atual = datetime.now().strftime("%Y-%m")
index_padrao = mes_opcoes.index(mes_atual) if mes_atual in mes_opcoes else 0

mes_selecionado = st.selectbox("Filtrar por mês:", mes_opcoes, index=index_padrao)

def filtrar_mes(df, mes):
    if mes=="Todos": return df
    return df[df["MES_ANO"]==mes]

def ordenar(df):
    return df.sort_values("DATA", ascending=False) if "DATA" in df.columns else df

vendas_filtradas = ordenar(filtrar_mes(dfs["VENDAS"], mes_selecionado))
compras_filtradas = ordenar(filtrar_mes(dfs["COMPRAS"], mes_selecionado))
estoque_df = dfs["ESTOQUE"]

# ----------------------------
# KPIs
# ----------------------------
total_vendido = (vendas_filtradas["VALOR TOTAL"].fillna(0)).sum()
total_lucro   = (vendas_filtradas["LUCRO UNITARIO"].fillna(0)*vendas_filtradas["QTD"]).sum()
total_compras = compras_filtradas["CUSTO TOTAL (RECALC)"].sum()

c1,c2,c3 = st.columns(3)
c1.markdown(f"<div class='kpi kpi-vendas'><h3>💵 Total Vendido</h3><span>{formatar_reais_sem_centavos(total_vendido)}</span></div>", unsafe_allow_html=True)
c2.markdown(f"<div class='kpi kpi-lucro'><h3>🧾 Total Lucro</h3><span>{formatar_reais_sem_centavos(total_lucro)}</span></div>", unsafe_allow_html=True)
c3.markdown(f"<div class='kpi kpi-compras'><h3>💸 Total Compras</h3><span>{formatar_reais_sem_centavos(total_compras)}</span></div>", unsafe_allow_html=True)

# ----------------------------
# ABAS
# ----------------------------
tabs = st.tabs([
    "🛒 VENDAS",
    "🏆 TOP10 (VALOR)",
    "🏅 TOP10 (QUANTIDADE)",
    "💰 TOP10 LUCRO",
    "📦 CONSULTAR ESTOQUE",
    "🔍 PESQUISAR PRODUTO"
])

def preparar_tabela(df):
    df2 = df.copy()
    df2["DATA"] = df2["DATA"].dt.strftime("%d/%m/%y")
    return formatar_valor_reais(df2, ["VALOR VENDA","VALOR TOTAL","MEDIA CUSTO UNITARIO","LUCRO UNITARIO"])

# ----------------------------
# ABA: VENDAS
# ----------------------------
with tabs[0]:
    if vendas_filtradas.empty:
        st.info("Sem vendas no período.")
    else:
        st.dataframe(preparar_tabela(vendas_filtradas), use_container_width=True)

# ----------------------------
# TOP10 VALOR
# ----------------------------
with tabs[1]:
    if vendas_filtradas.empty:
        st.info("Sem dados.")
    else:
        dfv = vendas_filtradas.copy()
        if "VALOR TOTAL" not in dfv:
            dfv["VALOR TOTAL"]=dfv["VALOR VENDA"]*dfv["QTD"]
        top_val = dfv.groupby("PRODUTO").agg(
            VALOR_TOTAL=("VALOR TOTAL","sum"),
            QTD_TOTAL=("QTD","sum")
        ).reset_index().sort_values("VALOR_TOTAL", ascending=False).head(10)

        top_val["LABEL"] = top_val["VALOR_TOTAL"].apply(formatar_reais_sem_centavos)

        fig = px.bar(top_val, x="PRODUTO", y="VALOR_TOTAL", text="LABEL",
                     hover_data={"QTD_TOTAL":True})
        fig.update_traces(textposition="inside")
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(top_val.drop(columns=["LABEL"]), use_container_width=True)

# ----------------------------
# TOP10 QUANTIDADE
# ----------------------------
with tabs[2]:
    if vendas_filtradas.empty:
        st.info("Sem dados.")
    else:
        top_q = vendas_filtradas.groupby("PRODUTO")["QTD"].sum().reset_index() \
                 .sort_values("QTD",ascending=False).head(10)
        fig2 = px.bar(top_q, x="PRODUTO", y="QTD", text="QTD")
        fig2.update_traces(textposition="inside")
        fig2.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(top_q, use_container_width=True)

# ----------------------------
# TOP10 LUCRO
# ----------------------------
with tabs[3]:
    if vendas_filtradas.empty:
        st.info("Sem dados.")
    else:
        dfv = vendas_filtradas.copy()
        dfv["LUCRO_TOTAL"] = dfv["LUCRO UNITARIO"].fillna(0)*dfv["QTD"]
        top_l = dfv.groupby("PRODUTO").agg(
            LUCRO_TOTAL=("LUCRO_TOTAL","sum"),
            QTD_TOTAL=("QTD","sum")
        ).reset_index().sort_values("LUCRO_TOTAL", ascending=False).head(10)

        top_l["LABEL"] = top_l["LUCRO_TOTAL"].apply(formatar_reais_sem_centavos)

        fig3 = px.bar(top_l, x="PRODUTO", y="LUCRO_TOTAL", text="LABEL",
                      hover_data={"QTD_TOTAL":True})
        fig3.update_traces(textposition="inside")
        fig3.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig3, use_container_width=True)
        st.dataframe(top_l.drop(columns=["LABEL"]), use_container_width=True)

# ----------------------------
# CONSULTAR ESTOQUE
# ----------------------------
with tabs[4]:
    df_e = estoque_df.copy()
    df_e = formatar_valor_reais(df_e, ["Media C. UNITARIO","Valor Venda Sugerido"])
    if "EM ESTOQUE" in df_e:
        df_e["EM ESTOQUE"] = df_e["EM ESTOQUE"].astype(int)
        df_e = df_e.sort_values("EM ESTOQUE", ascending=False)
    st.dataframe(df_e.reset_index(drop=True), use_container_width=True)

# ----------------------------
# PESQUISAR PRODUTO
# ----------------------------
with tabs[5]:
    termo = st.text_input("Digite o nome do produto:")
    if termo:
        df_s = estoque_df[estoque_df["PRODUTO"].str.contains(termo, case=False, na=False)]
        if not df_s.empty:
            df_s = formatar_valor_reais(df_s, ["Media C. UNITARIO","Valor Venda Sugerido"])
            st.dataframe(df_s.reset_index(drop=True), use_container_width=True)
        else:
            st.info("Nenhum produto encontrado.")

st.success("✅ Dashboard carregado com sucesso!")
