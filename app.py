import streamlit as st
import pandas as pd
from pathlib import Path

# ==============================
# ⚙️ CONFIGURAÇÃO
# ==============================
st.set_page_config(page_title="Visualização de Abas - Loja Importados", layout="wide")

st.markdown(
    """
    <style>
        body {background-color: #0e0e0e; color: #FFD700;}
        .stMarkdown h1, h2, h3, h4 {color: #FFD700;}
        .block-container {padding-top: 1rem;}
        .stDataFrame {background-color: #1a1a1a !important; color: #FFD700 !important;}
    </style>
    """,
    unsafe_allow_html=True
)

st.title("📘 Visualização das Abas - Loja Importados")

# ==============================
# 🔍 DETECTA CABEÇALHO AUTOMATICAMENTE
# ==============================
def detect_header(path, sheet_name):
    temp = pd.read_excel(path, sheet_name=sheet_name, header=None)
    for i in range(len(temp)):
        if "PRODUTO" in str(temp.iloc[i].values).upper():
            df = pd.read_excel(path, sheet_name=sheet_name, header=i)
            st.write(f"✅ Cabeçalho detectado na linha {i+1} da aba **{sheet_name}**")
            return df
    st.warning(f"⚠️ Nenhum cabeçalho com 'PRODUTO' detectado na aba **{sheet_name}**")
    return pd.read_excel(path, sheet_name=sheet_name)

# ==============================
# 🧽 LIMPEZA E FORMATAÇÃO
# ==============================
def limpar_e_formatar(df, aba):
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

    if aba == "ESTOQUE":
        for col in ["Media C. UNITARIO", "Valor Venda Sugerido"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                df[col] = df[col].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notna(x) else "")
    
    elif aba == "VENDAS":
        df = df.drop(columns=[c for c in df.columns if "OBS" in c.upper()], errors="ignore")
        for col in ["VALOR VENDA", "VALOR TOTAL", "MEDIA CUSTO UNITARIO", "LUCRO"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                df[col] = df[col].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notna(x) else "")
    
    elif aba == "COMPRAS":
        for col in ["CUSTO UNITÁRIO", "CUSTO TOTAL"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                df[col] = df[col].apply(lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if pd.notna(x) else "")
    
    return df

# ==============================
# 📂 LEITURA DO ARQUIVO
# ==============================
file_path = "LOJA IMPORTADOS.xlsx"

if not Path(file_path).exists():
    st.error("❌ O arquivo 'LOJA IMPORTADOS.xlsx' não foi encontrado no diretório atual.")
else:
    xls = pd.ExcelFile(file_path)
    abas_validas = ["ESTOQUE", "VENDAS", "COMPRAS"]
    abas_encontradas = [a for a in xls.sheet_names if a in abas_validas]

    st.write("📄 Abas encontradas:", abas_encontradas)

    for aba in abas_validas:
        if aba in abas_encontradas:
            st.subheader(f"📊 Aba: {aba}")
            df = detect_header(file_path, aba)
            df = limpar_e_formatar(df, aba)

            st.write("🧱 **Colunas detectadas:**", list(df.columns))
            st.dataframe(df.head(10))
            st.markdown("---")
        else:
            st.warning(f"❌ Aba '{aba}' não encontrada no arquivo.")
