import streamlit as st
import pandas as pd

from data.loader import load_data
from core.matchup import prob_victoria, pts_esperados

st.set_page_config(layout="wide")

st.title("⚔️ Calculadora de Matchup")

df = load_data()

st.caption("Selecciona dos combos para predecir quién tiene ventaja y con qué probabilidad.")

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
def get_combo_data(df, blade, ratchet, bit):
    row = df[(df["Blade"] == blade) & (df["Ratchet"] == ratchet) & (df["Bit"] == bit)]
    if not row.empty:
        r = row.iloc[0]
        return {
            "ws":          float(r["Wilson Score"]),
            "pts_ganados": float(r["Pts Ganados/Combate"]),
            "pts_cedidos": float(r["Pts Cedidos/Combate"]),
            "winrate":     float(r["Win %"]),
            "partidas":    int(r["Partidas"]),
            "real":        True,
        }
    # Estimado por piezas
    ws_vals = []
    pts_g, pts_c = [], []
    for col, val in [("Blade", blade), ("Ratchet", ratchet), ("Bit", bit)]:
        s = df[df[col] == val]
        if not s.empty:
            ws_vals.append(s["Wilson Score"].mean())
            pts_g.append(s["Pts Ganados/Combate"].mean())
            pts_c.append(s["Pts Cedidos/Combate"].mean())
    return {
        "ws":          round(float(sum(ws_vals) / len(ws_vals)), 4) if ws_vals else 0.5,
        "pts_ganados": round(float(sum(pts_g) / len(pts_g)), 3) if pts_g else 1.0,
        "pts_cedidos": round(float(sum(pts_c) / len(pts_c)), 3) if pts_c else 1.0,
        "winrate":     None,
        "partidas":    0,
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