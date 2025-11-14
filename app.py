import streamlit as st
import pandas as pd

st.set_page_config(page_title="Diagnóstico da Planilha", layout="wide")
st.title("🛠️ Diagnóstico Automático da Planilha do Drive")

URL_PLANILHA = "https://drive.google.com/uc?export=download&id=1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b"

# =====================================================
# FUNÇÃO ROBUSTA PARA CARREGAR
# =====================================================
def carregar_arquivo(url):
    try:
        xls = pd.ExcelFile(url)
        return xls, None
    except Exception as e:
        return None, str(e)

xls, erro = carregar_arquivo(URL_PLANILHA)

if erro:
    st.error("❌ ERRO AO CARREGAR A PLANILHA INTEIRA")
    st.code(erro)
    st.stop()

st.success("✅ Arquivo aberto com sucesso!")

# Remover aba EXCELENTEJOAO
abas = [a for a in xls.sheet_names if a.upper() != "EXCELENTEJOAO"]
st.write("📄 **Abas detectadas:**", abas)

# =====================================================
# DEFINIÇÃO DAS ABAS E COLUNAS ESPERADAS
# =====================================================
regras = {
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

# =====================================================
# FUNÇÃO DE DIAGNÓSTICO
# =====================================================
def diagnosticar_aba(nome_aba, colunas_esperadas):
    st.header(f"📌 Diagnóstico da aba: **{nome_aba}**")

    # Tentar carregar
    try:
        df = pd.read_excel(URL_PLANILHA, sheet_name=nome_aba)
        st.success(f"✔ Aba **{nome_aba}** carregada!")
    except Exception as e:
        st.error(f"❌ Não foi possível abrir a aba {nome_aba}:")
        st.code(str(e))
        return None

    # Listar colunas encontradas
    colunas_encontradas = df.columns.tolist()
    st.write("📋 **Colunas encontradas:**", colunas_encontradas)

    # Comparar colunas
    faltando = [c for c in colunas_esperadas if c not in colunas_encontradas]
    extras = [c for c in colunas_encontradas if c not in colunas_esperadas]

    # Erros detectados
    if faltando:
        st.error("❌ COLUNAS FALTANDO:")
        st.write(faltando)
        st.info("💡 **Correção sugerida:** Verifique nomes, acentos, espaços e letras maiúsculas/minúsculas.")

    if extras:
        st.warning("⚠️ COLUNAS EXTRAS (não esperadas):")
        st.write(extras)
        st.info("💡 **Correção sugerida:** Avalie se estas colunas deveriam existir ou se têm nome errado.")

    if not faltando and not extras:
        st.success("🎉 Todas as colunas estão corretas!")

    # Mostrar a aba
    st.subheader("📄 Pré-visualização dos dados")
    st.dataframe(df)

    return df

# =====================================================
# EXECUTAR DIAGNÓSTICO ABA POR ABA
# =====================================================
dfs = {}

for aba in regras.keys():
    if aba in abas:
        df = diagnosticar_aba(aba, regras[aba])
        dfs[aba] = df
    else:
        st.error(f"❌ A aba **{aba}** NÃO existe no arquivo!")
        st.info(f"💡 Crie a aba {aba} na planilha ou verifique se o nome está escrito exatamente assim.")


# =====================================================
# TENTAR CONVERTER CAMPOS DE DINHEIRO
# =====================================================
def converter_valores(df, campos):
    for c in campos:
        if c not in df.columns:
            continue
        try:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        except:
            st.error(f"❌ Erro ao converter valor monetário da coluna {c}")

if dfs.get("VENDAS") is not None:
    converter_valores(dfs["VENDAS"], ["VALOR VENDA", "VALOR TOTAL", "MEDIA CUSTO UNITARIO", "LUCRO UNITARIO"])

if dfs.get("COMPRAS") is not None:
    converter_valores(dfs["COMPRAS"], ["CUSTO UNITÁRIO", "CUSTO TOTAL"])

if dfs.get("ESTOQUE") is not None:
    converter_valores(dfs["ESTOQUE"], ["Media C. UNITARIO", "Valor Venda Sugerido"])

st.success("💰 Conversão monetária executada (onde possível).")

