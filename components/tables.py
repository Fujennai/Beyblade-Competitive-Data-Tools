import html
import streamlit as st

from core.compatibility import nombre_blade


# ── Helpers ───────────────────────────────────────────────────────────────────

def _col_score(df):
    if "Wilson Score" in df.columns:
        return "Wilson Score"
    if "Wilson Score Predicho" in df.columns:
        return "Wilson Score Predicho"
    return None


def _nombre_pieza(row, nombre):
    nombre_lower = nombre.lower()
    if "combo" in nombre_lower:
        blade = nombre_blade(row.get("Blade", "?"), row.get("Assist", ""))
        return blade, f"{row.get('Ratchet','?')} · {row.get('Bit','?')}"
    if "assist" in nombre_lower:
        return row.get("Assist", "?"), None
    if "blade" in nombre_lower:
        return row.get("Blade", "?"), None
    if "ratchet" in nombre_lower:
        return row.get("Ratchet", "?"), None
    if "bit" in nombre_lower:
        return row.get("Bit", "?"), None
    return str(row.iloc[0]), None


RANK_COLORS = ["#E8B923", "#B8BCC6", "#C98A4B"]
BAR_FLOOR = 0.40   # la barra parte de aquí para que se noten las diferencias
MIN_PARTIDAS = 30  # por debajo, la muestra se marca como poco fiable

_CSS = """
<style>
.lb{font-family:inherit;margin-top:4px}
.lb-head{display:flex;justify-content:space-between;font-size:.72em;color:#6b7280;
  text-transform:uppercase;letter-spacing:.05em;padding:0 4px 6px;border-bottom:1px solid #23263a}
.lb-row{display:grid;grid-template-columns:28px 1fr auto;align-items:center;gap:10px;
  padding:9px 4px;border-bottom:1px solid #1c1f30}
.lb-rank{font-weight:700;font-size:.9em;color:#6b7280;text-align:center}
.lb-name{color:#e5e7eb;font-weight:600;font-size:.92em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lb-sub{color:#9ca3af;font-weight:400;font-size:.85em}
.lb-meta{color:#6b7280;font-size:.74em;margin-top:1px}
.lb-low{color:#d9a441}
.lb-bar{height:3px;background:#23263a;border-radius:2px;margin-top:5px}
.lb-bar>div{height:3px;border-radius:2px;background:#6EC1E4}
.lb-score{font-variant-numeric:tabular-nums;font-weight:600;font-size:.92em;color:#d1d5db}
</style>
"""


def _leaderboard_html(df_sorted, nombre, col_score):
    max_ws = df_sorted[col_score].max() or 1
    rows = []
    for idx, (_, row) in enumerate(df_sorted.iterrows()):
        ws = float(row[col_score])
        titulo, subtitulo = _nombre_pieza(row, nombre)
        color = RANK_COLORS[idx] if idx < 3 else None
        rank_style = f' style="color:{color}"' if color else ""
        score_style = f' style="color:{color}"' if color else ""

        meta = []
        if "Partidas" in row and row["Partidas"] == row["Partidas"]:
            p = int(row["Partidas"])
            if p < MIN_PARTIDAS:
                meta.append(f'<span class="lb-low" title="Muestra pequeña">{p} partidas ⚠</span>')
            else:
                meta.append(f"{p} partidas")
        winpct = row.get("Win %", None)
        if winpct is not None and winpct == winpct:
            meta.append(f"{winpct:.1f}% WR")

        sub_html = f' <span class="lb-sub">{html.escape(str(subtitulo))}</span>' if subtitulo else ""
        bar_pct = max(3, min(100, (ws - BAR_FLOOR) / max(max_ws - BAR_FLOOR, 1e-9) * 100))
        rows.append(
            f'<div class="lb-row">'
            f'<div class="lb-rank"{rank_style}>{idx + 1}</div>'
            f'<div style="min-width:0">'
            f'<div class="lb-name">{html.escape(str(titulo))}{sub_html}</div>'
            f'<div class="lb-meta">{" · ".join(meta)}</div>'
            f'<div class="lb-bar"><div style="width:{bar_pct:.0f}%"></div></div>'
            f'</div>'
            f'<div class="lb-score"{score_style}>{ws:.3f}</div>'
            f'</div>'
        )
    head = f'<div class="lb-head"><span>{html.escape(nombre)}</span><span>{html.escape(col_score)}</span></div>'
    return _CSS + '<div class="lb">' + head + "".join(rows) + "</div>"


# ── Componente principal ──────────────────────────────────────────────────────

def mostrar_top10(df, nombre, key_suffix=None):
    """
    Muestra un top 10 como ranking compacto (una fila por pieza) con toggle a tabla.
    Funciona tanto en el layout principal como dentro de st.columns.
    """
    key = f"top10_{nombre.lower().replace(' ', '_')}"
    if key_suffix:
        key += f"_{key_suffix}"

    if key not in st.session_state:
        st.session_state[key] = "cards"

    st.subheader(f"🏆 Top 10 {nombre}")
    label = "📊 Tabla" if st.session_state[key] == "cards" else "🏅 Ranking"
    if st.button(label, key=f"{key}_btn"):
        st.session_state[key] = "tabla" if st.session_state[key] == "cards" else "cards"
        st.rerun()

    if df.empty:
        st.warning("No hay datos")
        return

    col_score = _col_score(df)
    if col_score is None:
        st.dataframe(df.head(10), use_container_width=True, hide_index=True)
        return

    df_sorted = df.sort_values(by=col_score, ascending=False).head(10)

    if st.session_state[key] == "cards":
        st.markdown(_leaderboard_html(df_sorted, nombre, col_score), unsafe_allow_html=True)
    else:
        st.dataframe(df_sorted, use_container_width=True, hide_index=True)
