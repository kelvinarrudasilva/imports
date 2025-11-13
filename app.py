import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import re

# ---------------------------
# Configuração da página
# ---------------------------
st.set_page_config(page_title="Dashboard - Loja Importados", layout="wide")
st.markdown(
    """
    <style>
      :root { --gold: #E8C36A; --bg: #0b0b0b; --card: #121212; --muted:#9e9b8f; }
      .stApp { background-color: var(--bg); color: var(--gold); }
      [data-testid="stHeader"] { background: none; }
      .kpi-card { background: linear-gradient(90deg, rgba(18,18,18,0.9), rgba(12,12,12,0.9)); padding:14px; border-radius:10px; text-align:center; }
      .kpi-label { color: var(--muted); font-size:13px; }
      .kpi-value { color: var(--gold); font-size:22px; font-weight:700; }
      .small-muted { color: var(--muted); font-size:12px; }
      /* dataframes */
      .stDataFrame table { background-color: #0b0b0b; color:#e6e2d3; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("<h1 style='color:var(--gold); margin-bottom:6px'>📊 Dashboard - Loja Importados</h1>", unsafe_allow_html=True)
st.markdown("<div class='small-muted'>Tema: Dark (preto + dourado) • Dados: ESTOQUE / VENDAS / COMPRAS</div>", unsafe_allow_html=True)
st.markdown("---")

# ---------------------------
# Helpers
# ---------------------------
def normalize_col_name(s: str) -> str:
    if s is None:
        return ""
    s = str(s).strip()
    s = re.sub(r"\s+", " ", s)
    return s.upper()

def find_col(df: pd.DataFrame, candidates):
    """Procura por uma coluna no df que contenha algum dos candidatos (case-insensitive)."""
    if df is None or df.empty:
        return None
    cols = [normalize_col_name(c) for c in df.columns]
    for cand in candidates:
        cand_u = normalize_col_name(cand)
        for original, col_u in zip(df.columns, cols):
            if cand_u in col_u:
                return original
    return None

def read_clean_sheet(path, sheet_name, header_guess=0):
    """Lê a sheet tentando remover cabeçalhos quebrados e Unnamed."""
    try:
        # ler sem header para inspecionar
        raw = pd.read_excel(path, sheet_name=sheet_name, header=None)
    except Exception as e:
        return None, f"Erro ao abrir aba '{sheet_name}': {e}"

    # procurar linha que contém uma palavra-chave comum para cabeçalho
    header_row = None
    key_terms = ["PRODUTO", "DATA", "QTD", "QUANTIDADE", "VALOR", "CUSTO"]
    for i in range(min(6, len(raw))):
        row_vals = raw.iloc[i].astype(str).str.upper().fillna("")
        if any(any(k in v for v in row_vals) for k in key_terms):
            header_row = i
            break
    if header_row is None:
        # fallback: use first non-empty row
        header_row = 0

    # read again with header
    try:
        df = pd.read_excel(path, sheet_name=sheet_name, header=header_row)
    except Exception as e:
        return None, f"Erro ao ler '{sheet_name}' com header={header_row}: {e}"

    # drop fully empty columns and Unnamed
    df.columns = [str(c).strip() for c in df.columns]
    df = df.loc[:, ~df.columns.str.contains("^Unnamed", na=False)]
    df = df.dropna(axis=1, how="all")
    df = df.dropna(axis=0, how="all").reset_index(drop=True)
    # normalize column names keeping original mapping
    df.columns = [c if isinstance(c, str) else str(c) for c in df.columns]
    return df, None

def fmt_brl(x):
    try:
        return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

# ---------------------------
# Carregar arquivo
# ---------------------------
EXCEL_PATH = "LOJA IMPORTADOS.xlsx"

with st.sidebar:
    st.header("Controles")
    st.markdown("Certifique-se de que **LOJA IMPORTADOS.xlsx** está no mesmo diretório do app.")
    diag = st.button("🔍 Mostrar diagnóstico")
    st.markdown("---")
    filtro_produto = st.selectbox("🔎 Filtrar por Produto (todas por padrão)", options=["(Todas)"], index=0)
    st.markdown("")

# read sheets
estoque, err_e = read_clean_sheet(EXCEL_PATH, "ESTOQUE")
vendas, err_v = read_clean_sheet(EXCEL_PATH, "VENDAS")
compras, err_c = read_clean_sheet(EXCEL_PATH, "COMPRAS")

# mostrar erros de leitura
if err_e:
    st.error(err_e)
if err_v:
    st.error(err_v)
if err_c:
    st.error(err_c)

# ---------------------------
# Mostrar diagnóstico se pedido
# ---------------------------
if diag:
    st.subheader("🔧 Diagnóstico de leitura")
    def show_info(name, df):
        if df is None:
            st.write(f"**{name}**: não carregada.")
            return
        st.write(f"**{name}** — {df.shape[0]} linhas × {df.shape[1]} colunas")
        st.write([c for c in df.columns])
        st.dataframe(df.head(10))
    show_info("ESTOQUE", estoque)
    show_info("VENDAS", vendas)
    show_info("COMPRAS", compras)
    st.stop()

# ---------------------------
# Confirmar que carregou algo
# ---------------------------
if (estoque is None) and (vendas is None) and (compras is None):
    st.error("Arquivo não carregado ou abas não encontradas. Verifique o nome do arquivo e as abas ESTOQUE, VENDAS, COMPRAS.")
    st.stop()

# ---------------------------
# Normalizar colunas (mapear exatamente como você listou)
# ---------------------------
# ESTOQUE expected: PRODUTO, EM ESTOQUE, COMPRAS, Media C. UNITARIO, Valor Venda Sugerido, VENDAS
# VENDAS expected: DATA, PRODUTO, QTD, VALOR VENDA, VALOR TOTAL, MEDIA CUSTO UNITARIO, LUCRO, ...
# COMPRAS expected: DATA, PRODUTO, STATUS, QUANTIDADE, CUSTO UNITÁRIO, CUSTO TOTAL, OBSERVAÇÃO

# Encontrar colunas em cada df (mantemos nomes originais)
# Estoque
e_col_prod = find_col = find_col = None
if estoque is not None:
    e_col_prod = find_col = find_col = find_col = find_col = None  # placeholder
# We'll use the robust find_col function implemented above

# Re-use the find_col helper defined earlier
def fc(df, *cands):
    return find_col(df, cands) if df is not None else None

# Mapas para ESTOQUE
e_prod_col = find_col(estoque, ["PRODUTO"]) if estoque is not None else None
e_qtd_col = find_col(estoque, ["EM ESTOQUE", "QUANT", "QTD", "QUANTIDADE"]) if estoque is not None else None
e_media_custo_col = find_col(estoque, ["MEDIA C. UNITARIO", "MEDIA C", "CUSTO UNIT"]) if estoque is not None else None

# Mapas para VENDAS
v_data_col = find_col(vendas, ["DATA"]) if vendas is not None else None
v_prod_col = find_col(vendas, ["PRODUTO"]) if vendas is not None else None
v_qtd_col = find_col(vendas, ["QTD", "QUANT", "QUANTIDADE"]) if vendas is not None else None
v_valor_venda_col = find_col(vendas, ["VALOR VENDA", "VALOR_VENDA", "VALOR VENDA SUGERIDO", "VALOR"]) if vendas is not None else None
v_valor_total_col = find_col(vendas, ["VALOR TOTAL", "VALOR_TOTAL", "TOTAL"]) if vendas is not None else None
v_media_custo_col = find_col(vendas, ["MEDIA CUSTO UNITARIO", "MEDIA C. UNITARIO", "CUSTO UNITARIO"]) if vendas is not None else None

# Mapas para COMPRAS
c_data_col = find_col(compras, ["DATA"]) if compras is not None else None
c_prod_col = find_col(compras, ["PRODUTO"]) if compras is not None else None
c_qtd_col = find_col(compras, ["QUANTIDADE", "QTD", "QUANT"]) if compras is not None else None
c_custo_unit_col = find_col(compras, ["CUSTO UNIT", "CUSTO UNITÁRIO", "CUSTO_UNITÁRIO", "CUSTO"]) if compras is not None else None
c_custo_total_col = find_col(compras, ["CUSTO TOTAL", "VALOR TOTAL", "TOTAL"]) if compras is not None else None

# Avisos sobre colunas faltando (mais explícitos)
missing = []
if vendas is None:
    missing.append("VENDAS não carregada")
else:
    if not v_prod_col: missing.append("VENDAS: coluna PRODUTO não encontrada")
    if not (v_valor_total_col or v_valor_venda_col): missing.append("VENDAS: coluna VALOR (VALOR TOTAL ou VALOR VENDA) não encontrada")
    if not v_qtd_col: missing.append("VENDAS: coluna QTD não encontrada")

if compras is None:
    missing.append("COMPRAS não carregada")
else:
    if not (c_custo_total_col or (c_custo_unit_col and c_qtd_col)): missing.append("COMPRAS: coluna CUSTO não encontrada")
    if not c_prod_col: missing.append("COMPRAS: coluna PRODUTO não encontrada")

if estoque is None:
    missing.append("ESTOQUE não carregada")
else:
    if not e_qtd_col: missing.append("ESTOQUE: coluna EM ESTOQUE não encontrada")
    if not e_prod_col: missing.append("ESTOQUE: coluna PRODUTO não encontrada")

if missing:
    with st.expander("⚠️ Avisos / Colunas faltando (clique para ver)"):
        for m in missing:
            st.warning(m)

# ---------------------------
# Filtros (criar lista de produtos combinada)
# ---------------------------
all_products = set()
if vendas is not None and v_prod_col: all_products.update(vendas[v_prod_col].dropna().astype(str).unique())
if compras is not None and c_prod_col: all_products.update(compras[c_prod_col].dropna().astype(str).unique())
if estoque is not None and e_prod_col: all_products.update(estoque[e_prod_col].dropna().astype(str).unique())
all_products_list = sorted([p for p in all_products if str(p).strip() != ""])
all_products_list = ["(Todas)"] + all_products_list

# replace sidebar filter created earlier if is default
try:
    if filtro_produto == "(Todas)":
        filtro_produto = "(Todas)"
except:
    filtro_produto = "(Todas)"

filtro_produto = st.sidebar.selectbox("🔎 Filtrar por Produto", options=all_products_list, index=0)

# filtro de data (pela VENDAS)
date_min, date_max = None, None
if vendas is not None and v_data_col:
    try:
        vendas[v_data_col] = pd.to_datetime(vendas[v_data_col], errors="coerce")
        date_min = vendas[v_data_col].min()
        date_max = vendas[v_data_col].max()
        dr = st.sidebar.date_input("Filtrar por período (VENDAS)", value=(date_min.date() if pd.notna(date_min) else None, date_max.date() if pd.notna(date_max) else None))
        if isinstance(dr, (list, tuple)) and len(dr) == 2:
            dt_from, dt_to = dr
            vendas = vendas[(vendas[v_data_col].dt.date >= dt_from) & (vendas[v_data_col].dt.date <= dt_to)]
    except Exception:
        pass

# ---------------------------
# Preparar dados numéricos e cálculos
# ---------------------------
# Função utilitária
def to_numeric_safe(ser):
    return pd.to_numeric(ser, errors="coerce").fillna(0)

# Total Vendas: prefer VALOR TOTAL, senão VALOR VENDA * QTD
total_vendas = 0.0
if vendas is not None:
    try:
        if v_valor_total_col and v_valor_total_col in vendas.columns:
            total_vendas = to_numeric_safe(vendas[v_valor_total_col]).sum()
        elif v_valor_venda_col and v_qtd_col and v_valor_venda_col in vendas.columns and v_qtd_col in vendas.columns:
            total_vendas = (to_numeric_safe(vendas[v_valor_venda_col]) * to_numeric_safe(vendas[v_qtd_col])).sum()
        else:
            total_vendas = 0.0
    except Exception as e:
        st.error(f"Erro ao calcular Total Vendas: {e}")
        total_vendas = 0.0

# Total Compras (CUSTO): prefer CUSTO TOTAL, senão CUSTO UNITÁRIO * QUANTIDADE
total_compras = 0.0
if compras is not None:
    try:
        if c_custo_total_col and c_custo_total_col in compras.columns:
            total_compras = to_numeric_safe(compras[c_custo_total_col]).sum()
        elif c_custo_unit_col and c_qtd_col and c_custo_unit_col in compras.columns and c_qtd_col in compras.columns:
            total_compras = (to_numeric_safe(compras[c_custo_unit_col]) * to_numeric_safe(compras[c_qtd_col])).sum()
        else:
            total_compras = 0.0
    except Exception as e:
        st.error(f"Erro ao calcular Total Compras: {e}")
        total_compras = 0.0

# Quantidade em Estoque
qtd_estoque = 0
if estoque is not None and e_qtd_col:
    try:
        qtd_estoque = int(to_numeric_safe(estoque[e_qtd_col]).sum())
    except:
        qtd_estoque = 0

# Recalcular LUCRO por linha: (VALOR VENDA - CUSTO UNITÁRIO) * QTD
lucro_estimado = 0.0
if vendas is not None:
    # preparar colunas de trabalho
    vendas_work = vendas.copy()
    # tentar obter custo unitário por essa ordem:
    # 1) coluna MEDIA CUSTO UNITARIO na própria VENDAS
    # 2) coluna Media C. UNITARIO na ESTOQUE (lookup por produto)
    # 3) cálculo do custo médio na COMPRAS (groupby PRODUTO -> mean(CUSTO UNITÁRIO))
    # else fallback 0
    # garantir colunas QTD e VALOR VENDA numéricas
    if v_qtd_col in vendas_work.columns:
        vendas_work["_QTD"] = to_numeric_safe(vendas_work[v_qtd_col])
    else:
        vendas_work["_QTD"] = 0
    if v_valor_venda_col in vendas_work.columns:
        vendas_work["_VALOR_VENDA"] = to_numeric_safe(vendas_work[v_valor_venda_col])
    else:
        vendas_work["_VALOR_VENDA"] = 0

    # custo direto na VENDAS?
    if v_media_custo_col and v_media_custo_col in vendas_work.columns:
        vendas_work["_CUSTO_UNIT"] = to_numeric_safe(vendas_work[v_media_custo_col])
    else:
        # tentar buscar em ESTOQUE por produto
        vendas_work["_CUSTO_UNIT"] = 0
        if (estoque is not None) and (e_prod_col in estoque.columns and e_media_custo_col in estoque.columns):
            # criar mapping produto -> custo
            try:
                mapa_custo_estoque = estoque[[e_prod_col, e_media_custo_col]].dropna()
                mapa_custo_estoque[e_prod_col] = mapa_custo_estoque[e_prod_col].astype(str).str.strip()
                mapa = mapa_custo_estoque.set_index(e_prod_col)[e_media_custo_col].to_dict()
                vendas_work["_CUSTO_UNIT"] = vendas_work[v_prod_col].astype(str).str.strip().map(mapa).fillna(0)
            except Exception:
                vendas_work["_CUSTO_UNIT"] = 0

        # se ainda zero, tentar custo médio das COMPRAS
        if (vendas_work["_CUSTO_UNIT"] == 0).any() and (compras is not None) and (c_prod_col in compras.columns and c_custo_unit_col in compras.columns):
            try:
                comp = compras[[c_prod_col, c_custo_unit_col]].copy()
                comp[c_prod_col] = comp[c_prod_col].astype(str).str.strip()
                comp[c_custo_unit_col] = to_numeric_safe(comp[c_custo_unit_col])
                media_compra = comp.groupby(c_prod_col)[c_custo_unit_col].mean().to_dict()
                # preencher somente onde custo ainda zero
                mask_zero = vendas_work["_CUSTO_UNIT"] == 0
                vendas_work.loc[mask_zero, "_CUSTO_UNIT"] = vendas_work.loc[mask_zero, v_prod_col].astype(str).str.strip().map(media_compra).fillna(0)
            except Exception:
                pass

    # agora calcular lucro linha a linha
    vendas_work["_LUCRO_LIN"] = (vendas_work["_VALOR_VENDA"].fillna(0) - vendas_work["_CUSTO_UNIT"].fillna(0)) * vendas_work["_QTD"].fillna(0)
    lucro_estimado = vendas_work["_LUCRO_LIN"].sum()

    # aplicar filtro por produto se selecionado
    if filtro_produto and filtro_produto != "(Todas)":
        vendas_work = vendas_work[vendas_work[v_prod_col].astype(str).str.strip() == filtro_produto]
        # recompute totals for filtered
        total_vendas = (vendas_work["_VALOR_VENDA"] * vendas_work["_QTD"]).sum()
        lucro_estimado = vendas_work["_LUCRO_LIN"].sum()

# ---------------------------
# Exibir KPIs
# ---------------------------
k1, k2, k3, k4 = st.columns(4)
k1.markdown(f"<div class='kpi-card'><div class='kpi-label'>💰 Total de Vendas</div><div class='kpi-value'>{fmt_brl(total_vendas)}</div></div>", unsafe_allow_html=True)
k2.markdown(f"<div class='kpi-card'><div class='kpi-label'>🧾 Total de Compras</div><div class='kpi-value'>{fmt_brl(total_compras)}</div></div>", unsafe_allow_html=True)
k3.markdown(f"<div class='kpi-card'><div class='kpi-label'>📈 Lucro Estimado</div><div class='kpi-value'>{fmt_brl(lucro_estimado)}</div></div>", unsafe_allow_html=True)
k4.markdown(f"<div class='kpi-card'><div class='kpi-label'>📦 Qtde em Estoque</div><div class='kpi-value'>{int(qtd_estoque):,}</div></div>", unsafe_allow_html=True)

st.markdown("---")

# ---------------------------
# Gráficos interativos
# ---------------------------
px.defaults.template = "plotly_dark"
color_scale = "YlOrBr"

tab = st.radio("Visualização", ["Resumo", "Vendas (detalhado)", "Compras", "Estoque", "Diagnóstico"], horizontal=True)

if tab == "Resumo":
    st.subheader("Evolução de vendas x compras (mensal)")
    # Vendas mensais
    if vendas is not None and v_data_col in vendas.columns:
        tmp = vendas.copy()
        tmp[v_data_col] = pd.to_datetime(tmp[v_data_col], errors="coerce")
        tmp["_MES"] = tmp[v_data_col].dt.to_period("M").astype(str)
        if v_valor_total_col in tmp.columns:
            vendas_mes = tmp.groupby("_MES")[v_valor_total_col].sum().reset_index()
            fig = px.bar(vendas_mes, x="_MES", y=v_valor_total_col, title="Vendas Mensais", color=v_valor_total_col, color_continuous_scale=color_scale)
            fig.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b")
            st.plotly_chart(fig, use_container_width=True)
        elif v_valor_venda_col and v_qtd_col:
            tmp["_VAL_TOTAL"] = to_numeric_safe(tmp[v_valor_venda_col]) * to_numeric_safe(tmp[v_qtd_col])
            vendas_mes = tmp.groupby("_MES")["_VAL_TOTAL"].sum().reset_index()
            fig = px.bar(vendas_mes, x="_MES", y="_VAL_TOTAL", title="Vendas Mensais (calculado)", color="_VAL_TOTAL", color_continuous_scale=color_scale)
            fig.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b")
            st.plotly_chart(fig, use_container_width=True)
    # Compras mensais
    if compras is not None and c_data_col in compras.columns:
        tmpc = compras.copy()
        tmpc[c_data_col] = pd.to_datetime(tmpc[c_data_col], errors="coerce")
        tmpc["_MES"] = tmpc[c_data_col].dt.to_period("M").astype(str)
        if c_custo_total_col in tmpc.columns:
            comp_mes = tmpc.groupby("_MES")[c_custo_total_col].sum().reset_index()
            fig2 = px.line(comp_mes, x="_MES", y=c_custo_total_col, title="Compras Mensais (custo)", markers=True, color_discrete_sequence=[px.colors.sequential.YlOrBr[3]])
            fig2.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b")
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.subheader("Top Produtos (vendas)")
    if vendas is not None and v_prod_col in vendas.columns and v_valor_venda_col in vendas.columns and v_qtd_col in vendas.columns:
        df_top = vendas.copy()
        df_top["_VAL_TOTAL"] = to_numeric_safe(df_top[v_valor_venda_col]) * to_numeric_safe(df_top[v_qtd_col])
        top = df_top.groupby(v_prod_col)["_VAL_TOTAL"].sum().nlargest(10).reset_index()
        fig3 = px.bar(top, x=v_prod_col, y="_VAL_TOTAL", title="Top 10 produtos por vendas", color="_VAL_TOTAL", color_continuous_scale=color_scale)
        fig3.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b")
        st.plotly_chart(fig3, use_container_width=True)

elif tab == "Vendas (detalhado)":
    st.subheader("Tabela de Vendas")
    if vendas is not None:
        disp = vendas.copy()
        # show relevant columns with friendly names if existing
        cols_show = []
        for c in ["DATA", v_prod_col, v_qtd_col, v_valor_venda_col, v_valor_total_col, v_media_custo_col, "LUCRO_CALC"]:
            if c and c in disp.columns:
                cols_show.append(c)
        if "LUCRO_CALC" not in disp.columns and "_LUCRO_LIN" in locals():
            disp["_LUCRO_CALC"] = vendas_work["_LUCRO_LIN"]
            cols_show.append("_LUCRO_CALC")
        st.dataframe(disp.head(1000))
    else:
        st.info("Nenhuma venda carregada.")

elif tab == "Compras":
    st.subheader("Compras detalhadas")
    if compras is not None:
        st.dataframe(compras.head(1000))
    else:
        st.info("Nenhuma compra carregada.")

elif tab == "Estoque":
    st.subheader("Estoque atual")
    if estoque is not None:
        st.dataframe(estoque.head(1000))
    else:
        st.info("Estoque vazio.")

elif tab == "Diagnóstico":
    st.subheader("🔍 Diagnóstico (colunas detectadas)")
    st.markdown("**ESTOQUE**")
    st.write(list(estoque.columns) if estoque is not None else "não carregada")
    st.markdown("**VENDAS**")
    st.write(list(vendas.columns) if vendas is not None else "não carregada")
    st.markdown("**COMPRAS**")
    st.write(list(compras.columns) if compras is not None else "não carregada")
    st.markdown("---")
    st.write("Mapeamentos detectados (colunas usadas internamente):")
    st.write({
        "ESTOQUE": {"PRODUTO": e_prod_col, "EM ESTOQUE": e_qtd_col, "MEDIA CUSTO": e_media_custo_col},
        "VENDAS": {"DATA": v_data_col, "PRODUTO": v_prod_col, "QTD": v_qtd_col, "VALOR VENDA": v_valor_venda_col, "VALOR TOTAL": v_valor_total_col, "MEDIA CUSTO VENDAS": v_media_custo_col},
        "COMPRAS": {"DATA": c_data_col, "PRODUTO": c_prod_col, "QUANTIDADE": c_qtd_col, "CUSTO UNIT": c_custo_unit_col, "CUSTO TOTAL": c_custo_total_col}
    })

st.markdown("---")
st.caption("© 2025 Loja Importados — Dashboard gerado em Python + Streamlit • Tema: Dark (Preto + Dourado)")
