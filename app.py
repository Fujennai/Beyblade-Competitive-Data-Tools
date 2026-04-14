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
    st.dataframe(df_sorted, use_container_width=True)


# ----------------------------
# Tabs
# ----------------------------

tabs = st.tabs([
    "🏅 Combos",
    "🧩 Blades",
    "⚙️ Ratchets",
    "🔘 Bits"
])

# ----------------------------
# Contenido
# ----------------------------

with tabs[0]:
    mostrar_top10(df_main, "Combos")

with tabs[1]:
    mostrar_top10(df_blade, "Blades")

with tabs[2]:
    mostrar_top10(df_ratchet, "Ratchets")

with tabs[3]:
    mostrar_top10(df_bit, "Bits")
