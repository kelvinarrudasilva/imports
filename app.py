# ================================================
# app.py — Corrigido: detecção robusta de HEADER / DATA
# Loja Importados — Top5 (quantidade + valor) — Layout 3
# ================================================

import streamlit as st
import pandas as pd
import plotly.express as px
import re
from datetime import datetime, timedelta
import requests
from io import BytesIO

st.set_page_config(page_title="Loja Importados – Dashboard", layout="wide")

# ---------- CONFIG ----------
URL_PLANILHA = "https://docs.google.com/spreadsheets/d/1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b/export?format=xlsx"

# ---------- CSS (dark) ----------
st.markdown("""
<style>
:root{--bg:#0b0b0b;--card:#141414;--accent:#8b5cf6;--accent2:#a78bfa;--text:#f2f2f2;}
body, .stApp { background:var(--bg) !important; color:var(--text) !important; font-family: Inter, system-ui, -apple-system, 'Segoe UI', Roboto; }
.kpi-box{ background:var(--card); padding:12px 14px; border-radius:12px; border-left:5px solid var(--accent); box-shadow:0 6px 18px rgba(0,0,0,0.45); }
</style>
""", unsafe_allow_html=True)

# ---------- HELPERS ----------
def baixar_xlsx(url):
    r = requests.get(url, timeout=25)
    r.raise_for_status()
    return BytesIO(r.content)

def encontrar_linha_header(df_raw, keyword_list=None, max_rows=12):
    """
    Procura a melhor linha que contém qualquer keyword (ex: 'DATA', 'PRODUTO').
    Retorna o index da linha encontrada (0-based). Se não achar, retorna None.
    """
    if keyword_list is None:
        keyword_list = ["DATA", "PRODUTO"]
    n = min(len(df_raw), max_rows)
    for i in range(n):
        # concatena valores da linha e procura keywords
        row_text = " ".join([str(x).upper().strip() for x in df_raw.iloc[i].astype(str).tolist()])
        for kw in keyword_list:
            if kw.upper() in row_text:
                return i
    return None

def construir_df_com_header_real(df_raw, preferred_keywords=None):
    """
    Recebe df_raw (header=None) e tenta detectar a linha de header.
    Se não achar header pela heurística, usa a linha index 1 se existir, senão 0.
    Retorna um DataFrame com header aplicado e colunas limpas (remove Unnamed).
    """
    # se veio com header já, devolve normalizado
    if df_raw is None or df_raw.empty:
        return pd.DataFrame()

    header_idx = encontrar_linha_header(df_raw, preferred_keywords)
    if header_idx is None:
        # preferir a segunda linha se existe (muitos arquivos têm cabeçalho na linha 2)
        if len(df_raw) > 1:
            header_idx = 1
        else:
            header_idx = 0

    df = df_raw.copy()
    # garantir strings limpos
    new_cols = df.iloc[header_idx].astype(str).map(lambda x: str(x).strip())
    df = df.iloc[header_idx+1:].copy().reset_index(drop=True)
    df.columns = new_cols
    # remover colunas Unnamed ou vazias
    df = df.loc[:, ~df.columns.astype(str).str.upper().str.contains("^UNNAMED") ]
    df = df.loc[:, ~df.columns.astype(str).str.strip().eq("") ]
    # strip column names again
    df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]
    return df

def limpar_moeda(x):
    if pd.isna(x): return 0.0
    s = str(x)
    s = s.replace("R$","").replace(".","").replace(",",".")
    s = re.sub(r"[^\d\.\-]","", s)
    try:
        return float(s)
    except:
        return 0.0

def formatar_reais(v):
    try:
        v = float(v)
    except:
        return "R$ 0"
    return f"R$ {v:,.0f}".replace(",", ".")

def detectar_col_por_keywords(df, keywords):
    """Retorna nome de coluna que contém uma das keywords (insensitive)."""
    if df is None or df.empty: return None
    for c in df.columns:
        cu = str(c).upper().replace(" ", "")
        for kw in keywords:
            if kw.upper().replace(" ", "") in cu:
                return c
    return None

def detectar_col_data_por_conteudo(df, sample_rows=20):
    """Tenta descobrir qual coluna tem datas convertíveis (olha primeiras linhas)."""
    if df is None or df.empty: return None
    for c in df.columns:
        try:
            converted = pd.to_datetime(df[c].head(sample_rows), errors="coerce")
            # se algum converteu com sucesso, consideramos
            if converted.notna().sum() > 0:
                return c
        except:
            continue
    return None

# ---------- CARREGAR ARQUIVO ----------
try:
    arquivo = baixar_xlsx(URL_PLANILHA)
    xls = pd.ExcelFile(arquivo)
except Exception as e:
    st.error("Erro ao baixar/abrir a planilha — verifique URL/permissão.")
    st.exception(e)
    st.stop()

# ---------- LER AS 3 ABAS -----
sheets_expected = ["VENDAS", "COMPRAS", "ESTOQUE"]
dfs_raw = {}
for s in sheets_expected:
    if s in xls.sheet_names:
        # ler sem header
        df_raw = pd.read_excel(arquivo, sheet_name=s, header=None, dtype=object)
        dfs_raw[s] = df_raw
    else:
        dfs_raw[s] = pd.DataFrame()

# ---------- CONSTRUIR DFs LIMPOS ----------
vendas = construir_df_com_header_real(dfs_raw["VENDAS"], preferred_keywords=["DATA","PRODUTO","QTD"])
compras = construir_df_com_header_real(dfs_raw["COMPRAS"], preferred_keywords=["DATA","CUSTO","QTD"])
estoque = construir_df_com_header_real(dfs_raw["ESTOQUE"], preferred_keywords=["PRODUTO","EM ESTOQUE","MEDIA"])

# ---------- GARANTIR COLUNA DATA EM VENDAS ----------
# 1) se existe coluna com nome DATA (exato ou similar), usamos
col_data = detectar_col_por_keywords(vendas, ["DATA","DT","DIA"])
if col_data:
    vendas = vendas.rename(columns={col_data: "DATA"})
# 2) se depois disso não existir 'DATA', tentamos detectar por conteúdo
if "DATA" not in vendas.columns:
    detect_by_content = detectar_col_data_por_conteudo(vendas)
    if detect_by_content:
        vendas = vendas.rename(columns={detect_by_content: "DATA"})

# agora, se existir DATA, converte; se não existir, cria coluna vazia mas sem causar KeyError
if "DATA" in vendas.columns:
    vendas["DATA"] = pd.to_datetime(vendas["DATA"], errors="coerce")
else:
    vendas["DATA"] = pd.NaT
    st.warning("A coluna DATA não foi encontrada automaticamente; criamos uma coluna DATA vazia para evitar crashes.")

# ---------- NORMALIZAR QTD e VALORES em VENDAS ----------
# detectar coluna de quantidade
col_qtd = detectar_col_por_keywords(vendas, ["QTD","QUANT","QTY"])
if col_qtd and col_qtd != "QTD":
    vendas = vendas.rename(columns={col_qtd: "QTD"})

if "QTD" in vendas.columns:
    vendas["QTD"] = pd.to_numeric(vendas["QTD"], errors="coerce").fillna(0).astype(int)
else:
    vendas["QTD"] = 0

# detectar coluna valor total ou valor venda
col_val_total = detectar_col_por_keywords(vendas, ["VALORTOTAL","VALOR TOTAL","TOTAL"])
col_val_unit = detectar_col_por_keywords(vendas, ["VALORVENDA","VALOR VENDA","PRECO","PRICE","VALOR"])

if col_val_total and col_val_total != "VALOR TOTAL":
    vendas = vendas.rename(columns={col_val_total: "VALOR TOTAL"})
if col_val_unit and col_val_unit != "VALOR VENDA":
    vendas = vendas.rename(columns={col_val_unit: "VALOR VENDA"})

if "VALOR TOTAL" in vendas.columns:
    vendas["VALOR TOTAL"] = vendas["VALOR TOTAL"].map(limpar_moeda)
else:
    if "VALOR VENDA" in vendas.columns:
        vendas["VALOR VENDA"] = vendas["VALOR VENDA"].map(limpar_moeda)
        vendas["VALOR TOTAL"] = vendas["VALOR VENDA"].fillna(0) * vendas["QTD"].fillna(0)
    else:
        vendas["VALOR TOTAL"] = 0.0

# garantir produto
col_prod = detectar_col_por_keywords(vendas, ["PRODUTO","PROD","ITEM","NOME","DESCR"])
if col_prod and col_prod != "PRODUTO":
    vendas = vendas.rename(columns={col_prod: "PRODUTO"})
if "PRODUTO" not in vendas.columns:
    # fallback: primeira coluna object/string
    possible = None
    for c in vendas.columns:
        if vendas[c].dtype == object:
            possible = c
            break
    if possible:
        vendas = vendas.rename(columns={possible: "PRODUTO"})
    else:
        vendas["PRODUTO"] = "SEM_PRODUTO"

# criar MES_ANO
vendas["MES_ANO"] = vendas["DATA"].dt.strftime("%Y-%m")

# ---------- NORMALIZAR COMPRAS ----------
# (detectar data, qtd, custo — similar ao acima; garantimos campos usados)
col_data_c = detectar_col_por_keywords(compras, ["DATA","DT","DIA"])
if col_data_c and col_data_c != "DATA":
    compras = compras.rename(columns={col_data_c: "DATA"})
if "DATA" in compras.columns:
    compras["DATA"] = pd.to_datetime(compras["DATA"], errors="coerce")
col_qtd_c = detectar_col_por_keywords(compras, ["QTD","QUANT","QTY"])
if col_qtd_c and col_qtd_c != "QUANTIDADE":
    compras = compras.rename(columns={col_qtd_c: "QUANTIDADE"})
if "QUANTIDADE" in compras.columns:
    compras["QUANTIDADE"] = pd.to_numeric(compras["QUANTIDADE"], errors="coerce").fillna(0).astype(int)
col_custo_c = detectar_col_por_keywords(compras, ["CUSTO","PRECO","VALOR","UNIT"])
if col_custo_c and col_custo_c != "CUSTO":
    compras = compras.rename(columns={col_custo_c: "CUSTO"})
if "CUSTO" in compras.columns:
    compras["CUSTO"] = compras["CUSTO"].map(limpar_moeda)
else:
    compras["CUSTO"] = 0.0
compras["CUSTO TOTAL"] = compras.get("QUANTIDADE", 0) * compras["CUSTO"]
if "DATA" in compras.columns:
    compras["MES_ANO"] = compras["DATA"].dt.strftime("%Y-%m")

# ---------- NORMALIZAR ESTOQUE ----------
col_prod_e = detectar_col_por_keywords(estoque, ["PRODUTO","ITEM","NOME"])
if col_prod_e and col_prod_e != "PRODUTO":
    estoque = estoque.rename(columns={col_prod_e: "PRODUTO"})
col_qtd_e = detectar_col_por_keywords(estoque, ["EMESTOQUE","EM ESTOQUE","ESTOQUE","QTD"])
if col_qtd_e and col_qtd_e != "EM_ESTOQUE":
    estoque = estoque.rename(columns={col_qtd_e: "EM_ESTOQUE"})
col_media_e = detectar_col_por_keywords(estoque, ["MEDIA","CUSTO","CUSTO UNIT"])
if col_media_e and col_media_e != "MEDIA CUSTO UNITARIO":
    estoque = estoque.rename(columns={col_media_e: "MEDIA CUSTO UNITARIO"})
col_venda_e = detectar_col_por_keywords(estoque, ["VALORVENDA","VALOR VENDA","VENDA","PRECO"])
if col_venda_e and col_venda_e != "VALOR VENDA SUGERIDO":
    estoque = estoque.rename(columns={col_venda_e: "VALOR VENDA SUGERIDO"})

if "EM_ESTOQUE" in estoque.columns:
    estoque["EM_ESTOQUE"] = pd.to_numeric(estoque["EM_ESTOQUE"], errors="coerce").fillna(0).astype(int)
else:
    estoque["EM_ESTOQUE"] = 0
if "MEDIA CUSTO UNITARIO" in estoque.columns:
    estoque["MEDIA CUSTO UNITARIO"] = estoque["MEDIA CUSTO UNITARIO"].map(limpar_moeda).fillna(0)
else:
    # tentar variações
    for alt in ["Media C. UNITARIO","Media C. UNITARIO","MEDIA C. UNITARIO"]:
        if alt in estoque.columns:
            estoque["MEDIA CUSTO UNITARIO"] = estoque[alt].map(limpar_moeda).fillna(0)
            break
if "VALOR VENDA SUGERIDO" in estoque.columns:
    estoque["VALOR VENDA SUGERIDO"] = estoque["VALOR VENDA SUGERIDO"].map(limpar_moeda).fillna(0)
else:
    estoque["VALOR VENDA SUGERIDO"] = 0.0

estoque["VALOR_CUSTO_TOTAL"] = estoque["MEDIA CUSTO UNITARIO"].fillna(0) * estoque["EM_ESTOQUE"].fillna(0)
estoque["VALOR_VENDA_TOTAL"] = estoque["VALOR VENDA SUGERIDO"].fillna(0) * estoque["EM_ESTOQUE"].fillna(0)

# ---------- FILTRO MÊS ----------
meses = ["Todos"]
if not vendas.empty:
    meses += sorted(vendas["MES_ANO"].dropna().unique().tolist(), reverse=True)
mes_atual = datetime.now().strftime("%Y-%m")
idx = meses.index(mes_atual) if mes_atual in meses else 0
mes_selecionado = st.selectbox("Filtrar por mês (YYYY-MM):", meses, index=idx)

def filtrar_por_mes(df, mes):
    if df is None or df.empty: return pd.DataFrame()
    if mes == "Todos": return df
    if "MES_ANO" in df.columns:
        return df[df["MES_ANO"] == mes].copy()
    return df

vendas_filtradas = filtrar_por_mes(vendas, mes_selecionado)
compras_filtradas = filtrar_por_mes(compras, mes_selecionado)

# ---------- KPIs ----------
total_vendas = vendas_filtradas["VALOR TOTAL"].sum() if not vendas_filtradas.empty else 0
total_qtd = vendas_filtradas["QTD"].sum() if not vendas_filtradas.empty else 0
total_compras = compras_filtradas["CUSTO TOTAL"].sum() if not compras_filtradas.empty else 0
valor_custo_estoque = estoque["VALOR_CUSTO_TOTAL"].sum() if not estoque.empty else 0
valor_venda_estoque = estoque["VALOR_VENDA_TOTAL"].sum() if not estoque.empty else 0

c1,c2,c3,c4,c5 = st.columns(5)
c1.markdown(f"<div class='kpi-box'><h4>💵 Vendas</h4><h2>{formatar_reais(total_vendas)}</h2></div>", unsafe_allow_html=True)
c2.markdown(f"<div class='kpi-box'><h4>📦 Itens Vendidos</h4><h2>{int(total_qtd)}</h2></div>", unsafe_allow_html=True)
c3.markdown(f"<div class='kpi-box'><h4>💸 Compras</h4><h2>{formatar_reais(total_compras)}</h2></div>", unsafe_allow_html=True)
c4.markdown(f"<div class='kpi-box'><h4>🏷 Estoque (Venda)</h4><h2>{formatar_reais(valor_venda_estoque)}</h2></div>", unsafe_allow_html=True)
c5.markdown(f"<div class='kpi-box'><h4>📥 Estoque (Custo)</h4><h2>{formatar_reais(valor_custo_estoque)}</h2></div>", unsafe_allow_html=True)

# ---------- ABAS (VENDAS com Top5 geral) ----------
aba_vendas, aba_estoque, aba_pesquisar = st.tabs(["🛒 VENDAS", "📦 ESTOQUE", "🔍 PESQUISAR"])

with aba_vendas:
    st.subheader("🔥 Top 5 — Geral (quantidade)")

    # Top5 por quantidade (GERAL — todas as vendas)
    if "PRODUTO" in vendas.columns and "QTD" in vendas.columns:
        top5_qtd = vendas.groupby("PRODUTO", dropna=False)["QTD"].sum().reset_index().sort_values("QTD", ascending=False).head(5)
        if not top5_qtd.empty:
            fig_q = px.bar(top5_qtd, x="QTD", y="PRODUTO", orientation="h", text="QTD", color_discrete_sequence=["#8b5cf6"], height=340)
            fig_q.update_traces(textposition="inside")
            fig_q.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b", font_color="#f2f2f2")
            st.plotly_chart(fig_q, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Nenhum registro de venda encontrado.")
    else:
        st.warning("Não foi possível detectar colunas PRODUTO e/ou QTD para calcular Top5 (GERAL).")

    st.markdown("---")

    st.subheader("💰 Top 5 — Geral (valor total)")

    # Top5 por valor total (GERAL)
    if "PRODUTO" in vendas.columns and "VALOR TOTAL" in vendas.columns:
        top5_val = vendas.groupby("PRODUTO", dropna=False)["VALOR TOTAL"].sum().reset_index().sort_values("VALOR TOTAL", ascending=False).head(5)
        if not top5_val.empty:
            top5_val["LABEL"] = top5_val["VALOR TOTAL"].apply(formatar_reais)
            fig_v = px.bar(top5_val, x="VALOR TOTAL", y="PRODUTO", orientation="h", text="LABEL", color_discrete_sequence=["#8b5cf6"], height=340)
            fig_v.update_traces(textposition="inside")
            fig_v.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b", font_color="#f2f2f2")
            st.plotly_chart(fig_v, use_container_width=True, config={"displayModeBar": False})
        else:
            st.info("Nenhum registro de venda encontrado.")
    else:
        st.warning("Não foi possível detectar colunas PRODUTO e/ou VALOR TOTAL para calcular Top5 (GERAL).")

    st.markdown("---")

    st.subheader("📅 Faturamento Semanal — (mês selecionado)")
    df_sem = vendas_filtradas.copy()
    if "DATA" in df_sem.columns and df_sem["DATA"].notna().any():
        df_sem = df_sem.dropna(subset=["DATA"])
        df_sem["SEMANA"] = df_sem["DATA"].dt.isocalendar().week
        df_sem["ANO"] = df_sem["DATA"].dt.year
        df_week = df_sem.groupby(["ANO","SEMANA"], dropna=False)["VALOR TOTAL"].sum().reset_index()
        def intervalo_sem(row):
            try:
                ini = datetime.fromisocalendar(int(row["ANO"]), int(row["SEMANA"]), 1)
                fim = ini + timedelta(days=6)
                return f"{ini.strftime('%d/%m')} → {fim.strftime('%d/%m')}"
            except:
                return "N/A"
        df_week["INTERVALO"] = df_week.apply(intervalo_sem, axis=1)
        df_week["LABEL"] = df_week["VALOR TOTAL"].apply(formatar_reais)
        fig_week = px.bar(df_week, x="INTERVALO", y="VALOR TOTAL", text="LABEL", color_discrete_sequence=["#8b5cf6"], height=340)
        fig_week.update_traces(textposition="inside")
        fig_week.update_layout(plot_bgcolor="#0b0b0b", paper_bgcolor="#0b0b0b", font_color="#f2f2f2")
        st.plotly_chart(fig_week, use_container_width=True, config={"displayModeBar": False})
    else:
        st.info("Sem dados com DATA válidos no período selecionado para o gráfico semanal.")

    st.markdown("---")
    st.subheader("📄 Tabela de Vendas (mês selecionado)")
    if vendas_filtradas.empty:
        st.info("Sem vendas no mês selecionado.")
    else:
        cols_show = [c for c in ["DATA","PRODUTO","QTD","VALOR VENDA","VALOR TOTAL"] if c in vendas_filtradas.columns]
        st.dataframe(vendas_filtradas[cols_show].sort_values("DATA", ascending=False).reset_index(drop=True), use_container_width=True)

with aba_estoque:
    st.subheader("📦 Estoque — visão")
    if estoque.empty:
        st.info("Sem dados de estoque.")
    else:
        st.dataframe(estoque.reset_index(drop=True), use_container_width=True)

with aba_pesquisar:
    st.subheader("🔍 Buscar produto no estoque")
    termo = st.text_input("Digite parte do nome do produto:")
    if termo and not estoque.empty and "PRODUTO" in estoque.columns:
        res = estoque[estoque["PRODUTO"].astype(str).str.contains(termo, case=False, na=False)]
        st.dataframe(res.reset_index(drop=True), use_container_width=True)
    elif termo:
        st.warning("Nenhum dado de estoque disponível ou coluna PRODUTO ausente.")

# ---------- fim ----------
