import streamlit as st
import pandas as pd
import numpy as np

from data.loader import load_data
from core.predictor import entrenar_modelo
from core.meta_hidden import generar_combos

st.set_page_config(layout="wide")

st.title("🧬 Descubridor de META oculto (robusto)")

df = load_data()

# ----------------------------
# Modelo cacheado
# ----------------------------

@st.cache_resource
def get_model(df):
    return entrenar_modelo(df)

model, columns = get_model(df)

# ----------------------------
# Generar combos nuevos
# ----------------------------

df_nuevos = generar_combos(df)

# limitar volumen
df_nuevos = df_nuevos.sample(min(2000, len(df_nuevos)), random_state=42)

# ----------------------------
# Encoding
# ----------------------------

df_encoded = pd.get_dummies(df_nuevos)
df_encoded = df_encoded.reindex(columns=columns, fill_value=0)

# volumen simulado
if "Partidas_log" in columns:
    df_encoded["Partidas_log"] = np.log1p(50)

# ----------------------------
# Scores de piezas (CLAVE)
# ----------------------------

from core.predictor import calcular_score_pieza

blade_dict = calcular_score_pieza(df, "Blade")
ratchet_dict = calcular_score_pieza(df, "Ratchet")
bit_dict = calcular_score_pieza(df, "Bit")

df_encoded["Blade_score"] = df_nuevos["Blade"].map(blade_dict)
df_encoded["Ratchet_score"] = df_nuevos["Ratchet"].map(ratchet_dict)
df_encoded["Bit_score"] = df_nuevos["Bit"].map(bit_dict)

# ----------------------------
# Predicción
# ----------------------------

df_nuevos["Win % predicho"] = model.predict(df_encoded) * 100

# ----------------------------
# Ranking final
# ----------------------------

df_nuevos = df_nuevos.sort_values("Win % predicho", ascending=False)

# ----------------------------
# UI
# ----------------------------

st.subheader("🏆 Mejores combos no explorados")

st.dataframe(
    df_nuevos.head(20),
    use_container_width=True,
    hide_index=True
)