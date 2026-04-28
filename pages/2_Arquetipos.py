import streamlit as st
import plotly.express as px

from data.loader import load_data

st.set_page_config(layout="wide")

st.title("🧠 Arquetipos del META (basados en scoring)")

# ----------------------------
# Explicación
# ----------------------------

st.info(
    "Los arquetipos se derivan directamente del sistema de puntuación.\n\n"
    "➡️ Eje X = puntos que ganas cuando ganas (tipo de victoria)\n"
    "⬇️ Eje Y = puntos que cedes cuando pierdes (tipo de derrota)\n\n"
    "Esto permite identificar estilos reales:\n"
    "- Spin finish → defensivo\n"
    "- Burst / Over → balance/agresivo\n"
    "- Xtreme → muy agresivo"
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
# Clasificación por scoring
# ----------------------------

def categorizar(valor):
    if valor < 0.5:
        return 0
    elif valor < 1.5:
        return 1
    elif valor < 2.5:
        return 2
    else:
        return 3

df_filtered["tipo_victoria"] = df_filtered["Pts Ganados/Combate"].apply(categorizar)
df_filtered["tipo_derrota"] = df_filtered["Pts Cedidos/Combate"].apply(categorizar)

# ----------------------------
# Etiquetas legibles
# ----------------------------

map_victoria = {
    0: "❌ No gana",
    1: "🛡️ Spin finish",
    2: "⚖️ Burst/Over",
    3: "🔥 Xtreme"
}

map_derrota = {
    0: "🏆 Casi no pierde",
    1: "🛡️ Pierde por spin",
    2: "⚖️ Pierde por burst/over",
    3: "🔥 Pierde por xtreme"
}

df_filtered["victoria_label"] = df_filtered["tipo_victoria"].map(map_victoria)
df_filtered["derrota_label"] = df_filtered["tipo_derrota"].map(map_derrota)

# ----------------------------
# Arquetipo combinado
# ----------------------------

df_filtered["arquetipo"] = (
    df_filtered["victoria_label"] + " / " + df_filtered["derrota_label"]
)

# ----------------------------
# Gráfico principal
# ----------------------------

st.subheader("🗺️ Mapa de arquetipos")

fig = px.scatter(
    df_filtered,
    x="Pts Ganados/Combate",
    y="Pts Cedidos/Combate",
    color="tipo_victoria",  # color por estilo de ataque
    hover_data=[
        "Blade",
        "Ratchet",
        "Bit",
        "Win %",
        "Partidas",
        "arquetipo"
    ],
    opacity=0.7
)

fig.update_traces(marker=dict(size=6))

fig.update_layout(
    xaxis_title="Puntos ganados por combate",
    yaxis_title="Puntos cedidos por combate",
    legend_title="Tipo de victoria"
)

# invertir eje Y
fig.update_yaxes(autorange="reversed")

st.plotly_chart(fig, use_container_width=True)

st.caption(
    "📌 Derecha = tipo de victoria más agresivo\n"
    "📌 Abajo = pierde menos (más sólido)\n"
    "📌 Cada punto tiene un arquetipo basado en cómo gana y pierde"
)

# ----------------------------
# Filtro por arquetipo
# ----------------------------

st.subheader("🔍 Filtrar por arquetipo")

arquetipos = ["Todos"] + sorted(df_filtered["arquetipo"].unique())

arquetipo_sel = st.selectbox("Selecciona arquetipo", arquetipos)

if arquetipo_sel != "Todos":
    df_view = df_filtered[df_filtered["arquetipo"] == arquetipo_sel]
else:
    df_view = df_filtered

# ----------------------------
# Tabla
# ----------------------------

st.subheader("📊 Combos")

st.dataframe(
    df_view[[
        "Blade",
        "Ratchet",
        "Bit",
        "Partidas",
        "Win %",
        "victoria_label",
        "derrota_label"
    ]],
    use_container_width=True,
    hide_index=True
)