import streamlit as st
import pandas as pd

from data.loader import load_data
from core.deckbuilder import optimizar_deck
from core.compatibility import ratchets_validos

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
        blade_sel = st.session_state.get(f"blade_{i}", "—")
        r_opts = ratchets_validos(
            blade_sel,
            sorted(df["Ratchet"].unique())
        ) if blade_sel != "—" else sorted(df["Ratchet"].unique())
        ratchet = st.selectbox(
            f"Ratchet {i+1}",
            ["—"] + r_opts,
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

# ── Optimización: leer total directamente del session_state ───────────────────
total_fijadas = sum(
    (1 if st.session_state.get(f"blade_{i}",   "—") != "—" else 0) +
    (1 if st.session_state.get(f"ratchet_{i}", "—") != "—" else 0) +
    (1 if st.session_state.get(f"bit_{i}",     "—") != "—" else 0)
    for i in range(3)
)

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
        "Blade":              label(bey["Blade"],   bey["Blade fijada"]),
        "Ratchet":            label(bey["Ratchet"], bey["Ratchet fijado"]),
        "Bit":                label(bey["Bit"],     bey["Bit fijado"]),
        "Wilson Score":       bey["Wilson Score"],
        "Arquetipo victoria": bey["Arquetipo victoria"],
        "Arquetipo derrota":  bey["Arquetipo derrota"],
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
    },
)

st.caption(
    "🔒 Pieza elegida por ti · ✨ Sugerida por el sistema"
)

st.divider()

# ── Alternativas ──────────────────────────────────────────────────────────────
st.subheader("💬 Alternativas")

from core.recommender import recomendar_builds

piezas_usadas = {
    "Blade":   [b["Blade"]   for b in deck],
    "Ratchet": [b["Ratchet"] for b in deck],
    "Bit":     [b["Bit"]     for b in deck],
}

for i, bey in enumerate(deck):
    blade_fijada   = bey["Blade fijada"]
    ratchet_fijado = bey["Ratchet fijado"]
    bit_fijado     = bey["Bit fijado"]
    if blade_fijada and ratchet_fijado and bit_fijado:
        continue

    bey_num    = bey["Bey"]
    bey_blade  = bey["Blade"]
    bey_ratchet= bey["Ratchet"]
    bey_bit    = bey["Bit"]
    st.markdown(f"**Bey {bey_num} — {bey_blade} / {bey_ratchet} / {bey_bit}**")

    # Obtener alternativas manteniendo las piezas fijadas de este bey
    blade_fijo   = bey_blade   if blade_fijada   else None
    ratchet_fijo = bey_ratchet if ratchet_fijado else None
    bit_fijo     = bey_bit     if bit_fijado     else None

    df_alt = recomendar_builds(df, blade_fijo, ratchet_fijo, bit_fijo, top_n=50)

    # Excluir el combo ya recomendado y piezas usadas en otros beys
    otras_blades   = [b["Blade"]   for j, b in enumerate(deck) if j != i]
    otras_ratchets = [b["Ratchet"] for j, b in enumerate(deck) if j != i]
    otros_bits     = [b["Bit"]     for j, b in enumerate(deck) if j != i]

    df_alt = df_alt[
        ~df_alt["Blade"].isin(otras_blades) &
        ~df_alt["Ratchet"].isin(otras_ratchets) &
        ~df_alt["Bit"].isin(otros_bits) &
        ~((df_alt["Blade"] == bey["Blade"]) &
          (df_alt["Ratchet"] == bey["Ratchet"]) &
          (df_alt["Bit"] == bey["Bit"]))
    ].head(3)

    if df_alt.empty:
        st.caption("No hay alternativas disponibles.")
    else:
        for _, alt in df_alt.iterrows():
            diferencias = []
            alt_blade   = alt["Blade"]
            alt_ratchet = alt["Ratchet"]
            alt_bit     = alt["Bit"]
            if alt_blade   != bey_blade:    diferencias.append(f"Blade → **{alt_blade}**")
            if alt_ratchet != bey_ratchet:  diferencias.append(f"Ratchet → **{alt_ratchet}**")
            if alt_bit     != bey_bit:      diferencias.append(f"Bit → **{alt_bit}**")
            cambios = " · ".join(diferencias)
            delta = alt["Wilson Score Predicho"] - bey["Wilson Score"]
            signo = "+" if delta >= 0 else ""
            if delta > 0:
                color = "#2ECC71"
            elif delta < 0:
                color = "#E74C3C"
            else:
                color = "#888888"
            delta_str = f"{signo}{delta:.4f}"
            st.markdown(
                f"- {alt_blade} / {alt_ratchet} / {alt_bit} &nbsp; "
                f"({cambios}) &nbsp; "
                f'<span style="color:{color};font-family:monospace">{delta_str}</span>',
                unsafe_allow_html=True
            )