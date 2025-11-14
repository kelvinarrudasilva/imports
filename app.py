# app.py — Dashboard final (link fixo, filtro por mês, top10, correção compras)
import streamlit as st
import pandas as pd
import plotly.express as px
import re

st.set_page_config(page_title="Dashboard Loja Importados", layout="wide")

# --------------------------
# Visual simples
# --------------------------
st.markdown(
    """
    <style>
      :root { --gold:#FFD700; }
      body, .stApp { background-color:#0b0b0b; color:#EEE; }
      h1,h2,h3,h4 { color: var(--gold); }
      .stMetric { background:#111; padding:10px; border-radius:8px; border:1px solid #333; }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 Dashboard – Loja Importados")

# --------------------------
# Link fixo do Google Drive
# --------------------------
URL_PLANILHA = "https://drive.google.com/uc?export=download&id=1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b"

# --------------------------
# Helpers de limpeza/parse
# --------------------------
def parse_money_value(x):
    """Parse único valor em ponto flutuante, tolerante a formatos BR/EN e símbolos."""
    try:
        if pd.isna(x):
            return float("nan")
    except:
        pass
    s = str(x).strip()
    if s == "" or s.lower() == "nan":
        return float("nan")
    # remover símbolos (letras, R$, espaços, etc.), mas manter . e ,
    s = re.sub(r"[^\d\.,\-]", "", s)
    # se contém '.' e ',' -> provavelmente formato BR (1.234,56)
    if "." in s and "," in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        # se contém apenas ',' -> considerar decimal separator
        if "," in s and "." not in s:
            s = s.replace(",", ".")
        # se contém vários '.', remover thousand separators
        if s.count(".") > 1:
            s = s.replace(".", "")
    # limpeza final
    s = re.sub(r"[^\d\.\-]", "", s)
    try:
        return float(s) if s not in ("", ".", "-") else float("nan")
    except:
        return float("nan")

def parse_money_series(serie):
    return serie.astype(str).map(lambda x: parse_money_value(x)).astype("float64")

def parse_int_series(serie):
    # tenta extrair inteiro (remove tudo que não seja dígito)
    def to_int(x):
        try:
            if pd.isna(x):
                return pd.NA
        except:
            pass
        s = str(x)
        s = re.sub(r"[^\d\-]", "", s)
        if s == "" or s == "-" or s.lower() == "nan":
            return pd.NA
        try:
            return int(float(s))
        except:
            return pd.NA
    return serie.map(to_int).astype("Int64")

# --------------------------
# Funções de detecção/limpeza de cabeçalho (mantidas)
# --------------------------
def detectar_linha_cabecalho(df_raw, chave):
    linha_cab = None
    for i in range(len(df_raw)):
        linha = df_raw.iloc[i].astype(str).str.upper().tolist()
        if chave in " ".join(linha):
            linha_cab = i
            break
    return linha_cab

def limpar_aba_raw(df_raw, nome_aba):
    busca = "PRODUTO" if nome_aba not in ("VENDAS", "COMPRAS") else "DATA"
    linha = detectar_linha_cabecalho(df_raw, busca)
    if linha is None:
        return None
    df_raw.columns = df_raw.iloc[linha]
    df = df_raw.iloc[linha+1:].copy()
    # remover colunas Unnamed
    df = df.loc[:, ~df.columns.astype(str).str.contains("Unnamed")]
    df = df.reset_index(drop=True)
    # limpar nomes de colunas: strip
    df.columns = [str(c).strip() for c in df.columns]
    return df

# --------------------------
# Carregar Excel (mantendo seu método)
# --------------------------
def carregar_xls(url):
    try:
        xls = pd.ExcelFile(url)
        return xls, None
    except Exception as e:
        return None, str(e)

xls, erro = carregar_xls(URL_PLANILHA)
if erro:
    st.error("Erro ao abrir planilha do Google Drive.")
    st.code(str(erro))
    st.stop()

# ignorar aba EXCELENTEJOAO
abas = [a for a in xls.sheet_names if a.upper() != "EXCELENTEJOAO"]

# =========================
# Colunas esperadas (suas)
# =========================
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

# --------------------------
# Ler e processar abas
# --------------------------
dfs = {}
for aba in colunas_esperadas.keys():
    if aba not in abas:
        continue
    bruto = pd.read_excel(URL_PLANILHA, sheet_name=aba, header=None)
    limpo = limpar_aba_raw(bruto, aba)
    if limpo is None:
        continue
    dfs[aba] = limpo

# --------------------------
# Converter valores e recalcular compras com QUANTIDADE * CUSTO UNITÁRIO
# --------------------------
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
    # convertendo exatamente os nomes que você confirmou
    if "VALOR VENDA" in df_v.columns:
        df_v["VALOR VENDA"] = parse_money_series(df_v["VALOR VENDA"])
    if "VALOR TOTAL" in df_v.columns:
        df_v["VALOR TOTAL"] = parse_money_series(df_v["VALOR TOTAL"])
    if "MEDIA CUSTO UNITARIO" in df_v.columns:
        df_v["MEDIA CUSTO UNITARIO"] = parse_money_series(df_v["MEDIA CUSTO UNITARIO"])
    if "LUCRO UNITARIO" in df_v.columns:
        df_v["LUCRO UNITARIO"] = parse_money_series(df_v["LUCRO UNITARIO"])
    if "QTD" in df_v.columns:
        df_v["QTD"] = parse_int_series(df_v["QTD"]).fillna(0)
    # garantir DATA
    if "DATA" in df_v.columns:
        df_v["DATA"] = pd.to_datetime(df_v["DATA"], errors="coerce")
        df_v["MES_ANO"] = df_v["DATA"].dt.strftime("%Y-%m")
    else:
        df_v["MES_ANO"] = pd.NA
    dfs["VENDAS"] = df_v

# Compras
if "COMPRAS" in dfs:
    df_c = dfs["COMPRAS"]
    if "QUANTIDADE" in df_c.columns:
        df_c["QUANTIDADE"] = parse_int_series(df_c["QUANTIDADE"]).fillna(0)
    if "CUSTO UNITÁRIO" in df_c.columns:
        df_c["CUSTO UNITÁRIO"] = parse_money_series(df_c["CUSTO UNITÁRIO"]).fillna(0.0)
    # recalcular custo total com segurança
    if "QUANTIDADE" in df_c.columns and "CUSTO UNITÁRIO" in df_c.columns:
        df_c["CUSTO TOTAL (RECALC)"] = (df_c["QUANTIDADE"].fillna(0).astype(float) *
                                         df_c["CUSTO UNITÁRIO"].fillna(0.0))
    else:
        if "CUSTO TOTAL" in df_c.columns:
            df_c["CUSTO TOTAL (RECALC)"] = parse_money_series(df_c["CUSTO TOTAL"]).fillna(0.0)
        else:
            df_c["CUSTO TOTAL (RECALC)"] = 0.0
    if "DATA" in df_c.columns:
        df_c["DATA"] = pd.to_datetime(df_c["DATA"], errors="coerce")
        df_c["MES_ANO"] = df_c["DATA"].dt.strftime("%Y-%m")
    else:
        df_c["MES_ANO"] = pd.NA
    dfs["COMPRAS"] = df_c

# --------------------------
# FILTRO POR MÊS (YYYY-MM)
# --------------------------
meses_venda = []
if "VENDAS" in dfs:
    meses_venda = sorted(dfs["VENDAS"]["MES_ANO"].dropna().unique().tolist(), reverse=True)
meses = ["Todos"] + meses_venda
mes_selecionado = st.selectbox("Filtrar por mês (YYYY-MM):", meses, index=0)

def filtrar_mes(df, mes):
    if mes == "Todos" or mes is None:
        return df
    if "MES_ANO" in df.columns:
        return df[df["MES_ANO"] == mes].copy()
    return df

vendas_filtradas = filtrar_mes(dfs.get("VENDAS", pd.DataFrame()), mes_selecionado)
compras_filtradas = filtrar_mes(dfs.get("COMPRAS", pd.DataFrame()), mes_selecionado)
estoque_df = dfs.get("ESTOQUE", pd.DataFrame())

# --------------------------
# KPIs: total vendido e total lucro (R$) no período
# --------------------------
def calcular_totais_vendas(df):
    if df is None or df.empty:
        return 0.0, 0.0
    tv = 0.0
    tl = 0.0
    if "VALOR TOTAL" in df.columns:
        tv = df["VALOR TOTAL"].fillna(0.0).sum()
    elif "VALOR VENDA" in df.columns and "QTD" in df.columns:
        tv = (df["VALOR VENDA"].fillna(0.0) * df["QTD"].fillna(0)).sum()
    # lucro
    if "LUCRO UNITARIO" in df.columns and "QTD" in df.columns:
        tl = (df["LUCRO UNITARIO"].fillna(0.0) * df["QTD"].fillna(0)).sum()
    elif "LUCRO UNITARIO" in df.columns:
        tl = df["LUCRO UNITARIO"].fillna(0.0).sum()
    else:
        # tentativa por diferença com custo médio
        if "VALOR TOTAL" in df.columns and "MEDIA CUSTO UNITARIO" in df.columns and "QTD" in df.columns:
            custo_estim = (df["MEDIA CUSTO UNITARIO"].fillna(0.0) * df["QTD"].fillna(0)).sum()
            tl = df["VALOR TOTAL"].sum() - custo_estim
    return float(tv), float(tl)

total_vendido, total_lucro = calcular_totais_vendas(vendas_filtradas)

# total compras recalcadas (filtradas)
total_compras = 0.0
if not compras_filtradas.empty and "CUSTO TOTAL (RECALC)" in compras_filtradas.columns:
    total_compras = compras_filtradas["CUSTO TOTAL (RECALC)"].fillna(0.0).sum()

k1, k2, k3 = st.columns(3)
k1.metric("💵 Total Vendido (R$)", f"R$ {total_vendido:,.2f}")
k2.metric("🧾 Total Lucro (R$)", f"R$ {total_lucro:,.2f}")
k3.metric("💸 Total Compras (R$)", f"R$ {total_compras:,.2f}")

# --------------------------
# Top 10 produtos por VALOR TOTAL
# --------------------------
st.subheader("🏆 Top 10 Produtos Mais Vendidos (por VALOR)")

if vendas_filtradas is None or vendas_filtradas.empty:
    st.info("Sem dados de vendas para o período selecionado.")
else:
    dfv = vendas_filtradas.copy()
    # criar VALOR TOTAL se não existir
    if "VALOR TOTAL" not in dfv.columns and "VALOR VENDA" in dfv.columns and "QTD" in dfv.columns:
        dfv["VALOR TOTAL"] = dfv["VALOR VENDA"].fillna(0.0) * dfv["QTD"].fillna(0)

    if "PRODUTO" in dfv.columns and "VALOR TOTAL" in dfv.columns:
        top10 = (dfv.groupby("PRODUTO")
                 .agg(QTD_TOTAL=pd.NamedAgg(column="QTD", aggfunc="sum"),
                      VALOR_TOTAL=pd.NamedAgg(column="VALOR TOTAL", aggfunc="sum"),
                      LUCRO_TOTAL=pd.NamedAgg(column="LUCRO UNITARIO", aggfunc=lambda s: (s.fillna(0.0) * dfv.loc[s.index, "QTD"].fillna(0)).sum() if "LUCRO UNITARIO" in dfv.columns else 0.0)
                      )
                 .reset_index()
                 .sort_values("VALOR_TOTAL", ascending=False)
                 .head(10))
        # formatar
        top10["VALOR_TOTAL"] = top10["VALOR_TOTAL"].fillna(0.0)
        top10["LUCRO_TOTAL"] = top10["LUCRO_TOTAL"].fillna(0.0)
        top10["QTD_TOTAL"] = top10["QTD_TOTAL"].fillna(0).astype("Int64")
        st.dataframe(top10.style.format({"VALOR_TOTAL": "R$ {:,.2f}", "LUCRO_TOTAL": "R$ {:,.2f}", "QTD_TOTAL": "{:,.0f}"}), use_container_width=True)
        fig_top = px.bar(top10, x="PRODUTO", y="VALOR_TOTAL", title="Top 10 - Vendas (R$)")
        st.plotly_chart(fig_top, use_container_width=True)
    else:
        st.warning("Colunas necessárias (PRODUTO, VALOR TOTAL) não encontradas em VENDAS.")

# --------------------------
# Evolução do faturamento (diária) — gráfico
# --------------------------
st.subheader("📈 Evolução do Faturamento (período selecionado)")
if not vendas_filtradas.empty and "DATA" in vendas_filtradas.columns and "VALOR TOTAL" in vendas_filtradas.columns:
    series_fat = vendas_filtradas.groupby("DATA")["VALOR TOTAL"].sum().reset_index().sort_values("DATA")
    fig_fat = px.line(series_fat, x="DATA", y="VALOR TOTAL", title="Faturamento Diário")
    st.plotly_chart(fig_fat, use_container_width=True)
else:
    st.info("Sem dados de faturamento por data para exibir.")

# --------------------------
# Compras — mostrar recalc e série
# --------------------------
st.subheader("📥 Compras (período selecionado)")
if not compras_filtradas.empty:
    dfc = compras_filtradas.copy()
    if "CUSTO TOTAL (RECALC)" in dfc.columns:
        # remover valores absurdos (defensivo)
        dfc["CUSTO TOTAL (RECALC)"] = pd.to_numeric(dfc["CUSTO TOTAL (RECALC)"], errors="coerce")
        dfc.loc[dfc["CUSTO TOTAL (RECALC)"] > 1e12, "CUSTO TOTAL (RECALC)"] = pd.NA
        st.metric("Total Compras (recalculado)", f"R$ {dfc['CUSTO TOTAL (RECALC)'].sum():,.2f}")
        if "DATA" in dfc.columns:
            serie_comp = dfc.groupby("DATA")["CUSTO TOTAL (RECALC)"].sum().reset_index().sort_values("DATA")
            fig_comp = px.line(serie_comp, x="DATA", y="CUSTO TOTAL (RECALC)", title="Gastos com Compras")
            st.plotly_chart(fig_comp, use_container_width=True)
    else:
        st.info("Coluna de custo não encontrada ou não foi possível recalcular.")
    st.dataframe(dfc, use_container_width=True)
else:
    st.info("Sem dados de compras para o período selecionado.")

# --------------------------
# Estoque (resumo)
# --------------------------
st.subheader("📦 Estoque")
if not estoque_df.empty:
    df_e = estoque_df.copy()
    if "EM ESTOQUE" in df_e.columns:
        df_e["EM ESTOQUE"] = parse_int_series(df_e["EM ESTOQUE"]).fillna(0)
    if "PRODUTO" in df_e.columns and "EM ESTOQUE" in df_e.columns:
        criticos = df_e.sort_values("EM ESTOQUE").head(10)
        st.write("Produtos com menor estoque")
        st.dataframe(criticos[["PRODUTO", "EM ESTOQUE"]], use_container_width=True)
    else:
        st.dataframe(df_e, use_container_width=True)
else:
    st.info("Aba ESTOQUE não encontrada ou vazia.")

st.success("✅ Dashboard atualizado")
