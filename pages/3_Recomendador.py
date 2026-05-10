import streamlit as st
from data.loader import load_data
from core.recommender import recomendar_builds

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

# ── Advertencia si no se fija ninguna pieza ────────────────────────────────────
if not any([blade, ratchet, bit]):
    st.warning(
        "⚠️ Sin filtros el modelo evalúa **todas** las combinaciones posibles. "
        "Considera fijar al menos una pieza para resultados más relevantes."
    )

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

    # Tabla principal
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

    # Mostrar solo columnas que existan (compatibilidad con pkl antiguo)
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