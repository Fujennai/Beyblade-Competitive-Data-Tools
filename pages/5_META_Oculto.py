import streamlit as st
import pandas as pd

from data.loader import load_data
from core.meta_hidden import predecir_combos_nuevos

st.set_page_config(layout="wide")

st.title("🧬 Descubridor de META oculto")

@st.cache_data(ttl=3600)
def get_combos_nuevos():
    df = load_data()
    return df, predecir_combos_nuevos(df, muestra=2000)

with st.spinner("Calculando combos no explorados..."):
    df, df_nuevos = get_combos_nuevos()

if df_nuevos.empty:
    st.warning("No se encontraron combos nuevos.")
    st.stop()

# ── Filtros ───────────────────────────────────────────────────────────────────
st.subheader("🔎 Filtros")

col1, col2, col3 = st.columns(3)

with col1:
    blade = st.selectbox("Blade", ["Todos"] + sorted(df_nuevos["Blade"].unique()))

with col2:
    ratchet = st.selectbox("Ratchet", ["Todos"] + sorted(df_nuevos["Ratchet"].unique()))

with col3:
    bit = st.selectbox("Bit", ["Todos"] + sorted(df_nuevos["Bit"].unique()))

col4, col5 = st.columns(2)

with col4:
    arq_victoria = st.selectbox(
        "Arquetipo victoria",
        ["Todos"] + sorted(df_nuevos["Arquetipo victoria"].unique())
    )

with col5:
    arq_derrota = st.selectbox(
        "Arquetipo derrota",
        ["Todos"] + sorted(df_nuevos["Arquetipo derrota"].unique())
    )

# ── Aplicar filtros ───────────────────────────────────────────────────────────
df_fil = df_nuevos.copy()

if blade        != "Todos": df_fil = df_fil[df_fil["Blade"]               == blade]
if ratchet      != "Todos": df_fil = df_fil[df_fil["Ratchet"]             == ratchet]
if bit          != "Todos": df_fil = df_fil[df_fil["Bit"]                 == bit]
if arq_victoria != "Todos": df_fil = df_fil[df_fil["Arquetipo victoria"]  == arq_victoria]
if arq_derrota  != "Todos": df_fil = df_fil[df_fil["Arquetipo derrota"]   == arq_derrota]

# ── Métricas ──────────────────────────────────────────────────────────────────
st.divider()

m1, m2, m3 = st.columns(3)
m1.metric("Combos encontrados",   len(df_fil))
m2.metric("Mejor Wilson Score",   f"{df_fil['Wilson Score Predicho'].max():.4f}" if not df_fil.empty else "—")
m3.metric("Mejor Win % Predicho", f"{df_fil['Win % Predicho'].max():.2f}%"       if not df_fil.empty else "—")

st.divider()

# ── Tabla ─────────────────────────────────────────────────────────────────────
st.subheader("🏆 Mejores combos no explorados")

if df_fil.empty:
    st.warning("No hay resultados para los filtros seleccionados.")
else:
    st.dataframe(
        df_fil.head(20),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Wilson Score Predicho": st.column_config.ProgressColumn(
                "Wilson Score Predicho",
                format="%.4f",
                min_value=0,
                max_value=1,
            ),
            "Win % Predicho": st.column_config.NumberColumn(
                "Win % Predicho",
                format="%.2f%%"
            ),
            "Arquetipo victoria": st.column_config.TextColumn("Arquetipo victoria"),
            "Arquetipo derrota":  st.column_config.TextColumn("Arquetipo derrota"),
        },
    )
    st.caption("Combos sin partidas registradas. Wilson Score y arquetipos son estimaciones del modelo.")