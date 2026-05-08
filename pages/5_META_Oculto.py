import streamlit as st
import pandas as pd

from data.loader import load_data
from core.meta_hidden import predecir_combos_nuevos
from components.view_toggle import view_toggle

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

INSUFICIENTE = "⚪ Datos insuficientes"

def ordenar_arquetipos(valores):
    sin_insuf = sorted(v for v in valores if v != INSUFICIENTE)
    return sin_insuf + ([INSUFICIENTE] if INSUFICIENTE in valores else [])

# Opciones fijas con todos los valores posibles, no solo los presentes
TODOS_VICTORIA = [
    "⚫ Alta tendencia a perder",
    "🔵 Spin finish",
    "🟠 Burst / Over",
    "🟢 Xtreme finish",
    INSUFICIENTE,
]
TODOS_DERROTA = [
    "🟡 Alta tendencia a ganar",
    "🔵 Pierde por spin",
    "🟠 Pierde por burst/over",
    "🟢 Pierde por xtreme",
    INSUFICIENTE,
]

col4, col5 = st.columns(2)

with col4:
    arq_victoria = st.selectbox(
        "Arquetipo victoria",
        ["Todos"] + TODOS_VICTORIA
    )

with col5:
    arq_derrota = st.selectbox(
        "Arquetipo derrota",
        ["Todos"] + TODOS_DERROTA
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

# ── Resultados ───────────────────────────────────────────────────────────────
st.subheader("🏆 Mejores combos no explorados")

if df_fil.empty:
    st.warning("No hay resultados para los filtros seleccionados.")
else:
    modo = view_toggle(key="meta_oculto_view")

    if modo == "cards":
        top = df_fil.head(20)
        cols = st.columns(4)
        for idx, (_, row) in enumerate(top.iterrows()):
            ws      = row["Wilson Score Predicho"]
            winpct  = row["Win % Predicho"]
            bar_pct = int(ws * 100)
            arq_v   = row["Arquetipo victoria"]
            arq_d   = row["Arquetipo derrota"]
            blade   = row["Blade"]
            ratchet = row["Ratchet"]
            bit     = row["Bit"]
            card = (
                '<div style="background:#1a1a2e;border-radius:12px;padding:14px 16px;border:1px solid #2a2a4a;margin-bottom:8px">' +
                f'<div style="font-weight:700;font-size:0.95em;color:#fff;margin-bottom:6px">{blade}</div>' +
                f'<div style="font-size:0.82em;color:#aaa;margin-bottom:2px">{ratchet} &nbsp;·&nbsp; {bit}</div>' +
                '<div style="margin:10px 0 4px">' +
                f'<div style="background:#2a2a4a;border-radius:4px;height:5px">' +
                f'<div style="background:#6EC1E4;width:{bar_pct}%;height:5px;border-radius:4px"></div>' +
                '</div></div>' +
                f'<div style="display:flex;justify-content:space-between;font-size:0.8em;color:#888">' +
                f'<span>Wilson</span><span style="color:#fff;font-weight:700">{ws:.4f}</span></div>' +
                f'<div style="display:flex;justify-content:space-between;font-size:0.8em;color:#888;margin-top:2px">' +
                f'<span>Win %</span><span style="color:#fff;font-weight:700">{winpct:.2f}%</span></div>' +
                f'<div style="margin-top:8px;font-size:0.72em;color:#666">{arq_v}<br>{arq_d}</div>' +
                '</div>'
            )
            with cols[idx % 4]:
                st.markdown(card, unsafe_allow_html=True)
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