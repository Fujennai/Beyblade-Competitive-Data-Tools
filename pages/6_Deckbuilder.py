import streamlit as st
import pandas as pd

from data.loader import load_data
from core.deckbuilder import optimizar_deck
from core.compatibility import ratchets_validos
from components.view_toggle import view_toggle
from components.demo_button import boton_demo, combos_aleatorios

st.set_page_config(layout="wide")

st.title("🧩 Deckbuilder")

df = load_data()

st.caption(
    "Fija las piezas que quieras para cada bey. "
    "El sistema completa el resto optimizando el deck en conjunto. "
    "🔒 = elegido por ti · ✨ = sugerido por el sistema"
)

# ── Botón de demostración ─────────────────────────────────────────────────────
if boton_demo(
    key="demo_db",
    help_text="Fija 3 Blades aleatorios de combos reales del dataset "
              "(ponderados por partidas) para que el optimizador construya el deck.",
):
    combos = combos_aleatorios(df, n=10)  # margen de sobra para evitar duplicados
    blades_usados = []
    for c in combos:
        if c["Blade"] not in blades_usados:
            blades_usados.append(c["Blade"])
        if len(blades_usados) == 3:
            break
    if len(blades_usados) == 3:
        for i, blade in enumerate(blades_usados):
            st.session_state[f"blade_{i}"]   = blade
            st.session_state[f"ratchet_{i}"] = "—"
            st.session_state[f"bit_{i}"]     = "—"
        st.toast(f"🎬 Demo: {', '.join(blades_usados)}", icon="✨")
    st.rerun()

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

# ── Deck recomendado ─────────────────────────────────────────────────────────
st.subheader("🏆 Deck recomendado")

modo_deck = view_toggle(key="deck_view")

if modo_deck == "cards":
    deck_cols = st.columns(3)
    for col_idx, bey in enumerate(deck):
        ws = bey["Wilson Score"]
        bar_pct = int(ws * 100)

        def piece_row(label, val, fijado):
            icon  = "🔒" if fijado else "✨"
            color = "#cccccc" if fijado else "#F39C12"
            return (
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin:3px 0">' +
                f'<span style="color:#888;font-size:0.8em">{label}</span>' +
                f'<span style="color:{color};font-weight:600">{icon} {val}</span>' +
                '</div>'
            )

        bey_num = bey["Bey"]
        arq_v   = bey["Arquetipo victoria"]
        arq_d   = bey["Arquetipo derrota"]
        card = (
            '<div style="background:#1a1a2e;border-radius:12px;padding:18px;border:1px solid #2a2a4a">' +
            f'<div style="font-size:0.8em;color:#888;margin-bottom:10px">BEY {bey_num}</div>' +
            piece_row("Blade",   bey["Blade"],   bey["Blade fijada"])   +
            piece_row("Ratchet", bey["Ratchet"], bey["Ratchet fijado"]) +
            piece_row("Bit",     bey["Bit"],     bey["Bit fijado"])     +
            '<div style="margin:12px 0 4px">' +
            f'<div style="background:#2a2a4a;border-radius:4px;height:6px">' +
            f'<div style="background:#6EC1E4;width:{bar_pct}%;height:6px;border-radius:4px"></div>' +
            '</div></div>' +
            f'<div style="display:flex;justify-content:space-between;font-size:0.8em;color:#888">' +
            f'<span>Wilson Score</span><span style="color:#fff;font-weight:700">{ws:.4f}</span></div>' +
            '<div style="margin-top:10px;font-size:0.75em;color:#666">' +
            f'{arq_v} &nbsp;·&nbsp; {arq_d}' +
            '</div></div>'
        )

        with deck_cols[col_idx]:
            st.markdown(card, unsafe_allow_html=True)

    st.caption("🔒 Pieza elegida por ti · ✨ Sugerida por el sistema")

else:
    def label(val, fijado):
        return f"🔒 {val}" if fijado else f"✨ {val}"

    rows = []
    for bey in deck:
        rows.append({
            "Blade":              label(bey["Blade"],   bey["Blade fijada"]),
            "Ratchet":            label(bey["Ratchet"], bey["Ratchet fijado"]),
            "Bit":                label(bey["Bit"],     bey["Bit fijado"]),
            "Wilson Score":       bey["Wilson Score"],
            "Arquetipo victoria": bey["Arquetipo victoria"],
            "Arquetipo derrota":  bey["Arquetipo derrota"],
        })

    st.dataframe(
        pd.DataFrame(rows),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Wilson Score": st.column_config.ProgressColumn(
                "Wilson Score", format="%.4f", min_value=0, max_value=1,
            ),
            "Arquetipo victoria": st.column_config.TextColumn("Arquetipo victoria"),
            "Arquetipo derrota":  st.column_config.TextColumn("Arquetipo derrota"),
        },
    )
    st.caption("🔒 Pieza elegida por ti · ✨ Sugerida por el sistema")

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
        alt_cols = st.columns(len(df_alt))
        for col_idx, (_, alt) in enumerate(df_alt.iterrows()):
            alt_blade   = alt["Blade"]
            alt_ratchet = alt["Ratchet"]
            alt_bit     = alt["Bit"]
            delta = alt["Wilson Score Predicho"] - bey["Wilson Score"]
            signo = "+" if delta >= 0 else ""
            if delta > 0:
                delta_color = "#2ECC71"
            elif delta < 0:
                delta_color = "#E74C3C"
            else:
                delta_color = "#888888"

            def piece_html(label, val, ref):
                c = "#F39C12" if val != ref else "#cccccc"
                return f'<span style="color:{c};font-weight:600">{val}</span> <span style="color:#666;font-size:0.78em">{label}</span>'

            card = (
                '<div style="background:#1a1a2e;border-radius:10px;padding:14px 16px;border:1px solid #2a2a4a;margin-bottom:4px">' +
                '<div style="line-height:2em;margin-bottom:8px">' +
                piece_html("Blade",   alt_blade,   bey_blade)   + '<br>' +
                piece_html("Ratchet", alt_ratchet, bey_ratchet) + '<br>' +
                piece_html("Bit",     alt_bit,     bey_bit) +
                '</div>' +
                f'<div style="font-size:1.1em;font-family:monospace;font-weight:700;color:{delta_color}">{signo}{delta:.4f}</div>' +
                '</div>'
            )
            with alt_cols[col_idx]:
                st.markdown(card, unsafe_allow_html=True)