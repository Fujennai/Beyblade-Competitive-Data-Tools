import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from data.loader import load_data
from core.matchup import simular_deck_match, orden_optimo

st.set_page_config(layout="wide")

st.title("🥊 Deck Match")

st.caption(
    "Simula un enfrentamiento entre dos decks de 3 combos mediante "
    "Monte Carlo. Cada combate se resuelve por Wilson Score relativo "
    "y los puntos se acumulan hasta llegar a 4."
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

min_partidas = st.slider(
    "Partidas mínimas por combo",
    min_value=1,
    max_value=int(df["Partidas"].max()) if "Partidas" in df.columns else 50,
    value=10,
)

df_filt = df[df["Partidas"] >= min_partidas].sort_values(
    "Wilson Score", ascending=False
)

if len(df_filt) < 6:
    st.warning("Necesitas al menos 6 combos disponibles. Baja el slider de partidas.")
    st.stop()

opciones = df_filt["combo"].tolist()


def construir_deck(label, key_prefix, default_offset):
    st.subheader(label)
    deck = []
    for i in range(3):
        idx_default = (default_offset + i) % len(opciones)
        sel = st.selectbox(
            f"Bey {i+1}",
            opciones,
            index=idx_default,
            key=f"{key_prefix}_{i}",
        )
        row = df_filt[df_filt["combo"] == sel].iloc[0]
        deck.append({
            "nombre": sel,
            "ws": float(row["Wilson Score"]),
            "pts_ganados": float(row.get("Pts Ganados/Combate", 1.0)),
            "pts_cedidos": float(row.get("Pts Cedidos/Combate", 1.0)),
        })
    return deck


# ── Selección de decks ───────────────────────────────────────────────────────
col_a, col_vs, col_b = st.columns([5, 1, 5])

with col_a:
    deck_a = construir_deck("🔵 Tu Deck", "deck_a", 0)

with col_vs:
    st.markdown(
        "<div style='text-align:center;font-size:2.5rem;padding-top:8rem'>🥊</div>",
        unsafe_allow_html=True,
    )

with col_b:
    deck_b = construir_deck("🔴 Deck Rival", "deck_b", 3)

# Validar combos únicos dentro de cada deck
nombres_a = [b["nombre"] for b in deck_a]
nombres_b = [b["nombre"] for b in deck_b]

if len(set(nombres_a)) < 3 or len(set(nombres_b)) < 3:
    st.warning("Cada deck debe tener 3 combos distintos.")
    st.stop()

st.divider()

# ── Configuración de simulación ──────────────────────────────────────────────
with st.expander("⚙️ Configuración de simulación"):
    n_sims = st.slider(
        "Nº de simulaciones",
        min_value=1_000, max_value=20_000, value=5_000, step=1_000,
    )
    calcular_orden = st.checkbox(
        "Calcular orden óptimo (más lento)",
        value=False,
        help="Prueba todas las permutaciones de tu deck contra todas las del rival.",
    )

# ── Simulación principal ─────────────────────────────────────────────────────
with st.spinner("Simulando deck match..."):
    p_a = simular_deck_match(deck_a, deck_b, n_sims=n_sims)

p_b = 1 - p_a

st.subheader("🎯 Probabilidad de ganar el deck match")

fig = go.Figure()
fig.add_trace(go.Bar(
    y=[""], x=[p_a * 100],
    name="Tu deck",
    orientation="h",
    marker=dict(color="#3498DB"),
    text=[f"{p_a*100:.1f}%"],
    textposition="inside",
    insidetextanchor="middle",
    textfont=dict(color="white", size=18, family="monospace"),
))
fig.add_trace(go.Bar(
    y=[""], x=[p_b * 100],
    name="Rival",
    orientation="h",
    marker=dict(color="#E74C3C"),
    text=[f"{p_b*100:.1f}%"],
    textposition="inside",
    insidetextanchor="middle",
    textfont=dict(color="white", size=18, family="monospace"),
))
fig.update_layout(
    barmode="stack",
    height=120,
    margin=dict(l=10, r=10, t=10, b=10),
    showlegend=False,
    xaxis=dict(range=[0, 100], visible=False),
    yaxis=dict(visible=False),
)
st.plotly_chart(fig, use_container_width=True)

m1, m2, m3 = st.columns(3)
m1.metric("🔵 P(ganas tú)", f"{p_a*100:.1f}%")
m2.metric("🔴 P(gana rival)", f"{p_b*100:.1f}%")
m3.metric("Simulaciones", f"{n_sims:,}".replace(",", "."))

st.divider()

# ── Detalle de los decks ─────────────────────────────────────────────────────
st.subheader("📋 Detalle de los decks")

c1, c2 = st.columns(2)
with c1:
    st.markdown("**🔵 Tu deck**")
    st.dataframe(
        pd.DataFrame([
            {"Bey": i+1, "Combo": b["nombre"], "Wilson Score": round(b["ws"], 4),
             "Pts Ganados": b["pts_ganados"]}
            for i, b in enumerate(deck_a)
        ]),
        hide_index=True, use_container_width=True,
    )
with c2:
    st.markdown("**🔴 Deck rival**")
    st.dataframe(
        pd.DataFrame([
            {"Bey": i+1, "Combo": b["nombre"], "Wilson Score": round(b["ws"], 4),
             "Pts Ganados": b["pts_ganados"]}
            for i, b in enumerate(deck_b)
        ]),
        hide_index=True, use_container_width=True,
    )

# ── Orden óptimo (opcional) ──────────────────────────────────────────────────
if calcular_orden:
    st.divider()
    st.subheader("🧮 Orden óptimo de tu deck")

    with st.spinner("Probando permutaciones..."):
        resultados = orden_optimo(deck_a, deck_b, n_sims=max(1_000, n_sims // 5))

    rows = []
    for perm, deck_orden, prob in resultados:
        rows.append({
            "Orden": " → ".join(b["nombre"].split(" / ")[0] for b in deck_orden),
            "P(victoria)": f"{prob*100:.1f}%",
            "_sort": prob,
        })
    df_orden = pd.DataFrame(rows).sort_values("_sort", ascending=False).drop(columns="_sort")
    st.dataframe(df_orden, hide_index=True, use_container_width=True)

    mejor = resultados[0]
    st.success(
        f"🏆 Mejor orden: **{' → '.join(b['nombre'] for b in mejor[1])}** "
        f"con {mejor[2]*100:.1f}% de probabilidad media."
    )

with st.expander("ℹ️ ¿Cómo funciona la simulación?"):
    st.markdown(
        """
- Se enfrentan los Bey 1 de cada deck. El ganador suma sus **Pts Ganados**.
- El perdedor cambia al siguiente Bey de su deck; el ganador sigue.
- El primero en llegar a **4 puntos** gana el deck match.
- La probabilidad de cada combate se calcula con **Wilson Score relativo**:
  `P(A gana) = WS(A) / (WS(A) + WS(B))`.
- Se repite el proceso N veces (Monte Carlo) para estimar la probabilidad final.
        """
    )
