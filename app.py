import streamlit as st
import pandas as pd
import plotly.express as px
import requests
import io
from pathlib import Path
import re
import unicodedata

st.set_page_config(page_title="Dashboard Loja", layout="wide")

# ======================
# ESTILO GLOBAL
# ======================
st.markdown(
    """
    <style>
        .metric-card {
            background-color: #111;
            border-radius: 12px;
            padding: 20px;
            color: white;
            text-align: center;
            border: 1px solid #333;
        }
        .subtitle {
            font-size: 14px;
            color: #ccc;
            margin-top: -10px;
            margin-bottom: 20px;
        }
        h2, h3 {
            color: #FFD700;
        }
        .small-selectbox label { font-size:13px !important; color:#FFD700 !important; }
        .small-selectbox div[data-baseweb="select"] div { font-size:12px !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# ======================
# FUNÇÕES
# ======================

def normalize(s):
    if not isinstance(s, str):
        return ""
    s2 = unicodedata.normalize("NFKD", s)
    s2 = "".join([c for c in s2 if not unicodedata.combining(c)])
    return s2.strip().upper()


def detect_header(df):
    for i in range(min(10, len(df))):
        row = df.iloc[i].astype(str).str.upper()
        score = sum(
            [
                ("DATA" in str(x)) or
                ("PROD" in str(x)) or
                ("QTD" in str(x)) or
                ("VAL" in str(x))
                for x in row
            ]
        )
        if score >= 2:
            new_df = df.iloc[i:].reset_index(drop=True)
            new_df.columns = df.iloc[i].astype(str).tolist()
            return new_df
    return df


def load_excel_from_onedrive(url):
    try:
        if "download=1" not in url:
            if "?" in url:
                url = url + "&download=1"
            else:
                url = url + "?download=1"

        r = requests.get(url)
        r.raise_for_status()
        bytes_data = io.BytesIO(r.content)
        xls = pd.ExcelFile(bytes_data)

        sheet_map = {normalize(s): s for s in xls.sheet_names}
        st.write("SHEETS (originais):", xls.sheet_names)
        st.write("SHEET MAP (UPPER->original):", sheet_map)

        return xls, sheet_map
    except Exception as e:
        st.error(f"Erro ao baixar arquivo: {str(e)}")
        return None, {}


def map_vendas_columns(df):
    cols = {normalize(c): c for c in df.columns}
    st.write("VENDAS columns:", df.columns.tolist())

    m = {}
    m["DATA"] = cols.get("DATA")
    m["PRODUTO"] = cols.get("PRODUTO") or cols.get("_PROD_NORM")
    m["QTD"] = cols.get("QTD") or cols.get("_QTD")
    m["VALOR VENDA"] = cols.get("VALOR VENDA")
    m["VALOR TOTAL"] = cols.get("VALOR TOTAL")
    m["LUCRO"] = cols.get("_LUCRO")

    st.write("Mapeamento tentado para VENDAS:", m)
    return m


def map_estoque_columns(df):
    cols = {normalize(c): c for c in df.columns}
    st.write("ESTOQUE columns:", df.columns.tolist())
    m = {}
    m["PRODUTO"] = cols.get("PRODUTO")
    m["ESTOQUE_QTD"] = cols.get("_QTD")
    m["VAL_VENDA_UNIT"] = cols.get("_VAL_VENDA_UNIT")
    return m


# ======================
# LAYOUT SUPERIOR
# ======================

st.title("📊 Dashboard - Loja de Importados")

url = st.text_input(
    "Cole aqui o link público do OneDrive (Excel)", 
    value="https://1drv.ms/x/c/bc81746c0a7c734e/IQDHyRSnkqqEQZT1Vg9e3VJwARLyccQhj9JG3uL2lBdduGg"
)

if url:
    xls, sheet_map = load_excel_from_onedrive(url)

    if xls:
        # ======================
        # CARREGAR PLANILHAS
        # ======================
        vendas_sheet = sheet_map.get("VENDAS")
        estoque_sheet = sheet_map.get("ESTOQUE")

        if not vendas_sheet:
            st.error("Aba 'VENDAS' não encontrada.")
            st.stop()

        if not estoque_sheet:
            st.error("Aba 'ESTOQUE' não encontrada.")
            st.stop()

        vendas_raw = pd.read_excel(xls, vendas_sheet)
        estoque_raw = pd.read_excel(xls, estoque_sheet)

        vendas = detect_header(vendas_raw)
        estoque = detect_header(estoque_raw)

        map_v = map_vendas_columns(vendas)
        map_e = map_estoque_columns(estoque)

        # Normalizações
        if map_v["PRODUTO"]:
            vendas["_PROD"] = vendas[map_v["PRODUTO"]].astype(str)
        else:
            vendas["_PROD"] = ""

        if map_v["QTD"]:
            vendas["_QTD2"] = pd.to_numeric(vendas[map_v["QTD"]], errors="coerce")
        else:
            vendas["_QTD2"] = 0

        if map_v["VALOR TOTAL"]:
            vendas["_VALT"] = pd.to_numeric(vendas[map_v["VALOR TOTAL"]], errors="coerce")
        else:
            vendas["_VALT"] = 0

        # Período
        if map_v["DATA"]:
            vendas["_DATA2"] = pd.to_datetime(vendas[map_v["DATA"]], errors="coerce")
            vendas["_PERIODO"] = vendas["_DATA2"].dt.strftime("%Y-%m")
        else:
            vendas["_DATA2"] = pd.NaT
            vendas["_PERIODO"] = "SEM_DATA"

        period_options = ["Geral"] + sorted(vendas["_PERIODO"].unique())
        period_map = {p: None if p == "Geral" else p for p in period_options}

        # ======================
        # TABS
        # ======================
        tab1, tab2 = st.tabs(["📈 Visão Geral", "📦 Estoque"])

        # ======================
        # TAB 1 - VISÃO GERAL
        # ======================
        with tab1:

            # 🔥 PERÍODO MENOR E BONITO
            with st.container():
                st.markdown("<div class='small-selectbox'>", unsafe_allow_html=True)
                periodo_sel = st.selectbox("📅 Período", period_options)
                st.markdown("</div>", unsafe_allow_html=True)

            periodo_val = period_map.get(periodo_sel)

            if periodo_val is None:
                vendas_period = vendas.copy()
            else:
                vendas_period = vendas[vendas["_PERIODO"] == periodo_val].copy()

            st.markdown(
                f"<div class='subtitle'>Mostrando resultados para: <b>{periodo_sel}</b></div>",
                unsafe_allow_html=True
            )

            total_vendido = vendas_period["_VALT"].sum()
            total_qtd = vendas_period["_QTD2"].sum()

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.markdown("<div class='metric-card'>💰 Vendido<br>"
                    f"<h2>R$ {total_vendido:,.2f}</h2></div>", unsafe_allow_html=True)

            with c2:
                st.markdown("<div class='metric-card'>📦 Quantidade<br>"
                    f"<h2>{int(total_qtd)}</h2></div>", unsafe_allow_html=True)

            with c3:
                st.markdown("<div class='metric-card'>💸 Lucro<br><h2>R$ 0,00</h2></div>", unsafe_allow_html=True)

            with c4:
                st.markdown("<div class='metric-card'>📦 Valor do Estoque<br><h2>R$ 0,00</h2></div>", unsafe_allow_html=True)

            st.subheader("🏆 Top Produtos")
            vendas_group = vendas_period.groupby("_PROD")["_QTD2"].sum().sort_values(ascending=False).head(10)

            if len(vendas_group) > 0:
                fig = px.bar(vendas_group, title="Produtos Mais Vendidos")
                fig.update_layout(height=380)
                st.plotly_chart(fig, use_container_width=True)

            st.subheader("📋 Vendas do Período")
            st.dataframe(vendas_period, use_container_width=True, height=400)

        # ======================
        # TAB 2 - ESTOQUE
        # ======================
        with tab2:
            st.subheader("📦 Estoque Atual")

            if map_e["PRODUTO"] and map_e["ESTOQUE_QTD"]:
                st.dataframe(
                    estoque[[map_e["PRODUTO"], map_e["ESTOQUE_QTD"]]],
                    use_container_width=True
                )
            else:
                st.error("Estoque vazio ou colunas não encontradas.")
