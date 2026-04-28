import streamlit as st
import plotly.express as px

from data.loader import load_data

st.set_page_config(layout="wide")

st.title("🧠 Arquetipos del META (scoring real)")

# ----------------------------
# Explicación
# ----------------------------

st.info(
    "Análisis basado en el sistema de puntuación.\n\n"
    "➡️ X = tipo de victoria\n"
    "⬇️ Y = tipo de derrota (invertido → abajo es mejor)\n\n"
    "Puedes ver cómo gana y cómo pierde cada combo."
)

# ----------------------------
# Datos
# ----------------------------

df = load_data()

# ----------------------------
# Filtros base
# ----------------------------

df = df[df["Partidas"] >= 10]
df = df[df["Win %"] >= 50]

# ----------------------------
# Clasificación
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
    0: "Siempre pierde",
    1: "Spin finish",
    2: "Burst / Over",
    3: "Xtreme finish"
}

map_derrota = {
    0: "Siempre gana",
    1: "Pierde por spin",
    2: "Pierde por burst/over",
    3: "Pierde por xtreme"
}

df["victoria_label"] = df["tipo_victoria"].map(map_victoria)
df["derrota_label"] = df["tipo_derrota"].map(map_derrota)

# ----------------------------
# Filtros dependientes (piezas)
# ----------------------------

st.subheader("🔍 Filtros por piezas")

col1, col2, col3 = st.columns(3)

df_temp = df.copy()

with col1:
    blade_sel = st.selectbox("Blade", ["Todos"] + sorted(df_temp["Blade"].unique()))

if blade_sel != "Todos":
    df_temp = df_temp[df_temp["Blade"] == blade_sel]

with col2:
    ratchet_sel = st.selectbox("Ratchet", ["Todos"] + sorted(df_temp["Ratchet"].unique()))

if ratchet_sel != "Todos":
    df_temp = df_temp[df_temp["Ratchet"] == ratchet_sel]

with col3:
    bit_sel = st.selectbox("Bit", ["Todos"] + sorted(df_temp["Bit"].unique()))

if bit_sel != "Todos":
    df_temp = df_temp[df_temp["Bit"] == bit_sel]

df_filtered = df_temp.copy()

# ----------------------------
# Selector de color
# ----------------------------

st.subheader("🎨 Color del gráfico")

color_mode = st.radio(
    "Colorear por:",
    ["Victoria", "Derrota"]
)

# 🎨 Colores definidos por ti
color_map_victoria = {
    0: "#888888",  # gris → siempre pierde
    1: "#6EC1E4",  # azul claro → spin
    2: "#F39C12",  # naranja → burst/over
    3: "#2ECC71"   # verde → xtreme
}

color_map_derrota = {
    0: "#F4D03F",  # amarillo → siempre gana
    1: "#6EC1E4",  # azul claro
    2: "#F39C12",  # naranja
    3: "#2ECC71"   # verde
}

if color_mode == "Victoria":
    color_col = "tipo_victoria"
    color_map = color_map_victoria
else:
    color_col = "tipo_derrota"
    color_map = color_map_derrota

# ----------------------------
# Gráfico (NO afectado por arquetipos)
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
# Filtro arquetipos (SOLO tabla)
# ----------------------------

st.subheader("🎯 Filtro de arquetipos (tabla)")

col1, col2 = st.columns(2)

with col1:
    victoria_sel = st.selectbox(
        "Filtrar por victoria",
        ["Todos"] + sorted(df_filtered["victoria_label"].unique())
    )

with col2:
    derrota_sel = st.selectbox(
        "Filtrar por derrota",
        ["Todos"] + sorted(df_filtered["derrota_label"].unique())
    )

df_table = df_filtered.copy()

if victoria_sel != "Todos":
    df_table = df_table[df_table["victoria_label"] == victoria_sel]

if derrota_sel != "Todos":
    df_table = df_table[df_table["derrota_label"] == derrota_sel]

# ----------------------------
# Tabla
# ----------------------------

st.subheader("📊 Datos")

st.dataframe(
    df_table[[
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