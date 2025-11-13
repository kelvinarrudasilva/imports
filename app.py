import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io
import chardet

# =====================================
# 🎯 Função para detectar encoding
# =====================================
def detectar_encoding(arquivo):
    resultado = chardet.detect(arquivo.read())
    arquivo.seek(0)
    return resultado["encoding"]

# =====================================
# 🎯 Função para detectar nomes de colunas automaticamente
# =====================================
def detectar_coluna(df, opcoes):
    for col in df.columns:
        nome = str(col).strip().lower()
        for op in opcoes:
            if op in nome:
                return col
    return None

# =====================================
# 🎨 Interface do Streamlit
# =====================================
st.set_page_config(page_title="Gestão de Estoque - Kelvin Arruda", layout="wide")

st.title("📦 Gestão de Estoque - Kelvin Arruda")

st.sidebar.header("📁 Dados do Arquivo")

arquivo_csv = st.sidebar.file_uploader("Envie seu arquivo CSV de estoque", type=["csv"])

if arquivo_csv is not None:
    try:
        # Detectar encoding e ler o CSV
        encoding = detectar_encoding(arquivo_csv)
        df = pd.read_csv(arquivo_csv, encoding=encoding)

        st.sidebar.success(f"Arquivo lido com sucesso! (Encoding: {encoding})")

        # Remover linhas totalmente vazias
        df = df.dropna(how="all")

        # Detectar colunas automaticamente
        col_produto = detectar_coluna(df, ["produto", "descrição", "nome"])
        col_estoque = detectar_coluna(df, ["estoque", "em estoque", "quantidade"])
        col_compras = detectar_coluna(df, ["compra", "entrada", "compras"])
        col_preco = detectar_coluna(df, ["preço", "valor", "venda sugerido"])
        col_vendas = detectar_coluna(df, ["venda", "vendida", "quantidade vendida", "saída"])

        # Evitar duplicação de colunas
        if col_vendas == col_preco:
            col_vendas = None

        # Mostrar colunas detectadas
        st.write("### 🧭 Colunas detectadas (verifique se estão corretas):")
        st.json({
            "produto": col_produto,
            "estoque": col_estoque,
            "compras": col_compras,
            "preco_venda": col_preco,
            "vendas": col_vendas
        })

        # Verificação básica
        if not col_produto or not col_estoque:
            st.error("❌ Não foi possível identificar colunas essenciais ('Produto' e 'Estoque'). Verifique o arquivo.")
            st.stop()

        # Limpar e preparar os dados
        df = df.rename(columns={
            col_produto: "Produto",
            col_estoque: "Estoque",
            col_compras: "Compras" if col_compras else None,
            col_preco: "PrecoVenda" if col_preco else None,
            col_vendas: "Vendas" if col_vendas else None
        })
        df = df.loc[:, ~df.columns.duplicated()]
        df = df[df["Produto"].astype(str).str.strip().ne("")]

        # Converter números
        for col in ["Estoque", "Compras", "PrecoVenda", "Vendas"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # ===============================
        # 📊 Análises e Indicadores
        # ===============================
        total_produtos = len(df)
        total_estoque = df["Estoque"].sum()
        total_compras = df["Compras"].sum() if "Compras" in df.columns else 0
        total_vendas = df["Vendas"].sum() if "Vendas" in df.columns else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Produtos Cadastrados", f"{total_produtos}")
        col2.metric("Total em Estoque", f"{total_estoque:,.0f}")
        col3.metric("Total Compras", f"{total_compras:,.0f}")
        col4.metric("Total Vendas", f"{total_vendas:,.0f}")

        st.divider()

        # ===============================
        # ⚠️ Produtos com estoque baixo
        # ===============================
        limite = st.sidebar.number_input("Definir limite de alerta (ex: 5 unidades)", min_value=0, value=5)
        alertas = df[df["Estoque"] <= limite]

        st.subheader("🚨 Alertas de Reposição")
        if alertas.empty:
            st.success("✅ Todos os produtos estão acima do limite mínimo de estoque.")
        else:
            st.warning(f"⚠️ {len(alertas)} produtos abaixo do limite definido:")
            st.dataframe(alertas[["Produto", "Estoque"]])

        st.divider()

        # ===============================
        # 📈 Gráficos de desempenho
        # ===============================
        st.subheader("📈 Gráficos de Estoque e Vendas")

        fig, ax = plt.subplots(figsize=(10, 5))
        top_estoque = df.nlargest(10, "Estoque")
        ax.barh(top_estoque["Produto"], top_estoque["Estoque"])
        ax.set_xlabel("Quantidade em Estoque")
        ax.set_ylabel("Produto")
        ax.set_title("Top 10 Produtos com Maior Estoque")
        st.pyplot(fig)

        if "Vendas" in df.columns:
            fig2, ax2 = plt.subplots(figsize=(10, 5))
            top_vendas = df.nlargest(10, "Vendas")
            ax2.barh(top_vendas["Produto"], top_vendas["Vendas"], color="orange")
            ax2.set_xlabel("Quantidade Vendida")
            ax2.set_ylabel("Produto")
            ax2.set_title("Top 10 Produtos Mais Vendidos")
            st.pyplot(fig2)

        st.divider()

        # ===============================
        # 💾 Exportar relatório
        # ===============================
        st.subheader("💾 Exportar Dados")
        buffer = io.BytesIO()
        df.to_csv(buffer, index=False, encoding="utf-8-sig")
        st.download_button("⬇️ Baixar relatório em CSV", buffer.getvalue(), "relatorio_estoque.csv", "text/csv")

    except Exception as e:
        st.error(f"❌ Erro ao ler o arquivo: {e}")

else:
    st.info("👈 Envie um arquivo CSV para começar a análise.")
