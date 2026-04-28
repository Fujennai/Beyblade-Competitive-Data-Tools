import streamlit as st
import plotly.express as px
import pandas as pd

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

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
    "🔵 Tamaño = número de partidas (fiabilidad)\n\n"
    "Activa clustering para explorar la estructura oculta del meta."
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
# Clustering (opcional)
# ----------------------------

st.divider()
st.subheader("⚙️ Análisis avanzado")

usar_clusters = st.checkbox("Activar clustering")

if usar_clusters:

    n_clusters = st.slider("Número de clusters (k)", 2, 6, 3)

    features = df_filtered[[
        "Pts Ganados/Combate",
        "Pts Cedidos/Combate"
    ]].dropna()

    if len(features) >= n_clusters:

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(features)

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(X_scaled)

        df_filtered.loc[features.index, "cluster"] = clusters

        st.caption("Clusters detectados automáticamente")

    else:
        st.warning("No hay suficientes datos para aplicar clustering")
        usar_clusters = False

# ----------------------------
# Mapa de eficiencia
# ----------------------------

st.subheader("🗺️ Mapa de eficiencia del META")

st.caption(
    "➡️ Derecha = más daño infligido\n"
    "⬇️ Abajo = menos daño recibido (mejor)"
)

color_col = "Eficiencia"

if usar_clusters:
    color_col = "cluster"

fig = px.scatter(
    df_filtered,
    x="Pts Ganados/Combate",
    y="Pts Cedidos/Combate",
    size="Partidas",
    color=color_col,
    color_continuous_scale="RdYlGn" if not usar_clusters else None,
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

# invertir eje Y
fig.update_yaxes(autorange="reversed")

st.plotly_chart(fig, use_container_width=True)

st.caption(
    "📌 Abajo-derecha = zona óptima\n"
    "📌 Tamaño grande = datos fiables\n"
    "📌 Color = eficiencia o cluster"
)

# ----------------------------
# Info de clusters (modo avanzado)
# ----------------------------

if usar_clusters:
    st.subheader("📊 Análisis de clusters")

    resumen = df_filtered.groupby("cluster").agg({
        "Pts Ganados/Combate": "mean",
        "Pts Cedidos/Combate": "mean",
        "Win %": "mean",
        "Partidas": "mean"
    }).round(2)

    st.dataframe(resumen, use_container_width=True)

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