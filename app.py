# app.py
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
import re

# ======================
# Config visual (Alto contraste: Preto + Dourado)
# ======================
st.set_page_config(page_title="Painel - Loja Importados", layout="wide")

st.markdown(
    """
    <style>
      :root { --gold:#FFD700; --bg:#000000; --card:#0f0f0f; --muted:#bfbfbf; }
      .stApp { background-color: var(--bg); color: var(--gold); }
      .title { color: var(--gold); font-weight:700; font-size:22px; }
      .subtitle { color: var(--muted); font-size:12px; margin-bottom:12px; }
      .kpi { background: linear-gradient(90deg, #111111, #0b0b0b); padding:12px; border-radius:10px; text-align:center; }
      .kpi-value { color: var(--gold); font-size:20px; font-weight:700; }
      .kpi-label { color:var(--muted); font-size:13px; }
      .stDataFrame table { background-color:#050505; color:#e6e2d3; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div class='title'>📊 Painel — Loja Importados</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Tema: Alto contraste — Preto & Dourado • Abas: Visão Geral / Estoque</div>", unsafe_allow_html=True)
st.markdown("---")

# ======================
# Util helpers: detect header, clean df, col finder, formatting
# ======================
def detect_header(path, sheet_name, look_for="PRODUTO"):
    """Leia sem header, detecte linha que contém look_for e retorne df com header correto."""
    raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
    header_row = None
    for i in range(min(len(raw), 12)):
        row = raw.iloc[i].astype(str).str.upper().fillna("")
        if any(look_for.upper() in v for v in row):
            header_row = i
            break
    if header_row is None:
        header_row = 0
    df = pd.read_excel(path, sheet_name=sheet_name, header=header_row)
    return df, header_row

def clean_df(df):
    if df is None:
        return None
    # remove Unnamed columns and empty cols/rows
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains("^Unnamed", na=False)]
    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all").reset_index(drop=True)
    return df

def find_col(df, *candidates):
    """Retorna o nome original da primeira coluna que contém qualquer candidato (case-insensitive)."""
    if df is None:
        return None
    for cand in candidates:
        pattern = re.sub(r"\s+", " ", str(cand)).strip().upper()
        for c in df.columns:
            if pattern in str(c).upper():
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
# Carregar planilha (apenas 3 abas)
# ======================
EXCEL = "LOJA IMPORTADOS.xlsx"
if not Path(EXCEL).exists():
    st.error(f"Arquivo '{EXCEL}' não encontrado no diretório do app.")
    st.stop()

xls = pd.ExcelFile(EXCEL)
available = set([s.upper() for s in xls.sheet_names])
needed = {"ESTOQUE", "VENDAS", "COMPRAS"}
found = needed.intersection(available)
st.sidebar.markdown("### Fonte")
st.sidebar.write("Abas encontradas:", list(xls.sheet_names))
st.sidebar.markdown("---")

# load and clean each sheet
def load_sheet(name):
    if name not in available:
        return None, f"Aba '{name}' não encontrada"
    df, hdr = detect_header(EXCEL, name)
    df = clean_df(df)
    return df, None

estoque, err_e = load_sheet("ESTOQUE")
vendas, err_v = load_sheet("VENDAS")
compras, err_c = load_sheet("COMPRAS")

# show read errors
if err_e: st.warning(err_e)
if err_v: st.warning(err_v)
if err_c: st.warning(err_c)

# ======================
# Mapear colunas com base nos nomes reais que você forneceu
# ======================
# Estoque: PRODUTO, EM ESTOQUE, Media C. UNITARIO, Valor Venda Sugerido
e_prod = find_col(estoque, "PRODUTO")
e_qtd = find_col(estoque, "EM ESTOQUE", "QTD", "QUANTIDADE")
e_valor_unit = find_col(estoque, "Valor Venda Sugerido", "VALOR VENDA")

# Vendas: DATA, PRODUTO, QTD, VALOR VENDA, VALOR TOTAL, MEDIA CUSTO UNITARIO, LUCRO
v_data = find_col(vendas, "DATA")
v_prod = find_col(vendas, "PRODUTO")
v_qtd = find_col(vendas, "QTD", "QUANTIDADE")
v_val_unit = find_col(vendas, "VALOR VENDA", "VALOR_VENDA")
v_val_total = find_col(vendas, "VALOR TOTAL", "VALOR_TOTAL", "TOTAL")
v_media_custo = find_col(vendas, "MEDIA CUSTO UNITARIO", "MEDIA C. UNITARIO")
v_lucro = find_col(vendas, "LUCRO")

# Compras: DATA, PRODUTO, QUANTIDADE, CUSTO UNITÁRIO, CUSTO TOTAL
c_data = find_col(compras, "DATA")
c_prod = find_col(compras, "PRODUTO")
c_qtd = find_col(compras, "QUANTIDADE", "QTD")
c_custo_unit = find_col(compras, "CUSTO UNITÁRIO", "CUSTO UNIT")
c_custo_total = find_col(compras, "CUSTO TOTAL", "VALOR TOTAL")

# Aviso se algo essencial faltar (não para, só avisa)
missing = []
if estoque is None: missing.append("ESTOQUE não carregada")
if vendas is None: missing.append("VENDAS não carregada")
if compras is None: missing.append("COMPRAS não carregada")
if missing:
    st.warning(" | ".join(missing))

# ======================
# Preparar/normalizar dados
# ======================
# VENDAS: datas e valores
if vendas is not None:
    if v_data in vendas.columns:
        vendas[v_data] = pd.to_datetime(vendas[v_data], errors="coerce")
    # ensure numeric
    if v_val_unit in (vendas.columns if vendas is not None else []):
        vendas["_VAL_UNIT"] = to_num(vendas[v_val_unit])
    if v_qtd in (vendas.columns if vendas is not None else []):
        vendas["_QTD"] = to_num(vendas[v_qtd])
    # prefer VALOR TOTAL column; if missing, compute from unit*qty
    if v_val_total in (vendas.columns if vendas is not None else []):
        vendas["_VAL_TOTAL"] = to_num(vendas[v_val_total])
    elif "_VAL_UNIT" in vendas.columns and "_QTD" in vendas.columns:
        vendas["_VAL_TOTAL"] = vendas["_VAL_UNIT"] * vendas["_QTD"]
    else:
        vendas["_VAL_TOTAL"] = 0
    # lucro: use user column if exists, otherwise compute (but we prefer user's)
    if v_lucro in (vendas.columns if vendas is not None else []):
        vendas["_LUCRO_USR"] = to_num(vendas[v_lucro])
        vendas["_LUCRO"] = vendas["_LUCRO_USR"]
    else:
        # try compute using media custo or lookup from estoque
        if v_media_custo in (vendas.columns if vendas is not None else []):
            vendas["_CUSTO_UNIT"] = to_num(vendas[v_media_custo])
        else:
            vendas["_CUSTO_UNIT"] = 0
            # try map from estoque media custo
            e_media = find_col(estoque, "Media C. UNITARIO", "MEDIA C")
            if e_media and e_prod in (estoque.columns if estoque is not None else []) and v_prod in (vendas.columns if vendas is not None else []):
                mapa = estoque[[e_prod, e_media]].dropna()
                try:
                    mapa[e_prod] = mapa[e_prod].astype(str).str.strip()
                    mapa_dict = mapa.set_index(e_prod)[e_media].to_dict()
                    vendas["_CUSTO_UNIT"] = vendas[v_prod].astype(str).str.strip().map(mapa_dict).fillna(0)
                except Exception:
                    vendas["_CUSTO_UNIT"] = 0
        vendas["_LUCRO"] = (vendas["_VAL_UNIT"].fillna(0) - vendas["_CUSTO_UNIT"].fillna(0)) * vendas["_QTD"].fillna(0)

# COMPRAS numeric/date
if compras is not None:
    if c_data in compras.columns:
        compras[c_data] = pd.to_datetime(compras[c_data], errors="coerce")
    if c_custo_total in (compras.columns if compras is not None else []):
        compras["_CUSTO_TOTAL"] = to_num(compras[c_custo_total])
    if c_custo_unit in (compras.columns if compras is not None else []):
        compras["_CUSTO_UNIT"] = to_num(compras[c_custo_unit])
    if c_qtd in (compras.columns if compras is not None else []):
        compras["_QTD"] = to_num(compras[c_qtd])

# ESTOQUE numeric
if estoque is not None:
    if e_qtd in (estoque.columns if estoque is not None else []):
        estoque["_QTD_ESTOQUE"] = to_num(estoque[e_qtd])
    if e_valor_unit in (estoque.columns if estoque is not None else []):
        estoque["_VAL_UNIT_ESTOQ"] = to_num(estoque[e_valor_unit])
    if "_QTD_ESTOQUE" in estoque.columns and "_VAL_UNIT_ESTOQ" in estoque.columns:
        estoque["_VAL_TOTAL_ESTOQUE"] = estoque["_QTD_ESTOQUE"] * estoque["_VAL_UNIT_ESTOQ"]
    else:
        estoque["_VAL_TOTAL_ESTOQUE"] = 0

# ======================
# Sidebar filters (period and product)
# ======================
st.sidebar.header("Filtros")
# date filter based on vendas
if vendas is not None and v_data in vendas.columns:
    min_date = vendas[v_data].min().date() if pd.notna(vendas[v_data].min()) else None
    max_date = vendas[v_data].max().date() if pd.notna(vendas[v_data].max()) else None
    date_range = st.sidebar.date_input("Período (Vendas)", value=(min_date, max_date))
else:
    date_range = None

# product filter from union of vendas+estoque
prod_set = set()
if vendas is not None and v_prod in (vendas.columns if vendas is not None else []):
    prod_set.update(vendas[v_prod].dropna().astype(str).unique())
if estoque is not None and e_prod in (estoque.columns if estoque is not None else []):
    prod_set.update(estoque[e_prod].dropna().astype(str).unique())
prod_list = sorted([p for p in prod_set if str(p).strip() != ""])
prod_filter = st.sidebar.multiselect("Produtos (filtrar)", options=prod_list, default=prod_list)

st.sidebar.markdown("---")
st.sidebar.caption("Aplicar filtros atualiza KPIs e os Top 10 automaticamente.")

# Apply filters
vendas_f = vendas.copy() if vendas is not None else pd.DataFrame()
if date_range and isinstance(date_range, (list, tuple)) and len(date_range) == 2 and v_data in (vendas.columns if vendas is not None else []):
    d_from, d_to = date_range
    try:
        vendas_f = vendas_f[(vendas_f[v_data].dt.date >= d_from) & (vendas_f[v_data].dt.date <= d_to)]
    except Exception:
        pass

if prod_filter:
    vendas_f = vendas_f[vendas_f[v_prod].astype(str).isin(prod_filter)]

# ======================
# Abas: Visão Geral / Estoque
# ======================
tab1, tab2 = st.tabs(["📈 Visão Geral", "📦 Estoque Atual"])

with tab1:
    st.markdown("## Visão Geral — vendas e lucro (período filtrado)")
    # KPIs: total vendido no período, lucro no período, valor total estoque
    total_vendido_period = vendas_f["_VAL_TOTAL"].sum() if "_VAL_TOTAL" in vendas_f.columns else 0
    lucro_period = vendas_f["_LUCRO"].sum() if "_LUCRO" in vendas_f.columns else 0
    valor_total_estoque = estoque["_VAL_TOTAL_ESTOQUE"].sum() if estoque is not None and "_VAL_TOTAL_ESTOQUE" in estoque.columns else 0
    k1, k2, k3 = st.columns(3)
    k1.markdown(f"<div class='kpi'><div class='kpi-label'>💰 Vendido no período</div><div class='kpi-value'>{fmt_brl(total_vendido_period)}</div></div>", unsafe_allow_html=True)
    k2.markdown(f"<div class='kpi'><div class='kpi-label'>📈 Lucro no período</div><div class='kpi-value'>{fmt_brl(lucro_period)}</div></div>", unsafe_allow_html=True)
    k3.markdown(f"<div class='kpi'><div class='kpi-label'>📦 Valor total do estoque</div><div class='kpi-value'>{fmt_brl(valor_total_estoque)}</div></div>", unsafe_allow_html=True)
    st.markdown("---")

    # Top 10 produtos mais vendidos (quantidade e valor total)
    st.subheader("🏆 Top 10 — Produtos Mais Vendidos (quantidade + valor)")
    if v_prod in (vendas_f.columns if vendas_f is not None else []) and v_qtd in (vendas_f.columns if vendas_f is not None else []):
        top = vendas_f.groupby(v_prod).agg(
            QTDE_SOMADA=(v_qtd, lambda s: to_num(s).sum()),
            VAL_TOTAL=( "_VAL_TOTAL", lambda s: to_num(s).sum())
        ).reset_index()
        top = top.sort_values("VAL_TOTAL", ascending=False).head(10)
        if not top.empty:
            # bar horizontal: valor total (gold), show quantity as annotation
            fig_top = px.bar(top, x="VAL_TOTAL", y=v_prod, orientation="h", text="QTDE_SOMADA", color="VAL_TOTAL", color_continuous_scale=["#FFD700", "#B8860B"])
            fig_top.update_traces(texttemplate='%{text:.0f} un', textposition='outside')
            fig_top.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000", font_color="#FFD700", yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_top, use_container_width=True)
            # table
            top_display = top.copy()
            top_display["VAL_TOTAL"] = top_display["VAL_TOTAL"].apply(fmt_brl)
            top_display["QTDE_SOMADA"] = top_display["QTDE_SOMADA"].astype(int)
            st.table(top_display.rename(columns={v_prod:"PRODUTO","QTDE_SOMADA":"QUANTIDADE","VAL_TOTAL":"VALOR TOTAL"}))
        else:
            st.info("Nenhuma venda no período/filtragem selecionada.")
    else:
        st.warning("Colunas de produto/quantidade não encontradas em VENDAS.")

    st.markdown("---")
    # Vendas e Lucro por mês (linha)
    st.subheader("📅 Vendas mensais & Lucro mensal")
    if v_data in (vendas.columns if vendas is not None else []):
        tmp = vendas.copy()
        tmp[v_data] = pd.to_datetime(tmp[v_data], errors="coerce")
        tmp["_MES"] = tmp[v_data].dt.to_period("M").astype(str)
        if "_VAL_TOTAL" in tmp.columns:
            vendas_mes = tmp.groupby("_MES")["_VAL_TOTAL"].sum().reset_index().rename(columns={"_VAL_TOTAL":"VALOR"})
            fig_vmes = px.bar(vendas_mes, x="_MES", y="VALOR", title="Vendas Mensais", color="VALOR", color_continuous_scale=["#FFD700","#B8860B"])
            fig_vmes.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000", font_color="#FFD700")
            st.plotly_chart(fig_vmes, use_container_width=True)
        if "_LUCRO" in tmp.columns:
            lucro_mes = tmp.groupby("_MES")["_LUCRO"].sum().reset_index().rename(columns={"_LUCRO":"LUCRO"})
            fig_luc = px.line(lucro_mes, x="_MES", y="LUCRO", title="Lucro Mensal", markers=True)
            fig_luc.update_traces(line=dict(color="#FFD700"))
            fig_luc.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000", font_color="#FFD700")
            st.plotly_chart(fig_luc, use_container_width=True)
    else:
        st.info("Coluna DATA não encontrada em VENDAS para análise mensal.")

with tab2:
    st.markdown("## Estoque Atual — controle claro")
    if estoque is not None and e_prod in (estoque.columns if estoque is not None else []) and "_QTD_ESTOQUE" in (estoque.columns if estoque is not None else []):
        # optionally filter estoque by selected products
        est_view = estoque.copy()
        est_view["PRODUTO"] = est_view[e_prod].astype(str)
        est_view["QUANTIDADE"] = est_view["_QTD_ESTOQUE"].astype(int)
        if e_valor_unit in (estoque.columns if estoque is not None else []):
            est_view["PRECO_UNITARIO_VENDA"] = est_view["_VAL_UNIT_ESTOQ"]
            est_view["VALOR_TOTAL_ESTOQUE"] = est_view["_VAL_TOTAL_ESTOQUE"]
        else:
            est_view["PRECO_UNITARIO_VENDA"] = 0
            est_view["VALOR_TOTAL_ESTOQUE"] = 0

        # allow product filter here (same prod_filter used)
        if prod_filter and prod_filter != []:
            est_view = est_view[est_view["PRODUTO"].astype(str).isin(prod_filter)]

        # show total value and total qty
        total_qty_est = est_view["QUANTIDADE"].sum()
        total_val_est = est_view["VALOR_TOTAL_ESTOQUE"].sum()
        c1, c2 = st.columns(2)
        c1.metric("📦 Qtde total em estoque", f"{int(total_qty_est):,}".replace(",", "."))
        c2.metric("💰 Valor total do estoque", fmt_brl(total_val_est))

        st.markdown("---")
        st.subheader("Tabela de Estoque (visualização)")
        display_cols = ["PRODUTO", "QUANTIDADE"]
        if "PRECO_UNITARIO_VENDA" in est_view.columns:
            display_cols += ["PRECO_UNITARIO_VENDA", "VALOR_TOTAL_ESTOQUE"]
        df_show = est_view[display_cols].copy()
        # format numeric columns for display
        if "PRECO_UNITARIO_VENDA" in df_show.columns:
            df_show["PRECO_UNITARIO_VENDA"] = df_show["PRECO_UNITARIO_VENDA"].apply(fmt_brl)
            df_show["VALOR_TOTAL_ESTOQUE"] = df_show["VALOR_TOTAL_ESTOQUE"].apply(fmt_brl)
        st.dataframe(df_show.sort_values("QUANTIDADE", ascending=False).reset_index(drop=True))

        st.markdown("---")
        # chart top by total value
        top_value = est_view.sort_values("VALOR_TOTAL_ESTOQUE", ascending=False).head(15)
        if not top_value.empty:
            fig_e = px.bar(top_value, x="PRODUTO", y="VALOR_TOTAL_ESTOQUE", title="Top 15 - Valor em Estoque", color="VALOR_TOTAL_ESTOQUE", color_continuous_scale=["#FFD700","#B8860B"])
            fig_e.update_layout(plot_bgcolor="#000000", paper_bgcolor="#000000", font_color="#FFD700")
            st.plotly_chart(fig_e, use_container_width=True)
    else:
        st.warning("Aba ESTOQUE ou colunas necessárias não encontradas. Verifique Diagnóstico.")

# ======================
# Diagnóstico (expansível)
# ======================
with st.expander("🔧 Diagnóstico (colunas detectadas e amostras)"):
    st.markdown("**ESTOQUE**")
    if estoque is not None:
        st.write(list(estoque.columns))
        st.dataframe(estoque.head(6))
    else:
        st.write("ESTOQUE não carregado.")
    st.markdown("**VENDAS**")
    if vendas is not None:
        st.write(list(vendas.columns))
        st.dataframe(vendas.head(6))
    else:
        st.write("VENDAS não carregado.")
    st.markdown("**COMPRAS**")
    if compras is not None:
        st.write(list(compras.columns))
        st.dataframe(compras.head(6))
    else:
        st.write("COMPRAS não carregado.")

st.markdown("---")
st.caption("Dashboard — Tema: Preto + Dourado (alto contraste). Desenvolvido em Streamlit.")
