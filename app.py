# ============================================================
# ========================= DASHBOARD =========================
# ============================================================

st.title("📊 Dashboard Geral – Gestão Loja Importados")

# Criar referências
estoque_df = dfs.get("ESTOQUE")
vendas_df  = dfs.get("VENDAS")
compras_df = dfs.get("COMPRAS")

# Ajeitar datas
if "DATA" in vendas_df.columns:
    vendas_df["DATA"] = pd.to_datetime(vendas_df["DATA"], errors="coerce")
if "DATA" in compras_df.columns:
    compras_df["DATA"] = pd.to_datetime(compras_df["DATA"], errors="coerce")

# ============================================================
# KPI – Indicadores Gerais
# ============================================================
st.subheader("📌 Indicadores Gerais")

col1, col2, col3, col4 = st.columns(4)

# Faturamento total
try:
    fat_total = vendas_df["VALOR TOTAL"].sum()
    col1.metric("💰 Faturamento Total", f"R$ {fat_total:,.2f}")
except:
    col1.metric("💰 Faturamento Total", "Erro")

# Lucro total
try:
    lucro_total = vendas_df["LUCRO UNITARIO"].sum()
    col2.metric("📈 Lucro Total", f"R$ {lucro_total:,.2f}")
except:
    col2.metric("📈 Lucro Total", "Erro")

# Ticket médio
try:
    ticket_medio = vendas_df["VALOR TOTAL"].mean()
    col3.metric("🧾 Ticket Médio", f"R$ {ticket_medio:,.2f}")
except:
    col3.metric("🧾 Ticket Médio", "Erro")

# Produtos cadastrados
try:
    total_produtos = estoque_df["PRODUTO"].nunique()
    col4.metric("📦 Produtos Cadastrados", total_produtos)
except:
    col4.metric("📦 Produtos Cadastrados", "Erro")

# ============================================================
# FILTROS
# ============================================================
st.subheader("🔎 Filtros")

produtos_lista = vendas_df["PRODUTO"].dropna().unique().tolist()
filtro_produto = st.multiselect("Filtrar produtos:", produtos_lista)

if filtro_produto:
    vendas_filtrado = vendas_df[vendas_df["PRODUTO"].isin(filtro_produto)]
else:
    vendas_filtrado = vendas_df.copy()

# ============================================================
# GRÁFICO – Faturamento por Data
# ============================================================
st.subheader("📈 Evolução do Faturamento")

try:
    fat_data = vendas_filtrado.groupby("DATA")["VALOR TOTAL"].sum().reset_index()
    fig = px.line(fat_data, x="DATA", y="VALOR TOTAL",
                  markers=True, title="Faturamento Diário")
    st.plotly_chart(fig, use_container_width=True)
except:
    st.error("Não foi possível gerar gráfico de faturamento diário.")

# ============================================================
# GRÁFICO – Top 10 Produtos Mais Vendidos
# ============================================================
st.subheader("🔥 Top 10 Produtos Mais Vendidos")

try:
    top10 = vendas_df.groupby("PRODUTO")["QTD"].sum().sort_values(ascending=False).head(10)
    fig = px.bar(top10, x=top10.index, y=top10.values,
                 title="Top 10 Produtos Mais Vendidos")
    st.plotly_chart(fig, use_container_width=True)
except:
    st.error("Erro ao gerar ranking de produtos.")

# ============================================================
# GRÁFICO – Produtos com Estoque Baixo
# ============================================================
st.subheader("🚨 Produtos com Estoque Baixo")

try:
    baixo = estoque_df[estoque_df["EM ESTOQUE"] < 5]
    fig = px.bar(baixo, x="PRODUTO", y="EM ESTOQUE",
                 title="Estoque Crítico (<5 unidades)")
    st.plotly_chart(fig, use_container_width=True)
except:
    st.error("Erro ao gerar gráfico de estoque crítico.")

# ============================================================
# GRÁFICO – Evolução dos Custos (COMPRAS)
# ============================================================
st.subheader("📉 Evolução dos Gastos em Compras")

try:
    comp = compras_df.groupby("DATA")["CUSTO TOTAL"].sum().reset_index()
    fig = px.line(comp, x="DATA", y="CUSTO TOTAL",
                  markers=True, title="Gastos com Compras")
    st.plotly_chart(fig, use_container_width=True)
except:
    st.error("Erro ao gerar gráfico de compras.")
