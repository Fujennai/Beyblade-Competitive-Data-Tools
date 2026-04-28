import streamlit as st
from data.loader import load_data
from core.recommender import recomendar_builds

st.set_page_config(layout="wide")

st.title("🔧 Recomendador de Builds")

df = load_data()

st.info("Selecciona una pieza para recibir builds recomendadas basadas en uso y rendimiento.")

col1, col2, col3 = st.columns(3)

with col1:
    blade = st.selectbox("Blade", ["Todos"] + sorted(df["Blade"].unique()))

with col2:
    ratchet = st.selectbox("Ratchet", ["Todos"] + sorted(df["Ratchet"].unique()))

with col3:
    bit = st.selectbox("Bit", ["Todos"] + sorted(df["Bit"].unique()))

blade = None if blade == "Todos" else blade
ratchet = None if ratchet == "Todos" else ratchet
bit = None if bit == "Todos" else bit

df_rec = recomendar_builds(df, blade, ratchet, bit)

if df_rec.empty:
    st.warning("No hay datos suficientes")
else:
    st.dataframe(df_rec, use_container_width=True, hide_index=True)