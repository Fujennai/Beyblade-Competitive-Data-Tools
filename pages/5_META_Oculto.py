import streamlit as st
import pandas as pd

from data.loader import load_data
from core.predictor import entrenar_modelo
from core.meta_hidden import generar_combos

st.set_page_config(layout="wide")

st.title("🧬 Descubridor de META oculto")

df = load_data()

st.info("Explora combinaciones no utilizadas que podrían ser fuertes según el modelo.")

model, columns = entrenar_modelo(df)

df_nuevos = generar_combos(df)

# limitar tamaño (muy importante)
df_nuevos = df_nuevos.sample(min(2000, len(df_nuevos)), random_state=42)

# encoding
df_encoded = pd.get_dummies(df_nuevos)
df_encoded = df_encoded.reindex(columns=columns, fill_value=0)

df_nuevos["Win % predicho"] = model.predict(df_encoded)

df_nuevos = df_nuevos.sort_values("Win % predicho", ascending=False)

st.subheader("🏆 Mejores combos no explorados")

st.dataframe(
    df_nuevos.head(20),
    use_container_width=True,
    hide_index=True
)