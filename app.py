import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import os

st.set_page_config(page_title="Gestão de Estoque - Kelvin Arruda", layout="wide")
st.title("📦 Gestão de Estoque - Kelvin Arruda")

ARQUIVO = "LOJA IMPORTADOS.xlsx"

# --- Função para detectar a linha do cabeçalho ---
def encontrar_cabecalho(arquivo):
    import openpyxl
    wb = openpyxl.load_workbook(arquivo, read_only=True)
    ws = wb.active
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        row_values = [str(cell).strip().lower() if cell else "" for cell in row]
        if any("esto" in c or "produto" in c or "descr" in c for c in row_values):
            return i  # índice da linha que contém o cabeçalho
    return 0  # fallback

# --- Carregar e limpar Excel ---
def carregar_dados(caminho):
    linha_cabecalho = encontrar_cabecalho(caminho)
    df = pd.read_excel(caminho, header=linha_cabecalho, engine="openpyxl")
    df.columns = [str(c).strip().lower() for c in df.columns]
    df = df.dropna(how="all")

    # --- detectar colunas ---
    mapa = {"produto": None, "estoque": None, "preco_venda": None, "vendas": None}
    for c in df.columns:
        nome = str(c).lower()
        if any(x in nome for x in ["prod", "descr", "item", "nome"]):
            mapa["produto"] = c
        elif "esto" in nome or "quant" in nome:
            mapa["estoque"] = c
        elif "preç" in nome or "valor" in nome:
            if mapa["preco_venda"] is None:
                mapa["preco_venda"] = c
            else:
                mapa["vendas"] = c
        elif "vend" in nome:
            mapa["vendas"] = c

    return df, mapa

# --- MAIN ---
if not os.path.exists(ARQUIVO):
    st.error("❌ O arquivo 'LOJA IMPORTADOS.xlsx' não foi encontrado.")
else:
    try:
        df, mapa = carregar_dados(ARQUIVO)
        st.write("🔍 **Colunas detectadas (verifique)**")
        st.json(mapa)

        if mapa["produto"] is None or mapa["estoque"] is None:
            st.error("❌ Não foi possível identificar as colunas principais (Produto / Estoque). Verifique se o Excel contém esses nomes.")
        else:
            df = df.rename(columns={
                mapa["produto"]: "Produto",
                mapa["estoque"]: "Estoque",
                mapa["preco_venda"]: "Preço",
                mapa["vendas"]: "Vendas"
            })

            # converter numéricos
            for c in ["Estoque", "Preço", "Vendas"]:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

            st.subheader("📋 Tabela de Estoque")
            st.dataframe(df, use_container_width=True)

            st.subheader("📊 Gráfico de Estoque")
            fig, ax = plt.subplots(figsize=(8, 4))
            df.plot(kind="bar", x="Produto", y="Estoque", ax=ax, legend=False)
            ax.set_ylabel("Quantidade em Estoque")
            ax.set_xlabel("")
            st.pyplot(fig)

            st.subheader("⚠️ Alertas de Reposição")
            baixo = df[df["Estoque"] <= 5]
            if baixo.empty:
                st.success("✅ Nenhum produto com estoque baixo.")
            else:
                st.warning("🚨 Produtos com baixo estoque:")
                st.dataframe(baixo, use_container_width=True)

    except Exception as e:
        st.error(f"❌ Erro ao processar o arquivo: {e}")
