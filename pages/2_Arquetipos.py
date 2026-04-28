import streamlit as st
import plotly.express as px

from data.loader import load_data

st.set_page_config(layout="wide")

st.title("🧠 Arquetipos del META (scoring real)")

# ----------------------------
# Explicación
# ----------------------------

st.info(
    "Clasificación basada en el sistema de puntuación.\n\n"
    "➡️ X = tipo de victoria\n"
    "⬇️ Y = tipo de derrota\n\n"
    "Puedes analizar cómo gana y cómo pierde cada combo."
)

# ----------------------------
# Datos
# ----------------------------

df = load_data()

# ----------------------------
# Filtros base (fijos)
# ----------------------------

min_partidas = 10
min_winrate = 50

df = df[df["Partidas"] >= min_partidas]
df = df[df["Win %"] >= min_winrate]

# ----------------------------
# Clasificación scoring
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

df["tipo_victoria"] = df["Pts Ganados/Combate"].apply(categorizar)
df["tipo_derrota"] = df["Pts Cedidos/Combate"].apply(categorizar)

# ----------------------------
# Labels
# ----------------------------

map_victoria = {
    0: "0 - No gana",
    1: "1 - Spin finish",
    2: "2 - Burst/Over",
    3: "3 - Xtreme"
}

map_derrota = {
    0: "0 - No pierde",
    1: "1 - Pierde spin",
    2: "2 - Pierde burst/over",
    3: "3 - Pierde xtreme"
}

df["victoria_label"] = df["tipo_victoria"].map(map_victoria)
df["derrota_label"] = df["tipo_derrota"].map(map_derrota)

# ----------------------------
# Filtros dependientes (pieza)
# ----------------------------

st.subheader("🔍 Filtros por piezas")

col1, col2, col3 = st.columns(3)

df_temp = df.copy()

with col1:
    blade_options = sorted(df_temp["Blade"].unique())
    blade_sel = st.selectbox("Blade", ["Todos"] + blade_options)

if blade_sel != "Todos":
    df_temp = df_temp[df_temp["Blade"] == blade_sel]

with col2:
    ratchet_options = sorted(df_temp["Ratchet"].unique())
    ratchet_sel = st.selectbox("Ratchet", ["Todos"] + ratchet_options)

if ratchet_sel != "Todos":
    df_temp = df_temp[df_temp["Ratchet"] == ratchet_sel]

with col3:
    bit_options = sorted(df_temp["Bit"].unique())
    bit_sel = st.selectbox("Bit", ["Todos"] + bit_options)

if bit_sel != "Todos":
    df_temp = df_temp[df_temp["Bit"] == bit_sel]

df_filtered = df_temp.copy()

# ----------------------------
# Filtros de arquetipo
# ----------------------------

st.subheader("🎯 Filtros de arquetipo")

col1, col2 = st.columns(2)

with col1:
    victorias = ["Todos"] + sorted(df_filtered["victoria_label"].unique())
    victoria_sel = st.selectbox("Arquetipo de victoria", victorias)

with col2:
    derrotas = ["Todos"] + sorted(df_filtered["derrota_label"].unique())
    derrota_sel = st.selectbox("Arquetipo de derrota", derrotas)

if victoria_sel != "Todos":
    df_filtered = df_filtered[df_filtered["victoria_label"] == victoria_sel]

if derrota_sel != "Todos":
    df_filtered = df_filtered[df_filtered["derrota_label"] == derrota_sel]

# ----------------------------
# Selector de color
# ----------------------------

st.subheader("🎨 Color del gráfico")

color_mode = st.radio(
    "Colorear por:",
    ["Tipo de victoria", "Tipo de derrota"]
)

color_map_victoria = {
    0: "#aaaaaa",
    1: "#2ecc71",
    2: "#f1c40f",
    3: "#e74c3c"
}

color_map_derrota = {
    0: "#2ecc71",
    1: "#3498db",
    2: "#f1c40f",
    3: "#e74c3c"
}

color_col = "tipo_victoria"
color_map = color_map_victoria

if color_mode == "Tipo de derrota":
    color_col = "tipo_derrota"
    color_map = color_map_derrota

# ----------------------------
# Gráfico
# ----------------------------

st.subheader("🗺️ Mapa de arquetipos")

fig = px.scatter(
    df_filtered,
    x="Pts Ganados/Combate",
    y="Pts Cedidos/Combate",
    color=color_col,
    color_discrete_map=color_map,
    hover_data=[
        "Blade",
        "Ratchet",
        "Bit",
        "Win %",
        "Partidas",
        "victoria_label",
        "derrota_label"
    ],
    opacity=0.7
)

fig.update_traces(marker=dict(size=6))

fig.update_layout(
    xaxis_title="Puntos ganados por combate",
    yaxis_title="Puntos cedidos por combate",
)

fig.update_yaxes(autorange="reversed")

st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# Tabla
# ----------------------------

st.subheader("📊 Datos")

st.dataframe(
    df_filtered[[
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