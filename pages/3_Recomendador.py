import streamlit as st
from data.loader import load_data
from core.recommender import recomendar_builds

st.set_page_config(layout="wide")

st.title("🔧 Recomendador de Builds")

df = load_data()

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

if not any([blade, ratchet, bit]):
    st.warning("⚠️ Fija al menos una pieza para obtener resultados más relevantes.")

# ── Generación ────────────────────────────────────────────────────────────────
with st.spinner("Calculando recomendaciones..."):
    df_rec = recomendar_builds(df, blade, ratchet, bit, top_n=int(top_n))

# ── Resultados ────────────────────────────────────────────────────────────────
if df_rec.empty:
    st.warning("No se encontraron combinaciones para los filtros seleccionados.")
else:
    m1, m2, m3 = st.columns(3)
    m1.metric("Mejor Wilson Score", f"{df_rec['Wilson Score Predicho'].max():.4f}")
    m2.metric("Promedio Top N",     f"{df_rec['Wilson Score Predicho'].mean():.4f}")
    m3.metric("Confianza Alta",     len(df_rec[df_rec["Confianza"] == "🟢 Alta"]))

    st.divider()

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
        "🔍 Confianza basada en el rendimiento histórico de cada pieza: "
        "🟢 Alta · 🟡 Media · 🔴 Baja. "
        "Referencia más cercana: build real con Wilson Score similar."
    )