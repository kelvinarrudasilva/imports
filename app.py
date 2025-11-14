# ----------------------------
# FUNÇÃO: limpar colunas vazias e formatar valores monetários
# ----------------------------
def preparar_df(df, moedas=None, inteiros=None):
    """
    Remove colunas totalmente vazias e formata valores monetários e inteiros
    moedas: lista de colunas a formatar como R$
    inteiros: lista de colunas a formatar como inteiro
    """
    df = df.dropna(axis=1, how="all")  # remover colunas totalmente vazias

    if moedas:
        for c in moedas:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    if inteiros:
        for c in inteiros:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    return df

# ----------------------------
# PREPARAR DFs
# ----------------------------
if "ESTOQUE" in dfs:
    estoque_df = preparar_df(
        dfs["ESTOQUE"],
        moedas=["Media C. UNITARIO","Valor Venda Sugerido"],
        inteiros=["EM ESTOQUE","VENDAS"]
    )

if "VENDAS" in dfs:
    vendas_filtradas = filtrar_mes(dfs["VENDAS"], mes_selecionado)
    vendas_filtradas = preparar_df(
        vendas_filtradas,
        moedas=["VALOR VENDA","VALOR TOTAL","MEDIA CUSTO UNITARIO","LUCRO UNITARIO"],
        inteiros=["QTD"]
    )

if "COMPRAS" in dfs:
    compras_filtradas = filtrar_mes(dfs["COMPRAS"], mes_selecionado)
    compras_filtradas = preparar_df(
        compras_filtradas,
        moedas=["CUSTO UNITÁRIO","CUSTO TOTAL (RECALC)"],
        inteiros=["QUANTIDADE"]
    )

# ----------------------------
# ABA CONSULTAR ESTOQUE
# ----------------------------
with tabs[3]:
    st.subheader("Consulta completa do Estoque")
    if estoque_df.empty:
        st.info("Aba ESTOQUE não encontrada ou vazia.")
    else:
        df_e = estoque_df.copy()
        # formatar valores monetários em R$
        for c in ["Media C. UNITARIO","Valor Venda Sugerido"]:
            if c in df_e.columns:
                df_e[c] = df_e[c].map(lambda x: f"R$ {x:,.2f}")
        st.dataframe(df_e.sort_values(by="PRODUTO").reset_index(drop=True), use_container_width=True)

# ----------------------------
# ABA VENDAS — tabela completa
# ----------------------------
with tabs[0]:
    st.subheader("Vendas (período selecionado)")
    if vendas_filtradas.empty:
        st.info("Sem dados de vendas para o período selecionado.")
    else:
        df_v = vendas_filtradas.copy()
        # formatar valores monetários
        for c in ["VALOR VENDA","VALOR TOTAL","MEDIA CUSTO UNITARIO","LUCRO UNITARIO"]:
            if c in df_v.columns:
                df_v[c] = df_v[c].map(lambda x: f"R$ {x:,.2f}")
        st.dataframe(df_v, use_container_width=True)

# ----------------------------
# ABA TOP10 — VALOR e LUCRO
# ----------------------------
with tabs[1]:
    st.subheader("Top 10 — por VALOR (R$)")
    if vendas_filtradas.empty:
        st.info("Sem dados de vendas para o período selecionado.")
    else:
        dfv = vendas_filtradas.copy()
        dfv["VALOR_TOTAL_NUM"] = dfv["VALOR TOTAL"].replace({"R\$ ": ""}, regex=True).astype(float)
        top_val = dfv.groupby("PRODUTO")["VALOR_TOTAL_NUM"].sum().reset_index().sort_values("VALOR_TOTAL_NUM", ascending=False).head(10)
        fig = px.bar(top_val, x="PRODUTO", y="VALOR_TOTAL_NUM",
                     text=top_val["VALOR_TOTAL_NUM"].map(lambda x: f"R$ {x:,.2f}"))
        fig.update_traces(textposition="inside")
        st.plotly_chart(fig, use_container_width=True)
        # Top 10 lucro
        if "LUCRO UNITARIO" in dfv.columns and "QTD" in dfv.columns:
            dfv["LUCRO_TOTAL"] = dfv["LUCRO UNITARIO"].replace({"R\$ ": ""}, regex=True).astype(float) * dfv["QTD"]
            top_lucro = dfv.groupby("PRODUTO")["LUCRO_TOTAL"].sum().reset_index().sort_values("LUCRO_TOTAL", ascending=False).head(10)
            fig2 = px.bar(top_lucro, x="PRODUTO", y="LUCRO_TOTAL",
                          text=top_lucro["LUCRO_TOTAL"].map(lambda x: f"R$ {x:,.2f}"))
            fig2.update_traces(textposition="inside")
            st.subheader("Top 10 — Lucro (R$)")
            st.plotly_chart(fig2, use_container_width=True)
