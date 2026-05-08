import streamlit as st
from data.loader import load_data
from core.recommender import recomendar_builds

st.set_page_config(layout="wide")

st.title("🔧 Recomendador de Builds")

df = load_data()

# ── Filtros ───────────────────────────────────────────────────────────────────
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

# ── Resultados ────────────────────────────────────────────────────────────────
with st.spinner("Calculando recomendaciones..."):
    df_rec = recomendar_builds(df, blade, ratchet, bit, top_n=int(top_n))

if df_rec.empty:
    st.warning("No se encontraron combinaciones para los filtros seleccionados.")
else:
    n_reales    = len(df_rec[df_rec["Tipo"] == "✅ Real"])
    n_predichos = len(df_rec[df_rec["Tipo"] == "🔮 Predicho"])

    m1, m2, m3 = st.columns(3)
    m1.metric("Mejor Wilson Score",          f"{df_rec['Wilson Score Predicho'].max():.4f}")
    m2.metric("Combos con datos reales",     n_reales)
    m3.metric("Combos predichos",            n_predichos)

    st.divider()

    st.dataframe(
        df_rec,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Wilson Score Predicho": st.column_config.ProgressColumn(
                "Wilson Score",
                format="%.4f",
                min_value=0,
                max_value=1,
            ),
            "Partidas":            st.column_config.NumberColumn("Partidas"),
            "Tipo":                st.column_config.TextColumn("Tipo"),
            "Arquetipo victoria":  st.column_config.TextColumn("Arquetipo victoria"),
            "Arquetipo derrota":   st.column_config.TextColumn("Arquetipo derrota"),
        },
    )

    st.caption(
        "✅ Real: combo con partidas registradas. "
        "🔮 Predicho: combo sin datos reales, estimado a partir de piezas del mismo arquetipo."
    )