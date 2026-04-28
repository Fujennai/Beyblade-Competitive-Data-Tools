import streamlit as st
from data.loader import load_data
from core.predictor import entrenar_modelo, predecir

@st.cache_resource
def get_model(df):
    return entrenar_modelo(df)

st.set_page_config(layout="wide")

st.title("🔮 Predictor de rendimiento")

df = load_data()

model, columns = get_model(df)

col1, col2, col3 = st.columns(3)

blade = col1.selectbox("Blade", sorted(df["Blade"].unique()))
ratchet = col2.selectbox("Ratchet", sorted(df["Ratchet"].unique()))
bit = col3.selectbox("Bit", sorted(df["Bit"].unique()))

if st.button("Predecir rendimiento"):
    pred = predecir(model, columns, blade, ratchet, bit)

    st.metric("Winrate estimado", f"{pred}%")