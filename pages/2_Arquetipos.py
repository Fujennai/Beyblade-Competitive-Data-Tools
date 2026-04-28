import streamlit as st
import plotly.express as px

from data.loader import load_data

st.set_page_config(layout="wide")

st.title("🧠 Análisis del META")

# ----------------------------
# Explicación
# ----------------------------

st.info(
    "Mapa del rendimiento real de los combos.\n\n"
    "➡️ Eje X = daño infligido (Pts Ganados/Combate)\n"
    "⬇️ Eje Y = daño recibido (invertido → abajo es mejor)\n"
    "🎨 Color = eficiencia global\n"
    "🔵 Tamaño = número de partidas (fiabilidad)"
)

# ----------------------------
# Datos
# ----------------------------

df = load_data()

# ----------------------------
# Filtros
# ----------------------------

col1, col2 = st.columns(2)

with col1:
    min_partidas = st.slider(
        "Mínimo de partidas",
        0,
        int(df["Partidas"].max()),
        50
    )

with col2:
    min_winrate = st.slider(
        "Winrate mínimo (%)",
        0,
        100,
        0
    )

df_filtered = df.copy()

df_filtered = df_filtered[df_filtered["Partidas"] >= min_partidas]
df_filtered = df_filtered[df_filtered["Win %"] >= min_winrate]

st.caption(f"{len(df_filtered)} combos tras filtros")

# ----------------------------
# Mapa de eficiencia
# ----------------------------

st.subheader("🗺️ Mapa de eficiencia del META")

fig = px.scatter(
    df_filtered,
    x="Pts Ganados/Combate",
    y="Pts Cedidos/Combate",
    size="Partidas",
    color="Eficiencia",
    color_continuous_scale="RdYlGn",
    hover_data=[
        "Blade",
        "Ratchet",
        "Bit",
        "Win %",
        "Partidas",
        "Eficiencia"
    ],
    opacity=0.7
)

fig.update_layout(
    xaxis_title="Daño infligido",
    yaxis_title="Daño recibido"
)

# invertir eje Y (clave)
fig.update_yaxes(autorange="reversed")

st.plotly_chart(fig, use_container_width=True)

st.caption(
    "📌 Abajo-derecha = zona óptima (alto daño, bajo daño recibido)\n"
    "📌 Tamaño grande = datos fiables\n"
    "📌 Color verde = alta eficiencia global"
)

# ----------------------------
# Ranking
# ----------------------------

st.subheader("🏆 Ranking de combos")

df_ranked = df_filtered.sort_values("Eficiencia", ascending=False)

st.dataframe(
    df_ranked[[
        "Blade",
        "Ratchet",
        "Bit",
        "Partidas",
        "Win %",
        "Eficiencia",
        "Pts Ganados/Combate",
        "Pts Cedidos/Combate"
    ]],
    use_container_width=True,
    hide_index=True
)