import streamlit as st
import plotly.express as px

from data.loader import load_data

st.set_page_config(layout="wide")

st.title("🧠 Análisis del comportamiento del META")

# ----------------------------
# Explicación
# ----------------------------

st.info(
    "Este gráfico muestra el comportamiento real de los combos en combate.\n\n"
    "➡️ Eje X = daño infligido (Pts Ganados/Combate)\n"
    "⬇️ Eje Y = daño recibido (invertido → abajo es mejor)\n\n"
    "El objetivo es identificar builds que hacen mucho daño y reciben poco."
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
# Gráfico principal
# ----------------------------

st.subheader("🗺️ Mapa de comportamiento del META")

fig = px.scatter(
    df_filtered,
    x="Pts Ganados/Combate",
    y="Pts Cedidos/Combate",
    hover_data=[
        "Blade",
        "Ratchet",
        "Bit",
        "Win %",
        "Partidas"
    ],
    opacity=0.6
)

# tamaño fijo para evitar ruido visual
fig.update_traces(marker=dict(size=6))

fig.update_layout(
    xaxis_title="Daño infligido",
    yaxis_title="Daño recibido"
)

# invertir eje Y (clave)
fig.update_yaxes(autorange="reversed")

st.plotly_chart(fig, use_container_width=True)

st.caption(
    "📌 Derecha = más daño\n"
    "📌 Abajo = menos daño recibido (mejor)\n"
    "📌 Zona óptima → abajo a la derecha"
)

# ----------------------------
# Ranking (secundario)
# ----------------------------

st.subheader("🏆 Ranking de combos")

df_ranked = df_filtered.sort_values("Win %", ascending=False)

st.dataframe(
    df_ranked[[
        "Blade",
        "Ratchet",
        "Bit",
        "Partidas",
        "Win %",
        "Pts Ganados/Combate",
        "Pts Cedidos/Combate"
    ]],
    use_container_width=True,
    hide_index=True
)