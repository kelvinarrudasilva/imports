# app.py — Dashboard final seguro e completo
import streamlit as st
import pandas as pd
import plotly.express as px
import re

st.set_page_config(page_title="Loja Importados – Dashboard", layout="wide")

# ----------------------------
# LINK FIXO XLSX
# ----------------------------
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b/export?format=xlsx"

# ----------------------------
# VISUAL
# ----------------------------
st.markdown("""
<style>
:root { --gold:#FFD700; }
body, .stApp { background-color:#0b0b0b; color:#EEE; }
h1,h2,h3,h4 { color: var(--gold); }
</style>
""", unsafe_allow_html=True)
st.title("📊 Loja Importados — Dashboard")

# ----------------------------
# Funções de parse de valores
# ----------------------------
def parse_money_value(x):
    try:
        if pd.isna(x):
            return 0.0
    except:
        pass
    s = str(x).strip()
    s = re.sub(r"[^\d\.,\-]", "", s)
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s and "." not in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except:
        return 0.0

def parse_money_series(serie):
    return serie.map(parse_money_value)

def parse_int_series(serie):
    def to_int(x):
        try:
            if pd.isna(x):
                return 0
        except:
            pass
        s = str(x)
        s = re.sub(r"[^\d\-]", "", s)
        try:
            return int(float(s))
        except:
            return 0
    return serie.map(to_int)

# ----------------------------
# Detectar cabeçalho
# ----------------------------
def detectar_linha_cabecalho(df_raw, chave):
    for i in range(len(df_raw)):
        linha = df_raw.iloc[i].astype(str).str.upper().tolist()
        if chave in " ".join(linha):
            return i
    return None

def limpar_aba_raw(df_raw, nome_aba):
    busca = "PRODUTO" if nome_aba not in ("VENDAS", "COMPRAS") else "DATA"
    linha = detectar_linha_cabecalho(df_raw, busca)
    if linha is None:
        return None
    df_raw.columns = df_raw.iloc[linha]
    df = df_raw.iloc[linha+1:].copy()
    df = df.loc[:, ~df.columns.astype(str).str.contains("Unnamed")]
    df = df.reset_index(drop=True)
    df.columns = [str(c).strip() for c in df.columns]
    return df

# ----------------------------
# Carregar XLSX e limpar abas
# ----------------------------
dfs = {}  # inicializa dicionário
try:
    xls = pd.ExcelFile(URL_PLANILHA)
except Exception as e:
    st.error("Erro ao carregar planilha XLSX do Google Drive.")
    st.code(str(e))
    st.stop()

abas_all = [a for a in xls.sheet_names if a.upper() != "EXCELENTEJOAO"]

colunas_esperadas = {
    "ESTOQUE": ["PRODUTO","EM ESTOQUE","COMPRAS","Media C. UNITARIO","Valor Venda Sugerido","VENDAS"],
    "VENDAS": ["DATA","PRODUTO","QTD","VALOR VENDA","VALOR TOTAL","MEDIA CUSTO UNITARIO","LUCRO UNITARIO","MAKEUP","% DE LUCRO SOBRE CUSTO","STATUS","CLIENTE","OBS"],
    "COMPRAS": ["DATA","PRODUTO","STATUS","QUANTIDADE","CUSTO UNITÁRIO","CUSTO TOTAL"]
}

for aba in colunas_esperadas.keys():
    if aba not in abas_all:
        continue
    bruto = pd.read_excel(URL_PLANILHA, sheet_name=aba, header=None)
    limpo = limpar_aba_raw(bruto, aba)
    if limpo is None:
        st.warning(f"Aba {aba}: cabeçalho não encontrado — pulando.")
        continue
    dfs[aba] = limpo

# ----------------------------
# Converter valores
# ----------------------------
# ESTOQUE
df_estoque = dfs.get("ESTOQUE")
if df_estoque is not None:
    if "Media C. UNITARIO" in df_estoque.columns:
        df_estoque["Media C. UNITARIO"] = parse_money_series(df_estoque["Media C. UNITARIO"])
    if "Valor Venda Sugerido" in df_estoque.columns:
        df_estoque["Valor Venda Sugerido"] = parse_money_series(df_estoque["Valor Venda Sugerido"])
    if "EM ESTOQUE" in df_estoque.columns:
        df_estoque["EM ESTOQUE"] = parse_int_series(df_estoque["EM ESTOQUE"])
    if "VENDAS" in df_estoque.columns:
        df_estoque["VENDAS"] = parse_int_series(df_estoque["VENDAS"])

# VENDAS
df_vendas = dfs.get("VENDAS")
if df_vendas is not None:
    if "VALOR VENDA" in df_vendas.columns:
        df_vendas["VALOR VENDA"] = parse_money_series(df_vendas["VALOR VENDA"])
    if "VALOR TOTAL" in df_vendas.columns:
        df_vendas["VALOR TOTAL"] = parse_money_series(df_vendas["VALOR TOTAL"])
    if "MEDIA CUSTO UNITARIO" in df_vendas.columns:
        df_vendas["MEDIA CUSTO UNITARIO"] = parse_money_series(df_vendas["MEDIA CUSTO UNITARIO"])
    if "LUCRO UNITARIO" in df_vendas.columns:
        df_vendas["LUCRO UNITARIO"] = parse_money_series(df_vendas["LUCRO UNITARIO"])
    if "QTD" in df_vendas.columns:
        df_vendas["QTD"] = parse_int_series(df_vendas["QTD"])
    if "DATA" in df_vendas.columns:
        df_vendas["DATA"] = pd.to_datetime(df_vendas["DATA"], errors="coerce")
        df_vendas["MES_ANO"] = df_vendas["DATA"].dt.strftime("%Y-%m")
    else:
        df_vendas["MES_ANO"] = pd.NA

# COMPRAS
df_compras = dfs.get("COMPRAS")
if df_compras is not None:
    if "QUANTIDADE" in df_compras.columns:
        df_compras["QUANTIDADE"] = parse_int_series(df_compras["QUANTIDADE"])
    if "CUSTO UNITÁRIO" in df_compras.columns:
        df_compras["CUSTO UNITÁRIO"] = parse_money_series(df_compras["CUSTO UNITÁRIO"])
    if "QUANTIDADE" in df_compras.columns and "CUSTO UNITÁRIO" in df_compras.columns:
        df_compras["CUSTO TOTAL (RECALC)"] = df_compras["QUANTIDADE"] * df_compras["CUSTO UNITÁRIO"]
    else:
        df_compras["CUSTO TOTAL (RECALC)"] = parse_money_series(df_compras.get("CUSTO TOTAL", pd.Series(0)))

# ----------------------------
# Filtro por mês
# ----------------------------
meses = ["Todos"]
if df_vendas is not None:
    meses += sorted(df_vendas["MES_ANO"].dropna().unique().tolist(), reverse=True)
mes_selecionado = st.selectbox("Filtrar por mês (YYYY-MM):", meses)

def filtrar_mes(df, mes):
    if df is None or df.empty:
        return pd.DataFrame()
    if mes == "Todos":
        return df
    return df[df["MES_ANO"]==mes].copy()

vendas_filtradas = filtrar_mes(df_vendas, mes_selecionado)
compras_filtradas = filtrar_mes(df_compras, mes_selecionado)

# ----------------------------
# KPIs
# ----------------------------
def calcular_totais_vendas(df):
    if df is None or df.empty:
        return 0.0, 0.0
    total_vendido = df["VALOR TOTAL"].sum() if "VALOR TOTAL" in df.columns else 0.0
    total_lucro = (df["LUCRO UNITARIO"] * df["QTD"]).sum() if "LUCRO UNITARIO" in df.columns and "QTD" in df.columns else 0.0
    return total_vendido, total_lucro

total_vendido, total_lucro = calcular_totais_vendas(vendas_filtradas)
total_compras = compras_filtradas["CUSTO TOTAL (RECALC)"].sum() if not compras_filtradas.empty else 0.0

k1, k2, k3 = st.columns(3)
k1.metric("💵 Total Vendido (R$)", f"R$ {total_vendido:,.2f}")
k2.metric("🧾 Total Lucro (R$)", f"R$ {total_lucro:,.2f}")
k3.metric("💸 Total Compras (R$)", f"R$ {total_compras:,.2f}")

# ----------------------------
# Abas
# ----------------------------
tabs = st.tabs(["🛒 VENDAS","🏆 TOP10 (VALOR)","🏅 TOP10 (QUANTIDADE)","📈 TOP10 LUCRO","📦 CONSULTAR ESTOQUE"])

# --- VENDAS
with tabs[0]:
    st.subheader("Vendas (período selecionado)")
    if vendas_filtradas.empty:
        st.info("Sem dados para o período selecionado.")
    else:
        df_show = vendas_filtradas.copy()
        for col in ["VALOR VENDA","VALOR TOTAL","LUCRO UNITARIO","MEDIA CUSTO UNITARIO"]:
            if col in df_show.columns:
                df_show[col] = df_show[col].map(lambda x: f"R$ {x:,.2f}")
        st.dataframe(df_show, use_container_width=True)

# --- TOP10 VALOR
with tabs[1]:
    st.subheader("Top 10 — por VALOR (R$)")
    if not vendas_filtradas.empty:
        top_val = vendas_filtradas.groupby("PRODUTO")["VALOR TOTAL"].sum().reset_index().sort_values("VALOR TOTAL", ascending=False).head(10)
        top_val["VALOR_FORMAT"] = top_val["VALOR TOTAL"].map(lambda x: f"R$ {x:,.2f}")
        fig = px.bar(top_val, x="PRODUTO", y="VALOR TOTAL", text="VALOR_FORMAT")
        fig.update_traces(textposition="inside")
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(top_val.drop(columns=["VALOR_FORMAT"]).style.format({"VALOR TOTAL":"R$ {:,.2f}"}))

# --- TOP10 QUANTIDADE
with tabs[2]:
    st.subheader("Top 10 — por QUANTIDADE")
    if not vendas_filtradas.empty:
        top_q = vendas_filtradas.groupby("PRODUTO")["QTD"].sum().reset_index().sort_values("QTD", ascending=False).head(10)
        top_q["QTD_TEXT"] = top_q["QTD"].astype(int).astype(str)
        fig2 = px.bar(top_q, x="PRODUTO", y="QTD", text="QTD_TEXT")
        fig2.update_traces(textposition="inside")
        st.plotly_chart(fig2, use_container_width=True)
        st.dataframe(top_q.drop(columns=["QTD_TEXT"]).style.format({"QTD":"{:,.0f}"}))

# --- TOP10 LUCRO
with tabs[3]:
    st.subheader("Top 10 — por LUCRO (R$)")
    if not vendas_filtradas.empty and "LUCRO UNITARIO" in vendas_filtradas.columns:
        top_lucro = (vendas_filtradas.assign(LUCRO_TOTAL=vendas_filtradas["LUCRO UNITARIO"]*vendas_filtradas["QTD"])
                     .groupby("PRODUTO")["LUCRO_TOTAL"].sum().reset_index().sort_values("LUCRO_TOTAL", ascending=False).head(10))
        top_lucro["LUCRO_FORMAT"] = top_lucro["LUCRO_TOTAL"].map(lambda x: f"R$ {x:,.2f}")
        fig3 = px.bar(top_lucro, x="PRODUTO", y="LUCRO_TOTAL", text="LUCRO_FORMAT")
        fig3.update_traces(textposition="inside")
        st.plotly_chart(fig3, use_container_width=True)
        st.dataframe(top_lucro.drop(columns=["LUCRO_FORMAT"]).style.format({"LUCRO_TOTAL":"R$ {:,.2f}"}))

# --- CONSULTAR ESTOQUE
with tabs[4]:
    st.subheader("Consulta completa do Estoque")
    if df_estoque is None or df_estoque.empty:
        st.info("Aba ESTOQUE não encontrada ou vazia.")
    else:
        df_show = df_estoque.copy()
        # remover colunas NAN
        df_show = df_show.loc[:, df_show.columns.notna()]
        st.dataframe(df_show.sort_values(by="PRODUTO").reset_index(drop=True), use_container_width=True)

st.success("✅ Dashboard carregado com sucesso!")
