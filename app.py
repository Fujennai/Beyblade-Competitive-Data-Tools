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
    return df_main


df_main = load_data()

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


def calcular_agregados(df):
    df_blade = (
        df.groupby("Blade")[["Wins", "Losses", "Partidas"]]
        .sum()
        .reset_index()
    )

    df_ratchet = (
        df.groupby("Ratchet")[["Wins", "Losses", "Partidas"]]
        .sum()
        .reset_index()
    )

    df_bit = (
        df.groupby("Bit")[["Wins", "Losses", "Partidas"]]
        .sum()
        .reset_index()
    )

    # Wilson Score
    def wilson(w, n, z=1.96):
        if n == 0:
            return 0
        p = w / n
        return (p + z**2/(2*n) - z*((p*(1-p)+z**2/(4*n))/n)**0.5) / (1 + z**2/n)

    for df_ in [df_blade, df_ratchet, df_bit]:
        df_["Wilson Score"] = df_.apply(
            lambda row: wilson(row["Wins"], row["Partidas"]), axis=1
        )

    return df_blade, df_ratchet, df_bit


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
        "La Wilson score estima la fiabilidad de un winrate teniendo en cuenta "
        "el número de partidas. Penaliza muestras pequeñas."
    )

    # ----------------------------
    # Slider
    # ----------------------------

    min_partidas = st.slider(
        "Mínimo de partidas",
        min_value=0,
        max_value=int(df_main["Partidas"].max()),
        value=50,
        step=10
    )

    # ----------------------------
    # Filtros globales
    # ----------------------------

    st.subheader("🔍 Filtros")

    col1, col2, col3 = st.columns(3)

    with col1:
        blade_filter = st.selectbox(
            "Blade",
            ["Todos"] + sorted(df_main["Blade"].dropna().unique())
        )

    with col2:
        ratchet_filter = st.selectbox(
            "Ratchet",
            ["Todos"] + sorted(df_main["Ratchet"].dropna().unique())
        )

    with col3:
        bit_filter = st.selectbox(
            "Bit",
            ["Todos"] + sorted(df_main["Bit"].dropna().unique())
        )

    st.caption(f"Mostrando datos con al menos {min_partidas} partidas")

    # ----------------------------
    # Filtrado global
    # ----------------------------

    df_filtered = df_main.copy()

    # Partidas mínimas
    df_filtered = df_filtered[df_filtered["Partidas"] >= min_partidas]

    # Filtros por piezas
    if blade_filter != "Todos":
        df_filtered = df_filtered[df_filtered["Blade"] == blade_filter]

    if ratchet_filter != "Todos":
        df_filtered = df_filtered[df_filtered["Ratchet"] == ratchet_filter]

    if bit_filter != "Todos":
        df_filtered = df_filtered[df_filtered["Bit"] == bit_filter]

    # ----------------------------
    # Agregados dinámicos
    # ----------------------------

    df_blade, df_ratchet, df_bit = calcular_agregados(df_filtered)

    # ----------------------------
    # UI
    # ----------------------------

    # Combos
    mostrar_top10(df_filtered, "Combos")

    st.divider()

    # 3 columnas
    col1, col2, col3 = st.columns(3)

    with col1:
        mostrar_top10(df_blade, "Blades")

    with col2:
        mostrar_top10(df_ratchet, "Ratchets")

    with col3:
        mostrar_top10(df_bit, "Bits")
