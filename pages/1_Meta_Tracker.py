import streamlit as st
st.set_page_config(layout="wide")
import pandas as pd

from data.loader import load_data, load_history
from core.metrics import calcular_agregados
from core.trending import calcular_trending
from components.charts import plot_winrate
from components.tables import mostrar_top10
from components.filters import filtros_dependientes
from components.view_toggle import view_toggle

st.title("📊 META Tracker")


def _solo_scrapeados(df):
    """
    Garantiza que solo aparezcan combos realmente scrapeados:
    - Partidas > 0 (descarta filas vacías o predichas)
    - Sin NaN en métricas críticas
    - Si por algún motivo apareciera una columna Tipo (recomendador / META oculto),
      filtra solo los marcados como reales.
    """
    if df is None or df.empty:
        return df
    df = df.copy()
    if "Partidas" in df.columns:
        df = df[df["Partidas"].fillna(0) > 0]
    for c in ["Wilson Score", "Wins", "Losses"]:
        if c in df.columns:
            df = df[df[c].notna()]
    if "Tipo" in df.columns:
        df = df[df["Tipo"].fillna("").str.contains("Real", na=False)]
    return df


df_main    = _solo_scrapeados(load_data())
df_history = _solo_scrapeados(load_history())

# ----------------------------
# Explicación Wilson Score
# ----------------------------

st.info(
    "📊 La Wilson Score ajusta el winrate según el número de partidas.\n\n"
    "Un combo con 100% de victorias en 2 partidas no es tan fiable "
    "como uno con 70% en 500 partidas.\n\n"
    "Esto permite detectar combinaciones realmente consistentes "
    "y evitar resultados inflados por muestras pequeñas."
)

with st.expander("ℹ️ Explicación detallada de la Wilson Score"):
    st.markdown("""
La Wilson Score es una métrica estadística utilizada para estimar
la fiabilidad real de un winrate.

En lugar de usar únicamente el porcentaje bruto de victorias,
también tiene en cuenta cuántas partidas se han jugado.

Esto evita que combinaciones con muy pocas partidas aparezcan
artificialmente como las mejores del META.

### Ejemplo

| Combo | Winrate | Partidas | Wilson Score |
|---|---|---|---|
| Combo A | 100% | 2 | ~34% |
| Combo B | 72% | 500 | ~68% |

Aunque el Combo A tiene un winrate perfecto,
la muestra es demasiado pequeña para considerarlo fiable.

La Wilson Score penaliza automáticamente este tipo de casos,
priorizando resultados más consistentes y representativos.
""")

# ----------------------------
# Filtros
# ----------------------------

st.subheader("🔍 Filtros")

min_partidas = st.slider(
    "Mínimo de partidas",
    0,
    int(df_main["Partidas"].max()),
    0
)

df_filtered, blade, ratchet, bit = filtros_dependientes(df_main, key_prefix="main")
df_filtered = df_filtered[df_filtered["Partidas"] >= min_partidas]

st.caption(f"{len(df_filtered)} combinaciones encontradas")

st.divider()

# ----------------------------
# Top combos
# ----------------------------

st.subheader("🏆 Top 10 Combos (Wilson Score)")

modo_combos = view_toggle(key="meta_tracker_view")

df_top = df_filtered.sort_values("Wilson Score", ascending=False).head(10)

if modo_combos == "cards":
    if df_top.empty:
        st.warning("No hay datos")
    else:
        cols = st.columns(4)
        for idx, (_, row) in enumerate(df_top.iterrows()):
            ws      = row["Wilson Score"]
            bar_pct = int(ws * 100)
            winpct  = row["Win %"]
            partidas= int(row["Partidas"])
            r_blade  = row["Blade"]
            r_ratchet= row["Ratchet"]
            r_bit    = row["Bit"]
            arq_v   = row.get("Arquetipo victoria", "")
            arq_d   = row.get("Arquetipo derrota", "")
            arq_str = f'<div style="margin-top:8px;font-size:0.72em;color:#666">{arq_v}<br>{arq_d}</div>' if arq_v else ""
            card = (
                '<div style="background:#1a1a2e;border-radius:12px;padding:14px 16px;border:1px solid #2a2a4a;margin-bottom:8px">' +
                f'<div style="font-weight:700;font-size:0.95em;color:#fff;margin-bottom:4px">{r_blade}</div>' +
                f'<div style="font-size:0.82em;color:#aaa;margin-bottom:2px">{r_ratchet} &nbsp;·&nbsp; {r_bit}</div>' +
                f'<div style="font-size:0.78em;color:#666;margin-bottom:8px">{partidas} partidas · {winpct:.1f}% WR</div>' +
                '<div style="margin:6px 0 4px">' +
                f'<div style="background:#2a2a4a;border-radius:4px;height:5px">' +
                f'<div style="background:#6EC1E4;width:{bar_pct}%;height:5px;border-radius:4px"></div>' +
                '</div></div>' +
                f'<div style="display:flex;justify-content:space-between;font-size:0.8em;color:#888">' +
                f'<span>Wilson Score</span><span style="color:#fff;font-weight:700">{ws:.4f}</span></div>' +
                arq_str +
                '</div>'
            )
            with cols[idx % 4]:
                st.markdown(card, unsafe_allow_html=True)
else:
    mostrar_top10(df_filtered, "Combos")

st.divider()

# Piezas individuales — usan el mismo toggle que los combos
df_blade, df_ratchet, df_bit = calcular_agregados(df_filtered)


def _render_top_piezas(df_piezas, nombre, col_pieza):
    """Render del top 10 de una pieza, en cards o tabla según `modo_combos`."""
    st.subheader(f"Top 10 {nombre} (Wilson Score)")

    if df_piezas.empty:
        st.warning("No hay datos")
        return

    df_sorted = df_piezas.sort_values("Wilson Score", ascending=False).head(10)

    if modo_combos == "cards":
        for _, row in df_sorted.iterrows():
            ws       = row["Wilson Score"] or 0
            bar_pct  = int(ws * 100)
            partidas = int(row["Partidas"])
            wins     = int(row.get("Wins", 0))
            losses   = int(row.get("Losses", 0))
            winpct   = (wins / partidas * 100) if partidas else 0
            nombre_pieza = row[col_pieza]

            card = (
                '<div style="background:#1a1a2e;border-radius:10px;padding:10px 14px;'
                'border:1px solid #2a2a4a;margin-bottom:6px">'
                f'<div style="font-weight:700;font-size:0.92em;color:#fff;'
                f'margin-bottom:2px">{nombre_pieza}</div>'
                f'<div style="font-size:0.75em;color:#666;margin-bottom:6px">'
                f'{partidas} partidas · {winpct:.1f}% WR</div>'
                '<div style="margin:4px 0">'
                '<div style="background:#2a2a4a;border-radius:4px;height:5px">'
                f'<div style="background:#6EC1E4;width:{bar_pct}%;height:5px;'
                'border-radius:4px"></div></div></div>'
                '<div style="display:flex;justify-content:space-between;'
                'font-size:0.75em;color:#888;margin-top:4px">'
                '<span>Wilson Score</span>'
                f'<span style="color:#fff;font-weight:700">{ws:.4f}</span>'
                '</div></div>'
            )
            st.markdown(card, unsafe_allow_html=True)
    else:
        st.dataframe(df_sorted, use_container_width=True, hide_index=True)


col1, col2, col3 = st.columns(3)
with col1:
    _render_top_piezas(df_blade, "Blades", "Blade")
with col2:
    _render_top_piezas(df_ratchet, "Ratchets", "Ratchet")
with col3:
    _render_top_piezas(df_bit, "Bits", "Bit")

st.divider()

# ----------------------------
# Trending
# ----------------------------

st.subheader("🔥 Trending")

st.info(
    "¿Qué significa el Trending Score?\n\n"
    "Este ranking mide qué combos están ganando relevancia recientemente.\n\n"
    "Se calcula combinando:\n"
    "- 📈 Crecimiento en número de partidas (uso)\n"
    "- 🎯 Winrate actual\n"
    "- ⚖️ Volumen total de partidas\n\n"
    "👉 Un valor alto indica que el combo está creciendo rápido, se usa bastante y además tiene buen rendimiento.\n\n"
    "⚠️ No significa necesariamente que sea el mejor combo, sino que su uso está aumentando."
)

df_trending = calcular_trending(df_history).head(10)

if df_trending.empty:
    st.warning("No hay suficientes datos históricos para calcular el trending.")
else:
    df_trending_show = df_trending[[
        "combo", "Partidas_new", "delta_partidas", "growth_pct", "trending_score", "delta_winrate"
    ]].rename(columns={
        "combo":          "Combo",
        "Partidas_new":   "Partidas actuales",
        "delta_partidas": "Nuevas partidas",
        "growth_pct":     "Crecimiento",
        "trending_score": "Trending Score",
        "delta_winrate":  "Δ Winrate (%)",
    })

    st.dataframe(
        df_trending_show,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Crecimiento": st.column_config.NumberColumn(
                "Crecimiento", format="%.1%"
            ),
            "Trending Score": st.column_config.ProgressColumn(
                "Trending Score", format="%.3f", min_value=0, max_value=float(df_trending_show["Trending Score"].max()) or 1
            ),
            "Δ Winrate (%)": st.column_config.NumberColumn(
                "Δ Winrate (%)", format="%.2f"
            ),
        }
    )

# ----------------------------
# Evolución (desde Trending)
# ----------------------------

st.subheader("📈 Evolución (Trending)")

df_trending = calcular_trending(df_history).head(10)

combo_sel = st.selectbox(
    "Selecciona un combo trending",
    df_trending["combo"].tolist(),
    key="evo_trending"
)

if combo_sel:
    blade_h, ratchet_h, bit_h = combo_sel.split(" | ")

    df_combo = df_history[
        (df_history["Blade"] == blade_h) &
        (df_history["Ratchet"] == ratchet_h) &
        (df_history["Bit"] == bit_h)
    ]

    if not df_combo.empty:
        df_plot = df_combo.groupby("fecha").agg(
            Partidas=("Partidas", "max"),
            Winrate=("Win %", "mean")
        ).reset_index()

        delta_partidas = int(df_plot["Partidas"].iloc[-1] - df_plot["Partidas"].iloc[0])
        delta_winrate  = df_plot["Winrate"].iloc[-1] - df_plot["Winrate"].iloc[0]

        m1, m2 = st.columns(2)
        m1.metric(
            "Crecimiento en partidas",
            f"{int(df_plot['Partidas'].iloc[-1])}",
            delta=f"+{delta_partidas} partidas"
        )
        m2.metric(
            "Cambio en winrate",
            f"{df_plot['Winrate'].iloc[-1]:.2f}%",
            delta=f"{delta_winrate:+.2f}%"
        )

        import plotly.express as px

        fig = px.line(df_plot, x="fecha", y="Partidas", markers=True)
        fig.update_layout(
            xaxis_title="Fecha",
            yaxis_title="Partidas acumuladas",
        )
        st.plotly_chart(fig, use_container_width=True, key="chart_trending")