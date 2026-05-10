import streamlit as st


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
        return row.get("Blade", "?"), f"{row.get('Ratchet','?')} · {row.get('Bit','?')}"
    if "blade" in nombre_lower:
        return row.get("Blade", "?"), None
    if "ratchet" in nombre_lower:
        return row.get("Ratchet", "?"), None
    if "bit" in nombre_lower:
        return row.get("Bit", "?"), None
    return str(row.iloc[0]), None


RANK_COLORS = ["#FFD700", "#C0C0C0", "#CD7F32"]


# ── Componente principal ──────────────────────────────────────────────────────

def mostrar_top10(df, nombre, key_suffix=None):
    """
    Muestra un top 10 con toggle cards/tabla.
    Funciona tanto en el layout principal como dentro de st.columns.
    No anida st.columns internamente para evitar errores de Streamlit.
    """
    key = f"top10_{nombre.lower().replace(' ', '_')}"
    if key_suffix:
        key += f"_{key_suffix}"

    if key not in st.session_state:
        st.session_state[key] = "cards"

    st.subheader(f"🏆 Top 10 {nombre}")
    label = "📊 Tabla" if st.session_state[key] == "cards" else "🃏 Cards"
    if st.button(label, key=f"{key}_btn"):
        st.session_state[key] = "tabla" if st.session_state[key] == "cards" else "cards"
        st.rerun()

    modo = st.session_state[key]

    if df.empty:
        st.warning("No hay datos")
        return

    col_score = _col_score(df)
    if col_score is None:
        st.dataframe(df.head(10), use_container_width=True, hide_index=True)
        return

    df_sorted = df.sort_values(by=col_score, ascending=False).head(10)

    if modo == "cards":
        cols = st.columns(4)
        for idx, (_, row) in enumerate(df_sorted.iterrows()):
            ws       = row[col_score]
            bar_pct  = int(ws * 100)
            partidas = int(row["Partidas"]) if "Partidas" in row else None
            winpct   = row.get("Win %", None)

            titulo, subtitulo = _nombre_pieza(row, nombre)

            rank_color = RANK_COLORS[idx] if idx < 3 else "#555"
            rank_label = ["🥇", "🥈", "🥉"][idx] if idx < 3 else f"#{idx+1}"
            border     = rank_color if idx < 3 else "#2a2a4a"

            subtitulo_html = (
                f'<div style="font-size:0.82em;color:#aaa;margin-bottom:2px">{subtitulo}</div>'
                if subtitulo else ""
            )
            meta_parts = []
            if partidas is not None:
                meta_parts.append(f"{partidas} partidas")
            if winpct is not None:
                meta_parts.append(f"{winpct:.1f}% WR")
            meta_html = (
                f'<div style="font-size:0.78em;color:#666;margin-bottom:8px">{" · ".join(meta_parts)}</div>'
                if meta_parts else ""
            )

            card = (
                f'<div style="background:#1a1a2e;border-radius:12px;padding:14px 16px;'
                f'border:1px solid {border};margin-bottom:8px">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">'
                f'<span style="font-size:1.1em">{rank_label}</span>'
                f'<span style="font-size:0.75em;color:{rank_color};font-weight:700">{ws:.4f}</span>'
                f'</div>'
                f'<div style="font-weight:700;font-size:0.95em;color:#fff;margin-bottom:4px">{titulo}</div>'
                + subtitulo_html
                + meta_html +
                '<div style="margin:6px 0 4px">'
                '<div style="background:#2a2a4a;border-radius:4px;height:5px">'
                f'<div style="background:#6EC1E4;width:{bar_pct}%;height:5px;border-radius:4px"></div>'
                '</div></div>'
                f'<div style="font-size:0.75em;color:#888;margin-top:4px">Wilson Score</div>'
                '</div>'
            )
            with cols[idx % 4]:
                st.markdown(card, unsafe_allow_html=True)
    else:
        st.dataframe(df_sorted, use_container_width=True, hide_index=True)