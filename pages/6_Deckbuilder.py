import streamlit as st
import pandas as pd

from data.loader import load_data
from core.deckbuilder import optimizar_deck
from core.compatibility import (
    ratchets_validos, ratchet_repetido, blade_repetido, assist_repetido,
    assists_validos, reglas_desde, nombre_blade,
)
from components.view_toggle import view_toggle
from components.demo_button import boton_autorellenar, combos_aleatorios

st.set_page_config(layout="wide")

st.title("🧩 Deckbuilder")

df = load_data()

st.caption(
    "Fija las piezas que quieras para cada bey. "
    "El sistema completa el resto optimizando el deck en conjunto. "
    "🔒 = elegido por ti · ✨ = sugerido por el sistema"
)

reglas = reglas_desde(df)
TODOS_ASSISTS = sorted(a for a in df["Assist"].unique() if a)


# ── Función auxiliar: obtener piezas ya seleccionadas (excluyendo posición actual) ──
def get_piezas_seleccionadas(tipo_pieza, excluir_pos):
    """Retorna lista de piezas del tipo especificado ya seleccionadas en otros Beys"""
    piezas = []
    for j in range(3):
        if j != excluir_pos:
            pieza = st.session_state.get(f"{tipo_pieza}_{j}", "—")
            if pieza != "—":
                piezas.append(pieza)
    return piezas


def _sanear(key, opciones):
    """Si el valor guardado ya no es una opción válida (p.ej. cambió el Blade), vuelve a "—"."""
    if st.session_state.get(key, "—") not in opciones:
        st.session_state[key] = "—"


# ── Botón de autorrelleno ─────────────────────────────────────────────────────
if boton_autorellenar(
    key="demo_db",
    help_text="Fija 3 Blades aleatorios de combos reales del dataset "
              "(ponderados por partidas) para que el optimizador construya el deck.",
):
    combos_usados = []   # (blade, assist)
    ratchets_usados = []
    bits_usados = []
    intentos = 0
    max_intentos = 5

    # Intentar varias veces para encontrar 3 combos únicos
    while len(combos_usados) < 3 and intentos < max_intentos:
        intentos += 1
        combos = combos_aleatorios(df, n=30)  # Margen amplio para garantizar diversidad

        for c in combos:
            blade, assist = c["Blade"], c["Assist"]
            ratchet = c["Ratchet"]
            bit = c["Bit"]

            # Verificar que no repite ninguna pieza física
            if (not blade_repetido(blade, assist, combos_usados)
                    and not ratchet_repetido(ratchet, ratchets_usados)
                    and bit not in bits_usados):
                combos_usados.append((blade, assist))
                ratchets_usados.append(ratchet)
                bits_usados.append(bit)

            if len(combos_usados) == 3:
                break

    if len(combos_usados) == 3:
        # Fijar solo los 3 Blades y dejar Assist + Ratchet + Bit sin fijar
        # para que el optimizador haga su trabajo.
        for i in range(3):
            st.session_state[f"blade_{i}"]   = combos_usados[i][0]
            st.session_state[f"assist_{i}"]  = "—"
            st.session_state[f"ratchet_{i}"] = "—"
            st.session_state[f"bit_{i}"]     = "—"
        st.toast(f"🎲 Autorellenado: {', '.join(b for b, _ in combos_usados)}", icon="✨")
        st.rerun()
    else:
        # Si falla, mostrar error
        st.error(f"❌ No se encontraron suficientes combos únicos. Intenta de nuevo o selecciona manualmente.")
        st.stop()

# ── Selección del usuario ─────────────────────────────────────────────────────
st.subheader("🎯 Piezas fijadas")
st.caption("El Assist solo se aplica a los CX y cualquier Assist sirve para cualquier CX.")

fijados = []

for i in range(3):
    st.markdown(f"**Bey {i+1}**")
    col1, col1b, col2, col3 = st.columns([3, 2, 2, 3])

    with col1:
        # Excluir Blades que comparten pieza física con las de otros Beys.
        # Con un Assist fijado solo tienen sentido los CX.
        otras_blades = [(b, "") for b in get_piezas_seleccionadas("blade", i)]
        assist_fijado = st.session_state.get(f"assist_{i}", "—") != "—"
        blade_opts = sorted([
            b for b in df["Blade"].unique()
            if not blade_repetido(b, "", otras_blades, reglas.cx)
            and (not assist_fijado or b in reglas.cx)
        ])
        _sanear(f"blade_{i}", ["—"] + blade_opts)

        blade = st.selectbox(
            f"Blade {i+1}",
            ["—"] + blade_opts,
            key=f"blade_{i}"
        )

    with col1b:
        # Assist: solo CX y sin repetir los de otros Beys
        assists_usados = get_piezas_seleccionadas("assist", i)
        base_assists = (TODOS_ASSISTS if blade == "—"
                        else [a for a in assists_validos(blade, TODOS_ASSISTS, reglas.cx) if a])
        assist_opts = [a for a in base_assists if not assist_repetido(a, assists_usados)]
        _sanear(f"assist_{i}", ["—"] + assist_opts)

        assist = st.selectbox(
            f"Assist {i+1}",
            ["—"] + assist_opts,
            key=f"assist_{i}",
            disabled=blade != "—" and blade not in reglas.cx,
            help="Solo CX",
        )

    with col2:
        r_opts = ratchets_validos(
            blade,
            sorted(df["Ratchet"].unique()),
            reglas.ux,
        ) if blade != "—" else sorted(df["Ratchet"].unique())

        # Excluir Ratchets ya seleccionados en otros Beys
        ratchets_usados = get_piezas_seleccionadas("ratchet", i)
        r_opts = [r for r in r_opts if not ratchet_repetido(r, ratchets_usados)]
        _sanear(f"ratchet_{i}", ["—"] + r_opts)

        ratchet = st.selectbox(
            f"Ratchet {i+1}",
            ["—"] + r_opts,
            key=f"ratchet_{i}"
        )

    with col3:
        # Excluir Bits ya seleccionados en otros Beys
        bits_usados = get_piezas_seleccionadas("bit", i)
        bit_opts = sorted([b for b in df["Bit"].unique() if b not in bits_usados])
        _sanear(f"bit_{i}", ["—"] + bit_opts)

        bit = st.selectbox(
            f"Bit {i+1}",
            ["—"] + bit_opts,
            key=f"bit_{i}"
        )

    bey = {}
    if blade   != "—": bey["Blade"]   = blade
    if assist  != "—": bey["Assist"]  = assist
    if ratchet != "—": bey["Ratchet"] = ratchet
    if bit     != "—": bey["Bit"]     = bit
    fijados.append(bey)

st.divider()

# ── Optimización: leer total directamente del session_state ───────────────────
total_fijadas = sum(
    (1 if st.session_state.get(f"blade_{i}",   "—") != "—" else 0) +
    (1 if st.session_state.get(f"assist_{i}",  "—") != "—" else 0) +
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
            (piece_row("Assist", bey["Assist"], bey["Assist fijado"]) if bey["Assist"] else "") +
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
            "Assist":             label(bey["Assist"],  bey["Assist fijado"]) if bey["Assist"] else "",
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

for i, bey in enumerate(deck):
    blade_fijada   = bey["Blade fijada"]
    assist_fijado  = bey["Assist fijado"]
    ratchet_fijado = bey["Ratchet fijado"]
    bit_fijado     = bey["Bit fijado"]
    if blade_fijada and ratchet_fijado and bit_fijado and (assist_fijado or not bey["Assist"]):
        continue

    bey_num    = bey["Bey"]
    bey_blade  = bey["Blade"]
    bey_assist = bey["Assist"]
    bey_ratchet= bey["Ratchet"]
    bey_bit    = bey["Bit"]
    st.markdown(f"**Bey {bey_num} — {nombre_blade(bey_blade, bey_assist)} / {bey_ratchet} / {bey_bit}**")

    # Obtener alternativas manteniendo las piezas fijadas de este bey
    df_alt = recomendar_builds(
        df,
        bey_blade   if blade_fijada   else None,
        bey_ratchet if ratchet_fijado else None,
        bey_bit     if bit_fijado     else None,
        top_n=50,
        assist=bey_assist if assist_fijado else None,
    )

    # Excluir el combo ya recomendado y piezas usadas en otros beys
    otros = [b for j, b in enumerate(deck) if j != i]
    otras_blades   = [(b["Blade"], b["Assist"]) for b in otros]
    otros_ratchets = [b["Ratchet"] for b in otros]
    otros_bits     = [b["Bit"]     for b in otros]

    if not df_alt.empty:
        df_alt = df_alt[[
            not blade_repetido(r["Blade"], r["Assist"], otras_blades)
            and not ratchet_repetido(r["Ratchet"], otros_ratchets)
            and r["Bit"] not in otros_bits
            and (r["Blade"], r["Assist"], r["Ratchet"], r["Bit"])
                != (bey_blade, bey_assist, bey_ratchet, bey_bit)
            for _, r in df_alt.iterrows()
        ]].head(3)

    if df_alt.empty:
        st.caption("No hay alternativas disponibles.")
    else:
        alt_cols = st.columns(len(df_alt))
        for col_idx, (_, alt) in enumerate(df_alt.iterrows()):
            alt_blade   = alt["Blade"]
            alt_assist  = alt["Assist"]
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
                (piece_html("Assist", alt_assist, bey_assist) + '<br>' if alt_assist else '') +
                piece_html("Ratchet", alt_ratchet, bey_ratchet) + '<br>' +
                piece_html("Bit",     alt_bit,     bey_bit) +
                '</div>' +
                f'<div style="font-size:1.1em;font-family:monospace;font-weight:700;color:{delta_color}">{signo}{delta:.4f}</div>' +
                '</div>'
            )
            with alt_cols[col_idx]:
                st.markdown(card, unsafe_allow_html=True)