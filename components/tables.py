import streamlit as st

def mostrar_top10(df, nombre):

    st.subheader(f"Top 10 {nombre}")

    if df.empty:
        st.warning("No hay datos")
        return

    df_sorted = df.sort_values(by="Wilson Score", ascending=False).head(10)

    st.dataframe(df_sorted, use_container_width=True, hide_index=True)