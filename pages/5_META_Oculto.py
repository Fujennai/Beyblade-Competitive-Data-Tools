import streamlit as st

from data.loader import load_data
from core.meta_hidden import predecir_combos_nuevos

st.set_page_config(layout="wide")

st.title("🧬 Descubridor de META oculto")

df = load_data()

df_nuevos = predecir_combos_nuevos(df, muestra=2000)

st.subheader("🏆 Mejores combos no explorados")

if df_nuevos.empty:
    st.warning("No se encontraron combos nuevos.")
else:
    st.dataframe(
        df_nuevos.head(20),
        use_container_width=True,
        hide_index=True
    )