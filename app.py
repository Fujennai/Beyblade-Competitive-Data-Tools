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
# Helper
# ----------------------------

def mostrar_top10(df, nombre):
    st.subheader(f"Top 10 {nombre}")

    if df.empty:
        st.warning("No hay datos con ese filtro")
        return

    df_sorted = df.sort_values(by="Wilson Score", ascending=False).head(10)
    st.dataframe(df_sorted, use_container_width=True, hide_index=True)


# ----------------------------
# Tabs
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

    # ----------------------------
    # Slider mínimo partidas
    # ----------------------------

    min_partidas = st.slider(
        "Mínimo de partidas",
        min_value=0,
        max_value=int(df_main["Partidas"].max()),
        value=50,
        step=10
    )

    # ----------------------------
    # Filtros
    # ----------------------------

    st.subheader("🔍 Filtros")

    col1, col2, col3 = st.columns(3)

    with col1:
        min_winrate = st.slider(
            "Winrate mínimo (%)",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=1.0
        )

    with col2:
        blade_filter = st.selectbox(
            "Blade",
            ["Todos"] + sorted(df_main["Blade"].dropna().unique().tolist())
        )

    with col3:
        search = st.text_input("Buscar combo")

    st.caption(f"Mostrando datos con al menos {min_partidas} partidas")

    # ----------------------------
    # Filtrado dataset principal
    # ----------------------------

    df_main_filtered = df_main.copy()

    # Partidas mínimas
    df_main_filtered = df_main_filtered[df_main_filtered["Partidas"] >= min_partidas]

    # Winrate mínimo
    df_main_filtered = df_main_filtered[df_main_filtered["Win %"] >= min_winrate]

    # Blade
    if blade_filter != "Todos":
        df_main_filtered = df_main_filtered[df_main_filtered["Blade"] == blade_filter]

    # Búsqueda
    if search:
        df_main_filtered = df_main_filtered[
            df_main_filtered.apply(lambda row: search.lower() in str(row).lower(), axis=1)
        ]

    # ----------------------------
    # Filtrado datasets agregados
    # ----------------------------

    df_blade_filtered = df_blade[df_blade["Partidas"] >= min_partidas]
    df_ratchet_filtered = df_ratchet[df_ratchet["Partidas"] >= min_partidas]
    df_bit_filtered = df_bit[df_bit["Partidas"] >= min_partidas]

    # ----------------------------
    # UI
    # ----------------------------

    # Combos (full width)
    mostrar_top10(df_main_filtered, "Combos")

    st.divider()

    # 3 columnas
    col1, col2, col3 = st.columns(3)

    with col1:
        mostrar_top10(df_blade_filtered, "Blades")

    with col2:
        mostrar_top10(df_ratchet_filtered, "Ratchets")

    with col3:
        mostrar_top10(df_bit_filtered, "Bits")
