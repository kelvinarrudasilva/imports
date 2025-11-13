import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# ==============================
# ⚙️ CONFIGURAÇÃO GERAL
# ==============================
st.set_page_config(page_title="Painel Gerencial - Loja Importados", layout="wide")

st.markdown(
    """
    <style>
        body {background-color: #0e0e0e; color: #FFD700;}
        .stMetric {background-color: #1b1b1b; border-radius: 10px; padding: 10px;}
        .stMarkdown h1, h2, h3, h4 {color: #FFD700;}
        .block-container {padding-top: 1rem;}
    </style>
    """,
    unsafe_allow_html=True
)

# ==============================
# 🔍 DETECTA CABEÇALHO AUTOMATICAMENTE
# ==============================
def detect_header(path, sheet_name):
    temp = pd.read_excel(path, sheet_name=sheet_name, header=None)
    for i in range(len(temp)):
        if "PRODUTO" in str(temp.iloc[i].values).upper():
            df = pd.read_excel(path, sheet_name=sheet_name, header=i)
            return df
    return pd.read_excel(path, sheet_name=sheet_name)


# ==============================
# 📂 LEITURA DAS ABAS
# ==============================
@st.cache_data
def load_data(path):
    try:
        xls = pd.ExcelFile(path)
        abas_validas = ["ESTOQUE", "VENDAS", "COMPRAS"]
        abas_encontradas = [a for a in xls.sheet_names if a in abas_validas]
        st.write("📄 Abas encontradas:", abas_encontradas)

        dataframes = {}
        for aba in abas_validas:
            if aba in abas_encontradas:
                dataframes[aba] = detect_header(path, aba)
            else:
                dataframes[aba] = None

        return dataframes["ESTOQUE"], dataframes["VENDAS"], dataframes["COMPRAS"]

    except Exception as e:
        st.error(f"❌ Erro ao ler arquivo: {e}")
        return None, None, None


# ==============================
# 🧭 CARREGA O ARQUIVO
# ==============================
st.title("📊 Painel Gerencial - Loja Importados")

file_path = "LOJA IMPORTADOS.xlsx"
if not Path(file_path).exists():
    st.warning("⚠️ O arquivo 'LOJA IMPORTADOS.xlsx' não foi encontrado no diretório atual.")
else:
    estoque, vendas, compras = load_data(file_path)

    # ==============================
    # 🔎 LOCALIZA NOMES DAS COLUNAS
    # ==============================
    def find_col(df, options):
        if df is None:
            return None
        for opt in options:
            for col in df.columns:
                if opt.lower() in str(col).lower():
                    return col
        return None

    if estoque is None or vendas is None or compras is None:
        st.error("❌ Não foi possível carregar todas as abas. Verifique se ESTOQUE, VENDAS e COMPRAS existem.")
        st.stop()

    e_prod_col = find_col(estoque, ["PRODUTO"])
    e_qtd_col = find_col(estoque, ["EM ESTOQUE"])

    v_total_col = find_col(vendas, ["VALOR TOTAL"])
    v_valor_col = find_col(vendas, ["VALOR VENDA"])
    v_prod_col = find_col(vendas, ["PRODUTO"])
    v_lucro_col = find_col(vendas, ["LUCRO"])

    c_total_col = find_col(compras, ["CUSTO TOTAL"])

    missing_cols = []
    if not e_prod_col or not e_qtd_col:
        missing_cols.append("ESTOQUE (PRODUTO / EM ESTOQUE)")
    if not v_total_col or not v_valor_col or not v_prod_col:
        missing_cols.append("VENDAS (VALOR TOTAL / VALOR VENDA / PRODUTO)")
    if not c_total_col:
        missing_cols.append("COMPRAS (CUSTO TOTAL)")

    if missing_cols:
        st.warning("⚠️ Colunas ausentes: " + ", ".join(missing_cols))
    else:
        # ==============================
        # 💰 CÁLCULOS AJUSTADOS
        # ==============================
        total_vendas = vendas[v_total_col].sum() if v_total_col else 0
        total_compras = compras[c_total_col].sum() if c_total_col else 0

        # 🟡 Usa o lucro calculado da planilha se existir
        if v_lucro_col:
            lucro_estimado = vendas[v_lucro_col].sum()
        else:
            lucro_estimado = total_vendas - total_compras

        total_estoque = estoque[e_qtd_col].sum() if e_qtd_col else 0

        # ==============================
        # 🧮 MÉTRICAS PRINCIPAIS
        # ==============================
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("💰 Total de Vendas", f"R$ {total_vendas:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c2.metric("🧾 Total de Compras", f"R$ {total_compras:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c3.metric("📈 Lucro Estimado", f"R$ {lucro_estimado:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
        c4.metric("📦 Qtde em Estoque", f"{total_estoque:,}".replace(",", "."))

        # ==============================
        # 📊 GRÁFICO DE VENDAS POR PRODUTO
        # ==============================
        if v_prod_col and v_valor_col:
            graf_vendas = vendas.groupby(v_prod_col)[v_valor_col].sum().reset_index()
            fig = px.bar(
                graf_vendas,
                x=v_prod_col,
                y=v_valor_col,
                title="💵 Vendas por Produto",
                color=v_valor_col,
                color_continuous_scale=[[0, "#FFD700"], [1, "#DAA520"]],
            )
            fig.update_layout(
                template="plotly_dark",
                plot_bgcolor="#0e0e0e",
                paper_bgcolor="#0e0e0e",
                font=dict(color="#FFD700"),
                title_x=0.5
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("⚠️ Colunas de vendas não encontradas para o gráfico.")
