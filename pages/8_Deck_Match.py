import streamlit as st
import pandas as pd
from itertools import permutations

from data.loader import load_data
from core.matchup import simular_deck_match, orden_optimo
from components.demo_button import boton_demo, combos_aleatorios

st.set_page_config(layout="wide")

st.title("🏟️ Simulador de Deck Match")

df = load_data()

st.caption("Introduce los dos decks y simula quién tiene más probabilidades de ganar. Indica cuál es el tuyo para ver el orden óptimo.")

# ── Función auxiliar: obtener piezas ya seleccionadas en un deck ──
def get_piezas_seleccionadas_deck(tipo_pieza, excluir_pos, prefix):
    """Retorna lista de piezas del tipo especificado ya seleccionadas en otros Beys del mismo deck"""
    piezas = []
    for j in range(3):
        if j != excluir_pos:
            pieza = st.session_state.get(f"{prefix}_{tipo_pieza}_{j}", "—")
            if pieza != "—":
                piezas.append(pieza)
    return piezas

# ── Botón de demostración ─────────────────────────────────────────────────────
if boton_demo(
    key="demo_dm",
    help_text="Rellena los dos decks con 6 combos reales aleatorios "
              "(ponderados por partidas) para mostrar la simulación.",
):
    blades_mio = []
    ratchets_mio = []
    bits_mio = []
    blades_rival = []
    ratchets_rival = []
    bits_rival = []
    intentos = 0
    max_intentos = 5

    # Intentar varias veces para encontrar 6 combos únicos (3 por deck, sin repeticiones dentro de cada deck)
    while (len(blades_mio) < 3 or len(blades_rival) < 3) and intentos < max_intentos:
        intentos += 1
        combos = combos_aleatorios(df, n=50)  # Margen amplio para garantizar diversidad

        # Extraer 3 combos únicos para mio
        if len(blades_mio) < 3:
            for c in combos:
                blade = c["Blade"]
                ratchet = c["Ratchet"]
                bit = c["Bit"]

                if blade not in blades_mio and ratchet not in ratchets_mio and bit not in bits_mio:
                    blades_mio.append(blade)
                    ratchets_mio.append(ratchet)
                    bits_mio.append(bit)

                if len(blades_mio) == 3:
                    break

        # Extraer 3 combos únicos para rival:
        # - Sin repetir piezas dentro de rival.
        # - Sin coincidir exactamente (Blade + Ratchet + Bit) con ningún combo de mi deck.
        if len(blades_rival) < 3:
            combos_mio = list(zip(blades_mio, ratchets_mio, bits_mio))
            for c in combos:
                blade = c["Blade"]
                ratchet = c["Ratchet"]
                bit = c["Bit"]

                # Evitar combo exacto ya presente en mi deck
                if (blade, ratchet, bit) in combos_mio:
                    continue

                if blade not in blades_rival and ratchet not in ratchets_rival and bit not in bits_rival:
                    blades_rival.append(blade)
                    ratchets_rival.append(ratchet)
                    bits_rival.append(bit)

                if len(blades_rival) == 3:
                    break

    if len(blades_mio) == 3 and len(blades_rival) == 3:
        # Asignar a mi deck
        for i in range(3):
            st.session_state[f"mio_blade_{i}"]   = blades_mio[i]
            st.session_state[f"mio_ratchet_{i}"] = ratchets_mio[i]
            st.session_state[f"mio_bit_{i}"]     = bits_mio[i]

        # Asignar a rival
        for i in range(3):
            st.session_state[f"rival_blade_{i}"]   = blades_rival[i]
            st.session_state[f"rival_ratchet_{i}"] = ratchets_rival[i]
            st.session_state[f"rival_bit_{i}"]     = bits_rival[i]

        st.toast("🎬 Demo: 6 combos reales asignados a ambos decks.", icon="✨")
        st.rerun()
    else:
        # Si falla, mostrar error
        st.error(f"❌ No se encontraron suficientes combos únicos. Intenta de nuevo o selecciona manualmente.")
        st.stop()

# ── Helper ────────────────────────────────────────────────────────────────────
def get_combo_data(df, blade, ratchet, bit, nombre):
    row = df[(df["Blade"] == blade) & (df["Ratchet"] == ratchet) & (df["Bit"] == bit)]
    if not row.empty:
        r = row.iloc[0]
        return {
            "nombre":      nombre,
            "ws":          float(r["Wilson Score"]),
            "pts_ganados": float(r["Pts Ganados/Combate"]),
            "pts_cedidos": float(r["Pts Cedidos/Combate"]),
            "real":        True,
        }
    ws_vals, pts_g, pts_c = [], [], []
    for col, val in [("Blade", blade), ("Ratchet", ratchet), ("Bit", bit)]:
        s = df[df[col] == val]
        if not s.empty:
            ws_vals.append(s["Wilson Score"].mean())
            pts_g.append(s["Pts Ganados/Combate"].mean())
            pts_c.append(s["Pts Cedidos/Combate"].mean())
    return {
        "nombre":      nombre,
        "ws":          round(float(sum(ws_vals)/len(ws_vals)), 4) if ws_vals else 0.5,
        "pts_ganados": round(float(sum(pts_g)/len(pts_g)), 3)    if pts_g   else 1.0,
        "pts_cedidos": round(float(sum(pts_c)/len(pts_c)), 3)    if pts_c   else 1.0,
        "real":        False,
    }

# ── Selección de decks ────────────────────────────────────────────────────────
col_mio, col_rival = st.columns(2)

deck_mio   = []
deck_rival = []
completo   = True

for col, deck_list, prefix, label in [
    (col_mio,   deck_mio,   "mio",   "🔵 Mi deck"),
    (col_rival, deck_rival, "rival", "🔴 Deck rival"),
]:
    with col:
        st.subheader(label)
        for i in range(3):
            st.markdown(f"**Bey {i+1}**")
            c1, c2, c3 = st.columns(3)

            # Excluir Blades ya seleccionadas EN EL MISMO DECK (pero NO en el otro)
            blades_usadas = get_piezas_seleccionadas_deck("blade", i, prefix)
            blade_opts = sorted([b for b in df["Blade"].unique() if b not in blades_usadas])
            blade = c1.selectbox("Blade", ["—"] + blade_opts, key=f"{prefix}_blade_{i}")

            # Excluir Ratchets ya seleccionados EN EL MISMO DECK
            ratchets_usados = get_piezas_seleccionadas_deck("ratchet", i, prefix)
            ratchet_opts = sorted([r for r in df["Ratchet"].unique() if r not in ratchets_usados])
            ratchet = c2.selectbox("Ratchet", ["—"] + ratchet_opts, key=f"{prefix}_ratchet_{i}")

            # Excluir Bits ya seleccionados EN EL MISMO DECK
            bits_usados = get_piezas_seleccionadas_deck("bit", i, prefix)
            bit_opts = sorted([b for b in df["Bit"].unique() if b not in bits_usados])
            bit = c3.selectbox("Bit", ["—"] + bit_opts, key=f"{prefix}_bit_{i}")

            if any(v == "—" for v in [blade, ratchet, bit]):
                completo = False
            else:
                nombre = f"{blade} / {ratchet} / {bit}"
                deck_list.append(get_combo_data(df, blade, ratchet, bit, nombre))

if not completo or len(deck_mio) < 3 or len(deck_rival) < 3:
    st.info("🔎 Completa los dos decks para ver la simulación.")
    st.stop()

# ── Simulación global ─────────────────────────────────────────────────────────
st.divider()

with st.spinner("Simulando deck match..."):
    # Probabilidad global: promedio sobre todos los órdenes de ambos decks
    todas_probs = []
    for mp in permutations(range(3)):
        for rp in permutations(range(3)):
            mi_orden    = [deck_mio[i]   for i in mp]
            rival_orden = [deck_rival[i] for i in rp]
            todas_probs.append(simular_deck_match(mi_orden, rival_orden, n_sims=2000))

    p_mio   = round(sum(todas_probs) / len(todas_probs), 4)
    p_rival = round(1 - p_mio, 4)

# ── Resultado visual ──────────────────────────────────────────────────────────
bar_mio   = int(p_mio * 100)
bar_rival = int(p_rival * 100)

st.markdown(f"""
<div style="background:#1a1a2e;border-radius:12px;padding:20px;border:1px solid #2a2a4a;margin-bottom:16px">
    <div style="text-align:center;font-size:1.1em;color:#aaa;margin-bottom:12px">Probabilidad de ganar el deck match</div>
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
        <span style="color:#3498DB;font-weight:700;width:80px">Mi deck</span>
        <div style="flex:1;background:#2a2a4a;border-radius:4px;height:22px;overflow:hidden">
            <div style="background:#3498DB;width:{bar_mio}%;height:100%;border-radius:4px;display:flex;align-items:center;padding-left:8px">
                <span style="color:#fff;font-size:0.85em;font-weight:700">{p_mio*100:.1f}%</span>
            </div>
        </div>
    </div>
    <div style="display:flex;align-items:center;gap:10px">
        <span style="color:#E74C3C;font-weight:700;width:80px">Rival</span>
        <div style="flex:1;background:#2a2a4a;border-radius:4px;height:22px;overflow:hidden">
            <div style="background:#E74C3C;width:{bar_rival}%;height:100%;border-radius:4px;display:flex;align-items:center;padding-left:8px">
                <span style="color:#fff;font-size:0.85em;font-weight:700">{p_rival*100:.1f}%</span>
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Orden óptimo ──────────────────────────────────────────────────────────────
st.subheader("📋 Orden óptimo de mi deck")
st.caption("Ordenado por probabilidad media de ganar contra cualquier orden del rival.")

with st.spinner("Calculando orden óptimo..."):
    ranking = orden_optimo(deck_mio, deck_rival, n_sims=2000)

for rank_idx, (perm, orden, prob) in enumerate(ranking):
    color_rank = "#2ECC71" if rank_idx == 0 else "#888"
    tag = " 👑 Óptimo" if rank_idx == 0 else ""

    beys_html = "".join([
        f'<div style="font-size:0.85em;color:#aaa;margin:2px 0">'
        f'<span style="color:#666">Bey {j+1}</span> &nbsp; '
        f'<span style="color:#fff;font-weight:600">{b["nombre"]}</span>'
        f'{"<span style=\'color:#888;font-size:0.8em\'> · estimado</span>" if not b["real"] else ""}'
        f'</div>'
        for j, b in enumerate(orden)
    ])

    card = (
        f'<div style="background:#1a1a2e;border-radius:10px;padding:14px 16px;'
        f'border:1px solid {"#2ECC71" if rank_idx == 0 else "#2a2a4a"};margin-bottom:8px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">'
        f'<span style="color:{color_rank};font-weight:700">#{rank_idx+1}{tag}</span>'
        f'<span style="color:{color_rank};font-family:monospace;font-weight:700">{prob*100:.1f}% de victorias</span>'
        f'</div>'
        f'{beys_html}'
        f'</div>'
    )
    st.markdown(card, unsafe_allow_html=True)

st.caption(
    "La probabilidad se calcula promediando contra todos los posibles órdenes del rival. "
    "El bey 3 puede no jugarse si se alcanzan 4 puntos antes."
)