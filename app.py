import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import unicodedata
import io

st.set_page_config(page_title="Gestão de Estoque - Kelvin Arruda", layout="wide")
st.title("📊 KELVIN ARRUDA - Painel de Estoque Inteligente")

# ==== Função auxiliar para normalizar texto ====
def normalizar(txt):
    if not isinstance(txt, str):
        return ""
    txt = txt.strip().lower()
    txt = unicodedata.normalize("NFKD", txt).encode("ASCII", "ignore").decode("utf-8")
    return txt

# ==== Tenta ler o Excel ignorando cabeçalhos errados ====
try:
    # Lê tudo sem cabeçalho
    df_raw = pd.read_excel("LOJA IMPORTADOS.xlsx", header=None)
except Exception as e:
    st.error(f"❌ Erro ao ler o arquivo: {e}")
    st.stop()

# === Localiza linha onde começa o cabeçalho verdadeiro ===
header_row = None
for i, row in df_raw.iterrows():
    row_norm = [normalizar(str(x)) for x in row.tolist()]
    if any("produto" in x for x in row_norm):
        header_row = i
        break

if header_row is None:
    st.error("❌ Não foi possível localizar o cabeçalho contendo 'PRODUTO'.")
    st.dataframe(df_raw.head())
    st.stop()

# === Lê novamente com o cabeçalho correto ===
df = pd.read_excel("LOJA IMPORTADOS.xlsx", header=header_row)
df = df.dropna(how="all")  # remove linhas vazias
df.columns = [normalizar(str(c)) for c in df.columns]

# === Detecta colunas ===
colunas = {"produto": None, "estoque": None, "preco_venda": None, "vendas": None}

for col in df.columns:
    nome = normalizar(col)
    if "produto" in nome:
        colunas["produto"] = col
    elif "estoque" in nome:
        colunas["estoque"] = col
    elif "preco" in nome or "valor venda" in nome:
        colunas["preco_venda"] = col
    elif "venda" in nome or "saida" in nome:
        colunas["vendas"] = col

st.write("🔍 **Colunas detectadas (verifique)**")
st.json(colunas)

if not colunas["produto"] or not colunas["estoque"]:
    st.warning("⚠️ Não foi possível identificar as colunas principais ('Produto' / 'Estoque'). Exibindo amostra bruta...")
    st.dataframe(df.head())
    st.stop()

# === Normaliza ===
df = df.rename(columns={
    colunas["produto"]: "Produto",
    colunas["estoque"]: "Estoque",
    colunas["preco_venda"]: "Preço_Venda" if colunas["preco_venda"] else None,
    colunas["vendas"]: "Vendas" if colunas["vendas"] else None,
})

# === Limpeza ===
df["Estoque"] = pd.to_numeric(df["Estoque"], errors="coerce").fillna(0)
df = df[df["Produto"].astype(str).str.strip() != ""]

# === Exibe estoque ===
st.subheader("📦 Estoque Atual")
st.dataframe(df, use_container_width=True)

# === Alerta de reposição ===
st.subheader("🚨 Produtos com Estoque Baixo (<5)")
alertas = df[df["Estoque"] < 5]
if not alertas.empty:
    st.dataframe(alertas[["Produto", "Estoque"]])
else:
    st.success("✅ Nenhum produto em nível crítico!")

# === Gráfico ===
st.subheader("📈 Gráfico de Estoque por Produto")
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(df["Produto"], df["Estoque"])
plt.xticks(rotation=45, ha="right")
plt.xlabel("Produto")
plt.ylabel("Estoque")
plt.tight_layout()
st.pyplot(fig)

# === Exportação ===
st.subheader("📤 Exportar Planilha Corrigida")
buffer = io.BytesIO()
df.to_excel(buffer, index=False)
st.download_button(
    label="💾 Baixar Estoque Limpo (Excel)",
    data=buffer.getvalue(),
    file_name="estoque_limpo.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

st.markdown("---")
st.caption("🧠 Sistema de Gestão Automatizada - Kelvin Arruda © 2025")
