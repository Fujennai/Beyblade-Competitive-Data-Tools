import streamlit as st
import pandas as pd

from data.loader import load_data
from core.deckbuilder import optimizar_deck

st.set_page_config(layout="wide")

st.title("🧩 Deckbuilder")

df = load_data()

st.caption(
    "Fija las piezas que quieras para cada bey. "
    "El sistema completa el resto optimizando el deck en conjunto. "
    "🔒 = elegido por ti · ✨ = sugerido por el sistema"
)

# ── Selección del usuario ─────────────────────────────────────────────────────
st.subheader("🎯 Piezas fijadas")

fijados = []

for i in range(3):
    st.markdown(f"**Bey {i+1}**")
    col1, col2, col3 = st.columns(3)

    with col1:
        blade = st.selectbox(
            f"Blade {i+1}",
            ["—"] + sorted(df["Blade"].unique()),
            key=f"blade_{i}"
        )
    with col2:
        ratchet = st.selectbox(
            f"Ratchet {i+1}",
            ["—"] + sorted(df["Ratchet"].unique()),
            key=f"ratchet_{i}"
        )
    with col3:
        bit = st.selectbox(
            f"Bit {i+1}",
            ["—"] + sorted(df["Bit"].unique()),
            key=f"bit_{i}"
        )

    bey = {}
    if blade   != "—": bey["Blade"]   = blade
    if ratchet != "—": bey["Ratchet"] = ratchet
    if bit     != "—": bey["Bit"]     = bit
    fijados.append(bey)

st.divider()

# ── Optimización ──────────────────────────────────────────────────────────────
total_fijadas = sum(len(bey) for bey in fijados)

if total_fijadas < 3:
    st.info(f"🔒 Fija al menos 3 piezas para generar recomendaciones ({total_fijadas}/3 seleccionadas).")
    st.stop()

with st.spinner("Optimizando deck..."):
    resultado = optimizar_deck(df, fijados)

if resultado is None:
    st.warning("No se encontró ningún deck válido con las piezas seleccionadas.")
    st.stop()

deck, score_deck = resultado

# ── Métricas ──────────────────────────────────────────────────────────────────
ws_scores = [bey["Wilson Score"] for bey in deck]

m1, m2, m3 = st.columns(3)
m1.metric("Score del deck",       f"{score_deck:.4f}")
m2.metric("Wilson Score medio",   f"{sum(ws_scores)/3:.4f}")
m3.metric("Bey más débil",        f"{min(ws_scores):.4f}")

st.divider()

# ── Tabla del deck ────────────────────────────────────────────────────────────
st.subheader("🏆 Deck recomendado")

rows = []
for bey in deck:
    def label(val, fijado):
        return f"🔒 {val}" if fijado else f"✨ {val}"

    rows.append({
        "Bey":                f"Bey {bey['Bey']}",
        "Blade":              label(bey["Blade"],   bey["Blade fijada"]),
        "Ratchet":            label(bey["Ratchet"], bey["Ratchet fijado"]),
        "Bit":                label(bey["Bit"],     bey["Bit fijado"]),
        "Wilson Score":       bey["Wilson Score"],
        "Arquetipo victoria": bey["Arquetipo victoria"],
        "Arquetipo derrota":  bey["Arquetipo derrota"],
        "Datos":              "✅ Real" if bey["Combo real"] else "🔮 Estimado",
    })

df_deck = pd.DataFrame(rows)

st.dataframe(
    df_deck,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Wilson Score": st.column_config.ProgressColumn(
            "Wilson Score",
            format="%.4f",
            min_value=0,
            max_value=1,
        ),
        "Arquetipo victoria": st.column_config.TextColumn("Arquetipo victoria"),
        "Arquetipo derrota":  st.column_config.TextColumn("Arquetipo derrota"),
        "Datos":              st.column_config.TextColumn("Datos"),
    },
)

st.caption(
    "🔒 Pieza elegida por ti. ✨ Sugerida por el sistema. "
    "✅ Real: combo con partidas registradas. 🔮 Estimado: sin datos reales."
)