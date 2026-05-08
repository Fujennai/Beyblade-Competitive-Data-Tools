import streamlit as st
from data.loader import load_data
from core.recommender import recomendar_builds

st.set_page_config(layout="wide")

st.title("🔧 Recomendador Predictivo de Builds")

df = load_data()

st.info(
    "💡 Este recomendador usa **Gradient Boosting** para predecir el rendimiento de "
    "combinaciones que **no existen en el dataset**. Fija una o más piezas para explorar "
    "qué compañeros optimizarían su Wilson Score."
)

# ── Filtros ────────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

with col1:
    blade = st.selectbox("Blade", ["Todos"] + sorted(df["Blade"].unique()))

with col2:
    ratchet = st.selectbox("Ratchet", ["Todos"] + sorted(df["Ratchet"].unique()))

with col3:
    bit = st.selectbox("Bit", ["Todos"] + sorted(df["Bit"].unique()))

with col4:
    top_n = st.number_input("Top N", min_value=5, max_value=100, value=20, step=5)

blade   = None if blade   == "Todos" else blade
ratchet = None if ratchet == "Todos" else ratchet
bit     = None if bit     == "Todos" else bit

# ── Advertencia si no se fija ninguna pieza ────────────────────────────────────
if not any([blade, ratchet, bit]):
    st.warning(
        "⚠️ Sin filtros el modelo evalúa **todas** las combinaciones posibles. "
        "Considera fijar al menos una pieza para resultados más relevantes."
    )

# ── Generación ────────────────────────────────────────────────────────────────
with st.spinner("Entrenando modelo y generando predicciones..."):
    df_rec = recomendar_builds(df, blade, ratchet, bit, top_n=int(top_n))

# ── Resultados ────────────────────────────────────────────────────────────────
if df_rec.empty:
    st.warning("No se encontraron combinaciones nuevas para los filtros seleccionados.")
else:
    st.success(f"✅ Se encontraron **{len(df_rec)}** builds predichas no presentes en el dataset.")

    # Métricas rápidas
    m1, m2, m3 = st.columns(3)
    m1.metric("Mejor Wilson Score Predicho", f"{df_rec['Wilson Score Predicho'].max():.4f}")
    m2.metric("Promedio Top N",              f"{df_rec['Wilson Score Predicho'].mean():.4f}")
    m3.metric("Builds con confianza Alta",
              len(df_rec[df_rec["Confianza"] == "🟢 Alta"]))

    st.divider()

    # Tabla principal
    st.dataframe(
        df_rec,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Wilson Score Predicho": st.column_config.ProgressColumn(
                "Wilson Score Predicho",
                format="%.4f",
                min_value=0,
                max_value=1,
            ),
            "Confianza": st.column_config.TextColumn("Confianza"),
            "Referencia más cercana": st.column_config.TextColumn(
                "Referencia más cercana", width="large"
            ),
        },
    )

    st.caption(
        "🔍 **Confianza**: estimada según el historial de partidas de cada pieza individual. "
        "🟢 Alta = piezas con muchos datos · 🟡 Media · 🔴 Baja = piezas poco probadas. "
        "**Referencia más cercana**: build real del dataset con Wilson Score más similar al predicho."
    )