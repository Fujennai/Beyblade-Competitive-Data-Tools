import streamlit as st
import pandas as pd

from data.loader import load_data
from core.matchup import prob_victoria, pts_esperados, ws_ponderado, _cargar_pesos
from components.demo_button import boton_demo, combos_aleatorios

st.set_page_config(layout="wide")

st.title("⚔️ Calculadora de Matchup")

df = load_data()

pesos = _cargar_pesos()
st.caption(
    f"Selecciona dos combos para predecir quién tiene ventaja. "
    f"Pesos estimados: Blade {pesos['Blade']*100:.0f}% · "
    f"Ratchet {pesos['Ratchet']*100:.0f}% · "
    f"Bit {pesos['Bit']*100:.0f}%"
)

# ── Botón de demostración ─────────────────────────────────────────────────────
if boton_demo(
    key="demo_match",
    help_text="Elige dos combos reales aleatorios del dataset "
              "(ponderados por partidas) para mostrar el matchup.",
):
    combos = combos_aleatorios(df, n=2)
    if len(combos) >= 2:
        a, b = combos[0], combos[1]
        st.session_state["blade_a"]   = a["Blade"]
        st.session_state["ratchet_a"] = a["Ratchet"]
        st.session_state["bit_a"]     = a["Bit"]
        st.session_state["blade_b"]   = b["Blade"]
        st.session_state["ratchet_b"] = b["Ratchet"]
        st.session_state["bit_b"]     = b["Bit"]
        st.toast(
            f"🎬 A: {a['Blade']} / {a['Ratchet']} / {a['Bit']}  ·  "
            f"B: {b['Blade']} / {b['Ratchet']} / {b['Bit']}",
            icon="✨",
        )
    st.rerun()

# ── Selección de combos ───────────────────────────────────────────────────────
col_a, col_sep, col_b = st.columns([5, 1, 5])

with col_a:
    st.subheader("🔵 Combo A")
    blade_a   = st.selectbox("Blade",   ["—"] + sorted(df["Blade"].unique()),   key="blade_a")
    ratchet_a = st.selectbox("Ratchet", ["—"] + sorted(df["Ratchet"].unique()), key="ratchet_a")
    bit_a     = st.selectbox("Bit",     ["—"] + sorted(df["Bit"].unique()),     key="bit_a")

with col_sep:
    st.markdown("<div style='text-align:center;font-size:2em;margin-top:80px'>VS</div>", unsafe_allow_html=True)

with col_b:
    st.subheader("🔴 Combo B")
    blade_b   = st.selectbox("Blade",   ["—"] + sorted(df["Blade"].unique()),   key="blade_b")
    ratchet_b = st.selectbox("Ratchet", ["—"] + sorted(df["Ratchet"].unique()), key="ratchet_b")
    bit_b     = st.selectbox("Bit",     ["—"] + sorted(df["Bit"].unique()),     key="bit_b")

# ── Validar selección ─────────────────────────────────────────────────────────
combos_completos = all(v != "—" for v in [blade_a, ratchet_a, bit_a, blade_b, ratchet_b, bit_b])

if not combos_completos:
    st.info("🔎 Selecciona ambos combos completos para ver el análisis.")
    st.stop()

# ── Buscar datos en el dataset ────────────────────────────────────────────────
INSUFICIENTE = "⚪ Datos insuficientes"


def _arquetipo_mas_comun(df, col, val, columna_arq):
    """Devuelve el arquetipo más frecuente entre los combos que comparten la pieza."""
    s = df[(df[col] == val) & (df[columna_arq] != INSUFICIENTE)]
    if s.empty or columna_arq not in s.columns:
        return INSUFICIENTE
    mode = s[columna_arq].mode()
    return mode.iloc[0] if not mode.empty else INSUFICIENTE


def get_combo_data(df, blade, ratchet, bit):
    # Wilson Score ponderado por pieza
    ws_blade   = df[df["Blade"]   == blade  ]["Wilson Score"].mean() if blade   else 0.5
    ws_ratchet = df[df["Ratchet"] == ratchet]["Wilson Score"].mean() if ratchet else 0.5
    ws_bit     = df[df["Bit"]     == bit    ]["Wilson Score"].mean() if bit     else 0.5

    row = df[(df["Blade"] == blade) & (df["Ratchet"] == ratchet) & (df["Bit"] == bit)]
    if not row.empty:
        r = row.iloc[0]
        return {
            "ws":          ws_ponderado(ws_blade, ws_ratchet, ws_bit),
            "ws_raw":      float(r["Wilson Score"]),
            "pts_ganados": float(r["Pts Ganados/Combate"]),
            "pts_cedidos": float(r["Pts Cedidos/Combate"]),
            "winrate":     float(r["Win %"]),
            "partidas":    int(r["Partidas"]),
            "arq_v":       r.get("Arquetipo victoria", INSUFICIENTE),
            "arq_d":       r.get("Arquetipo derrota",  INSUFICIENTE),
            "real":        True,
        }
    # Combo no visto: estimar arquetipos a partir de la moda por Blade
    arq_v = _arquetipo_mas_comun(df, "Blade", blade, "Arquetipo victoria") if "Arquetipo victoria" in df.columns else INSUFICIENTE
    arq_d = _arquetipo_mas_comun(df, "Blade", blade, "Arquetipo derrota")  if "Arquetipo derrota"  in df.columns else INSUFICIENTE

    pts_g, pts_c = [], []
    for col, val in [("Blade", blade), ("Ratchet", ratchet), ("Bit", bit)]:
        s = df[df[col] == val]
        if not s.empty:
            pts_g.append(s["Pts Ganados/Combate"].mean())
            pts_c.append(s["Pts Cedidos/Combate"].mean())
    return {
        "ws":          ws_ponderado(ws_blade, ws_ratchet, ws_bit),
        "ws_raw":      None,
        "pts_ganados": round(float(sum(pts_g)/len(pts_g)), 3) if pts_g else 1.0,
        "pts_cedidos": round(float(sum(pts_c)/len(pts_c)), 3) if pts_c else 1.0,
        "winrate":     None,
        "partidas":    0,
        "arq_v":       arq_v,
        "arq_d":       arq_d,
        "real":        False,
    }

data_a = get_combo_data(df, blade_a, ratchet_a, bit_a)
data_b = get_combo_data(df, blade_b, ratchet_b, bit_b)

# ── Cálculo ───────────────────────────────────────────────────────────────────
p_a = prob_victoria(data_a["ws"], data_b["ws"])
p_b = 1 - p_a
pts_e_a, pts_e_b = pts_esperados(
    data_a["ws"], data_b["ws"],
    data_a["pts_ganados"], data_b["pts_ganados"]
)

st.divider()

# ── Resultado visual ──────────────────────────────────────────────────────────
ganador = "🔵 Combo A" if p_a > p_b else ("🔴 Combo B" if p_b > p_a else "⚖️ Empate técnico")
color_a = "#3498DB"
color_b = "#E74C3C"
bar_a   = int(p_a * 100)
bar_b   = int(p_b * 100)

resultado_html = f"""
<div style="background:#1a1a2e;border-radius:12px;padding:20px;border:1px solid #2a2a4a;margin-bottom:16px">
    <div style="text-align:center;font-size:1.1em;color:#aaa;margin-bottom:12px">Probabilidad de victoria</div>
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
        <span style="color:{color_a};font-weight:700;width:80px">{blade_a[:12]}</span>
        <div style="flex:1;background:#2a2a4a;border-radius:4px;height:22px;overflow:hidden">
            <div style="background:{color_a};width:{bar_a}%;height:100%;border-radius:4px;display:flex;align-items:center;padding-left:8px">
                <span style="color:#fff;font-size:0.85em;font-weight:700">{p_a*100:.1f}%</span>
            </div>
        </div>
    </div>
    <div style="display:flex;align-items:center;gap:10px">
        <span style="color:{color_b};font-weight:700;width:80px">{blade_b[:12]}</span>
        <div style="flex:1;background:#2a2a4a;border-radius:4px;height:22px;overflow:hidden">
            <div style="background:{color_b};width:{bar_b}%;height:100%;border-radius:4px;display:flex;align-items:center;padding-left:8px">
                <span style="color:#fff;font-size:0.85em;font-weight:700">{p_b*100:.1f}%</span>
            </div>
        </div>
    </div>
</div>
"""
st.markdown(resultado_html, unsafe_allow_html=True)

# ── Métricas ──────────────────────────────────────────────────────────────────
m1, m2, m3, m4 = st.columns(4)
m1.metric("Ventaja",           ganador)
m2.metric("Wilson Score A",    f"{data_a['ws']:.4f}", delta=f"{'✅ Real' if data_a['real'] else '🔮 Estimado'}")
m3.metric("Wilson Score B",    f"{data_b['ws']:.4f}", delta=f"{'✅ Real' if data_b['real'] else '🔮 Estimado'}")
m4.metric("Pts/combate esperados", f"A: {pts_e_a} · B: {pts_e_b}")

# ── Resultados probables basados en arquetipos ────────────────────────────────
st.divider()
st.subheader("🎲 Resultados probables del enfrentamiento")
st.caption(
    "Combinación de la probabilidad de victoria con el arquetipo de cada combo: "
    "cómo tiende a ganar el vencedor (Spin / Burst / Xtreme) y cómo tiende a perder "
    "el rival. Los pesos suman 100% entre los 6 resultados posibles."
)

# Distribución base por arquetipo de VICTORIA (orden: spin, burst, xtreme)
_PESOS_VICTORIA = {
    "🔵 Spin finish":            [0.70, 0.20, 0.10],
    "🟠 Burst / Over":           [0.20, 0.70, 0.10],
    "🟢 Xtreme finish":          [0.10, 0.20, 0.70],
    "⚫ Alta tendencia a perder": [0.34, 0.33, 0.33],
    INSUFICIENTE:                [0.34, 0.33, 0.33],
}
# Distribución base por arquetipo de DERROTA (qué finish te castiga más)
_PESOS_DERROTA = {
    "🔵 Pierde por spin":         [0.70, 0.20, 0.10],
    "🟠 Pierde por burst/over":   [0.20, 0.70, 0.10],
    "🟢 Pierde por xtreme":       [0.10, 0.20, 0.70],
    "🟡 Alta tendencia a ganar":  [0.34, 0.33, 0.33],
    INSUFICIENTE:                 [0.34, 0.33, 0.33],
}

_FINISH_LABELS = [
    ("Spin Finish",  "1 pt", "🔵"),
    ("Burst / Over", "2 pt", "🟠"),
    ("Xtreme Finish", "3 pt", "🟢"),
]


def _proba_finishes(arq_victoria, arq_derrota):
    """Promedia las preferencias del ganador y las debilidades del perdedor."""
    v = _PESOS_VICTORIA.get(arq_victoria, [0.34, 0.33, 0.33])
    d = _PESOS_DERROTA.get(arq_derrota,   [0.34, 0.33, 0.33])
    combinada = [(v[i] + d[i]) / 2 for i in range(3)]
    total = sum(combinada) or 1
    return [c / total for c in combinada]


fin_a = _proba_finishes(data_a["arq_v"], data_b["arq_d"])
fin_b = _proba_finishes(data_b["arq_v"], data_a["arq_d"])

resultados = []
for i, (finish, pts, emoji) in enumerate(_FINISH_LABELS):
    resultados.append({
        "actor": "🔵 Combo A", "color": color_a, "label": f"{emoji} {finish}",
        "pts": pts, "prob": p_a * fin_a[i],
    })
for i, (finish, pts, emoji) in enumerate(_FINISH_LABELS):
    resultados.append({
        "actor": "🔴 Combo B", "color": color_b, "label": f"{emoji} {finish}",
        "pts": pts, "prob": p_b * fin_b[i],
    })

resultados.sort(key=lambda r: r["prob"], reverse=True)

for idx, r in enumerate(resultados):
    pct      = r["prob"] * 100
    bar_pct  = max(1, int(pct))
    medalla  = "🥇" if idx == 0 else ("🥈" if idx == 1 else ("🥉" if idx == 2 else f"#{idx+1}"))
    card = (
        f'<div style="background:#1a1a2e;border-radius:10px;padding:10px 14px;'
        f'border:1px solid #2a2a4a;margin-bottom:6px">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
        f'<span style="color:#888;font-weight:700;font-size:0.85em">{medalla}</span>'
        f'<span style="color:{r["color"]};font-weight:700">{r["actor"]} gana por {r["label"]}</span>'
        f'<span style="color:#666;font-size:0.78em">{r["pts"]}</span>'
        f'<span style="color:#fff;font-family:monospace;font-weight:700;min-width:60px;text-align:right">{pct:.1f}%</span>'
        f'</div>'
        f'<div style="background:#2a2a4a;border-radius:4px;height:5px">'
        f'<div style="background:{r["color"]};width:{bar_pct}%;height:5px;border-radius:4px"></div>'
        f'</div></div>'
    )
    st.markdown(card, unsafe_allow_html=True)

with st.expander("ℹ️ ¿Cómo se calculan estas probabilidades?"):
    st.markdown(
        """
- Se parte de **P(A gana)** y **P(B gana)** (Wilson Score relativo).
- A cada combo se le asigna una distribución sobre tipos de finish según
  su **arquetipo de victoria** (cómo suele ganar):
  - 🔵 Spin finish → 70% spin · 20% burst · 10% xtreme
  - 🟠 Burst / Over → 20% spin · 70% burst · 10% xtreme
  - 🟢 Xtreme finish → 10% spin · 20% burst · 70% xtreme
  - ⚪ Sin datos → distribución uniforme
- Se modula con el **arquetipo de derrota** del rival (por qué finish suele perder),
  usando la misma escala. Las dos distribuciones se promedian.
- Para cada uno de los 6 desenlaces posibles:
  `P(actor gana por finish) = P(actor gana) × P(finish | arquetipos)`.
        """
    )

# ── Detalle por combo ─────────────────────────────────────────────────────────
st.divider()
col1, col2 = st.columns(2)

for col, data, blade, ratchet, bit, color, label in [
    (col1, data_a, blade_a, ratchet_a, bit_a, color_a, "A"),
    (col2, data_b, blade_b, ratchet_b, bit_b, color_b, "B"),
]:
    with col:
        tipo = "✅ Datos reales" if data["real"] else "🔮 Estimado"
        wr_str = f"{data['winrate']:.1f}%" if data["winrate"] else "—"
        st.markdown(
            f'<div style="border-left:3px solid {color};padding-left:12px">'
            f'<div style="font-weight:700;font-size:1em">{blade} / {ratchet} / {bit}</div>'
            f'<div style="color:#888;font-size:0.85em;margin-top:4px">{tipo} · {data["partidas"]} partidas</div>'
            f'<div style="color:#aaa;font-size:0.85em;margin-top:4px">'
            f'Winrate histórico: {wr_str} &nbsp;·&nbsp; '
            f'Pts ganados/combate: {data["pts_ganados"]} &nbsp;·&nbsp; '
            f'Pts cedidos/combate: {data["pts_cedidos"]}'
            f'</div></div>',
            unsafe_allow_html=True
        )