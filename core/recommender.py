"""
core/recommender.py
-------------------
Recomienda builds de Beyblade estimando su Wilson Score esperado.

MEJORAS v2:
  - Features de interacción par-a-par en el modelo
  - Ancla bayesiana: mezcla predicción ML con evidencia real
  - Filtro de confianza más estricto basado en cobertura de datos reales
  - Columna "Evidencia" que explica en qué se basa cada predicción

Un combo es (Blade, Assist, Ratchet, Bit). El Assist solo existe en los CX
(vacío en UX/BX) y es intercambiable entre CX: el recomendador propone
combinaciones Blade CX + Assist aunque no se hayan jugado.
"""

import pandas as pd
import numpy as np

from core.model_loader import cargar_modelo
from core.compatibility import (
    generar_candidatos, reglas_desde, SIN_ASSIST, KEYS,
)

COLS_SALIDA = [
    "Blade", "Assist", "Ratchet", "Bit",
    "Tipo",
    "Wilson Score Predicho", "Win % Real",
    "Confianza", "Evidencia",
]

TIPO_REAL     = "🎯 Real"
TIPO_PREDICHO = "🔮 Predicho"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _wilson(w, n, z=1.96):
    if n == 0:
        return 0.0
    p = w / n
    return (p + z**2/(2*n) - z*((p*(1-p)+z**2/(4*n))/n)**0.5) / (1 + z**2/n)


def _calcular_score_par(df, col_a, col_b, min_partidas=5):
    stats = df.groupby([col_a, col_b]).agg({"Wins": "sum", "Partidas": "sum"}).reset_index()
    stats = stats[stats["Partidas"] >= min_partidas]
    stats["score"] = stats.apply(lambda r: _wilson(r["Wins"], r["Partidas"]), axis=1)
    return {(row[col_a], row[col_b]): row["score"] for _, row in stats.iterrows()}


def _pares(p, df):
    """Diccionarios de pares del payload (o calculados si el payload no los trae)."""
    def par(clave, a, b, sub=None):
        return p[clave] if clave in p else _calcular_score_par(df if sub is None else sub, a, b)
    return {
        "br": par("par_br", "Blade", "Ratchet"),
        "bb": par("par_bb", "Blade", "Bit"),
        "rb": par("par_rb", "Ratchet", "Bit"),
        "ba": par("par_ba", "Blade", "Assist", df[df["Assist"] != SIN_ASSIST]),
    }


def evidencia_y_confianza(cand, p, pares):
    """
    Ancla bayesiana y confianza de cada combo de `cand` (columnas KEYS).
    Devuelve (ancla, peso_ancla, nivel, texto_evidencia) como arrays/listas.

    Evidencia (peso): combo real (3·min(n/30,1)), cada par observado (1)
    y cada pieza individual (0,3). El Assist solo cuenta en los CX.
    """
    combo_dict = p.get("combo_dict", {})
    ws_mean    = p["ws_mean"]
    piezas = {
        "Blade":   p["blade_dict"],
        "Assist":  p.get("assist_dict", {}),
        "Ratchet": p["ratchet_dict"],
        "Bit":     p["bit_dict"],
    }

    anclas, pesos_ancla, niveles, textos = [], [], [], []
    for b, a, r, t in zip(cand["Blade"], cand["Assist"], cand["Ratchet"], cand["Bit"]):
        vals, pesos, fuentes = [], [], []
        real = combo_dict.get((b, a, r, t))
        if real is not None:
            ws_real, n_real = real
            vals.append(ws_real)
            pesos.append(min(n_real / 30.0, 1.0) * 3.0)
            fuentes.append(f"combo real ({n_real}p)")

        claves = [
            ("br", (b, r), f"{b}+{r}"),
            ("bb", (b, t), f"{b}+{t}"),
            ("rb", (r, t), f"{r}+{t}"),
        ]
        if a:
            claves.append(("ba", (b, a), f"{b}+{a}"))
        for k, key, nombre in claves:
            v = pares[k].get(key)
            if v is not None:
                vals.append(v)
                pesos.append(1.0)
                fuentes.append(f"par {nombre}")

        n_reales = len(fuentes)
        peso_real = sum(pesos)

        vals += [piezas["Blade"].get(b, ws_mean),
                 piezas["Ratchet"].get(r, ws_mean),
                 piezas["Bit"].get(t, ws_mean)]
        pesos += [0.3, 0.3, 0.3]
        if a:
            vals.append(piezas["Assist"].get(a, ws_mean))
            pesos.append(0.3)

        anclas.append(float(np.average(vals, weights=pesos)))
        pesos_ancla.append(min(peso_real / 6.0, 0.85))

        if real is not None and real[1] >= 10:
            niveles.append("🟢 Alta")
        elif n_reales >= 2:
            niveles.append("🟡 Media")
        elif n_reales == 1:
            niveles.append("🟠 Baja-Media")
        else:
            niveles.append("🔴 Baja")
        textos.append(", ".join(fuentes) if fuentes else "solo piezas individuales")

    return np.array(anclas), np.array(pesos_ancla), niveles, textos


def predecir(cand, p, df, partidas_supuestas):
    """
    Wilson Score predicho (ML + ancla) para los combos de `cand`.
    Descarta las piezas que el modelo no conoce. Devuelve el DataFrame con
    las columnas "Wilson Score Predicho", "Confianza" y "Evidencia".
    """
    encoders     = p["encoders"]
    ws_mean      = p["ws_mean"]
    pares        = _pares(p, df)

    valid = pd.Series(True, index=cand.index)
    for col in KEYS:
        valid &= cand[col].isin(set(encoders[col].classes_))
    out = cand[valid].copy()
    if out.empty:
        return out

    for col in KEYS:
        out[col + "_enc"] = encoders[col].transform(out[col].astype(str))

    out["Partidas_log"]  = np.log1p(partidas_supuestas)
    out["Blade_score"]   = out["Blade"].map(p["blade_dict"]).fillna(ws_mean)
    # Sin Assist (UX/BX) -> ws_mean, igual que en el entrenamiento
    out["Assist_score"]  = out["Assist"].map(p.get("assist_dict", {})).fillna(ws_mean)
    out["Ratchet_score"] = out["Ratchet"].map(p["ratchet_dict"]).fillna(ws_mean)
    out["Bit_score"]     = out["Bit"].map(p["bit_dict"]).fillna(ws_mean)

    out["BR_score"] = [pares["br"].get(k, ws_mean) for k in zip(out["Blade"], out["Ratchet"])]
    out["BB_score"] = [pares["bb"].get(k, ws_mean) for k in zip(out["Blade"], out["Bit"])]
    out["RB_score"] = [pares["rb"].get(k, ws_mean) for k in zip(out["Ratchet"], out["Bit"])]

    pred_ml = p["model"].predict(out[p["feature_cols"]].values.astype(float))
    anclas, pesos_ancla, niveles, textos = evidencia_y_confianza(out, p, pares)

    out["Wilson Score Predicho"] = np.round((1 - pesos_ancla) * pred_ml + pesos_ancla * anclas, 4)
    out["Confianza"] = niveles
    out["Evidencia"] = textos
    return out


# ── Función principal ─────────────────────────────────────────────────────────

def recomendar_builds(df, blade=None, ratchet=None, bit=None, top_n=20,
                      solo_confiables=False, tipo=None, assist=None):
    """
    Recomienda combos con Wilson Score predicho.

    assist: Assist fijado (solo CX). None = cualquiera (incluido sin Assist).
    solo_confiables=True → filtra resultados con confianza 🔴 Baja
    tipo: None | "real" | "predicho" → filtra por tipo de combo.
    """
    if df.empty or "Wilson Score" not in df.columns:
        return pd.DataFrame()

    # Modelo compartido (model.pkl, o entrenado en memoria por model_loader
    # con el mismo código que train_model.py si no existe o es antiguo).
    p = cargar_modelo()

    # Candidatos legales (reales y no jugados)
    blades   = [blade]   if blade   else sorted(df["Blade"].unique())
    assists  = [assist]  if assist  else sorted(df["Assist"].unique())
    ratchets = [ratchet] if ratchet else sorted(df["Ratchet"].unique())
    bits     = [bit]     if bit     else sorted(df["Bit"].unique())
    df_cand = generar_candidatos(blades, assists, ratchets, bits, reglas_desde(df))
    if df_cand.empty:
        return pd.DataFrame()

    df_enc = predecir(df_cand, p, df, partidas_supuestas=10)
    if df_enc.empty:
        return pd.DataFrame()

    # No hay estimación de winrate para combos no jugados: solo Wilson predicho.
    # "Win % Real" solo se rellena para combos con datos observados.
    df_enc["Win % Real"] = np.nan
    df_enc["Tipo"]       = TIPO_PREDICHO

    # ── Sobrescribir combos reales con sus valores observados ─────────────────
    # Asegura que el ranking incluya builds reales y use su Wilson Score real.
    reales = df[KEYS + ["Wilson Score", "Partidas", "Win %"]].rename(columns={
        "Wilson Score": "_ws", "Partidas": "_n", "Win %": "_wr"})
    df_enc = df_enc.merge(reales, on=KEYS, how="left")
    mask_real = df_enc["_ws"].notna()
    if mask_real.any():
        n_real = df_enc.loc[mask_real, "_n"].astype(int)
        df_enc.loc[mask_real, "Wilson Score Predicho"] = df_enc.loc[mask_real, "_ws"].round(4)
        df_enc.loc[mask_real, "Win % Real"] = df_enc.loc[mask_real, "_wr"].round(2)
        df_enc.loc[mask_real, "Confianza"] = ["🟢 Alta" if n >= 10 else "🟡 Media" for n in n_real]
        df_enc.loc[mask_real, "Evidencia"] = [f"combo real ({n}p)" for n in n_real]
        df_enc.loc[mask_real, "Tipo"] = TIPO_REAL

    # Filtros finales
    if solo_confiables:
        df_enc = df_enc[df_enc["Confianza"] != "🔴 Baja"]

    if tipo == "real":
        df_enc = df_enc[df_enc["Tipo"] == TIPO_REAL]
    elif tipo == "predicho":
        df_enc = df_enc[df_enc["Tipo"] == TIPO_PREDICHO]

    return (
        df_enc[COLS_SALIDA]
        .sort_values("Wilson Score Predicho", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )
