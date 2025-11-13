import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import unicodedata
import io

st.set_page_config(page_title="Gestão de Estoque - Kelvin Arruda", layout="wide")

st.title("📊 KELVIN ARRUDA - Painel de Estoque Inteligente")
st.markdown("Sistema automatizado de análise e visualização de estoque 💼")

# ==== Função auxiliar para normalizar texto ====
def normalizar(texto):
    if not isinstance(texto, str):
        return ""
    texto = texto.strip().lower()
    texto = unicodedata.normalize("NFKD", texto).encode("ASCII", "ignore").decode("utf-8")
    return texto

# ==== Leitura segura do Excel ====
try:
    df = pd.read_excel("LOJA IMPORTADOS.xlsx", header=0)
except Exception as e:
    st.error(f"❌ Erro ao ler o arquivo Excel: {e}")
    st.stop()

# Remove linhas e colunas totalmente vazias
df = df.dropna(how="all").copy()
df.columns = [normalizar(c) for c in df.columns]

# ==== Detecção de colunas ====
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

# ==== Validação mínima ====
if not colunas["produto"] or not colunas["estoque"]:
    st.warning("⚠️ Não foi possível identificar as colunas principais ('Produto' / 'Estoque'). Exibindo amostra bruta...")
    st.dataframe(df.head())
    st.stop()

# ==== Renomeia para padrão ====
df = df.rename(columns={
    colunas["produto"]: "Produto",
    colunas["estoque"]: "Estoque",
    colunas["preco_venda"]: "Preço_Venda" if colunas["preco_venda"] else None,
    colunas["vendas"]: "Vendas" if colunas["vendas"] else None,
})

# ==== Limpeza final ====
df = df.dropna(subset=["Produto", "Estoque"], how="any")
df["Estoque"] = pd.to_numeric(df["Estoque"], errors="coerce").fillna(0)
df = df[df["Produto"].astype(str).str.strip() != ""]

# ==== Exibição principal ====
st.subheader("📦 Estoque Atual")
st.dataframe(df, use_container_width=True)

# ==== Alertas de reposição ====
st.subheader("🚨 Alertas de Reposição (Estoque abaixo de 5 unidades)")
alertas = df[df["Estoque"] < 5]
if not alertas.empty:
    st.dataframe(alertas[["Produto", "Estoque"]])
else:
    st.success("✅ Nenhum produto com estoque crítico!")

# ==== Gráfico ====
st.subheader("📈 Gráfico de Estoque por Produto")
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(df["Produto"], df["Estoque"])
plt.xticks(rotation=45, ha="right")
plt.xlabel("Produto")
plt.ylabel("Quantidade em Estoque")
plt.tight_layout()
st.pyplot(fig)

# ==== Exportação ====
st.subheader("📤 Exportar Dados Limpos")
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
