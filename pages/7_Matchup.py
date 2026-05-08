import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from data.loader import load_data
from core.matchup import prob_victoria, pts_esperados

st.set_page_config(layout="wide")

st.title("⚔️ Matchup 1v1")

st.caption(
    "Calcula la probabilidad de victoria entre dos combos basándote en "
    "su Wilson Score relativo. También estima los puntos esperados por "
    "combate según los puntos que cada combo gana de media."
)

df = load_data()

if df.empty:
    st.warning("No hay datos disponibles.")
    st.stop()


# ── Helpers ──────────────────────────────────────────────────────────────────
def combo_label(row):
    return f"{row['Blade']} / {row['Ratchet']} / {row['Bit']}"


df = df.copy()
df["combo"] = df.apply(combo_label, axis=1)

# Filtro de partidas mínimas para tener selecciones fiables
min_partidas = st.slider(
    "Partidas mínimas para incluir un combo",
    min_value=1,
    max_value=int(df["Partidas"].max()) if "Partidas" in df.columns else 50,
    value=10,
    help="Filtra combos poco jugados para evitar Wilson Scores ruidosos.",
)

df_filt = df[df["Partidas"] >= min_partidas].sort_values(
    "Wilson Score", ascending=False
)

if df_filt.empty:
    st.warning("Ningún combo cumple ese mínimo de partidas. Baja el slider.")
    st.stop()

opciones = df_filt["combo"].tolist()


# ── Selección de combos ──────────────────────────────────────────────────────
col_a, col_vs, col_b = st.columns([5, 1, 5])

with col_a:
    st.subheader("🔵 Combo A")
    sel_a = st.selectbox("Elige el combo A", opciones, index=0, key="combo_a")

with col_vs:
    st.markdown(
        "<div style='text-align:center;font-size:2.5rem;padding-top:2.5rem'>⚔️</div>",
        unsafe_allow_html=True,
    )

with col_b:
    st.subheader("🔴 Combo B")
    default_b = 1 if len(opciones) > 1 else 0
    sel_b = st.selectbox("Elige el combo B", opciones, index=default_b, key="combo_b")

if sel_a == sel_b:
    st.info("Selecciona dos combos distintos para calcular el matchup.")
    st.stop()

row_a = df_filt[df_filt["combo"] == sel_a].iloc[0]
row_b = df_filt[df_filt["combo"] == sel_b].iloc[0]

ws_a = float(row_a["Wilson Score"])
ws_b = float(row_b["Wilson Score"])

pts_a = float(row_a.get("Pts Ganados/Combate", 1.0))
pts_b = float(row_b.get("Pts Ganados/Combate", 1.0))

# ── Cálculos ─────────────────────────────────────────────────────────────────
p_a = prob_victoria(ws_a, ws_b)
p_b = 1 - p_a
e_a, e_b = pts_esperados(ws_a, ws_b, pts_a, pts_b)

st.divider()

# ── Probabilidad de victoria (barra horizontal) ──────────────────────────────
st.subheader("🎯 Probabilidad de victoria")

fig = go.Figure()
fig.add_trace(go.Bar(
    y=[""], x=[p_a * 100],
    name="Combo A",
    orientation="h",
    marker=dict(color="#3498DB"),
    text=[f"{p_a*100:.1f}%"],
    textposition="inside",
    insidetextanchor="middle",
    textfont=dict(color="white", size=16, family="monospace"),
))
fig.add_trace(go.Bar(
    y=[""], x=[p_b * 100],
    name="Combo B",
    orientation="h",
    marker=dict(color="#E74C3C"),
    text=[f"{p_b*100:.1f}%"],
    textposition="inside",
    insidetextanchor="middle",
    textfont=dict(color="white", size=16, family="monospace"),
))
fig.update_layout(
    barmode="stack",
    height=110,
    margin=dict(l=10, r=10, t=10, b=10),
    showlegend=False,
    xaxis=dict(range=[0, 100], visible=False),
    yaxis=dict(visible=False),
)
st.plotly_chart(fig, use_container_width=True)

# ── Métricas ─────────────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("🔵 P(gana A)", f"{p_a*100:.1f}%")
m2.metric("🔴 P(gana B)", f"{p_b*100:.1f}%")
m3.metric("Pts esperados A", f"{e_a:.2f}")
m4.metric("Pts esperados B", f"{e_b:.2f}")

st.divider()

# ── Comparativa lado a lado ──────────────────────────────────────────────────
st.subheader("📋 Comparativa de stats")

comparativa = pd.DataFrame({
    "Stat": [
        "Wilson Score",
        "Win %",
        "Partidas",
        "Wins",
        "Losses",
        "Pts Ganados/Combate",
        "Pts Cedidos/Combate",
        "Eficiencia",
    ],
    "🔵 Combo A": [
        f"{ws_a:.4f}",
        f"{row_a.get('Win %', 0):.1f}%",
        int(row_a["Partidas"]),
        int(row_a.get("Wins", 0)),
        int(row_a.get("Losses", 0)),
        f"{row_a.get('Pts Ganados/Combate', 0):.2f}",
        f"{row_a.get('Pts Cedidos/Combate', 0):.2f}",
        f"{row_a.get('Eficiencia', 0):.1f}",
    ],
    "🔴 Combo B": [
        f"{ws_b:.4f}",
        f"{row_b.get('Win %', 0):.1f}%",
        int(row_b["Partidas"]),
        int(row_b.get("Wins", 0)),
        int(row_b.get("Losses", 0)),
        f"{row_b.get('Pts Ganados/Combate', 0):.2f}",
        f"{row_b.get('Pts Cedidos/Combate', 0):.2f}",
        f"{row_b.get('Eficiencia', 0):.1f}",
    ],
})

st.dataframe(comparativa, use_container_width=True, hide_index=True)

with st.expander("ℹ️ ¿Cómo se calcula?"):
    st.markdown(
        """
- **P(gana A)** = `WilsonScore(A) / (WilsonScore(A) + WilsonScore(B))`.
  Es una aproximación basada en el rendimiento relativo de cada combo
  contra el meta global, no contra el otro combo en concreto.
- **Pts esperados A** = `P(A) × Pts Ganados/Combate de A`.
- Si ambos combos tienen Wilson Score 0, la probabilidad cae a 50/50.
        """
    )
