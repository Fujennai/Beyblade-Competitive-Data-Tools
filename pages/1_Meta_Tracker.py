import streamlit as st
import pandas as pd

from data.loader import load_data, load_history
from core.metrics import calcular_agregados
from core.trending import calcular_trending
from components.charts import plot_winrate
from components.tables import mostrar_top10
from components.filters import filtros_dependientes


st.title("📊 META Tracker")

df_main = load_data()
df_history = load_history()

# ----------------------------
# Filtros
# ----------------------------

st.subheader("🔍 Filtros")

# Slider primero
min_partidas = st.slider(
    "Mínimo de partidas",
    0,
    int(df_main["Partidas"].max()),
    50
)

# Filtros dependientes (devuelven DF ya filtrado)
df_filtered, blade, ratchet, bit = filtros_dependientes(df_main, key_prefix="main")

# Aplicar filtro de partidas DESPUÉS
df_filtered = df_filtered[df_filtered["Partidas"] >= min_partidas]

# Info útil
st.caption(f"{len(df_filtered)} combinaciones encontradas")

st.divider()

# ----------------------------
# Top combos
# ----------------------------

mostrar_top10(df_filtered, "Combos")

df_blade, df_ratchet, df_bit = calcular_agregados(df_filtered)

col1, col2, col3 = st.columns(3)

with col1:
    mostrar_top10(df_blade, "Blades")

with col2:
    mostrar_top10(df_ratchet, "Ratchets")

with col3:
    mostrar_top10(df_bit, "Bits")

st.divider()

# ----------------------------
# Evolución (desde Trending)
# ----------------------------

st.subheader("📈 Evolución (Trending)")

df_trending = calcular_trending(df_history).head(10)

combo_sel = st.selectbox(
    "Selecciona un combo trending",
    df_trending["combo"].tolist(),
    key="evo_trending"
)

if combo_sel:

    blade_h, ratchet_h, bit_h = combo_sel.split(" | ")

    df_combo = df_history[
        (df_history["Blade"] == blade_h) &
        (df_history["Ratchet"] == ratchet_h) &
        (df_history["Bit"] == bit_h)
    ]

    if not df_combo.empty:

        df_plot = df_combo.groupby("fecha").agg({"Win %": "mean"}).reset_index()

        # métrica de cambio
        delta = df_plot["Win %"].iloc[-1] - df_plot["Win %"].iloc[0]

        st.metric(
            "Cambio total de winrate",
            f"{df_plot['Win %'].iloc[-1]:.2f}%",
            delta=f"{delta:.2f}%"
        )

        plot_winrate(df_plot, key="chart_trending")

# ----------------------------
# Evolución (solo con variación)
# ----------------------------

st.subheader("📈 Evolución (Combos con cambios reales)")

df_history["combo"] = (
    df_history["Blade"] + " | " +
    df_history["Ratchet"] + " | " +
    df_history["Bit"]
)

# calcular variación
df_var = df_history.groupby("combo")["Win %"].agg(lambda x: x.max() - x.min())

# umbral configurable
threshold = st.slider("Variación mínima (%)", 0.0, 10.0, 2.0)

combos_interesantes = df_var[df_var > threshold].index.tolist()

if combos_interesantes:

    combo_sel = st.selectbox(
        "Selecciona combo con variación",
        combos_interesantes,
        key="evo_variation"
    )

    blade_h, ratchet_h, bit_h = combo_sel.split(" | ")

    df_combo = df_history[
        (df_history["Blade"] == blade_h) &
        (df_history["Ratchet"] == ratchet_h) &
        (df_history["Bit"] == bit_h)
    ]

    df_plot = df_combo.groupby("fecha").agg({"Win %": "mean"}).reset_index()

    plot_winrate(df_plot, key="chart_variation")

else:
    st.warning("No hay combos con esa variación")

# ----------------------------
# Evolución (volatilidad)
# ----------------------------

st.subheader("📈 Evolución (Más volátiles)")

df_history["combo"] = (
    df_history["Blade"] + " | " +
    df_history["Ratchet"] + " | " +
    df_history["Bit"]
)

# calcular desviación estándar
df_vol = df_history.groupby("combo")["Win %"].std().sort_values(ascending=False)

top_vol = df_vol.head(15).index.tolist()

combo_sel = st.selectbox(
    "Selecciona combo volátil",
    top_vol,
    key="evo_volatility"
)

blade_h, ratchet_h, bit_h = combo_sel.split(" | ")

df_combo = df_history[
    (df_history["Blade"] == blade_h) &
    (df_history["Ratchet"] == ratchet_h) &
    (df_history["Bit"] == bit_h)
]

df_plot = df_combo.groupby("fecha").agg({"Win %": "mean"}).reset_index()

plot_winrate(df_plot, key="chart_volatility")

# ----------------------------
# Trending
# ----------------------------

st.subheader("🔥 Trending")

st.info(
    "¿Qué significa el Trending Score?\n\n"
    "Este ranking mide qué combos están ganando relevancia recientemente.\n\n"
    "Se calcula combinando:\n"
    "- 📈 Crecimiento en número de partidas (uso)\n"
    "- 🎯 Winrate actual\n"
    "- ⚖️ Volumen total de partidas\n\n"
    "👉 Un valor alto indica que el combo está creciendo rápido, se usa bastante y además tiene buen rendimiento.\n\n"
    "⚠️ No significa necesariamente que sea el mejor combo, sino el que está más 'de moda' ahora mismo."
)

df_trending = calcular_trending(df_history).head(10)

st.dataframe(
    df_trending[["combo", "trending_score"]].rename(columns={
        "combo": "Combo",
        "trending_score": "Trending Score (popularidad reciente)"
    }),
    use_container_width=True,
    hide_index=True
)