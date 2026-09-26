"""
core/meta_hidden.py
-------------------
META oculto: predice combos no jugados que podrían ser competitivos.

MEJORAS v2:
  - Usa features de interacción par-a-par (BR, BB, RB)
  - Aplica ancla bayesiana para combos con evidencia parcial
  - Filtra resultados con confianza muy baja antes de mostrarlos

Incluye combinaciones Blade CX + Assist no jugadas (los Assists son
intercambiables entre CX). Misma predicción que el recomendador
(core.recommender.predecir).
"""

import pandas as pd

from core.model_loader import cargar_modelo
from core.compatibility import generar_candidatos, reglas_desde, KEYS
from core.recommender import predecir


# ── Arquetipos esperados ──────────────────────────────────────────────────────
def _arquetipos_esperados(df, blade, ratchet, bit):
    """Deduce el arquetipo de victoria/derrota más probable basándose en datos reales."""
    # ... (lógica existente sin cambios)
    tipo_cols = [c for c in df.columns if c.startswith("Tipo") or c == "Arquetipo"]
    if not tipo_cols:
        return "Desconocido", "Desconocido"

    col = tipo_cols[0]
    sub = df[df["Blade"] == blade]
    if sub.empty:
        return "Desconocido", "Desconocido"

    wins_by_type   = sub.groupby(col)["Wins"].sum()
    losses_by_type = sub.groupby(col)["Losses"].sum() if "Losses" in sub.columns else wins_by_type * 0

    arq_vic    = wins_by_type.idxmax()   if not wins_by_type.empty   else "Desconocido"
    arq_derrota = losses_by_type.idxmax() if not losses_by_type.empty else "Desconocido"
    return arq_vic, arq_derrota


# ── Generar combos no vistos ──────────────────────────────────────────────────
def generar_combos(df):
    """Combos legales (incluidos Blade CX + Assist nuevos) que no están en los datos."""
    df_all = generar_candidatos(
        sorted(df["Blade"].unique()),
        sorted(df["Assist"].unique()),
        sorted(df["Ratchet"].unique()),
        sorted(df["Bit"].unique()),
        reglas_desde(df),
    )
    df_nuevos = df_all.merge(df[KEYS], on=KEYS, how="left", indicator=True)
    return df_nuevos[df_nuevos["_merge"] == "left_only"].drop(columns="_merge")


# ── Predicción ────────────────────────────────────────────────────────────────
def predecir_combos_nuevos(df, muestra=2000, min_confianza="media"):
    """
    min_confianza: "baja" → muestra todo, "media" → excluye solo Baja,
                   "alta" → solo Alta y Media.
    """
    p = cargar_modelo()

    df_nuevos = generar_combos(df)
    df_nuevos = df_nuevos.sample(min(muestra, len(df_nuevos)), random_state=42)

    df_nuevos = predecir(df_nuevos, p, df, partidas_supuestas=50)
    if df_nuevos.empty:
        return pd.DataFrame()

    # Filtro de confianza
    if min_confianza == "alta":
        df_nuevos = df_nuevos[df_nuevos["Confianza"].isin(["🟢 Alta", "🟡 Media"])]
    elif min_confianza == "media":
        df_nuevos = df_nuevos[df_nuevos["Confianza"] != "🔴 Baja"]

    # Arquetipos
    arq = df_nuevos.apply(
        lambda r: _arquetipos_esperados(df, r["Blade"], r["Ratchet"], r["Bit"]),
        axis=1,
    )
    df_nuevos["Arquetipo victoria"] = arq.apply(lambda x: x[0]) if not arq.empty else []
    df_nuevos["Arquetipo derrota"]  = arq.apply(lambda x: x[1]) if not arq.empty else []

    return (
        df_nuevos[[
            "Blade", "Assist", "Ratchet", "Bit",
            "Wilson Score Predicho",
            "Confianza",
            "Arquetipo victoria", "Arquetipo derrota",
        ]]
        .sort_values("Wilson Score Predicho", ascending=False)
        .reset_index(drop=True)
    )
