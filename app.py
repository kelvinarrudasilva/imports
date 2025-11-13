# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re

# ======================
# Configurações Iniciais
# ======================
st.set_page_config(page_title="Painel - Loja Importados", layout="wide")

# ------------------ TEMAS ------------------
themes = {
    "DARK ELEGANTE": {
        "bg": "#000000",
        "text": "#FFD700",
        "card": "#0f0f0f",
        "muted": "#bfbfbf",
        "accent": "#FFD700",
    },
    "CLARO MINIMALISTA": {
        "bg": "#FFFFFF",
        "text": "#222222",
        "card": "#f5f5f5",
        "muted": "#777777",
        "accent": "#B8860B",
    },
    "NEON MODERNO": {
        "bg": "#0b001a",
        "text": "#8ab4f8",
        "card": "#12002e",
        "muted": "#9c9cff",
        "accent": "#ff007f",
    },
}

# Botão de tema na barra lateral
st.sidebar.markdown("### 🎨 Tema Visual")
selected_theme = st.sidebar.radio(
    "Escolha o estilo:", list(themes.keys()), index=0, horizontal=False
)
t = themes[selected_theme]

# CSS Dinâmico
st.markdown(
    f"""
    <style>
      :root {{
        --bg:{t["bg"]};
        --text:{t["text"]};
        --card:{t["card"]};
        --muted:{t["muted"]};
        --accent:{t["accent"]};
      }}
      .stApp {{ background-color: var(--bg); color: var(--text); }}
      .title {{ color: var(--text); font-weight:700; font-size:22px; }}
      .subtitle {{ color: var(--muted); font-size:12px; margin-bottom:12px; }}
      .kpi {{
        background: linear-gradient(90deg, var(--card), var(--bg));
        padding:12px; border-radius:10px; text-align:center;
      }}
      .kpi-value {{ color: var(--accent); font-size:20px; font-weight:700; }}
      .kpi-label {{ color:var(--muted); font-size:13px; }}
      .stDataFrame table {{ background-color:var(--card); color:var(--text); }}
      .metric-value {{ color: var(--accent)!important; }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    f"<div class='title'>📊 Painel — Loja Importados</div>", unsafe_allow_html=True
)
st.markdown(
    f"<div class='subtitle'>Tema ativo: {selected_theme} • Abas: Visão Geral / Estoque</div>",
    unsafe_allow_html=True,
)
st.markdown("---")

# ======================
# Funções utilitárias
# ======================
def clean_df(df):
    if df is None:
        return None
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains("^Unnamed", na=False)]
    df = df.dropna(axis=1, how="all").dropna(axis=0, how="all").reset_index(drop=True)
    return df


def find_col(df, *cands):
    if df is None:
        return None
    for cand in cands:
        for c in df.columns:
            if cand.upper() in str(c).upper():
                return c
    return None


def to_num(s):
    return pd.to_numeric(s, errors="coerce").fillna(0)


def fmt_brl(x):
    try:
        return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"


# ======================
# Carregar planilha
# ======================
EXCEL = "LOJA IMPORTADOS.xlsx"
if not Path(EXCEL).exists():
    st.error(f"Arquivo '{EXCEL}' não encontrado.")
    st.stop()

xls = pd.ExcelFile(EXCEL)
abas = [s.upper() for s in xls.sheet_names]
if "EXCELENTEJOAO" in abas:
    abas.remove("EXCELENTEJOAO")

estoque = clean_df(pd.read_excel(EXCEL, sheet_name="ESTOQUE"))
vendas = clean_df(pd.read_excel(EXCEL, sheet_name="VENDAS"))
compras = clean_df(pd.read_excel(EXCEL, sheet_name="COMPRAS"))

# ======================
# Mapeamento de colunas
# ======================
e_prod = find_col(estoque, "PRODUTO")
e_qtd = find_col(estoque, "EM ESTOQUE")
e_venda = find_col(estoque, "Valor Venda Sugerido")
e_custo = find_col(estoque, "Media C. UNITARIO")

v_prod = find_col(vendas, "PRODUTO")
v_qtd = find_col(vendas, "QTD")
v_total = find_col(vendas, "VALOR TOTAL")
v_lucro = find_col(vendas, "LUCRO")
v_data = find_col(vendas, "DATA")

c_custo_unit = find_col(compras, "CUSTO UNITÁRIO")
c_custo_total = find_col(compras, "CUSTO TOTAL")

# ======================
# Preparar colunas
# ======================
estoque["_QTD"] = to_num(estoque[e_qtd])
estoque["_VAL_VENDA"] = to_num(estoque[e_venda])
estoque["_VAL_CUSTO"] = to_num(estoque[e_custo])
estoque["_VAL_TOTAL_VENDA"] = estoque["_QTD"] * estoque["_VAL_VENDA"]
estoque["_VAL_TOTAL_CUSTO"] = estoque["_QTD"] * estoque["_VAL_CUSTO"]

vendas["_VAL_TOTAL"] = to_num(vendas[v_total])
vendas["_LUCRO"] = to_num(vendas[v_lucro])
vendas["_DATA"] = pd.to_datetime(vendas[v_data], errors="coerce")

# ======================
# Abas do Painel
# ======================
tab1, tab2 = st.tabs(["📈 Visão Geral", "📦 Estoque Atual"])

# ------------------ VISÃO GERAL ------------------
with tab1:
    st.subheader("Resumo de Desempenho")

    total_vendas = vendas["_VAL_TOTAL"].sum()
    total_lucro = vendas["_LUCRO"].sum()
    total_estoque = estoque["_VAL_TOTAL_VENDA"].sum()

    c1, c2, c3 = st.columns(3)
    c1.markdown(
        f"<div class='kpi'><div class='kpi-label'>💰 Total de Vendas</div><div class='kpi-value'>{fmt_brl(total_vendas)}</div></div>",
        unsafe_allow_html=True,
    )
    c2.markdown(
        f"<div class='kpi'><div class='kpi-label'>📈 Lucro Estimado</div><div class='kpi-value'>{fmt_brl(total_lucro)}</div></div>",
        unsafe_allow_html=True,
    )
    c3.markdown(
        f"<div class='kpi'><div class='kpi-label'>📦 Valor de Estoque (Venda)</div><div class='kpi-value'>{fmt_brl(total_estoque)}</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.subheader("Top 10 Produtos Mais Vendidos")
    top = (
        vendas.groupby(v_prod)
        .agg(QTD=(v_qtd, "sum"), VALOR=("_VAL_TOTAL", "sum"))
        .sort_values("VALOR", ascending=False)
        .head(10)
        .reset_index()
    )

    fig_top = px.bar(
        top,
        x="VALOR",
        y=v_prod,
        orientation="h",
        text="QTD",
        color="VALOR",
        color_continuous_scale=["#FFD700", "#B8860B"],
    )
    fig_top.update_layout(
        plot_bgcolor=t["bg"],
        paper_bgcolor=t["bg"],
        font_color=t["text"],
        yaxis={"categoryorder": "total ascending"},
    )
    st.plotly_chart(fig_top, use_container_width=True)

# ------------------ ESTOQUE ------------------
with tab2:
    st.subheader("Controle de Estoque — Venda x Custo")

    val_venda_total = estoque["_VAL_TOTAL_VENDA"].sum()
    val_custo_total = estoque["_VAL_TOTAL_CUSTO"].sum()

    c1, c2 = st.columns(2)
    c1.metric("💰 Valor Total (Venda)", fmt_brl(val_venda_total))
    c2.metric("💸 Valor Total (Custo)", fmt_brl(val_custo_total))

    st.markdown("---")
    est_show = estoque[
        [e_prod, "_QTD", "_VAL_VENDA", "_VAL_CUSTO", "_VAL_TOTAL_VENDA", "_VAL_TOTAL_CUSTO"]
    ].rename(
        columns={
            e_prod: "PRODUTO",
            "_QTD": "QTD",
            "_VAL_VENDA": "PREÇO VENDA",
            "_VAL_CUSTO": "PREÇO CUSTO",
            "_VAL_TOTAL_VENDA": "TOTAL VENDA",
            "_VAL_TOTAL_CUSTO": "TOTAL CUSTO",
        }
    )
    for col in ["PREÇO VENDA", "PREÇO CUSTO", "TOTAL VENDA", "TOTAL CUSTO"]:
        est_show[col] = est_show[col].apply(fmt_brl)

    st.dataframe(est_show, use_container_width=True)

    st.markdown("---")
    fig_est = px.bar(
        estoque.sort_values("_VAL_TOTAL_VENDA", ascending=False).head(15),
        x=e_prod,
        y="_VAL_TOTAL_VENDA",
        title="Top 15 - Valor de Estoque (Venda)",
        color="_VAL_TOTAL_VENDA",
        color_continuous_scale=["#FFD700", "#B8860B"],
    )
    fig_est.update_layout(
        plot_bgcolor=t["bg"], paper_bgcolor=t["bg"], font_color=t["text"]
    )
    st.plotly_chart(fig_est, use_container_width=True)

st.markdown("---")
st.caption(f"Tema atual: {selected_theme} • Desenvolvido em Streamlit — Loja Importados 🛍️")
