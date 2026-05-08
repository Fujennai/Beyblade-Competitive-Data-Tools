import streamlit as st


# ─────────────────────────────────────────────────────────────────────────────
# Página de Inicio
# ─────────────────────────────────────────────────────────────────────────────
def inicio():
    st.set_page_config(
        page_title="Beyblade Competitive Tools",
        page_icon="🌀",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # CSS personalizado
    st.markdown(
        """
        <style>
        .hero {
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 50%, #6a3093 100%);
            padding: 2.5rem 2rem;
            border-radius: 18px;
            color: white;
            margin-bottom: 1.5rem;
            box-shadow: 0 8px 24px rgba(0,0,0,0.25);
        }
        .hero h1 {
            color: white !important;
            font-size: 2.6rem;
            margin: 0 0 0.4rem 0;
            font-weight: 800;
            letter-spacing: -0.5px;
        }
        .hero p {
            color: #e6e8ff;
            font-size: 1.1rem;
            margin: 0;
            opacity: 0.95;
        }
        .feature-card {
            background: linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.01) 100%);
            border: 1px solid rgba(128,128,128,0.25);
            border-radius: 14px;
            padding: 1.25rem 1.25rem 1rem 1.25rem;
            height: 100%;
            transition: transform .15s ease, border-color .15s ease, box-shadow .15s ease;
        }
        .feature-card:hover {
            transform: translateY(-3px);
            border-color: rgba(106, 48, 147, 0.55);
            box-shadow: 0 6px 18px rgba(106, 48, 147, 0.18);
        }
        .feature-icon {
            font-size: 2rem;
            line-height: 1;
            margin-bottom: 0.4rem;
        }
        .feature-title {
            font-size: 1.1rem;
            font-weight: 700;
            margin: 0 0 0.35rem 0;
        }
        .feature-desc {
            font-size: 0.92rem;
            opacity: 0.8;
            margin: 0 0 0.75rem 0;
            min-height: 2.6em;
        }
        .section-title {
            font-size: 1.35rem;
            font-weight: 700;
            margin: 0.5rem 0 0.75rem 0;
        }
        .tip-box {
            background: linear-gradient(135deg, rgba(106,48,147,0.10), rgba(30,60,114,0.10));
            border-left: 4px solid #6a3093;
            padding: 0.9rem 1.1rem;
            border-radius: 8px;
            margin-top: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── Hero ──────────────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="hero">
            <h1>🌀 Beyblade Competitive Data Tools</h1>
            <p>Análisis competitivo, scoring real, predicciones y construcción de decks — todo en un mismo sitio.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ── Métricas rápidas ──────────────────────────────────────────────────────
    try:
        from data.loader import load_data, load_history
        df = load_data()
        df_hist = load_history()

        n_combos = len(df)
        n_partidas = int(df["partidas"].sum()) if "partidas" in df.columns else None
        n_snapshots = df_hist["fecha"].nunique() if not df_hist.empty and "fecha" in df_hist.columns else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🧩 Combos analizados", f"{n_combos:,}".replace(",", "."))
        c2.metric(
            "⚔️ Partidas registradas",
            f"{n_partidas:,}".replace(",", ".") if n_partidas is not None else "—",
        )
        c3.metric("📅 Snapshots históricos", n_snapshots)
        c4.metric("🛠️ Herramientas", 7)
    except Exception:
        st.info("Cargando datos… abre el menú lateral para empezar.")

    st.markdown("<div style='height: 0.8rem;'></div>", unsafe_allow_html=True)

    # ── Feature cards ─────────────────────────────────────────────────────────
    st.markdown("<div class='section-title'>🚀 Herramientas disponibles</div>", unsafe_allow_html=True)

    features = [
        ("📊", "META Tracker", "Sigue la evolución de combos y winrates con Wilson Score.", "pages/1_META_Tracker.py"),
        ("🧠", "Arquetipos", "Descubre familias estratégicas con scoring real del meta.", "pages/2_Arquetipos.py"),
        ("🔧", "Recomendador", "Builds sugeridas según parámetros y filtros.", "pages/3_Recomendador.py"),
        ("🧬", "META Oculto", "Predice combos nuevos infrarrepresentados con potencial.", "pages/5_META_Oculto.py"),
        ("🧩", "Deckbuilder", "Optimiza decks de 3 combos con compatibilidad de piezas.", "pages/6_Deckbuilder.py"),
        ("⚔️", "Matchup 1v1", "Probabilidades cabeza a cabeza entre combos.", "pages/7_Matchup.py"),
        ("🥊", "Deck Match", "Simula enfrentamientos entre decks completos.", "pages/8_Deck_Match.py"),
    ]

    # 3 columnas por fila
    rows = [features[i:i + 3] for i in range(0, len(features), 3)]
    for row in rows:
        cols = st.columns(3)
        for col, (icon, title, desc, target) in zip(cols, row):
            with col:
                st.markdown(
                    f"""
                    <div class="feature-card">
                        <div class="feature-icon">{icon}</div>
                        <div class="feature-title">{title}</div>
                        <div class="feature-desc">{desc}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                if st.button(f"Abrir {title} →", key=f"btn_{title}", use_container_width=True):
                    st.switch_page(target)

    # ── Tip / footer ──────────────────────────────────────────────────────────
    st.markdown(
        """
        <div class="tip-box">
            💡 <b>¿Por dónde empezar?</b> Abre el <b>META Tracker</b> para ver el estado actual del meta,
            o salta directamente al <b>Deckbuilder</b> si vas a montar un equipo.
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption("🌀 Beyblade Competitive Data Tools · TFM · Datos actualizados desde el scraper")


# ─────────────────────────────────────────────────────────────────────────────
# Navegación con nombres personalizados
# ─────────────────────────────────────────────────────────────────────────────
pages = [
    st.Page(inicio, title="Inicio", icon="🏠", default=True, url_path="inicio"),
    st.Page("pages/1_META_Tracker.py", title="META Tracker", icon="📊"),
    st.Page("pages/2_Arquetipos.py", title="Arquetipos", icon="🧠"),
    st.Page("pages/3_Recomendador.py", title="Recomendador", icon="🔧"),
    st.Page("pages/5_META_Oculto.py", title="META Oculto", icon="🧬"),
    st.Page("pages/6_Deckbuilder.py", title="Deckbuilder", icon="🧩"),
    st.Page("pages/7_Matchup.py", title="Matchup 1v1", icon="⚔️"),
    st.Page("pages/8_Deck_Match.py", title="Deck Match", icon="🥊"),
]

pg = st.navigation(pages)
pg.run()
