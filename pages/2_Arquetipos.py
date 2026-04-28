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
    "➡️ X = puntos que ganas cuando ganas\n"
    "⬇️ Y = puntos que cedes cuando pierdes (invertido → abajo es mejor)\n\n"
    "Colores según tipo de victoria o derrota."
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
# Labels con emojis
# ----------------------------

map_victoria = {
    0: "⚫ Siempre pierde",
    1: "🔵 Spin finish",
    2: "🟠 Burst / Over",
    3: "🟢 Xtreme finish"
}

map_derrota = {
    0: "🟡 Siempre gana",
    1: "🔵 Pierde por spin",
    2: "🟠 Pierde por burst/over",
    3: "🟢 Pierde por xtreme"
}

df["victoria_label"] = df["tipo_victoria"].map(map_victoria)
df["derrota_label"] = df["tipo_derrota"].map(map_derrota)

# 🔥 IMPORTANTE: convertir a string para colores discretos
df["tipo_victoria_str"] = df["tipo_victoria"].astype(str)
df["tipo_derrota_str"] = df["tipo_derrota"].astype(str)

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

if color_mode == "Victoria":
    color_col = "tipo_victoria_str"
    color_map = {
        "0": "#888888",
        "1": "#6EC1E4",
        "2": "#F39C12",
        "3": "#2ECC71"
    }
    legend_map = map_victoria
else:
    color_col = "tipo_derrota_str"
    color_map = {
        "0": "#F4D03F",
        "1": "#6EC1E4",
        "2": "#F39C12",
        "3": "#2ECC71"
    }
    legend_map = map_derrota

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
    legend_title="Tipo"
)

fig.update_yaxes(autorange="reversed")

# 🔥 cambiar nombres de leyenda a emojis
for trace in fig.data:
    key = int(trace.name)
    trace.name = legend_map[key]

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
# Tabla con barras
# ----------------------------

st.subheader("📊 Datos")

st.dataframe(
    df_table,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Win %": st.column_config.ProgressColumn(
            "Winrate",
            min_value=0,
            max_value=100,
        ),
        "Partidas": st.column_config.ProgressColumn(
            "Partidas",
            min_value=0,
            max_value=df["Partidas"].max(),
        ),
    }
)