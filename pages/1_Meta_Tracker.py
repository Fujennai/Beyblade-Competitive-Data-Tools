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
# Evolución
# ----------------------------

st.subheader("📈 Evolución")

if df_history.empty:
    st.warning("No hay histórico")
    st.stop()

df_hist_filtered, blade_h, ratchet_h, bit_h = filtros_dependientes(df_history, key_prefix="history")

if blade_h and ratchet_h and bit_h:

    df_combo = df_history[
        (df_history["Blade"] == blade_h) &
        (df_history["Ratchet"] == ratchet_h) &
        (df_history["Bit"] == bit_h)
    ]

    if not df_combo.empty:
        df_plot = df_combo.groupby("fecha").agg({"Win %": "mean"}).reset_index()
        plot_winrate(df_plot)
    else:
        st.warning("No hay datos para ese combo")

else:
    st.info("Selecciona un combo para ver su evolución")

st.divider()

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
    df_trending[["combo", "trending_score"]],
    use_container_width=True,
    hide_index=True
)