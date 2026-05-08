import streamlit as st
import plotly.express as px

from data.loader import load_data

st.set_page_config(layout="wide")

st.title("🧠 Arquetipos del META (scoring real)")

# ----------------------------
# Datos
# ----------------------------

df = load_data()

# ----------------------------
# Filtros base
# ----------------------------

col1, col2 = st.columns(2)

with col1:
    min_partidas = st.slider(
        "Mínimo de partidas",
        min_value=0,
        max_value=int(df["Partidas"].max()),
        value=0
    )

with col2:
    min_winrate = st.slider(
        "Winrate mínimo (%)",
        min_value=0,
        max_value=100,
        value=50
    )

df = df[df["Partidas"] >= min_partidas]
df = df[df["Win %"] >= min_winrate]

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
    0: "⚫ Alta tendencia a perder",
    1: "🔵 Spin finish",
    2: "🟠 Burst / Over",
    3: "🟢 Xtreme finish"
}

map_derrota = {
    0: "🟡 Alta tendencia a ganar",
    1: "🔵 Pierde por spin",
    2: "🟠 Pierde por burst/over",
    3: "🟢 Pierde por xtreme"
}

df["Arquetipo de victoria"] = df["tipo_victoria"].map(map_victoria)
df["Arquetipo de derrota"] = df["tipo_derrota"].map(map_derrota)

# Para colores
df["tipo_victoria_str"] = df["tipo_victoria"].astype(str)
df["tipo_derrota_str"] = df["tipo_derrota"].astype(str)

# ----------------------------
# Filtros dependientes
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
# Selector color
# ----------------------------

st.subheader("🎨 Color del gráfico")

color_mode = st.radio("Colorear por:", ["Victoria", "Derrota"])

if color_mode == "Victoria":
    color_col = "tipo_victoria_str"
    color_map = {"0": "#888888", "1": "#6EC1E4", "2": "#F39C12", "3": "#2ECC71"}
    legend_map = map_victoria
else:
    color_col = "tipo_derrota_str"
    color_map = {"0": "#F4D03F", "1": "#6EC1E4", "2": "#F39C12", "3": "#2ECC71"}
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
        "Blade", "Ratchet", "Bit",
        "Win %", "Partidas",
        "Arquetipo de victoria",
        "Arquetipo de derrota"
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

# leyenda con emojis
for trace in fig.data:
    trace.name = legend_map[int(trace.name)]

st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# Filtro tabla
# ----------------------------

st.subheader("🎯 Filtro de arquetipos (tabla)")

col1, col2 = st.columns(2)

with col1:
    victoria_sel = st.selectbox(
        "Filtrar por victoria",
        ["Todos"] + sorted(df_filtered["Arquetipo de victoria"].unique())
    )

with col2:
    derrota_sel = st.selectbox(
        "Filtrar por derrota",
        ["Todos"] + sorted(df_filtered["Arquetipo de derrota"].unique())
    )

df_table = df_filtered.copy()

if victoria_sel != "Todos":
    df_table = df_table[df_table["Arquetipo de victoria"] == victoria_sel]

if derrota_sel != "Todos":
    df_table = df_table[df_table["Arquetipo de derrota"] == derrota_sel]

# ----------------------------
# FIX WINRATE (CLAVE)
# ----------------------------

df_table["Winrate_bar"] = (df_table["Win %"] / 100).clip(0, 1)
df_table["Win %"] = df_table["Win %"].round(1)

# limpiar columnas técnicas
df_table = df_table.drop(columns=[
    "tipo_victoria", "tipo_derrota",
    "tipo_victoria_str", "tipo_derrota_str"
], errors="ignore")

# ----------------------------
# Tabla final
# ----------------------------

st.subheader("📊 Datos")

st.dataframe(
    df_table[[
        "Blade", "Ratchet", "Bit",
        "Partidas", "Winrate_bar", "Win %",
        "Arquetipo de victoria", "Arquetipo de derrota"
    ]],
    use_container_width=True,
    hide_index=True,
    column_config={
        "Winrate_bar": st.column_config.ProgressColumn(
            "Winrate",
            min_value=0,
            max_value=1,
        ),
        "Win %": st.column_config.NumberColumn("Winrate (%)"),
        "Partidas": st.column_config.NumberColumn("Partidas"),
    }
)