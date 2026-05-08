import streamlit as st
import plotly.express as px

from data.loader import load_data
from components.filters import filtros_dependientes

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
        value=10
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
# Clasificación robusta
# ----------------------------

def categorizar(valor, partidas, winrate):

    # poca evidencia
    if partidas < 10:
        return -1

    # winrate sospechoso
    if winrate >= 95 and partidas < 25:
        return -1

    if valor < 0.5:
        return 0

    elif valor < 1.5:
        return 1

    elif valor < 2.5:
        return 2

    else:
        return 3


df["tipo_victoria"] = df.apply(
    lambda row: categorizar(
        row["Pts Ganados/Combate"],
        row["Partidas"],
        row["Win %"]
    ),
    axis=1
)

df["tipo_derrota"] = df.apply(
    lambda row: categorizar(
        row["Pts Cedidos/Combate"],
        row["Partidas"],
        row["Win %"]
    ),
    axis=1
)

# ----------------------------
# Labels
# ----------------------------

map_victoria = {
    -1: "⚪ Datos insuficientes",
    0: "⚫ Alta tendencia a perder",
    1: "🔵 Spin finish",
    2: "🟠 Burst / Over",
    3: "🟢 Xtreme finish"
}

map_derrota = {
    -1: "⚪ Datos insuficientes",
    0: "🟡 Alta tendencia a ganar",
    1: "🔵 Pierde por spin",
    2: "🟠 Pierde por burst/over",
    3: "🟢 Pierde por xtreme"
}

df["Arquetipo de victoria"] = df["tipo_victoria"].map(map_victoria)
df["Arquetipo de derrota"] = df["tipo_derrota"].map(map_derrota)

# columnas string para colores
df["tipo_victoria_str"] = df["tipo_victoria"].astype(str)
df["tipo_derrota_str"] = df["tipo_derrota"].astype(str)

# ----------------------------
# Filtros dependientes
# ----------------------------

df_filtered, blade_sel, ratchet_sel, bit_sel = filtros_dependientes(
    df,
    key_prefix="arquetipos"
)

# ----------------------------
# Nombre completo combo
# ----------------------------

df_filtered["Combo"] = (
    df_filtered["Blade"] + " " +
    df_filtered["Ratchet"] + " " +
    df_filtered["Bit"]
)



# ----------------------------
# Config color
# ----------------------------

color_mode = st.session_state.get(
    "arquetipo_color_mode",
    "Victoria"
)

if color_mode == "Victoria":

    color_col = "tipo_victoria_str"

    color_map = {
        "-1": "#AAAAAA",
        "0": "#888888",
        "1": "#6EC1E4",
        "2": "#F39C12",
        "3": "#2ECC71"
    }

    legend_map = map_victoria

else:

    color_col = "tipo_derrota_str"

    color_map = {
        "-1": "#AAAAAA",
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
    df_plot,

    x="Pts Ganados/Combate",
    y="Pts Cedidos/Combate",

    color=color_col,
    color_discrete_map=color_map,

    hover_name="Combo",

    hover_data={

        "Combo": False,
        "Blade": False,
        "Ratchet": False,
        "Bit": False,

        "Win %": ":.1f",
        "Partidas": True,

        "Pts Ganados/Combate": ":.2f",
        "Pts Cedidos/Combate": ":.2f",

        "Arquetipo de victoria": True,
        "Arquetipo de derrota": True,

        "tipo_victoria": False,
        "tipo_derrota": False,
        "tipo_victoria_str": False,
        "tipo_derrota_str": False,
    },

    opacity=0.7
)

fig.update_traces(
    marker=dict(size=6)
)

fig.update_layout(
    xaxis_title="Puntos ganados por combate",
    yaxis_title="Puntos cedidos por combate",
    legend_title="Tipo"
)

fig.update_yaxes(
    autorange="reversed"
)

# emojis leyenda
for trace in fig.data:

    trace.name = legend_map[int(trace.name)]

st.plotly_chart(
    fig,
    use_container_width=True
)

# ----------------------------
# Mostrar insuficientes
# ----------------------------

mostrar_insuficientes = st.checkbox(
    "Mostrar casos con datos insuficientes",
    value=False
)

df_plot = df_filtered.copy()

if not mostrar_insuficientes:

    df_plot = df_plot[
        (df_plot["tipo_victoria"] != -1) &
        (df_plot["tipo_derrota"] != -1)
    ]

# ----------------------------
# Selector color
# ----------------------------

st.subheader("🎨 Color del gráfico")

color_mode = st.radio(
    "Colorear por:",
    ["Victoria", "Derrota"],
    index=0 if color_mode == "Victoria" else 1,
    key="arquetipo_color_mode"
)

if color_mode != st.session_state.get("prev_color_mode"):

    st.session_state["prev_color_mode"] = color_mode
    st.rerun()

# ----------------------------
# Filtro tabla
# ----------------------------

st.subheader("🎯 Filtro de arquetipos (tabla)")

col1, col2 = st.columns(2)

with col1:

    victoria_sel = st.selectbox(
        "Filtrar por victoria",
        ["Todos"] + sorted(
            df_filtered["Arquetipo de victoria"].unique()
        )
    )

with col2:

    derrota_sel = st.selectbox(
        "Filtrar por derrota",
        ["Todos"] + sorted(
            df_filtered["Arquetipo de derrota"].unique()
        )
    )

df_table = df_filtered.copy()

if victoria_sel != "Todos":

    df_table = df_table[
        df_table["Arquetipo de victoria"] == victoria_sel
    ]

if derrota_sel != "Todos":

    df_table = df_table[
        df_table["Arquetipo de derrota"] == derrota_sel
    ]

# ----------------------------
# Fix winrate
# ----------------------------

df_table["Winrate_bar"] = (
    df_table["Win %"] / 100
).clip(0, 1)

df_table["Win %"] = (
    df_table["Win %"]
    .round(1)
)

# limpiar columnas técnicas
df_table = df_table.drop(
    columns=[
        "tipo_victoria",
        "tipo_derrota",
        "tipo_victoria_str",
        "tipo_derrota_str",
        "Combo"
    ],
    errors="ignore"
)

# ----------------------------
# Tabla final
# ----------------------------

st.subheader("📊 Datos")

st.dataframe(
    df_table[[
        "Blade",
        "Ratchet",
        "Bit",
        "Partidas",
        "Winrate_bar",
        "Win %",
        "Arquetipo de victoria",
        "Arquetipo de derrota"
    ]],
    use_container_width=True,
    hide_index=True,
    column_config={

        "Winrate_bar": st.column_config.ProgressColumn(
            "Winrate",
            min_value=0,
            max_value=1,
        ),

        "Win %": st.column_config.NumberColumn(
            "Winrate (%)"
        ),

        "Partidas": st.column_config.NumberColumn(
            "Partidas"
        ),
    }
)