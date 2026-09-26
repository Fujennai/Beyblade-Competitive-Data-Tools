import streamlit as st
import pandas as pd

from data.loader import load_data
from core.matchup import prob_victoria
from core.deck_match import DeckMatch, ORDENES
from components.demo_button import boton_autorellenar, deck_aleatorio
from core.compatibility import ratchet_repetido, blade_repetido, ratchets_validos, blades_con_ux_expanded

st.set_page_config(layout="wide")

st.title("🏟️ Simulador de Deck Match")

df = load_data()

st.caption("Introduce los dos decks y calcula quién tiene más probabilidades de ganar y cómo ordenar tus beys en cada ronda.")

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

# ── Autorrelleno por bando ────────────────────────────────────────────────────
def _autorellenar_deck(prefix):
    """Rellena un deck con 3 combos reales aleatorios, sin copiar combos del otro deck."""
    otro = "rival" if prefix == "mio" else "mio"
    combos_otro = [
        tuple(st.session_state.get(f"{otro}_{p}_{i}", "—") for p in ("blade", "ratchet", "bit"))
        for i in range(3)
    ]
    deck = deck_aleatorio(df, n=3, excluir=combos_otro)
    if not deck:
        st.toast("❌ No se encontraron suficientes combos únicos. Inténtalo de nuevo.", icon="⚠️")
        return
    for i, (blade, ratchet, bit) in enumerate(deck):
        st.session_state[f"{prefix}_blade_{i}"]   = blade
        st.session_state[f"{prefix}_ratchet_{i}"] = ratchet
        st.session_state[f"{prefix}_bit_{i}"]     = bit
    nombre = "Mi deck" if prefix == "mio" else "Deck rival"
    st.toast(f"🎲 {nombre} autorellenado.", icon="✨")


_AUTO_HELP = "Rellena este deck con 3 combos reales aleatorios del dataset (ponderados por partidas)."

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
        boton_autorellenar(key=f"auto_dm_{prefix}", help_text=_AUTO_HELP, on_click=_autorellenar_deck, args=(prefix,))
        for i in range(3):
            st.markdown(f"**Bey {i+1}**")
            c1, c2, c3 = st.columns(3)

            # Excluir Blades ya seleccionadas EN EL MISMO DECK (pero NO en el otro)
            blades_usadas = get_piezas_seleccionadas_deck("blade", i, prefix)
            blade_opts = sorted([b for b in df["Blade"].unique() if not blade_repetido(b, blades_usadas)])
            blade = c1.selectbox("Blade", ["—"] + blade_opts, key=f"{prefix}_blade_{i}")

            # Excluir Ratchets ya seleccionados EN EL MISMO DECK
            ratchets_usados = get_piezas_seleccionadas_deck("ratchet", i, prefix)
            base_ratchets = (ratchets_validos(blade, sorted(df["Ratchet"].unique()), blades_con_ux_expanded(df))
                             if blade != "—" else sorted(df["Ratchet"].unique()))
            ratchet_opts = [r for r in base_ratchets if not ratchet_repetido(r, ratchets_usados)]
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

# ── Cálculo exacto ────────────────────────────────────────────────────────────
st.divider()

# P(A gana un combate): provisional, pendiente del punto 8 (modelo de fuerza)
dm = DeckMatch(deck_mio, deck_rival, lambda a, b: prob_victoria(a["ws"], b["ws"]))

with st.spinner("Calculando deck match..."):
    p_mio, x_mio, y_rival = dm.estrategias(0, 0)
    p_azar = dm.valor_azar(0, 0)
    M0 = dm.matriz(0, 0)
p_rival = 1 - p_mio


def _orden_txt(orden, deck):
    return " → ".join(deck[i]["nombre"].split(" / ")[0] for i in orden)


# ── Resultado visual ──────────────────────────────────────────────────────────
bar_mio   = int(p_mio * 100)
bar_rival = int(p_rival * 100)

st.markdown(f"""
<div style="background:#1a1a2e;border-radius:12px;padding:20px;border:1px solid #2a2a4a;margin-bottom:16px">
    <div style="text-align:center;font-size:1.1em;color:#aaa;margin-bottom:12px">Probabilidad de ganar el deck match (ambos eligiendo bien el orden)</div>
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

st.caption(f"Si ambos eligieran el orden al azar en cada ronda: **{p_azar*100:.1f}%** para mi deck.")

st.divider()

# ── Orden en la 1ª ronda ──────────────────────────────────────────────────────
st.subheader("📋 Orden en la primera ronda")

# No suponemos que el rival juegue óptimo: puntuamos cada orden contra un rival
# que puede elegir cualquier orden (media) y desempatamos por el peor caso.
media = M0.mean(axis=1)
peor = M0.min(axis=1)
ranking = sorted(range(6), key=lambda k: (media[k], peor[k]), reverse=True)
mejor = ranking[0]
rango = (media.max() - media.min()) * 100

st.success(f"Orden recomendado: **{_orden_txt(ORDENES[mejor], deck_mio)}**")
if rango < 1.0:
    st.caption(
        f"🎲 La ventaja es pequeña (como mucho {rango:.1f} puntos entre el mejor y el peor orden), "
        "pero es el que mejor rinde frente a cualquier orden del rival."
    )

with st.expander("📊 Comparar los 6 órdenes"):
    st.dataframe(
        pd.DataFrame([
            {
                "Mi orden": _orden_txt(ORDENES[k], deck_mio),
                "P(ganar) vs rival cualquiera": media[k] * 100,
                "P(ganar) peor caso": peor[k] * 100,
                "Frecuencia teórica óptima": float(x_mio[k]) * 100,
            }
            for k in ranking
        ]),
        use_container_width=True, hide_index=True,
        column_config={
            "P(ganar) vs rival cualquiera": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100),
            "P(ganar) peor caso": st.column_config.NumberColumn(format="%.1f%%"),
            "Frecuencia teórica óptima": st.column_config.NumberColumn(format="%.0f%%"),
        },
    )
    st.caption(
        "«Rival cualquiera»: media contra los 6 órdenes posibles del rival (no se asume que juegue óptimo). "
        "«Peor caso»: si el rival acertara el mejor orden contra el tuyo. "
        "«Frecuencia teórica»: cómo repartir el orden si el rival jugara perfecto (teoría de juegos)."
    )

# ── Mejor respuesta si intuyes el orden del rival ─────────────────────────────
with st.expander("🔍 ¿Intuyes el orden del rival?"):
    opciones = {_orden_txt(o, deck_rival): o for o in ORDENES}
    sel = st.selectbox("Orden del rival en la 1ª ronda", list(opciones), key="dm_orden_rival")
    respuesta = dm.mejor_respuesta(opciones[sel])
    st.dataframe(
        pd.DataFrame([
            {"Mi orden": _orden_txt(o, deck_mio), "P(ganar)": p * 100} for o, p in respuesta
        ]),
        use_container_width=True, hide_index=True,
        column_config={"P(ganar)": st.column_config.ProgressColumn(format="%.1f%%", min_value=0, max_value=100)},
    )

# ── Estrategia según marcador ─────────────────────────────────────────────────
st.subheader("🧮 Estrategia según el marcador")
st.caption(
    "Si tras una ronda nadie llega a 4 puntos, ambos eligen un orden nuevo sabiendo el marcador. "
    "La recomendación cambia según cómo vaya la partida. Jugar bien puede dar menos que el azar "
    "porque el rival también juega bien."
)

filas = []
for sa, sb in dm.marcadores_posibles():
    v, x, _ = dm.estrategias(sa, sb)
    M = dm.matriz(sa, sb)
    mejores = sorted([(ORDENES[k], float(x[k])) for k in range(6) if x[k] > 0.01],
                     key=lambda t: t[1], reverse=True)
    if (M.max() - M.min()) * 100 < 1.0:
        rec = "Indiferente"
    elif len(mejores) == 1:
        rec = _orden_txt(mejores[0][0], deck_mio)
    else:
        rec = " | ".join(f"{p*100:.0f}% {_orden_txt(o, deck_mio)}" for o, p in mejores)
    filas.append({
        "Marcador (yo-rival)": f"{sa}-{sb}",
        "P(ganar) si ambos juegan bien": v * 100,
        "P(ganar) si ambos eligen al azar": dm.valor_azar(sa, sb) * 100,
        "Orden recomendado": rec,
    })

st.dataframe(
    pd.DataFrame(filas), use_container_width=True, hide_index=True,
    column_config={
        "P(ganar) si ambos juegan bien": st.column_config.NumberColumn(format="%.1f%%"),
        "P(ganar) si ambos eligen al azar": st.column_config.NumberColumn(format="%.1f%%"),
        "Orden recomendado": st.column_config.TextColumn(width="large"),
    },
)

with st.expander("ℹ️ Supuestos del cálculo"):
    st.markdown("""
- **Formato**: ambos cambian de bey tras cada combate; primero a 4 puntos; si nadie llega tras 3 combates,
  se elige un orden nuevo conociendo el marcador. Sin empates. Spin 1 · Burst/Over 2 · Xtreme 3.
- **Cálculo exacto** (no simulación): cada ronda es un juego de suma cero entre los 6 órdenes de cada jugador,
  resuelto por programación lineal. "Jugando bien" = ambos eligen de forma óptima.
- **Puntos por combate**: media entre los puntos por victoria del ganador y los que suele ceder el perdedor,
  repartida entre los dos valores enteros más cercanos (p.ej. 1,3 → 70% spin, 30% burst/over).
  Solo tenemos medias, no el desglose de finishes.
- **Probabilidad de ganar un combate**: provisional (Wilson relativo). No hay datos de enfrentamientos
  directos, así que no se capturan counters específicos entre combos; por eso el orden suele influir poco.
""")
