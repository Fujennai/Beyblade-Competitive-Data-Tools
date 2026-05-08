import streamlit as st
from data.loader import load_data
from core.recommender import recomendar_builds
from components.view_toggle import view_toggle

st.set_page_config(layout="wide")

st.title("🔧 Recomendador de Builds")

df = load_data()

# ── Filtros ───────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

with col1:
    blade = st.selectbox("Blade", ["Todos"] + sorted(df["Blade"].unique()))

with col2:
    ratchet = st.selectbox("Ratchet", ["Todos"] + sorted(df["Ratchet"].unique()))

with col3:
    bit = st.selectbox("Bit", ["Todos"] + sorted(df["Bit"].unique()))

with col4:
    top_n = st.number_input("Resultados", min_value=5, max_value=100, value=20, step=5)

blade   = None if blade   == "Todos" else blade
ratchet = None if ratchet == "Todos" else ratchet
bit     = None if bit     == "Todos" else bit

# ── Resultados ────────────────────────────────────────────────────────────────
if not any([blade, ratchet, bit]):
    st.info("🔎 Selecciona al menos una pieza para ver recomendaciones.")
    st.stop()

with st.spinner("Calculando recomendaciones..."):
    df_rec = recomendar_builds(df, blade, ratchet, bit, top_n=int(top_n))

if df_rec.empty:
    st.warning("No se encontraron combinaciones para los filtros seleccionados.")
else:
    n_reales    = len(df_rec[df_rec["Tipo"] == "✅ Real"])
    n_predichos = len(df_rec[df_rec["Tipo"] == "🔮 Predicho"])

    m1, m2, m3 = st.columns(3)
    m1.metric("Mejor Wilson Score",          f"{df_rec['Wilson Score Predicho'].max():.4f}")
    m2.metric("Combos con datos reales",     n_reales)
    m3.metric("Combos predichos",            n_predichos)

    st.divider()

    modo = view_toggle(key="rec_view")

    if modo == "cards":
        cols = st.columns(4)
        for idx, (_, row) in enumerate(df_rec.iterrows()):
            ws      = row["Wilson Score Predicho"]
            bar_pct = int(ws * 100)
            tipo    = row["Tipo"]
            partidas= int(row["Partidas"])
            arq_v   = row["Arquetipo victoria"]
            arq_d   = row["Arquetipo derrota"]
            r_blade  = row["Blade"]
            r_ratchet= row["Ratchet"]
            r_bit    = row["Bit"]
            tipo_color = "#2ECC71" if tipo == "✅ Real" else "#9B59B6"
            card = (
                '<div style="background:#1a1a2e;border-radius:12px;padding:14px 16px;border:1px solid #2a2a4a;margin-bottom:8px">' +
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px">' +
                f'<span style="font-weight:700;font-size:0.95em;color:#fff">{r_blade}</span>' +
                f'<span style="font-size:0.75em;color:{tipo_color}">{tipo}</span>' +
                '</div>' +
                f'<div style="font-size:0.82em;color:#aaa;margin-bottom:2px">{r_ratchet} &nbsp;·&nbsp; {r_bit}</div>' +
                f'<div style="font-size:0.78em;color:#666;margin-bottom:8px">{partidas} partidas</div>' +
                '<div style="margin:6px 0 4px">' +
                f'<div style="background:#2a2a4a;border-radius:4px;height:5px">' +
                f'<div style="background:#6EC1E4;width:{bar_pct}%;height:5px;border-radius:4px"></div>' +
                '</div></div>' +
                f'<div style="display:flex;justify-content:space-between;font-size:0.8em;color:#888">' +
                f'<span>Wilson Score</span><span style="color:#fff;font-weight:700">{ws:.4f}</span></div>' +
                f'<div style="margin-top:8px;font-size:0.72em;color:#666">{arq_v}<br>{arq_d}</div>' +
                '</div>'
            )
            with cols[idx % 4]:
                st.markdown(card, unsafe_allow_html=True)
    else:
        st.dataframe(
            df_rec,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Wilson Score Predicho": st.column_config.ProgressColumn(
                    "Wilson Score",
                    format="%.4f",
                    min_value=0,
                    max_value=1,
                ),
                "Partidas":           st.column_config.NumberColumn("Partidas"),
                "Tipo":               st.column_config.TextColumn("Tipo"),
                "Arquetipo victoria": st.column_config.TextColumn("Arquetipo victoria"),
                "Arquetipo derrota":  st.column_config.TextColumn("Arquetipo derrota"),
            },
        )

    st.caption(
        "✅ Real: combo con partidas registradas. "
        "🔮 Predicho: combo sin datos reales, estimado a partir de piezas del mismo arquetipo."
    )