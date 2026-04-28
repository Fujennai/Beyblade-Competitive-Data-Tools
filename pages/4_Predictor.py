import streamlit as st

from data.loader import load_data
from core.predictor import entrenar_modelo, predecir

st.set_page_config(layout="wide")

st.title("🔮 Predictor de rendimiento (robusto)")

df = load_data()

# ----------------------------
# Cache del modelo
# ----------------------------

@st.cache_resource
def get_model(df):
    return entrenar_modelo(df)

model, columns = get_model(df)

# ----------------------------
# Inputs
# ----------------------------

col1, col2, col3 = st.columns(3)

blade = col1.selectbox("Blade", sorted(df["Blade"].unique()))
ratchet = col2.selectbox("Ratchet", sorted(df["Ratchet"].unique()))
bit = col3.selectbox("Bit", sorted(df["Bit"].unique()))

# volumen esperado
partidas = st.slider(
    "Partidas esperadas (confianza del modelo)",
    10,
    500,
    50
)

# ----------------------------
# Predicción
# ----------------------------

if st.button("Predecir rendimiento"):

    pred = predecir(model, columns, blade, ratchet, bit, partidas)

    st.metric("Winrate estimado (ajustado por fiabilidad)", f"{pred}%")

    st.caption(
        "Este valor tiene en cuenta la fiabilidad estadística del combo "
        "mediante Wilson Score y volumen de partidas."
    )