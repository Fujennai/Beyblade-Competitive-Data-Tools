import streamlit as st
import plotly.express as px

from data.loader import load_data
from components.filters import filtros_dependientes
from components.view_toggle import view_toggle

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
# Estado checkbox
# ----------------------------

mostrar_insuficientes = st.session_state.get(
    "mostrar_insuficientes",
    False
)

# ----------------------------
# Dataset gráfico
# ----------------------------

df_plot = df_filtered.copy()

if not mostrar_insuficientes:

    df_plot = df_plot[
        (df_plot["tipo_victoria"] != -1) &
        (df_plot["tipo_derrota"] != -1)
    ]

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

# ----------------------------
# Leyenda emojis
# ----------------------------

for trace in fig.data:

    trace.name = legend_map[int(trace.name)]

# ----------------------------
# Forzar leyenda completa
# ----------------------------

if color_mode == "Victoria":

    categorias = [
        ("1", "🔵 Spin finish"),
        ("2", "🟠 Burst / Over"),
        ("3", "🟢 Xtreme finish"),
        ("0", "⚫ Alta tendencia a perder"),
    ]

else:

    categorias = [
        ("1", "🔵 Pierde por spin"),
        ("2", "🟠 Pierde por burst/over"),
        ("3", "🟢 Pierde por xtreme"),
        ("0", "🟡 Alta tendencia a ganar"),
    ]

presentes = [trace.name for trace in fig.data]

for key, label in categorias:

    if label not in presentes:

        fig.add_scatter(
            x=[None],
            y=[None],
            mode="markers",
            marker=dict(
                size=8,
                color=color_map[key]
            ),
            showlegend=True,
            name=label
        )

st.plotly_chart(
    fig,
    use_container_width=True
)

# ----------------------------
# Checkbox debajo gráfico
# ----------------------------

mostrar_insuficientes = st.checkbox(
    "Mostrar casos con datos insuficientes",
    value=mostrar_insuficientes,
    key="mostrar_insuficientes"
)

if mostrar_insuficientes != st.session_state.get("prev_insuficientes"):

    st.session_state["prev_insuficientes"] = mostrar_insuficientes
    st.rerun()

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
# Disclaimer tabla
# ----------------------------

st.info(
    "ℹ️ ¿Echas de menos un filtro?\n\n"
    "Prueba a ajustar el mínimo de partidas, "
    "el winrate mínimo o seleccionar más piezas "
    "en los filtros de la parte superior."
)

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

modo = view_toggle(key="arquetipos_view")

if modo == "cards":
    if df_table.empty:
        st.warning("No hay datos")
    else:
        cols = st.columns(4)
        for idx, (_, row) in enumerate(df_table.iterrows()):
            ws      = row["Winrate_bar"]
            bar_pct = int(ws * 100)
            winpct  = row["Win %"]
            partidas= int(row["Partidas"])
            r_blade  = row["Blade"]
            r_ratchet= row["Ratchet"]
            r_bit    = row["Bit"]
            arq_v   = row["Arquetipo de victoria"]
            arq_d   = row["Arquetipo de derrota"]
            card = (
                '<div style="background:#1a1a2e;border-radius:12px;padding:14px 16px;border:1px solid #2a2a4a;margin-bottom:8px">' +
                f'<div style="font-weight:700;font-size:0.95em;color:#fff;margin-bottom:4px">{r_blade}</div>' +
                f'<div style="font-size:0.82em;color:#aaa;margin-bottom:2px">{r_ratchet} &nbsp;·&nbsp; {r_bit}</div>' +
                f'<div style="font-size:0.78em;color:#666;margin-bottom:8px">{partidas} partidas</div>' +
                '<div style="margin:6px 0 4px">' +
                f'<div style="background:#2a2a4a;border-radius:4px;height:5px">' +
                f'<div style="background:#6EC1E4;width:{bar_pct}%;height:5px;border-radius:4px"></div>' +
                '</div></div>' +
                f'<div style="display:flex;justify-content:space-between;font-size:0.8em;color:#888">' +
                f'<span>Winrate</span><span style="color:#fff;font-weight:700">{winpct:.1f}%</span></div>' +
                f'<div style="margin-top:8px;font-size:0.72em;color:#666">{arq_v}<br>{arq_d}</div>' +
                '</div>'
            )
            with cols[idx % 4]:
                st.markdown(card, unsafe_allow_html=True)
else:
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