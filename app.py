import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Loja Importados", layout="wide")

st.title("📊 Dashboard Loja Importados")

# ============================
# LINK FIXO
# ============================
URL_PLANILHA = "https://drive.google.com/uc?export=download&id=1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b"

# ============================
# FUNÇÃO BASE PARA CARREGAR XLS
# ============================
def carregar_xls(url):
    try:
        return pd.ExcelFile(url), None
    except Exception as e:
        return None, str(e)

xls, erro = carregar_xls(URL_PLANILHA)
if erro:
    st.error("Erro ao abrir planilha.")
    st.code(erro)
    st.stop()

# ignorar aba EXCELENTEJOAO
abas = [a for a in xls.sheet_names if a.upper() != "EXCELENTEJOAO"]

# ============================
# COLUNAS ESPERADAS
# ============================
colunas_esperadas = {
    "ESTOQUE": [
        "PRODUTO", "EM ESTOQUE", "COMPRAS",
        "Media C. UNITARIO", "Valor Venda Sugerido", "VENDAS"
    ],
    "VENDAS": [
        "DATA", "PRODUTO", "QTD", "VALOR VENDA", "VALOR TOTAL",
        "MEDIA CUSTO UNITARIO", "LUCRO UNITARIO", "MAKEUP",
        "% DE LUCRO SOBRE CUSTO", "STATUS", "CLIENTE", "OBS"
    ],
    "COMPRAS": [
        "DATA", "PRODUTO", "STATUS",
        "QUANTIDADE", "CUSTO UNITÁRIO", "CUSTO TOTAL"
    ]
}

# ============================
# DETECTOR DE CABEÇALHO
# ============================
def limpar_aba(df, nome_aba):

    busca = "PRODUTO" if nome_aba != "VENDAS" and nome_aba != "COMPRAS" else "DATA"

    linha_cab = None
    for i in range(len(df)):
        linha = df.iloc[i].astype(str).str.upper().tolist()
        if busca in " ".join(linha):
            linha_cab = i
            break

    if linha_cab is None:
        return None

    df.columns = df.iloc[linha_cab]
    df = df.iloc[linha_cab + 1:]
    df = df.loc[:, ~df.columns.astype(str).str.contains("Unnamed")]
    df = df.reset_index(drop=True)

    return df

# ============================
# VALIDAÇÃO
# ============================
def validar(df, esperado):

    col_df = [str(c).strip() for c in df.columns]
    df.columns = col_df

    df = df.loc[:, ~df.columns.str.contains("Unnamed", case=False)]
    df = df.loc[:, df.columns != ""]
    df = df.loc[:, df.columns != "nan"]

    return df

# ============================
# CONVERTER MOEDAS
# ============================
def converter_moeda(df, colunas):
    for c in colunas:
        if c in df.columns:
            df[c] = (
                df[c]
                .astype(str)
                .str.replace("R$", "", regex=False)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

# ============================
# PROCESSAR TODAS AS ABAS
# ============================
dfs = {}

for aba in colunas_esperadas.keys():

    if aba not in abas:
        continue

    bruto = pd.read_excel(URL_PLANILHA, sheet_name=aba, header=None)
    limpo = limpar_aba(bruto, aba)

    if limpo is None:
        continue

    validado = validar(limpo, colunas_esperadas[aba])

    # conversão de moedas
    if aba == "ESTOQUE":
        validado = converter_moeda(validado, ["Media C. UNITARIO", "Valor Venda Sugerido"])
    elif aba == "VENDAS":
        validado = converter_moeda(validado, ["VALOR VENDA", "VALOR TOTAL", "MEDIA CUSTO UNITARIO", "LUCRO UNITARIO"])
    elif aba == "COMPRAS":
        validado = converter_moeda(validado, ["CUSTO UNITÁRIO", "CUSTO TOTAL"])

    dfs[aba] = validado

# ============================
# DASHBOARDS
# ============================
st.header("📈 Dashboards")

tabs = st.tabs(["📦 Estoque", "🛒 Vendas", "📥 Compras", "📄 Dados Brutos"])

# ============================================================
# ESTOQUE
# ============================================================
with tabs[0]:
    if "ESTOQUE" in dfs:
        df = dfs["ESTOQUE"]

        col1, col2, col3 = st.columns(3)

        col1.metric("Produtos cadastrados", df["PRODUTO"].nunique())
        col2.metric("Total em estoque", df["EM ESTOQUE"].sum())
        col3.metric("Total vendido (qtde)", df["VENDAS"].sum())

        fig = px.bar(
            df.sort_values("VENDAS", ascending=False).head(20),
            x="PRODUTO", y="VENDAS",
            title="Top 20 Produtos Mais Vendidos"
        )
        st.plotly_chart(fig, use_container_width=True)

# ============================================================
# VENDAS
# ============================================================
with tabs[1]:
    if "VENDAS" in dfs:
        df = dfs["VENDAS"]

        df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")

        col1, col2, col3 = st.columns(3)

        col1.metric("Faturamento Total", f"R$ {df['VALOR TOTAL'].sum():,.2f}")
        col2.metric("Lucro Total", f"R$ {df['LUCRO UNITARIO'].sum():,.2f}")
        col3.metric("Itens vendidos", df["QTD"].sum())

        # Faturamento diário
        fig = px.line(
            df.groupby("DATA")["VALOR TOTAL"].sum().reset_index(),
            x="DATA", y="VALOR TOTAL",
            title="Faturamento Diário"
        )
        st.plotly_chart(fig, use_container_width=True)

        # Ranking
        fig2 = px.bar(
            df.groupby("PRODUTO")["QTD"].sum().reset_index().sort_values("QTD", ascending=False).head(20),
            x="PRODUTO", y="QTD",
            title="Top 20 Produtos Vendidos"
        )
        st.plotly_chart(fig2, use_container_width=True)

# ============================================================
# COMPRAS
# ============================================================
with tabs[2]:
    if "COMPRAS" in dfs:
        df = dfs["COMPRAS"]
        df["DATA"] = pd.to_datetime(df["DATA"], errors="coerce")

        col1, col2 = st.columns(2)
        col1.metric("Compras registradas", len(df))
        col2.metric("Custo Total Compras", f"R$ {df['CUSTO TOTAL'].sum():,.2f}")

        fig = px.line(
            df.groupby("DATA")["CUSTO TOTAL"].sum().reset_index(),
            x="DATA", y="CUSTO TOTAL",
            title="Total de Compras por Dia"
        )
        st.plotly_chart(fig, use_container_width=True)

# ============================================================
# DADOS BRUTOS
# ============================================================
with tabs[3]:
    for k, v in dfs.items():
        st.subheader(k)
        st.dataframe(v, use_container_width=True)
