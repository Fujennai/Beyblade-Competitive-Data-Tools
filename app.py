import streamlit as st
import pandas as pd

# ----------------------------
# Configuración
# ----------------------------

st.set_page_config(page_title="Beyblade Analytics", layout="wide")

st.title("🏆 Beyblade Competitive Dashboard")

# ----------------------------
# Cargar datos
# ----------------------------

@st.cache_data
def load_data():
    df_main = pd.read_csv("beyblade_stats.csv")
    df_blade = pd.read_csv("blade_stats.csv")
    df_ratchet = pd.read_csv("ratchet_stats.csv")
    df_bit = pd.read_csv("bit_stats.csv")

    return df_main, df_blade, df_ratchet, df_bit


df_main, df_blade, df_ratchet, df_bit = load_data()

# ----------------------------
# Función helper
# ----------------------------

def mostrar_top10(df, nombre):
    df_sorted = df.sort_values(by="Wilson Score", ascending=False).head(10)

    st.subheader(f"Top 10 {nombre}")
    st.dataframe(df_sorted, use_container_width=True, hide_index=True)


# ----------------------------
# Tabs (solo una)
# ----------------------------

tab = st.tabs(["📊 META Tracker"])[0]

# ----------------------------
# Contenido
# ----------------------------

with tab:

    # Disclaimer
    st.info(
        "¿Qué es la Wilson Score?\n\n"
        "La Wilson score es una métrica estadística que permite estimar "
        "la fiabilidad de una proporción (como el winrate) teniendo en cuenta "
        "el número de partidas. Penaliza muestras pequeñas y evita rankings engañosos."
    )

    # Layout en grid (2x2)
    col1, col2 = st.columns(2)
    col3, col4 = st.columns(2)

    with col1:
        mostrar_top10(df_main, "Combos")

    with col2:
        mostrar_top10(df_blade, "Blades")

    with col3:
        mostrar_top10(df_ratchet, "Ratchets")

    with col4:
        mostrar_top10(df_bit, "Bits")
