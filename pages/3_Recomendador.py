import streamlit as st
from data.loader import load_data
from core.recommender import recomendar_builds
from components.view_toggle import view_toggle

st.set_page_config(layout="wide")

st.title("🔧 Recomendador Predictivo de Builds")

df = load_data()

# ── Filtros ────────────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 1, 1.3, 1])

with col1:
    blade = st.selectbox("Blade", ["Todos"] + sorted(df["Blade"].unique()))

with col2:
    ratchet = st.selectbox("Ratchet", ["Todos"] + sorted(df["Ratchet"].unique()))

with col3:
    bit = st.selectbox("Bit", ["Todos"] + sorted(df["Bit"].unique()))

with col4:
    top_n = st.number_input("Número de resultados", min_value=5, max_value=100, value=20, step=5)

with col5:
    tipo_label = st.selectbox(
        "Tipo",
        ["Todos", "🎯 Solo reales", "🔮 Solo predichos"],
        help="Real = combo presente en el dataset · Predicho = combo estimado por el modelo",
    )

with col6:
    solo_confiables = st.checkbox("Solo confiables", value=False,
                                   help="Oculta predicciones con confianza 🔴 Baja")

tipo = {"🎯 Solo reales": "real", "🔮 Solo predichos": "predicho"}.get(tipo_label)

blade   = None if blade   == "Todos" else blade
ratchet = None if ratchet == "Todos" else ratchet
bit     = None if bit     == "Todos" else bit

# ── Bloqueo: requiere al menos una pieza fijada ───────────────────────────────
if not any([blade, ratchet, bit]):
    st.info(
        "👆 Selecciona al menos una pieza (**Blade**, **Ratchet** o **Bit**) "
        "para generar recomendaciones."
    )
    st.stop()

# ── Generación ────────────────────────────────────────────────────────────────
with st.spinner("Generando predicciones..."):
    df_rec = recomendar_builds(
        df, blade, ratchet, bit,
        top_n=int(top_n),
        solo_confiables=solo_confiables,
        tipo=tipo,
    )

# ── Resultados ────────────────────────────────────────────────────────────────
if df_rec.empty:
    st.warning("No se encontraron combinaciones para los filtros seleccionados.")
else:
    st.success(f"✅ Se encontraron **{len(df_rec)}** builds.")

    # Métricas rápidas
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Mejor Wilson Score Predicho", f"{df_rec['Wilson Score Predicho'].max():.4f}")
    m2.metric("Promedio resultados",         f"{df_rec['Wilson Score Predicho'].mean():.4f}")
    m3.metric("🎯 Reales",    int((df_rec["Tipo"] == "🎯 Real").sum())     if "Tipo" in df_rec.columns else 0)
    m4.metric("🔮 Predichos", int((df_rec["Tipo"] == "🔮 Predicho").sum()) if "Tipo" in df_rec.columns else 0)

    st.divider()

    # ── Selector de vista (cards por defecto) ────────────────────────────────
    modo = view_toggle(key="recomendador_view")

    if modo == "cards":
        cols = st.columns(4)
        for idx, (_, row) in enumerate(df_rec.iterrows()):
            ws        = float(row["Wilson Score Predicho"])
            winpct    = float(row["Win % Predicho"])
            bar_pct   = int(max(0, min(ws, 1)) * 100)
            blade_v   = row["Blade"]
            ratchet_v = row["Ratchet"]
            bit_v     = row["Bit"]
            tipo_v    = row.get("Tipo", "")
            conf_v    = row["Confianza"]
            card = (
                '<div style="background:#1a1a2e;border-radius:12px;padding:14px 16px;border:1px solid #2a2a4a;margin-bottom:8px">' +
                f'<div style="font-weight:700;font-size:0.95em;color:#fff;margin-bottom:6px">{blade_v}</div>' +
                f'<div style="font-size:0.82em;color:#aaa;margin-bottom:2px">{ratchet_v} &nbsp;·&nbsp; {bit_v}</div>' +
                '<div style="margin:10px 0 4px">' +
                f'<div style="background:#2a2a4a;border-radius:4px;height:5px">' +
                f'<div style="background:#6EC1E4;width:{bar_pct}%;height:5px;border-radius:4px"></div>' +
                '</div></div>' +
                f'<div style="display:flex;justify-content:space-between;font-size:0.8em;color:#888">' +
                f'<span>Wilson</span><span style="color:#fff;font-weight:700">{ws:.4f}</span></div>' +
                f'<div style="display:flex;justify-content:space-between;font-size:0.8em;color:#888;margin-top:2px">' +
                f'<span>Win %</span><span style="color:#fff;font-weight:700">{winpct:.2f}%</span></div>' +
                f'<div style="margin-top:8px;font-size:0.72em;color:#666">{tipo_v}<br>{conf_v}</div>' +
                '</div>'
            )
            with cols[idx % 4]:
                st.markdown(card, unsafe_allow_html=True)
    else:
        col_config = {
            "Tipo":         st.column_config.TextColumn("Tipo"),
            "Wilson Score Predicho": st.column_config.ProgressColumn(
                "Wilson Score Predicho",
                format="%.4f",
                min_value=0,
                max_value=1,
            ),
            "Win % Predicho": st.column_config.NumberColumn(
                "Win % Predicho", format="%.2f%%"
            ),
            "Confianza":  st.column_config.TextColumn("Confianza"),
        }
        # Nota: "Evidencia" se calcula internamente pero NO se muestra al usuario.
        cols_mostrar = [c for c in [
            "Blade", "Ratchet", "Bit",
            "Tipo",
            "Wilson Score Predicho", "Win % Predicho",
            "Confianza",
        ] if c in df_rec.columns]

        st.dataframe(
            df_rec[cols_mostrar],
            use_container_width=True,
            hide_index=True,
            column_config=col_config,
        )

    st.caption(
        "🎯 **Real** = combo presente en el dataset (Wilson Score observado). "
        "🔮 **Predicho** = combo estimado por el modelo. "
        "**Confianza**: 🟢 Alta = combo real con 10+ partidas · 🟡 Media = pares observados · "
        "🟠 Baja-Media = un par observado · 🔴 Baja = solo piezas individuales."
    )