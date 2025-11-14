import streamlit as st
import pandas as pd

st.set_page_config(page_title="Diagnóstico Automático", layout="wide")
st.title("🛠️ Diagnóstico + Correção Automática da Planilha")

URL_PLANILHA = "https://drive.google.com/uc?export=download&id=1TsRjsfw1TVfeEWBBvhKvsGQ5YUCktn2b"

# ============================================================
# FUNÇÃO BASE PARA CARREGAR ARQUIVO
# ============================================================
def carregar_xls(url):
    try:
        xls = pd.ExcelFile(url)
        return xls, None
    except Exception as e:
        return None, str(e)


xls, erro = carregar_xls(URL_PLANILHA)

if erro:
    st.error("❌ ERRO AO LER O ARQUIVO")
    st.code(erro)
    st.stop()

# ignora aba EXCELENTEJOAO
abas = [a for a in xls.sheet_names if a.upper() != "EXCELENTEJOAO"]
st.write("📄 Abas detectadas:", abas)

# ============================================================
# COLUNAS ESPERADAS
# ============================================================
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

# ============================================================
# DETECTOR DE CABEÇALHO
# ============================================================
def limpar_aba(df, nome_aba):
    st.subheader(f"🔧 Limpando aba **{nome_aba}**")

    busca = "PRODUTO" if nome_aba != "VENDAS" and nome_aba != "COMPRAS" else "DATA"

    linha_cab = None
    for i in range(len(df)):
        linha = df.iloc[i].astype(str).str.upper().tolist()
        if busca in " ".join(linha):
            linha_cab = i
            break

    if linha_cab is None:
        st.error(f"⚠ Não encontrei o cabeçalho da aba {nome_aba}.")
        return None

    # define cabeçalho real
    df.columns = df.iloc[linha_cab]
    df = df.iloc[linha_cab + 1:]

    # apagar colunas Unnamed
    df = df.loc[:, ~df.columns.astype(str).str.contains("Unnamed")]

    # reset index
    df = df.reset_index(drop=True)

    st.success(f"✔ Cabeçalho encontrado na linha {linha_cab+1} e corrigido.")
    return df


# ============================================================
# VALIDAR COLUNAS
# ============================================================
def validar(df, esperado, nome_aba):
    st.subheader(f"📌 Validação da aba {nome_aba}")

    col_df = [c.strip() for c in df.columns]

    faltando = [c for c in esperado if c not in col_df]
    extras = [c for c in col_df if c not in esperado]

    if faltando:
        st.error("❌ COLUNAS FALTANDO:")
        st.write(faltando)
    else:
        st.success("✔ Todas as colunas obrigatórias estão presentes.")

    if extras:
        st.warning("⚠ COLUNAS EXTRAS:")
        st.write(extras)

    st.dataframe(df)

    return df


# ============================================================
# CONVERSÃO DE VALORES MONETÁRIOS
# ============================================================
def converter_moeda(df, colunas):
    for c in colunas:
        if c in df.columns:
            try:
                df[c] = (
                    df[c]
                    .astype(str)
                    .str.replace("R$", "", regex=False)
                    .str.replace(".", "", regex=False)
                    .str.replace(",", ".", regex=False)
                )
                df[c] = pd.to_numeric(df[c], errors="coerce")
            except:
                st.error(f"Erro ao converter moeda na coluna {c}")
    return df


# ============================================================
# PROCESSAR TODAS AS ABAS
# ============================================================
dfs = {}

for aba in colunas_esperadas.keys():

    if aba not in abas:
        st.error(f"❌ A aba {aba} não existe na planilha!")
        continue

    # Carregar bruto
    bruto = pd.read_excel(URL_PLANILHA, sheet_name=aba, header=None)

    # Corrigir cabeçalho
    limpo = limpar_aba(bruto, aba)

    if limpo is None:
        continue

    # Validar colunas
    validado = validar(limpo, colunas_esperadas[aba], aba)

    # Conversão de moedas
    if aba == "ESTOQUE":
        validado = converter_moeda(validado, ["Media C. UNITARIO", "Valor Venda Sugerido"])
    elif aba == "VENDAS":
        validado = converter_moeda(validado, ["VALOR VENDA", "VALOR TOTAL", "MEDIA CUSTO UNITARIO", "LUCRO UNITARIO"])
    elif aba == "COMPRAS":
        validado = converter_moeda(validado, ["CUSTO UNITÁRIO", "CUSTO TOTAL"])

    st.success(f"✔ Aba {aba} processada com sucesso!")
    dfs[aba] = validado

st.success("🎉 Processamento concluído. Se tudo estiver verde, já podemos montar o dashboard!")
