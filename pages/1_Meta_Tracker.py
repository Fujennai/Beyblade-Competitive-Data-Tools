import streamlit as st
st.set_page_config(layout="wide")
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
# Explicación Wilson Score
# ----------------------------

st.info(
    "📊 La Wilson Score ajusta el winrate según el número de partidas.\n\n"
    "Un combo con 100% de victorias en 2 partidas no es tan fiable "
    "como uno con 70% en 500 partidas.\n\n"
    "Esto permite detectar combinaciones realmente consistentes "
    "y evitar resultados inflados por muestras pequeñas."
)

with st.expander("ℹ️ Explicación detallada de la Wilson Score"):

    st.markdown("""
La Wilson Score es una métrica estadística utilizada para estimar
la fiabilidad real de un winrate.

En lugar de usar únicamente el porcentaje bruto de victorias,
también tiene en cuenta cuántas partidas se han jugado.

Esto evita que combinaciones con muy pocas partidas aparezcan
artificialmente como las mejores del META.

### Ejemplo

| Combo | Winrate | Partidas | Wilson Score |
|---|---|---|---|
| Combo A | 100% | 2 | ~34% |
| Combo B | 72% | 500 | ~68% |

Aunque el Combo A tiene un winrate perfecto,
la muestra es demasiado pequeña para considerarlo fiable.

La Wilson Score penaliza automáticamente este tipo de casos,
priorizando resultados más consistentes y representativos.
""")

# ----------------------------
# Filtros
# ----------------------------

st.subheader("🔍 Filtros")

# Slider primero
min_partidas = st.slider(
    "Mínimo de partidas",
    0,
    int(df_main["Partidas"].max()),
    0
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



