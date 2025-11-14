# ==============================
# Função para formatar valores monetários
# ==============================
def formatar_valor_reais(df, colunas):
    for col in colunas:
        if col in df.columns:
            df[col] = df[col].map(lambda x: f"R$ {x:,.2f}" if pd.notna(x) else "")
    return df

# ==============================
# Aba VENDAS — tabela completa filtrada
# ==============================
with tabs[0]:
    st.subheader("Vendas (período selecionado)")
    if vendas_filtradas.empty:
        st.info("Sem dados de vendas para o período selecionado.")
    else:
        df_show = vendas_filtradas.copy()
        df_show = df_show.dropna(axis=1, how='all')  # remove colunas totalmente NAN
        if "DATA" in df_show.columns:
            df_show["DATA"] = df_show["DATA"].dt.strftime("%d/%m/%y")  # formato compacto
        df_show = formatar_valor_reais(df_show, ["VALOR VENDA","VALOR TOTAL","MEDIA CUSTO UNITARIO","LUCRO UNITARIO"])
        st.dataframe(df_show, use_container_width=True)

# ==============================
# Aba TOP10 (VALOR)
# ==============================
with tabs[1]:
    st.subheader("Top 10 — por VALOR (R$)")
    if vendas_filtradas.empty:
        st.info("Sem dados de vendas para o período selecionado.")
    else:
        dfv = vendas_filtradas.copy()
        if "VALOR TOTAL" not in dfv.columns and "VALOR VENDA" in dfv.columns and "QTD" in dfv.columns:
            dfv["VALOR TOTAL"] = dfv["VALOR VENDA"].fillna(0.0) * dfv["QTD"].fillna(0)
        if "PRODUTO" in dfv.columns and "VALOR TOTAL" in dfv.columns:
            top_val = (dfv.groupby("PRODUTO")["VALOR TOTAL"].sum()
                       .reset_index().sort_values("VALOR TOTAL", ascending=False).head(10))
            top_val = formatar_valor_reais(top_val, ["VALOR TOTAL"])
            fig = px.bar(top_val, x="PRODUTO", y="VALOR TOTAL", text="VALOR TOTAL")
            fig.update_traces(textposition="inside")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(top_val, use_container_width=True)
        else:
            st.warning("Colunas necessárias (PRODUTO, VALOR TOTAL) não encontradas.")

# ==============================
# Aba TOP10 (QUANTIDADE) com labels no centro das barras
# ==============================
with tabs[2]:
    st.subheader("Top 10 — por QUANTIDADE")
    if vendas_filtradas.empty:
        st.info("Sem dados de vendas para o período selecionado.")
    else:
        dfv = vendas_filtradas.copy()
        if "QTD" not in dfv.columns and "QUANTIDADE" in dfv.columns:
            dfv["QTD"] = dfv["QUANTIDADE"]
        if "PRODUTO" in dfv.columns and "QTD" in dfv.columns:
            top_q = (dfv.groupby("PRODUTO")["QTD"].sum()
                     .reset_index()
                     .sort_values("QTD", ascending=False)
                     .head(10))
            top_q["QTD_TEXT"] = top_q["QTD"].astype(int).astype(str)
            fig2 = px.bar(top_q, x="PRODUTO", y="QTD", text="QTD_TEXT")
            fig2.update_traces(textposition="inside")
            st.plotly_chart(fig2, use_container_width=True)
            st.dataframe(top_q.drop(columns=["QTD_TEXT"]), use_container_width=True)
        else:
            st.warning("Colunas necessárias (PRODUTO, QTD) não encontradas.")

# ==============================
# Aba CONSULTAR ESTOQUE
# ==============================
with tabs[3]:
    st.subheader("Consulta completa do Estoque")
    if estoque_df.empty:
        st.info("Aba ESTOQUE não encontrada ou vazia.")
    else:
        df_e = estoque_df.copy()
        df_e = df_e.dropna(axis=1, how='all')  # remove colunas totalmente NAN
        # formatar valores
        df_e = formatar_valor_reais(df_e, ["Media C. UNITARIO","Valor Venda Sugerido"])
        if "EM ESTOQUE" in df_e.columns:
            df_e["EM ESTOQUE"] = df_e["EM ESTOQUE"].astype(int)
        st.dataframe(df_e.sort_values(by="PRODUTO").reset_index(drop=True), use_container_width=True)
