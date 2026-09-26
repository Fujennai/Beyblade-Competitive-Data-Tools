import streamlit as st
st.set_page_config(layout="wide")
import pandas as pd

from data.loader import load_data, load_history
from core.metrics import calcular_agregados
from core.trending import (
    preparar_historial, elegir_ventana, deltas_ventana, tendencias, evolucion,
    MIN_DIAS, MIN_PARTIDAS, MIN_RECIENTES, MIN_HISTORICAS,
)
from components.charts import plot_evolucion
from components.tables import mostrar_top10
from components.filters import filtros_dependientes

st.title("📊 META Tracker")

df_main = load_data()
df_history = load_history()

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

df_filtered, blade, ratchet, bit, assist = filtros_dependientes(df_main, key_prefix="main")
df_filtered = df_filtered[df_filtered["Partidas"] >= min_partidas]

st.caption(f"{len(df_filtered)} combinaciones encontradas")

st.divider()

# ----------------------------
# Top combos
# ----------------------------

mostrar_top10(df_filtered, "Combos")

df_blade, df_assist, df_ratchet, df_bit = calcular_agregados(df_filtered)

col1, col2 = st.columns(2)

with col1:
    mostrar_top10(df_blade, "Blades")

with col2:
    mostrar_top10(df_assist, "Assists")
    st.caption("Assists: solo CX. En CX, el Blade es lock chip + main blade (+ over blade).")

col3, col4 = st.columns(2)

with col3:
    mostrar_top10(df_ratchet, "Ratchets")

with col4:
    mostrar_top10(df_bit, "Bits")

st.divider()


# ----------------------------
# Tendencias
# ----------------------------

st.subheader("🔥 Tendencias")

hist = preparar_historial(df_history)

if hist.empty or hist["fecha"].nunique() < 2:
    st.info("Aún no hay suficientes capturas en el histórico para calcular tendencias.")
    st.stop()

ventana = elegir_ventana(hist)
fmt = lambda f: f.strftime("%d/%m/%Y")

if ventana["partidas"] == 0:
    ult = ventana["ultima_actividad"]
    st.warning(
        "Sin actividad registrada"
        + (f" desde el {fmt(ult)}." if ult is not None else ".")
        + " Las tendencias se actualizarán cuando entren partidas nuevas."
    )
    st.stop()

st.caption(
    f"📅 Periodo analizado: **{fmt(ventana['inicio'])} → {fmt(ventana['fin'])}** · "
    f"**{ventana['partidas']}** partidas nuevas"
    + ("" if ventana["suficiente"] else " · ⚠️ pocas partidas: resultados orientativos")
    + (f" · última actividad registrada: {fmt(ventana['ultima_actividad'])}"
       if ventana["ultima_actividad"] is not None and ventana["ultima_actividad"] < ventana["fin"] else "")
)

with st.expander("ℹ️ ¿Cómo se calculan las tendencias?"):
    st.markdown(f"""
- El periodo se amplía hacia atrás hasta cubrir al menos **{MIN_DIAS} días** y **{MIN_PARTIDAS} partidas nuevas**,
  para que una semana con poca actividad no deje todo a cero.
- **Variación de cuota**: qué porcentaje de las partidas del periodo lleva cada combo/pieza frente a su
  porcentaje en todo lo anterior. La cuota reciente se suaviza hacia la histórica para que 1-2 partidas
  sueltas no disparen el ranking.
- **En alza**: gana cuota (mín. {MIN_RECIENTES} partidas en el periodo). **En caída**: pierde cuota
  (mín. {MIN_HISTORICAS} partidas previas). **Novedades**: sin partidas antes del periodo.
- El WR reciente solo cuenta las partidas del periodo; con pocas partidas es muy variable.
""")

deltas = deltas_ventana(hist, ventana)
n_art = int(deltas["artefacto"].sum())
if n_art:
    st.caption(
        f"ℹ️ {n_art} combos excluidos: aparecen en el periodo por un cambio del scraper "
        "(p.ej. UX Expanded), no porque se empezaran a jugar ahora."
    )

nivel = st.radio("Nivel", ["Combo", "Blade", "Assist", "Ratchet", "Bit"], horizontal=True, key="trend_nivel")
if nivel == "Assist":
    st.caption("Assists: la cuota se calcula sobre las partidas de CX.")
tend = tendencias(deltas, nivel)

COLS = {
    "Nombre": nivel,
    "Partidas_rec": "Partidas periodo",
    "Partidas_prev": "Partidas previas",
    "variacion_pp": "Variación cuota (pp)",
    "cuota_rec": "Cuota periodo %",
    "cuota_hist": "Cuota previa %",
    "WR reciente": "WR periodo %",
    "WR histórico": "WR previo %",
}


def _tabla(df_t):
    if df_t.empty:
        st.caption("Nada que mostrar en este periodo.")
        return
    t = df_t.head(10)[list(COLS)].copy()
    t["cuota_rec"] *= 100
    t["cuota_hist"] *= 100
    t = t.rename(columns=COLS)
    st.dataframe(
        t, use_container_width=True, hide_index=True,
        column_config={
            "Partidas periodo": st.column_config.NumberColumn(format="%d"),
            "Partidas previas": st.column_config.NumberColumn(format="%d"),
            "Variación cuota (pp)": st.column_config.NumberColumn(format="%+.2f"),
            "Cuota periodo %": st.column_config.NumberColumn(format="%.1f%%"),
            "Cuota previa %": st.column_config.NumberColumn(format="%.1f%%"),
            "WR periodo %": st.column_config.NumberColumn(format="%.1f%%"),
            "WR previo %": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )


tab_alza, tab_caida, tab_nuevo = st.tabs(["📈 En alza", "📉 En caída", "🆕 Novedades"])
with tab_alza:
    _tabla(tend["en_alza"])
with tab_caida:
    _tabla(tend["en_caida"])
with tab_nuevo:
    _tabla(tend["novedades"])

# ----------------------------
# Evolución
# ----------------------------

st.subheader("📈 Evolución semanal")

candidatos = list(dict.fromkeys(
    tend["en_alza"]["Nombre"].head(10).tolist()
    + tend["en_caida"]["Nombre"].head(10).tolist()
    + tend["novedades"]["Nombre"].head(10).tolist()
))

if candidatos:
    sel = st.selectbox(f"{nivel}", candidatos, key="evo_trend_sel")
    evo = evolucion(hist, nivel, sel)
    if evo.empty:
        st.caption("Sin datos de evolución para esta selección.")
    else:
        plot_evolucion(evo, key="chart_evolucion")
        st.caption(
            "Barras: partidas nuevas por semana · Línea: % de las partidas de esa semana. "
            "Las semanas sin actividad global no tienen cuota."
        )
