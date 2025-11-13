# app.py (versão atualizada)
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

st.set_page_config(page_title="Painel de Estoque — Kelvin", layout="wide")
st.title("Painel Interativo de Estoque")
st.markdown("<h1 style='font-size:28px; margin-top:-8px;'>KELVIN ARRUDA</h1>", unsafe_allow_html=True)
st.write("Um painel claro, direto e pronto pra decisão — números que falam baixo mas dizem tudo.")

# ---------- Helpers ----------
def smart_read_csv(path, sep=';', encoding='latin1', skiprows=2):
    """Tenta ler diferentes formatos de CSV (como o seu que vinha com ; e linhas extras)."""
    df = pd.read_csv(path, sep=sep, encoding=encoding, skiprows=skiprows)
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]  # remove colunas vazias
    # strip nomes
    df.columns = [c.strip() for c in df.columns]
    return df

def normalize_columns(df):
    """
    Normaliza nomes variados de colunas para nomes canônicos:
    PRODUTO, EM_ESTOQUE, COMPRAS, MEDIA_CUSTO, VALOR_VENDA, VENDAS
    """
    new = {}
    for c in df.columns:
        cu = c.upper().strip()
        cu = cu.replace('.', '').replace('-', '_')
        cu = cu.replace('  ', ' ')
        # heurísticas
        if 'PROD' in cu:
            new[c] = 'PRODUTO'
        elif 'ESTOQUE' in cu:
            new[c] = 'EM_ESTOQUE'
        elif 'COMPRA' in cu and 'MEDIA' not in cu:
            new[c] = 'COMPRAS'
        elif 'MEDIA' in cu and ('C' in cu or 'CUSTO' in cu or 'UNI' in cu):
            new[c] = 'MEDIA_CUSTO'
        elif 'VALOR' in cu and 'VENDA' in cu:
            new[c] = 'VALOR_VENDA'
        elif 'VEND' in cu:
            new[c] = 'VENDAS'
        else:
            # tenta manter original com maiúsculas sem espaços
            safe = cu.replace(' ', '_')
            new[c] = safe
    df = df.rename(columns=new)
    return df

def to_number_series(s):
    """Limpa moeda e converte para float — tolerante a strings como 'R$ 1.234,56'."""
    s = s.fillna('').astype(str)
    s = s.str.replace(r'[^0-9,.\-]', '', regex=True)  # remove letras e símbolos
    s = s.str.replace(r'\.(?=\d{3}(?!\d))', '', regex=True)  # remove pontos de milhares
    s = s.str.replace(',', '.', regex=False)  # vírgula -> ponto decimal
    return pd.to_numeric(s.replace('', pd.NA), errors='coerce').fillna(0)

def ensure_product_names(df):
    """Se coluna PRODUTO faltar ou tiver NA, cria/normaliza com placeholder."""
    if 'PRODUTO' not in df.columns:
        df.insert(0, 'PRODUTO', df.index.map(lambda i: f"SKU_{i}"))
    df['PRODUTO'] = df['PRODUTO'].fillna('').astype(str).replace('', 'SEM_NOME_PRODUTO')
    return df

# ---------- Upload / Leitura ----------
st.sidebar.header("Dados")
use_upload = st.sidebar.checkbox("Fazer upload do CSV em vez de usar arquivo no repositório?", value=False)

uploaded = None
if use_upload:
    uploaded = st.sidebar.file_uploader("Arraste o CSV aqui (ex: LOJA IMPORTADOS(ESTOQUE).csv)", type=['csv', 'txt'])
    if uploaded is None:
        st.sidebar.info("Faça upload para visualizar os dados aqui.")
else:
    DEFAULT_CSV = "LOJA IMPORTADOS(ESTOQUE).csv"
    if not os.path.exists(DEFAULT_CSV) and not use_upload:
        st.warning(f"O arquivo padrão '{DEFAULT_CSV}' não foi encontrado no repositório. Marque a opção de upload na barra lateral ou envie o arquivo para o repo.")
        uploaded = None

# Carregar dataframe
try:
    if uploaded:
        # tenta carregar upload com diferentes separadores automaticamente
        try:
            df_raw = pd.read_csv(uploaded)
        except Exception:
            uploaded.seek(0)
            df_raw = pd.read_csv(uploaded, sep=';', encoding='latin1', skiprows=0)
    else:
        df_raw = smart_read_csv(DEFAULT_CSV)
except Exception as e:
    st.error("Erro ao ler CSV: " + str(e))
    st.stop()

# ---------- Normalização ----------
df = normalize_columns(df_raw.copy())
df = ensure_product_names(df)

# garantir colunas numéricas mínimas
for col in ['EM_ESTOQUE', 'COMPRAS', 'MEDIA_CUSTO', 'VALOR_VENDA', 'VENDAS']:
    if col in df.columns:
        df[col] = to_number_series(df[col])
    else:
        # se coluna não existir, cria com zeros (evita crashes)
        df[col] = 0

# Colunas derivadas
df['VALOR_ESTOQUE_CUSTO'] = df['EM_ESTOQUE'] * df['MEDIA_CUSTO']
df['VALOR_ESTOQUE_VENDA'] = df['EM_ESTOQUE'] * df['VALOR_VENDA']
df['MARGEM_UNIT'] = df['VALOR_VENDA'] - df['MEDIA_CUSTO']

# view filtrada
st.sidebar.header("Filtros & Exibição")
produto_sel = st.sidebar.multiselect("Filtrar produtos (pesquise)", options=sorted(df['PRODUTO'].unique()), default=None)
top_n = st.sidebar.slider("Top N (gráficos)", 3, 30, 10)
repor_lim = st.sidebar.number_input("Alerta de reposição: estoque menor ou igual a", min_value=0, value=5)

if produto_sel:
    df_view = df[df['PRODUTO'].isin(produto_sel)].copy()
else:
    df_view = df.copy()

# ---------- KPIs e Resumo Automático ----------
col1, col2, col3, col4 = st.columns([1,1,1,1])
col1.metric("Total SKUs", int(df['PRODUTO'].nunique()))
col2.metric("Total unidades em estoque", int(df['EM_ESTOQUE'].sum()))
col3.metric("Valor total do estoque (custo)", f"R$ {df['VALOR_ESTOQUE_CUSTO'].sum():,.2f}")
col4.metric("Lucro potencial (venda - custo)", f"R$ { (df['VALOR_ESTOQUE_VENDA'].sum() - df['VALOR_ESTOQUE_CUSTO'].sum()):,.2f}")

st.markdown("---")
st.subheader("Resumo rápido")
# Top vendidos
top_vendidos = df.sort_values('VENDAS', ascending=False).head(5)[['PRODUTO','VENDAS']]
# Top com menor estoque
top_menor_estoque = df.sort_values('EM_ESTOQUE', ascending=True).head(5)[['PRODUTO','EM_ESTOQUE']]
st.write(f"**Top {min(5, len(top_vendidos))} mais vendidos:** " + ", ".join(top_vendidos['PRODUTO'].tolist()) if not top_vendidos.empty else "Sem dados de vendas.")
st.write(f"**Top {min(5, len(top_menor_estoque))} com menor estoque:** " + ", ".join(top_menor_estoque['PRODUTO'].tolist()) if not top_menor_estoque.empty else "Sem dados de estoque.")
st.write(f"**Total de SKUs:** {int(df['PRODUTO'].nunique())} • **Unidades em estoque:** {int(df['EM_ESTOQUE'].sum())}")

st.markdown("---")

# ---------- Gráficos ----------
st.subheader("Top produtos por VENDAS")
if df_view['VENDAS'].sum() > 0:
    top_v = df_view.sort_values('VENDAS', ascending=False).head(top_n)
    fig1, ax1 = plt.subplots()
    ax1.barh(top_v['PRODUTO'][::-1], top_v['VENDAS'][::-1])
    ax1.set_xlabel("VENDAS (unidades)")
    st.pyplot(fig1)
else:
    st.info("Não há dados úteis na coluna 'VENDAS' para gerar este gráfico.")

st.subheader("Top produtos por ESTOQUE")
if df_view['EM_ESTOQUE'].sum() > 0:
    top_e = df_view.sort_values('EM_ESTOQUE', ascending=False).head(top_n)
    fig2, ax2 = plt.subplots()
    ax2.barh(top_e['PRODUTO'][::-1], top_e['EM_ESTOQUE'][::-1])
    ax2.set_xlabel("EM_ESTOQUE (unidades)")
    st.pyplot(fig2)
else:
    st.info("Não há dados úteis na coluna 'EM_ESTOQUE' para gerar este gráfico.")

# ---------- Alertas de Reposição (corrigido) ----------
st.markdown("---")
st.subheader("Alertas de Reposição")
# garantia: EM_ESTOQUE é numérico; se tinha NA antes, agora é 0. Mas queremos sinalizar também quando produto não tem dado de estoque.
mask_low = df_view['EM_ESTOQUE'] <= repor_lim
low_stock = df_view.loc[mask_low, ['PRODUTO', 'EM_ESTOQUE', 'COMPRAS', 'VALOR_ESTOQUE_CUSTO']].sort_values('EM_ESTOQUE')
if low_stock.empty:
    st.success("Nenhum produto abaixo do limite definido.")
else:
    # formatar para exibir números limpos
    low_stock_display = low_stock.copy()
    low_stock_display['EM_ESTOQUE'] = low_stock_display['EM_ESTOQUE'].astype(int)
    low_stock_display['VALOR_ESTOQUE_CUSTO'] = low_stock_display['VALOR_ESTOQUE_CUSTO'].map(lambda v: f"R$ {v:,.2f}")
    st.table(low_stock_display)

# ---------- Tabela e export ----------
st.markdown("---")
st.subheader("Tabela (filtrável)")
st.dataframe(df_view.reset_index(drop=True))

csv = df_view.to_csv(index=False).encode('utf-8')
st.download_button("Baixar CSV filtrado", csv, "estoque_filtrado.csv", "text/csv")

st.write("Observação: se seu CSV usa outro nome de coluna, o código tenta mapear automaticamente (heurísticas). Se algo ainda aparecer estranho, me manda as primeiras 10 linhas do CSV que eu ajusto o mapeamento.")
