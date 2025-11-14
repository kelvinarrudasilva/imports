# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re
from datetime import datetime

# ======================
# Config visual (Alto contraste: Preto + Dourado)
# ======================
st.set_page_config(page_title="Painel - Loja Importados", layout="wide")

st.markdown(
    """
    <style>
      :root { --gold:#FFD700; --bg:#000000; --card:#0f0f0f; --muted:#bbbbbb; --white:#FFFFFF; }
      .stApp { background-color: var(--bg); color: var(--gold); }
      .title { color: var(--gold); font-weight:700; font-size:22px; }
      .subtitle { color: var(--muted); font-size:12px; margin-bottom:12px; }
      .kpi { background: linear-gradient(90deg, #111111, #0b0b0b); padding:12px; border-radius:10px; text-align:center; }
      .kpi-value { color: var(--gold); font-size:22px; font-weight:700; }
      .kpi-label { color:var(--muted); font-size:13px; }
      .stDataFrame table { background-color:#050505; color:var(--white); }
      .small { color: var(--muted); font-size:12px; }
      /* table-card: emphasized block below Top10 */
      .table-card { background: linear-gradient(90deg,#0b0b0b,#111111); border: 1px solid rgba(255,215,0,0.08); padding:12px; border-radius:10px; }
      .table-card h4 { color: var(--gold); margin:0 0 8px 0; }
      .table-card .big { font-size:15px; color:var(--white); }
      /* make select smaller */
      .small-select .stSelectbox>div>div { font-size:14px; }
      /* increase dataframe font for the summary below */
      .summary-table .dataframe td, .summary-table .dataframe th { font-size:13px !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div class='title'>📊 Painel — Loja Importados</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Tema: Preto & Dourado (alto contraste) • Abas: Visão Geral / Estoque / Vendas</div>", unsafe_allow_html=True)
st.markdown("---")

# ======================
# Helpers: detect header, clean df, find_col, numeric, fmt
# ======================
def detect_header(path, sheet_name, look_for="PRODUTO"):
    try:
        raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
    except Exception:
        return None, None
    header_row = None
    for i in range(min(len(raw), 12)):
        row = raw.iloc[i].astype(str).str.upper().fillna("")
        if any(look_for.upper() in v for v in row):
            header_row = i
            break
    if header_row is None:
        header_row = 0
    try:
        df = pd.read_excel(path, sheet_name=sheet_name, header=header_row)
        return df, header_row
    except Exception:
        return None, None


def clean_df(df):
    if df is None:
        return None
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains("^Unnamed", na=False)]
    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all").reset_index(drop=True)
    return df


def find_col(df, *candidates):
    if df is None:
        return None
    for cand in candidates:
        if cand is None:
            continue
        pat = re.sub(r"\s+", " ", str(cand)).strip().upper()
        for c in df.columns:
            if pat in str(c).upper():
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
# Load file & sheets (only needed three)
# ======================
EXCEL = "LOJA IMPORTADOS.xlsx"
if not Path(EXCEL).exists():
    st.error(f"Arquivo '{EXCEL}' não encontrado no diretório do app.")
    st.stop()

xls = pd.ExcelFile(EXCEL)
available_sheets = [s.upper() for s in xls.sheet_names]

def load_and_clean(name):
    if name not in available_sheets:
        return None
    df, hdr = detect_header(EXCEL, name)
    df = clean_df(df)
    return df

estoque = load_and_clean("ESTOQUE")
vendas = load_and_clean("VENDAS")
compras = load_and_clean("COMPRAS")

# safe empty frames to avoid many ifs
if vendas is None:
    vendas = pd.DataFrame()
if estoque is None:
    estoque = pd.DataFrame()
if compras is None:
    compras = pd.DataFrame()

# ======================
# Map columns (robust)
# ======================
# ESTOQUE: PRODUTO, EM ESTOQUE, Media C. UNITARIO, Valor Venda Sugerido
e_prod = find_col(estoque, "PRODUTO")
e_qtd = find_col(estoque, "EM ESTOQUE", "QTD", "QUANTIDADE", "QUANT")
e_val_venda = find_col(estoque, "Valor Venda Sugerido", "VALOR VENDA", "VALOR VENDA SUGERIDO")
e_val_custo = find_col(estoque, "Media C. UNITARIO", "MEDIA C. UNITARIO", "CUSTO UNITARIO", "CUSTO")

# VENDAS: DATA, PRODUTO, QTD, VALOR VENDA, VALOR TOTAL, MEDIA CUSTO UNITARIO, LUCRO
v_data = find_col(vendas, "DATA", "DT")
v_prod = find_col(vendas, "PRODUTO")
v_qtd = find_col(vendas, "QTD", "QUANTIDADE", "QUANT")
v_val_unit = find_col(vendas, "VALOR VENDA", "VALOR_VENDA", "PRECO")
v_val_total = find_col(vendas, "VALOR TOTAL", "VALOR_TOTAL", "TOTAL")
v_lucro = find_col(vendas, "LUCRO")

# COMPRAS: CUSTO UNITÁRIO, CUSTO TOTAL
c_custo_unit = find_col(compras, "CUSTO UNITÁRIO", "CUSTO UNIT", "CUSTO_UNIT")
c_custo_total = find_col(compras, "CUSTO TOTAL", "VALOR TOTAL", "TOTAL")

# ======================
# Prepare numeric columns safely
# ======================
# Vendas: compute _VAL_TOTAL and ensure _LUCRO derived from column LUCRO if present
if not vendas.empty:
    if v_data and v_data in vendas.columns:
        vendas[v_data] = pd.to_datetime(vendas[v_data], errors="coerce")
    vendas["_QTD"] = to_num(vendas[v_qtd]) if v_qtd in vendas.columns else 0
    if v_val_total and v_val_total in vendas.columns:
        vendas["_VAL_TOTAL"] = to_num(vendas[v_val_total])
    elif v_val_unit and v_val_unit in vendas.columns:
        vendas["_VAL_TOTAL"] = to_num(vendas[v_val_unit]) * vendas["_QTD"]
    else:
        vendas["_VAL_TOTAL"] = 0
    if v_lucro and v_lucro in vendas.columns:
        vendas["_LUCRO"] = to_num(vendas[v_lucro])
    else:
        vendas["_LUCRO"] = 0

else:
    vendas["_QTD"] = pd.Series(dtype=float)
    vendas["_VAL_TOTAL"] = pd.Series(dtype=float)
    vendas["_LUCRO"] = pd.Series(dtype=float)

# Estoque: unit sale price and cost and totals
if not estoque.empty:
    estoque["_QTD"] = to_num(estoque[e_qtd]) if e_qtd in estoque.columns else 0
    estoque["_VAL_VENDA_UNIT"] = to_num(estoque[e_val_venda]) if e_val_venda in estoque.columns else 0
    estoque["_VAL_CUSTO_UNIT"] = to_num(estoque[e_val_custo]) if e_val_custo in estoque.columns else 0
    estoque["_VAL_TOTAL_VENDA"] = estoque["_QTD"] * estoque["_VAL_VENDA_UNIT"]
    estoque["_VAL_TOTAL_CUSTO"] = estoque["_QTD"] * estoque["_VAL_CUSTO_UNIT"]
else:
    estoque["_QTD"] = pd.Series(dtype=float)
    estoque["_VAL_VENDA_UNIT"] = pd.Series(dtype=float)
    estoque["_VAL_CUSTO_UNIT"] = pd.Series(dtype=float)
    estoque["_VAL_TOTAL_VENDA"] = pd.Series(dtype=float)
    estoque["_VAL_TOTAL_CUSTO"] = pd.Series(dtype=float)

# ======================
# Month selector (no sidebar) - for Visão Geral and Vendas Detalhadas
# ======================
# Build period options as YYYY-MM strings, display as "MMM YYYY" for UI
if not vendas.empty and "_VAL_TOTAL" in vendas.columns and v_data in vendas.columns:
    vendas["_PERIODO"] = vendas[v_data].dt.to_period("M").astype(str)  # e.g. '2025-11'
    unique_periods = sorted(vendas["_PERIODO"].unique(), reverse=True)
else:
    unique_periods = []

# build options: "Geral" + human readable list
period_options = ["Geral"]
period_map = {"Geral": None}
for p in unique_periods:
    # pretty label abbreviated
    try:
        year, month = p.split("-")
        pretty = datetime(int(year), int(month), 1).strftime("%b %Y")  # Nov 2025
    except Exception:
        pretty = p
    label = f"{pretty} ({p})"
    period_options.append(label)
    period_map[label] = p

# default: current month if exists, otherwise "Geral"
current_period = datetime.now().strftime("%Y-%m")
default_label = "Geral"
for lbl, val in period_map.items():
    if val == current_period:
        default_label = lbl
        break

# ======================
# Tabs: Visão Geral / Estoque / Vendas
# ======================
tab1, tab2, tab3 = st.tabs(["📈 Visão Geral", "📦 Estoque Atual", "🛒 Vendas Detalhadas"])

# ---- Tab 1: Visão Geral ----
with tab1:
    # compact month selector on the right
    col_sel, col_space = st.columns([1, 6])
    with col_space:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    with col_sel:
        periodo_sel = st.selectbox("", options=period_options, index=period_options.index(default_label) if default_label in period_options else 0, label_visibility='collapsed')
        # show small label next to selector
        st.markdown(f"<div class='small' style='text-align:right;'>Periodo: <strong style='color:var(--gold);'>{periodo_sel.split(' (')[0]}</strong></div>", unsafe_allow_html=True)

    # determine filter value
    periodo_val = period_map.get(periodo_sel)

    # filter vendas by period
    if periodo_val is None:
        vendas_period = vendas.copy()
    else:
        vendas_period = vendas[vendas.get("_PERIODO", "") == periodo_val].copy()

    # KPIs: Vendido, Qtde Vendida, Lucro do período, Valor do Estoque (venda)
    total_vendido = vendas_period["_VAL_TOTAL"].sum() if not vendas_period.empty else 0
    total_qtd = vendas_period["_QTD"].sum() if not vendas_period.empty else 0
    lucro_period = vendas_period["_LUCRO"].sum() if not vendas_period.empty else 0
    valor_estoque_venda = estoque["_VAL_TOTAL_VENDA"].sum() if not estoque.empty else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(f"<div class='kpi'><div class='kpi-label'>💰 Vendido</div><div class='kpi-value'>{fmt_brl(total_vendido)}</div></div>", unsafe_allow_html=True)
    c2.markdown(f"<div class='kpi'><div class='kpi-label'>📈 Qtde Vendida</div><div class='kpi-value'>{int(total_qtd)}</div></div>", unsafe_allow_html=True)
    c3.markdown(f"<div class='kpi'><div class='kpi-label'>💸 Lucro do Período</div><div class='kpi-value'>{fmt_brl(lucro_period)}</div></div>", unsafe_allow_html=True)
    c4.markdown(f"<div class='kpi'><div class='kpi-label'>📦 Valor Estoque (Venda)</div><div class='kpi-value'>{fmt_brl(valor_estoque_venda)}</div></div>", unsafe_allow_html=True)

    st.markdown("---")
    # Top 10 produtos mais vendidos no período
    st.subheader("🏆 Top 10 — Produtos Mais Vendidos (quantidade + valor)")
    if not vendas_period.empty and v_prod in vendas_period.columns:
        grp = vendas_period.groupby(v_prod).agg(QTDE_SOMADA=("_QTD", "sum"), VAL_TOTAL=("_VAL_TOTAL", "sum")).reset_index()
        grp = grp.sort_values("VAL_TOTAL", ascending=False).head(10)
        if not grp.empty:
            fig_top = px.bar(grp, x="VAL_TOTAL", y=v_prod, orientation="h", text="QTDE_SOMADA", color="VAL_TOTAL", color_continuous_scale=["#FFD700", "#B8860B"]) 
            fig_top.update_traces(texttemplate='%{text:.0f} un', textposition='outside')
            fig_top.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000", font_color="#FFD700", yaxis={'categoryorder':'total ascending'}, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_top, use_container_width=True)

            # Enhanced summary below Top10 — bigger, clearer, with subtle border
            display = grp.copy()
            display["VAL_TOTAL_FORMAT"] = display["VAL_TOTAL"].apply(fmt_brl)
            display["QTDE_SOMADA"] = display["QTDE_SOMADA"].astype(int)
            display = display.rename(columns={v_prod: "PRODUTO", "QTDE_SOMADA": "QUANTIDADE", "VAL_TOTAL_FORMAT": "VALOR TOTAL"})

            st.markdown("<div class='table-card'>", unsafe_allow_html=True)
            st.markdown("<h4>Resumo — Top 10</h4>", unsafe_allow_html=True)
            # create HTML table for higher visibility
            html = "<table style='width:100%; border-collapse:collapse;'>"
            html += "<thead><tr><th style='text-align:left;padding:6px;color:var(--muted)'>Produto</th><th style='text-align:right;padding:6px;color:var(--muted)'>Quantidade</th><th style='text-align:right;padding:6px;color:var(--muted)'>Valor Total</th></tr></thead><tbody>"
            for _, row in display.iterrows():
                html += f"<tr style='border-top:1px solid rgba(255,215,0,0.03)'><td style='padding:8px;color:var(--white);font-weight:600'>{row['PRODUTO']}</td><td style='padding:8px;text-align:right;color:var(--white)'>{int(row['QUANTIDADE'])}</td><td style='padding:8px;text-align:right;color:var(--gold);font-weight:700'>{row['VALOR TOTAL']}</td></tr>"
            html += "</tbody></table>"
            st.markdown(html, unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)

            # add extra spacing and a clear divider
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        else:
            st.info("Nenhum produto encontrado para o período selecionado.")
    else:
        st.info("Nenhuma venda disponível para o período ou coluna de produto ausente.")

    # Últimas vendas resumido (10 linhas)
    st.markdown("---")
    st.subheader("🕒 Últimas Vendas (resumido)")
    if not vendas.empty and v_data in vendas.columns and v_prod in vendas.columns:
        ult = vendas.sort_values(v_data, ascending=False).head(10)[[v_data, v_prod, "_QTD", "_VAL_TOTAL", "_LUCRO"]].copy()
        # format
        ult[v_data] = pd.to_datetime(ult[v_data], errors="coerce").dt.strftime("%d/%m/%Y")
        ult["_VAL_TOTAL"] = ult["_VAL_TOTAL"].apply(fmt_brl)
        if "_LUCRO" in ult.columns:
            ult["_LUCRO"] = ult["_LUCRO"].apply(fmt_brl)
        ult = ult.rename(columns={v_data: "Data", v_prod: "Produto", "_QTD": "Qtd", "_VAL_TOTAL": "Valor", "_LUCRO": "Lucro"})
        st.dataframe(ult.reset_index(drop=True))
    else:
        st.info("Sem vendas registradas.")

# ---- Tab 2: Estoque Atual ----
with tab2:
    st.markdown("## Estoque Atual — sem filtros (mostra tudo)")
    if not estoque.empty and e_prod in estoque.columns:
        est = estoque.copy()
        est["PRODUTO"] = est[e_prod].astype(str)
        est["QTD"] = est["_QTD"].astype(int) if "_QTD" in est.columns else 0
        # ensure total columns available
        if "_VAL_VENDA_UNIT" in est.columns:
            est["PRECO_VENDA_NUM"] = est["_VAL_VENDA_UNIT"]
            est["PRECO VENDA"] = est["_VAL_VENDA_UNIT"].apply(fmt_brl)
        else:
            est["PRECO_VENDA_NUM"] = 0
            est["PRECO VENDA"] = ""
        if "_VAL_CUSTO_UNIT" in est.columns:
            est["PRECO_CUSTO_NUM"] = est["_VAL_CUSTO_UNIT"]
            est["PRECO CUSTO"] = est["_VAL_CUSTO_UNIT"].apply(fmt_brl)
        else:
            est["PRECO_CUSTO_NUM"] = 0
            est["PRECO CUSTO"] = ""
        est["VALOR_TOTAL_VENDA"] = est.get("_VAL_TOTAL_VENDA", 0)
        est["VALOR_TOTAL_CUSTO"] = est.get("_VAL_TOTAL_CUSTO", 0)

        total_qtd_est = est["QTD"].sum()
        total_val_venda = est["VALOR_TOTAL_VENDA"].sum()
        total_val_custo = est["VALOR_TOTAL_CUSTO"].sum()
        c1, c2, c3 = st.columns([1,1,1])
        c1.metric("📦 Qtde total em estoque", f"{int(total_qtd_est):,}".replace(",","."))
        c2.metric("💰 Valor total (Venda)", fmt_brl(total_val_venda))
        c3.metric("💸 Valor total (Custo)", fmt_brl(total_val_custo))
        st.markdown("---")

        # Chart: show quantity inside the bar (center)
        st.subheader("Top 15 — Quantidade em Estoque (labels dentro das barras)")
        top_est = est.sort_values("QTD", ascending=False).head(15)
        if not top_est.empty:
            fig_est = px.bar(top_est, x="PRODUTO", y="QTD", text="QTD", color="QTD", color_continuous_scale=["#FFD700","#B8860B"]) 
            fig_est.update_traces(texttemplate='%{text}', textposition='inside')
            fig_est.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000", font_color="#FFD700", xaxis_title=None, yaxis_title="Quantidade", margin=dict(l=20,r=20,t=30,b=100))
            # make inside text white for visibility
            fig_est.update_traces(textfont=dict(color="black", size=12))
            st.plotly_chart(fig_est, use_container_width=True)

        st.markdown("---")
        # Table with formatted values
        df_show = est[["PRODUTO", "QTD", "PRECO VENDA", "PRECO CUSTO", "VALOR_TOTAL_VENDA", "VALOR_TOTAL_CUSTO"]].copy()
        df_show = df_show.rename(columns={"VALOR_TOTAL_VENDA":"VALOR TOTAL (VENDA)", "VALOR_TOTAL_CUSTO":"VALOR TOTAL (CUSTO)"})
        df_show["VALOR TOTAL (VENDA)"] = df_show["VALOR TOTAL (VENDA)"].apply(fmt_brl)
        df_show["VALOR TOTAL (CUSTO)"] = df_show["VALOR TOTAL (CUSTO)"].apply(fmt_brl)
        st.dataframe(df_show.sort_values("QTD", ascending=False).reset_index(drop=True))
    else:
        st.warning("Aba ESTOQUE não carregada ou colunas necessárias ausentes.")

# ---- Tab 3: Vendas Detalhadas ----
with tab3:
    st.markdown("### Seletor de mês (igual ao da Visão Geral)")
    periodo_sel2 = st.selectbox("Escolha mês (ou Geral):", options=period_options, index=period_options.index(default_label) if default_label in period_options else 0, key="vendas_period")
    periodo_val2 = period_map.get(periodo_sel2)
    if periodo_val2 is None:
        vendas_det = vendas.copy()
    else:
        vendas_det = vendas[vendas.get("_PERIODO", "") == periodo_val2].copy()

    if not vendas_det.empty and v_data in vendas_det.columns:
        vendas_det_display = vendas_det[[v_data, v_prod, "_QTD", "_VAL_TOTAL", "_LUCRO"]].copy() if "_LUCRO" in vendas_det.columns else vendas_det[[v_data, v_prod, "_QTD", "_VAL_TOTAL"]].copy()
        # formatting
        vendas_det_display["_VAL_TOTAL"] = vendas_det_display["_VAL_TOTAL"].apply(fmt_brl)
        if "_LUCRO" in vendas_det_display.columns:
            vendas_det_display["_LUCRO"] = vendas_det_display["_LUCRO"].apply(fmt_brl)
        vendas_det_display["_QTD"] = vendas_det_display["_QTD"].astype(int)
        vendas_det_display[v_data] = pd.to_datetime(vendas_det_display[v_data], errors="coerce").dt.strftime("%d/%m/%Y")
        vendas_det_display = vendas_det_display.rename(columns={v_data:"Data", v_prod:"Produto", "_QTD":"Quantidade", "_VAL_TOTAL":"Valor", "_LUCRO":"Lucro"})
        st.dataframe(vendas_det_display.sort_values("Data", ascending=False).reset_index(drop=True))
    else:
        st.info("Nenhuma venda encontrada para o período selecionado ou dados ausentes.")

# ======================
# Diagnóstico (expansível)
# ======================
with st.expander("🔧 Diagnóstico (colunas detectadas)"):
    st.write("ESTOQUE:", list(estoque.columns))
    st.write("VENDAS:", list(vendas.columns))
    st.write("COMPRAS:", list(compras.columns))
    st.write("Mapeamento usado:")
    st.write({
        "ESTOQUE": {"PRODUTO": e_prod, "QTD": e_qtd, "VAL VENDA UNIT": e_val_venda, "VAL CUSTO UNIT": e_val_custo},
        "VENDAS": {"DATA": v_data, "PROD": v_prod, "QTD": v_qtd, "VAL TOTAL": v_val_total, "LUCRO": v_lucro},
        "COMPRAS": {"CUSTO UNIT": c_custo_unit, "CUSTO TOTAL": c_custo_total}
    })

st.markdown("---")
st.caption("Dashboard — Tema: Preto + Dourado (alto contraste). Desenvolvido em Streamlit.")
