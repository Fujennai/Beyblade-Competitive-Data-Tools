"""
core/trending.py
----------------
Tendencias del meta a partir del histórico de capturas (history/*.csv).

Las capturas son ACUMULADAS: la diferencia de Wins/Losses/Partidas entre dos
capturas es lo que se jugó en ese periodo.

Diseño:
  - Ventana adaptativa: desde la última captura se va hacia atrás hasta
    cubrir al menos MIN_DIAS y reunir al menos MIN_PARTIDAS partidas nuevas
    (o hasta la primera captura). Así una semana floja no deja todo a 0.
  - Métrica: cuota de uso en la ventana frente a la cuota histórica previa.
    La cuota reciente se "encoge" hacia la histórica (K_SHRINK partidas
    virtuales) para que 1-2 partidas sueltas no disparen el ranking.
  - Tres listas: En alza, En caída y Novedades. Por combo y por pieza.
"""

import numpy as np
import pandas as pd

from core.compatibility import (
    filtrar_combos_validos, reglas_desde, asegurar_assist, nombre_combo, KEYS,
)
from core.metrics import wilson

MIN_DIAS = 28
MIN_PARTIDAS = 300
K_SHRINK = 100          # partidas virtuales de la cuota histórica
MIN_RECIENTES = 5       # mínimo de partidas en la ventana para "En alza"
MIN_HISTORICAS = 20     # mínimo de partidas previas para "En caída"
MIN_NOVEDAD = 3         # mínimo de partidas para aparecer en "Novedades"

# Fechas en las que el scraper empezó a reconocer combos que antes descartaba.
# Esos combos aparecen de golpe con todas sus partidas acumuladas: no son
# novedades ni crecimiento real en la ventana que contiene esa fecha.
CAMBIOS_PARSER = {
    "UX Expanded": "2026-09-24",   # Ratchet ficticio de los UX Expanded
}


def _nombre_combo(d):
    return [nombre_combo(b, a, r, t, sep=" · ")
            for b, a, r, t in zip(d["Blade"], d["Assist"], d["Ratchet"], d["Bit"])]


# ── Preparación ───────────────────────────────────────────────────────────────

def preparar_historial(df_history):
    """Limpia el histórico: solo combos legales y columnas necesarias."""
    if df_history is None or df_history.empty:
        return pd.DataFrame(columns=KEYS + ["Wins", "Losses", "Partidas", "fecha"])
    h = asegurar_assist(df_history)[KEYS + ["Wins", "Losses", "Partidas", "fecha"]].copy()
    h["fecha"] = pd.to_datetime(h["fecha"])
    ultima = h[h["fecha"] == h["fecha"].max()]
    h = filtrar_combos_validos(h, reglas_desde(ultima))
    return h


def totales_por_captura(h):
    """Partidas acumuladas por captura y partidas nuevas respecto a la anterior."""
    t = h.groupby("fecha")["Partidas"].sum().sort_index().to_frame("acumuladas")
    t["nuevas"] = t["acumuladas"].diff().fillna(0).clip(lower=0)
    return t


# ── Ventana ───────────────────────────────────────────────────────────────────

def elegir_ventana(h, min_dias=MIN_DIAS, min_partidas=MIN_PARTIDAS):
    """
    Devuelve dict con inicio, fin, partidas nuevas y última fecha con actividad.
    inicio = captura de referencia (su acumulado se resta); fin = última captura.
    """
    t = totales_por_captura(h)
    fechas = list(t.index)
    fin = fechas[-1]
    inicio = fechas[0]
    for f in reversed(fechas[:-1]):
        nuevas = t.loc[fin, "acumuladas"] - t.loc[f, "acumuladas"]
        if (fin - f).days >= min_dias and nuevas >= min_partidas:
            inicio = f
            break
    activas = t[t["nuevas"] > 0]
    return {
        "inicio": inicio,
        "fin": fin,
        "partidas": int(t.loc[fin, "acumuladas"] - t.loc[inicio, "acumuladas"]),
        "ultima_actividad": activas.index.max() if not activas.empty else None,
        "suficiente": bool(t.loc[fin, "acumuladas"] - t.loc[inicio, "acumuladas"] >= min_partidas),
    }


def _artefactos(ini, fin):
    """Ratchets cuyo cambio de parser cae dentro de la ventana (sus combos "nuevos" son artefactos)."""
    afectados = [r for r, fecha in CAMBIOS_PARSER.items()
                 if ini < pd.Timestamp(fecha) <= fin]
    return afectados


# ── Deltas y métricas ─────────────────────────────────────────────────────────

def deltas_ventana(h, ventana):
    """Una fila por combo con partidas/victorias antes y dentro de la ventana."""
    ini, fin = ventana["inicio"], ventana["fin"]
    a = h[h["fecha"] == ini].set_index(KEYS)[["Wins", "Losses", "Partidas"]]
    b = h[h["fecha"] == fin].set_index(KEYS)[["Wins", "Losses", "Partidas"]]
    d = b.join(a, rsuffix="_prev", how="left").fillna(0).reset_index()

    for c in ["Wins", "Losses", "Partidas"]:
        # Correcciones de la SBBL pueden dar diferencias negativas: se ignoran
        d[c + "_rec"] = (d[c] - d[c + "_prev"]).clip(lower=0)

    d["artefacto"] = False
    for ratchet in _artefactos(ini, fin):
        d.loc[(d["Ratchet"] == ratchet) & (d["Partidas_prev"] == 0), "artefacto"] = True
    return d


def _metricas(g):
    """Añade cuotas, variación y winrates a una tabla agregada."""
    R = g["Partidas_rec"].sum()
    H = g["Partidas_prev"].sum()
    g["cuota_hist"] = g["Partidas_prev"] / H if H > 0 else 0.0
    g["cuota_rec"] = g["Partidas_rec"] / R if R > 0 else 0.0
    g["cuota_rec_aj"] = ((g["Partidas_rec"] + K_SHRINK * g["cuota_hist"]) / (R + K_SHRINK)
                         if R > 0 else g["cuota_hist"])
    g["variacion_pp"] = (g["cuota_rec_aj"] - g["cuota_hist"]) * 100
    g["WR reciente"] = np.where(g["Partidas_rec"] > 0,
                                g["Wins_rec"] / g["Partidas_rec"].replace(0, np.nan) * 100, np.nan)
    g["WR histórico"] = np.where(g["Partidas_prev"] > 0,
                                 g["Wins_prev"] / g["Partidas_prev"].replace(0, np.nan) * 100, np.nan)
    g["Wilson reciente"] = [wilson(w, n) if n > 0 else np.nan
                            for w, n in zip(g["Wins_rec"], g["Partidas_rec"])]
    return g


def tendencias(d, nivel="Combo"):
    """
    nivel: "Combo", "Blade", "Assist", "Ratchet" o "Bit".
    Devuelve dict con DataFrames: en_alza, en_caida, novedades.
    """
    d = d[~d["artefacto"]].copy()
    cols = ["Wins_rec", "Losses_rec", "Partidas_rec", "Wins_prev", "Partidas_prev"]
    if nivel == "Combo":
        d["Nombre"] = _nombre_combo(d)
        g = d.groupby("Nombre", as_index=False)[cols].sum()
    else:
        if nivel == "Assist":
            d = d[d["Assist"] != ""]   # solo CX
        g = d.groupby(nivel, as_index=False)[cols].sum().rename(columns={nivel: "Nombre"})
    g = _metricas(g)

    en_alza = g[(g["Partidas_rec"] >= MIN_RECIENTES) & (g["variacion_pp"] > 0)]
    en_caida = g[(g["Partidas_prev"] >= MIN_HISTORICAS) & (g["variacion_pp"] < 0)]
    novedades = g[(g["Partidas_prev"] == 0) & (g["Partidas_rec"] >= MIN_NOVEDAD)]

    return {
        "en_alza": en_alza.sort_values("variacion_pp", ascending=False),
        "en_caida": en_caida.sort_values("variacion_pp"),
        "novedades": novedades.sort_values("Partidas_rec", ascending=False),
    }


# ── Evolución ─────────────────────────────────────────────────────────────────

def evolucion(h, nivel, nombre, freq="W-MON"):
    """
    Partidas nuevas y cuota de uso por semana para un combo o una pieza.
    nombre para "Combo": "Blade Assist · Ratchet · Bit".
    """
    h = h.copy()
    if nivel == "Combo":
        h["Nombre"] = _nombre_combo(h)
    else:
        if nivel == "Assist":
            h = h[h["Assist"] != ""]
        h["Nombre"] = h[nivel]
    acum = h.groupby(["fecha", "Nombre"])["Partidas"].sum().unstack(fill_value=0).sort_index()
    nuevas = acum.diff().clip(lower=0).iloc[1:]           # la 1ª captura no tiene periodo
    if nombre not in nuevas.columns:
        return pd.DataFrame(columns=["periodo", "partidas", "cuota"])
    por_semana = nuevas.resample(freq, label="right", closed="right").sum()
    total = por_semana.sum(axis=1)
    out = pd.DataFrame({
        "periodo": por_semana.index,
        "partidas": por_semana[nombre].values,
        "cuota": np.where(total > 0, por_semana[nombre] / total.replace(0, np.nan) * 100, np.nan),
        "total": total.values,
    })
    return out
