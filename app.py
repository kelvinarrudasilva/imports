# app.py
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

st.set_page_config(page_title="Painel de Estoque", layout="wide")
st.title("Painel Interativo de Estoque — Loja Importados")

# Caminho padrão: o mesmo arquivo CSV que você enviou.
# Se o seu CSV estiver em outro lugar, altere aqui.
DEFAULT_CSV = "LOJA IMPORTADOS(ESTOQUE).csv"

@st.cache_data
def load_data(path=DEFAULT_CSV, sep=';', encoding='latin1', skiprows=2):
    """
    Leitura robusta para arquivos CSV com:
    - delimitador ';'
    - possível cabeçalho em linhas antes da real header (skiprows)
    - encoding latin1 (comum em arquivos gerados no Brasil)
    """
    df = pd.read_csv(path, sep=sep, encoding=encoding, skiprows=skiprows)
    # remove colunas "Unnamed" que aparecem por causa de colunas extras
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
    # limpa nomes
    df.columns = [c.strip() for c in df.columns]
    return df

def to_number_series(s):
    """Converte strings com 'R$ 1.234,56' ou '1.234,56' para float"""
    s = s.fillna('').astype(str)
    # remove tudo que não é dígito, vírgula, ponto ou sinal
    s = s.str.replace(r'[^0-9,.\-]', '', regex=True)
    # remove pontos de milhares (ex: 1.234,56 -> 1234,56)
    s = s.str.replace(r'\.(?=\d{3}(?!\d))', '', regex=True)
    # vírgula decimal -> ponto
    s = s.str.replace(',', '.', regex=False)
    return pd.to_numeric(s.replace('', pd.NA), errors='coerce').fillna(0)

# carrega dados
if not os.path.exists(DEFAULT_CSV):
    st.error(f"Arquivo padrão não encontrado: {DEFAULT_CSV}. Coloque o CSV na mesma pasta que este app ou altere DEFAULT_CSV no código.")
    st.stop()

df = load_data()

# nomes esperados (mas o app é tolerante)
# exemplos de colunas vistas: 'PRODUTO', 'EM ESTOQUE', 'COMPRAS', 'Media C. UNITARIO', 'Valor Venda Sugerido', 'VENDAS'
# adapta se a coluna tiver variações
colnames = [c.upper().strip() for c in df.columns]
# tenta padronizar acessos com versões uppercase
df.columns = [c.upper().strip() for c in df.columns]

# Converte colunas numéricas que costumam vir como texto
for candidate in ["EM ESTOQUE", "COMPRAS", "MEDIA C. UNITARIO", "MEDIA C UNITARIO", "VALOR VENDA SUGERIDO", "VENDAS"]:
    if candidate in df.columns:
        df[candidate] = to_number_series(df[candidate])

# cria colunas derivadas quando possível
if "EM ESTOQUE" in df.columns and ("MEDIA C. UNITARIO" in df.columns or "MEDIA C UNITARIO" in df.columns):
    # escolher o nome presente
    media_col = "MEDIA C. UNITARIO" if "MEDIA C. UNITARIO" in df.columns else "MEDIA C UNITARIO"
    df["VALOR_ESTOQUE_CUSTO"] = df["EM ESTOQUE"] * df[media_col]
else:
    df["VALOR_ESTOQUE_CUSTO"] = 0

if "EM ESTOQUE" in df.columns and "VALOR VENDA SUGERIDO" in df.columns:
    df["VALOR_ESTOQUE_VENDA"] = df["EM ESTOQUE"] * df["VALOR VENDA SUGERIDO"]
else:
    df["VALOR_ESTOQUE_VENDA"] = 0

# interface lateral
st.sidebar.header("Filtros e opções")
produto_list = df["PRODUTO"].astype(str).unique().tolist() if "PRODUTO" in df.columns else []
produto_sel = st.sidebar.multiselect("Filtrar produtos (pesquise)", options=sorted(produto_list), default=None)
top_n = st.sidebar.slider("Top N (gráficos)", 5, 30, 10)
repor_lim = st.sidebar.number_input("Alerta de reposição: estoque menor que", min_value=0, value=5)

if produto_sel:
    df_view = df[df["PRODUTO"].isin(produto_sel)]
else:
    df_view = df.copy()

# KPIs
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total SKUs", int(df["PRODUTO"].nunique()) if "PRODUTO" in df.columns else 0)
col2.metric("Total unidades em estoque", int(df["EM ESTOQUE"].sum()) if "EM ESTOQUE" in df.columns else 0)
col3.metric("Valor total do estoque (custo)", f"R$ {df['VALOR_ESTOQUE_CUSTO'].sum():,.2f}")
lucro_pot = df['VALOR_ESTOQUE_VENDA'].sum() - df['VALOR_ESTOQUE_CUSTO'].sum()
col4.metric("Lucro potencial (venda - custo)", f"R$ {lucro_pot:,.2f}")

st.markdown("---")

# Gráfico: Top produtos por vendas
st.subheader("Top produtos por VENDAS")
if "VENDAS" in df_view.columns:
    top_v = df_view.sort_values("VENDAS", ascending=False).head(top_n)
    fig1, ax1 = plt.subplots()
    ax1.barh(top_v["PRODUTO"][::-1], top_v["VENDAS"][::-1])
    ax1.set_xlabel("VENDAS (unidades)")
    ax1.set_ylabel("PRODUTO")
    st.pyplot(fig1)
else:
    st.info("Coluna 'VENDAS' não encontrada — o gráfico de vendas não será exibido.")

# Gráfico: Top produtos por estoque
st.subheader("Top produtos por ESTOQUE")
if "EM ESTOQUE" in df_view.columns:
    top_e = df_view.sort_values("EM ESTOQUE", ascending=False).head(top_n)
    fig2, ax2 = plt.subplots()
    ax2.barh(top_e["PRODUTO"][::-1], top_e["EM ESTOQUE"][::-1])
    ax2.set_xlabel("EM ESTOQUE (unidades)")
    ax2.set_ylabel("PRODUTO")
    st.pyplot(fig2)

st.markdown("---")
st.subheader("Alertas de Reposição")
if "EM ESTOQUE" in df_view.columns:
    low_stock = df_view[df_view["EM ESTOQUE"] <= repor_lim].sort_values("EM ESTOQUE")
    if not low_stock.empty:
        st.table(low_stock[["PRODUTO", "EM ESTOQUE", "COMPRAS"]].head(50))
    else:
        st.write("Nenhum produto abaixo do limite definido.")
else:
    st.info("Coluna 'EM ESTOQUE' não encontrada — não posso gerar alertas de reposição.")

st.markdown("---")
st.subheader("Tabela completa (filtrável)")
st.dataframe(df_view)

# export do view filtrado
csv = df_view.to_csv(index=False).encode("utf-8")
st.download_button("Baixar CSV filtrado", csv, "estoque_filtrado.csv", "text/csv")

st.write("Dica: se os nomes das colunas no seu CSV tiverem grafias diferentes, edite as referências (ex: 'EM ESTOQUE', 'VENDAS') no código acima para combinar com o seu arquivo.")
