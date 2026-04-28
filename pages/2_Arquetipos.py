import streamlit as st
import plotly.express as px

from data.loader import load_data
from core.archetypes import calcular_arquetipos, etiquetar_arquetipos

st.set_page_config(layout="wide")

st.title("🧠 Arquetipos del META")

# ----------------------------
# Explicación
# ----------------------------

st.info(
    "Los arquetipos se calculan en base al comportamiento real.\n\n"
    "X = daño que haces\n"
    "Y = daño que recibes (invertido → abajo es mejor)"
)

# ----------------------------
# Datos
# ----------------------------

df = load_data()

# ----------------------------
# Clustering GLOBAL (IMPORTANTE)
# ----------------------------

df_clustered, kmeans, k = calcular_arquetipos(df)
df_clustered = etiquetar_arquetipos(df_clustered)

st.caption(f"Arquetipos detectados: {k}")

# ----------------------------
# Filtros (SOLO visuales)
# ----------------------------

min_partidas = st.slider(
    "Mínimo de partidas",
    0,
    int(df_clustered["Partidas"].max()),
    50
)

tipos = ["Todos"] + sorted(df_clustered["arquetipo"].dropna().unique())

tipo_sel = st.selectbox(
    "Filtrar por arquetipo",
    tipos
)

# aplicar filtros SOBRE dataset ya clusterizado
df_filtered = df_clustered.copy()

df_filtered = df_filtered[df_filtered["Partidas"] >= min_partidas]

if tipo_sel != "Todos":
    df_filtered = df_filtered[df_filtered["arquetipo"] == tipo_sel]

# ----------------------------
# Gráfico
# ----------------------------

color_map = {
    "🔥 Agresivo": "#1f77ff",
    "🛡️ Defensivo": "#2ecc71",
    "⚖️ Equilibrado": "#e74c3c"
}

fig = px.scatter(
    df_filtered,
    x="Pts Ganados/Combate",
    y="Pts Cedidos/Combate",
    color="arquetipo",
    color_discrete_map=color_map,
    hover_data=["Blade", "Ratchet", "Bit"],
    opacity=0.7
)

fig.update_layout(
    xaxis_title="Pts Ganados/Combate",
    yaxis_title="Pts Cedidos/Combate"
)

# invertir eje Y (clave)
fig.update_yaxes(autorange="reversed")

st.plotly_chart(fig, use_container_width=True)

st.caption("⬇️ Menos puntos cedidos = mejor")

# ----------------------------
# Tabla
# ----------------------------

st.subheader("Combos en este arquetipo")

st.dataframe(
    df_filtered[["Blade", "Ratchet", "Bit", "Partidas", "arquetipo"]],
    use_container_width=True,
    hide_index=True
)