import streamlit as st

from data.loader import load_data
from core.predictor import predecir

st.set_page_config(layout="wide")

st.title("🔮 Predictor de rendimiento")

df = load_data()

col1, col2, col3 = st.columns(3)

blade   = col1.selectbox("Blade",   sorted(df["Blade"].unique()))
ratchet = col2.selectbox("Ratchet", sorted(df["Ratchet"].unique()))
bit     = col3.selectbox("Bit",     sorted(df["Bit"].unique()))

partidas = st.slider("Partidas esperadas", 10, 500, 50)

if st.button("Predecir rendimiento"):

    pred = predecir(blade, ratchet, bit, partidas)

    if pred is None:
        st.warning("Alguna de las piezas no tiene datos históricos suficientes.")
    else:
        st.metric("Winrate estimado", f"{pred}%")
        st.caption(
            "Estimación basada en el Wilson Score del combo "
            "ajustado por volumen de partidas."
        )