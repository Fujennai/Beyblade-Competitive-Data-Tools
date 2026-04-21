import streamlit as st
import pandas as pd
import os
import numpy as np
from collections import Counter

# ----------------------------
# History
# ----------------------------

def load_history():
    files = sorted(os.listdir("history"))
    dfs = []

    for file in files:
        if file.endswith(".csv"):
            df = pd.read_csv(f"history/{file}")
            df["fecha"] = file.replace("beyblade_stats_", "").replace(".csv", "")
            dfs.append(df)

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()


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
    return pd.read_csv("beyblade_stats.csv")


df_main = load_data()


# ----------------------------
# Separar Blade / Assist
# ----------------------------

def detectar_prefijos(df):
    posibles = []

    for blade in df["Blade"]:
        partes = blade.split()
        if len(partes) >= 3:
            posibles.append(" ".join(partes[:-1]))

    conteo = Counter(posibles)
    return {p for p, c in conteo.items() if c >= 2}


def separar_blade(blade, prefijos_validos):
    partes = blade.split()

    if len(partes) >= 3:
        prefijo = " ".join(partes[:-1])
        if prefijo in prefijos_validos:
            return prefijo, partes[-1]

    return blade, None


prefijos_validos = detectar_prefijos(df_main)

df_main[["Blade Base", "Assist Blade"]] = df_main["Blade"].apply(
    lambda x: pd.Series(separar_blade(x, prefijos_validos))
)


# ----------------------------
# Helpers
# ----------------------------

def mostrar_top10(df, nombre):
    st.subheader(f"Top 10 {nombre}")

    if df.empty:
        st.warning("No hay datos con ese filtro")
        return

    df_sorted = df.sort_values(by="Wilson Score", ascending=False).head(10)

    columnas_ocultar = ["Blade Base", "Assist Blade", "Eficiencia"]

    df_display = df_sorted.drop(
        columns=[c for c in columnas_ocultar if c in df_sorted.columns]
    )

    st.dataframe(df_display, use_container_width=True, hide_index=True)


def calcular_agregados(df):
    df_blade = df.groupby("Blade")[["Wins", "Losses", "Partidas"]].sum().reset_index()
    df_ratchet = df.groupby("Ratchet")[["Wins", "Losses", "Partidas"]].sum().reset_index()
    df_bit = df.groupby("Bit")[["Wins", "Losses", "Partidas"]].sum().reset_index()

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

    df_history = load_history()

    st.info(
        "¿Qué es la Wilson Score?\n\n"
        "La Wilson score estima la fiabilidad de un winrate teniendo en cuenta "
        "el número de partidas."
    )

    # Slider
    min_partidas = st.slider(
        "Mínimo de partidas",
        min_value=0,
        max_value=int(df_main["Partidas"].max()),
        value=50,
        step=10
    )

    # Filtros
    st.subheader("🔍 Filtros")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        blade_base_filter = st.selectbox(
            "Blade Base",
            ["Todos"] + sorted(df_main["Blade Base"].dropna().unique())
        )

    with col2:
        assist_filter = st.selectbox(
            "Assist Blade",
            ["Todos"] + sorted(df_main["Assist Blade"].dropna().unique())
        )

    with col3:
        ratchet_filter = st.selectbox(
            "Ratchet",
            ["Todos"] + sorted(df_main["Ratchet"].dropna().unique())
        )

    with col4:
        bit_filter = st.selectbox(
            "Bit",
            ["Todos"] + sorted(df_main["Bit"].dropna().unique())
        )

    # Filtrado
    df_filtered = df_main.copy()
    df_filtered = df_filtered[df_filtered["Partidas"] >= min_partidas]

    if blade_base_filter != "Todos":
        df_filtered = df_filtered[df_filtered["Blade Base"] == blade_base_filter]

    if assist_filter != "Todos":
        df_filtered = df_filtered[df_filtered["Assist Blade"] == assist_filter]

    if ratchet_filter != "Todos":
        df_filtered = df_filtered[df_filtered["Ratchet"] == ratchet_filter]

    if bit_filter != "Todos":
        df_filtered = df_filtered[df_filtered["Bit"] == bit_filter]

    # Agregados
    df_blade, df_ratchet, df_bit = calcular_agregados(df_filtered)

    mostrar_top10(df_filtered, "Combos")

    st.divider()

    col1, col2, col3 = st.columns(3)

    with col1:
        mostrar_top10(df_blade, "Blades")

    with col2:
        mostrar_top10(df_ratchet, "Ratchets")

    with col3:
        mostrar_top10(df_bit, "Bits")

    # ----------------------------
    # Evolución
    # ----------------------------

    st.subheader("📈 Evolución de un combo")

    df_top = df_filtered.sort_values(by="Wilson Score", ascending=False).head(1)

    blade_options = sorted(df_history["Blade"].dropna().unique())
    ratchet_options = sorted(df_history["Ratchet"].dropna().unique())
    bit_options = sorted(df_history["Bit"].dropna().unique())

    default_blade = df_top.iloc[0]["Blade"] if not df_top.empty else blade_options[0]
    default_ratchet = df_top.iloc[0]["Ratchet"] if not df_top.empty else ratchet_options[0]
    default_bit = df_top.iloc[0]["Bit"] if not df_top.empty else bit_options[0]

    col1, col2, col3 = st.columns(3)

    blade_sel = col1.selectbox("Blade", blade_options, index=blade_options.index(default_blade))
    ratchet_sel = col2.selectbox("Ratchet", ratchet_options, index=ratchet_options.index(default_ratchet))
    bit_sel = col3.selectbox("Bit", bit_options, index=bit_options.index(default_bit))

    df_combo = df_history[
        (df_history["Blade"] == blade_sel) &
        (df_history["Ratchet"] == ratchet_sel) &
        (df_history["Bit"] == bit_sel)
    ]

    if not df_combo.empty:
        df_combo = df_combo.sort_values("fecha")
        df_combo_grouped = df_combo.groupby("fecha").agg({"Win %": "mean"})
        st.line_chart(df_combo_grouped)

    # ----------------------------
    # Trending Score
    # ----------------------------

    st.subheader("🔥 Trending Combos (Score)")
    st.caption("Ranking basado en crecimiento relativo, uso y winrate")

    if not df_history.empty:

        df_history["combo"] = (
            df_history["Blade"] + " | " +
            df_history["Ratchet"] + " | " +
            df_history["Bit"]
        )

        df_sorted = df_history.sort_values("fecha")

        latest = df_sorted.groupby("combo").tail(1)
        previous = df_sorted.groupby("combo").nth(-2)

        merged = latest.merge(previous, on="combo", suffixes=("_new", "_old"))

        merged["delta_partidas"] = merged["Partidas_new"] - merged["Partidas_old"]

        merged["growth_pct"] = (
            merged["delta_partidas"] / merged["Partidas_old"]
        ).replace([np.inf, -np.inf], 0).fillna(0)

        merged["trending_score"] = (
            merged["growth_pct"] *
            np.log1p(merged["Partidas_new"]) *
            (merged["Win %_new"] / 100)
        )

        top_trending = merged.sort_values("trending_score", ascending=False).head(10)

        top_trending["Crecimiento (%)"] = (top_trending["growth_pct"] * 100).round(1)
        top_trending["Winrate (%)"] = top_trending["Win %_new"].round(1)

        st.dataframe(
            top_trending[[
                "combo",
                "Crecimiento (%)",
                "Winrate (%)",
                "trending_score"
            ]].rename(columns={
                "combo": "Combo",
                "trending_score": "Trending Score"
            }),
            use_container_width=True,
            hide_index=True
        )
