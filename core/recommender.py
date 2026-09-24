"""
core/recommender.py
-------------------
Recomienda builds de Beyblade estimando su Wilson Score esperado.

MEJORAS v2:
  - Features de interacción par-a-par en el modelo
  - Ancla bayesiana: mezcla predicción ML con evidencia real
  - Filtro de confianza más estricto basado en cobertura de datos reales
  - Columna "Evidencia" que explica en qué se basa cada predicción
"""

import pandas as pd
import numpy as np
from itertools import product

from core.model_loader import cargar_modelo

COLS_SALIDA = [
    "Blade", "Ratchet", "Bit",
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


def _ancla_y_confianza(blade, ratchet, bit, combo_dict, par_br, par_bb, par_rb,
                        blade_dict, ratchet_dict, bit_dict, ws_mean):
    """
    Devuelve (ancla_score, peso_ancla, nivel_confianza, texto_evidencia).
    """
    evidencia_vals = []
    pesos          = []
    fuentes        = []

    # Combo completo real
    if (blade, ratchet, bit) in combo_dict:
        ws_real, n_real = combo_dict[(blade, ratchet, bit)]
        w = min(n_real / 30.0, 1.0)
        evidencia_vals.append(ws_real)
        pesos.append(w * 3.0)
        fuentes.append(f"combo real ({n_real}p)")

    # Pares observados
    for par_dict, key, nombre in [
        (par_br, (blade, ratchet), f"{blade}+{ratchet}"),
        (par_bb, (blade, bit),     f"{blade}+{bit}"),
        (par_rb, (ratchet, bit),   f"{ratchet}+{bit}"),
    ]:
        if key in par_dict:
            evidencia_vals.append(par_dict[key])
            pesos.append(1.0)
            fuentes.append(f"par {nombre}")

    # Piezas individuales
    evidencia_vals.append(blade_dict.get(blade, ws_mean))
    evidencia_vals.append(ratchet_dict.get(ratchet, ws_mean))
    evidencia_vals.append(bit_dict.get(bit, ws_mean))
    pesos.extend([0.3, 0.3, 0.3])

    ancla      = float(np.average(evidencia_vals, weights=pesos))
    n_reales   = len(fuentes)  # fuentes con datos reales (sin las 3 piezas)
    peso_ancla = min(sum(pesos[:n_reales]) / 6.0, 0.85)

    # Nivel de confianza
    if (blade, ratchet, bit) in combo_dict and combo_dict[(blade, ratchet, bit)][1] >= 10:
        nivel = "🟢 Alta"
    elif n_reales >= 2:
        nivel = "🟡 Media"
    elif n_reales == 1:
        nivel = "🟠 Baja-Media"
    else:
        nivel = "🔴 Baja"

    texto_evidencia = ", ".join(fuentes) if fuentes else "solo piezas individuales"
    return ancla, peso_ancla, nivel, texto_evidencia


# ── Función principal ─────────────────────────────────────────────────────────

def recomendar_builds(df, blade=None, ratchet=None, bit=None, top_n=20,
                      solo_confiables=False, tipo=None):
    """
    Recomienda combos con Wilson Score predicho.

    solo_confiables=True → filtra resultados con confianza 🔴 Baja
    tipo: None | "real" | "predicho" → filtra por tipo de combo.
    """
    if df.empty or "Wilson Score" not in df.columns:
        return pd.DataFrame()

    # Modelo compartido (model.pkl, o entrenado en memoria por model_loader
    # con el mismo código que train_model.py si no existe).
    p = cargar_modelo()
    model        = p["model"]
    encoders     = p["encoders"]
    feature_cols = p["feature_cols"]
    blade_dict   = p["blade_dict"]
    ratchet_dict = p["ratchet_dict"]
    bit_dict     = p["bit_dict"]
    ws_mean      = p["ws_mean"]
    # Pickles antiguos pueden no traer los pares: se calculan solo si faltan.
    par_br = p["par_br"] if "par_br" in p else _calcular_score_par(df, "Blade", "Ratchet")
    par_bb = p["par_bb"] if "par_bb" in p else _calcular_score_par(df, "Blade", "Bit")
    par_rb = p["par_rb"] if "par_rb" in p else _calcular_score_par(df, "Ratchet", "Bit")
    combo_dict   = p.get("combo_dict", {})

    # Generar combos candidatos (incluye reales y predichos)
    blades   = [blade]   if blade   else sorted(df["Blade"].unique())
    ratchets = [ratchet] if ratchet else sorted(df["Ratchet"].unique())
    bits     = [bit]     if bit     else sorted(df["Bit"].unique())

    # Lookup de combos reales presentes en el dataset
    real_lookup = {
        (str(r["Blade"]), str(r["Ratchet"]), str(r["Bit"])):
            (float(r["Wilson Score"]), int(r["Partidas"]), float(r["Win %"]))
        for _, r in df.iterrows()
    }

    rows = list(product(blades, ratchets, bits))
    df_cand = pd.DataFrame(rows, columns=["Blade", "Ratchet", "Bit"])

    if df_cand.empty:
        return pd.DataFrame()

    # Filtrar piezas no vistas por el encoder
    valid = pd.Series([True] * len(df_cand), index=df_cand.index)
    for col in ["Blade", "Ratchet", "Bit"]:
        valid &= df_cand[col].isin(set(encoders[col].classes_))
    df_enc = df_cand[valid].copy()

    if df_enc.empty:
        return pd.DataFrame()

    # Encodear
    for col in ["Blade", "Ratchet", "Bit"]:
        df_enc[col + "_enc"] = encoders[col].transform(df_enc[col].astype(str))

    # Features individuales
    df_enc["Partidas_log"]  = np.log1p(10)
    df_enc["Blade_score"]   = df_enc["Blade"].map(blade_dict).fillna(ws_mean)
    df_enc["Ratchet_score"] = df_enc["Ratchet"].map(ratchet_dict).fillna(ws_mean)
    df_enc["Bit_score"]     = df_enc["Bit"].map(bit_dict).fillna(ws_mean)

    # Features par-a-par
    df_enc["BR_score"] = df_enc.apply(
        lambda r: par_br.get((r["Blade"], r["Ratchet"]), ws_mean), axis=1)
    df_enc["BB_score"] = df_enc.apply(
        lambda r: par_bb.get((r["Blade"], r["Bit"]), ws_mean), axis=1)
    df_enc["RB_score"] = df_enc.apply(
        lambda r: par_rb.get((r["Ratchet"], r["Bit"]), ws_mean), axis=1)

    X = df_enc[feature_cols].values.astype(float)
    pred_ml = model.predict(X)

    # Ancla bayesiana + confianza por combo
    anclas      = []
    pesos_ancla = []
    niveles     = []
    evidencias  = []

    for _, row in df_enc.iterrows():
        ancla, peso, nivel, evid = _ancla_y_confianza(
            row["Blade"], row["Ratchet"], row["Bit"],
            combo_dict, par_br, par_bb, par_rb,
            blade_dict, ratchet_dict, bit_dict, ws_mean,
        )
        anclas.append(ancla)
        pesos_ancla.append(peso)
        niveles.append(nivel)
        evidencias.append(evid)

    anclas      = np.array(anclas)
    pesos_ancla = np.array(pesos_ancla)

    pred_final = (1 - pesos_ancla) * pred_ml + pesos_ancla * anclas

    df_enc["Wilson Score Predicho"] = np.round(pred_final, 4)
    # No hay estimación de winrate para combos no jugados: solo Wilson predicho.
    # "Win % Real" solo se rellena para combos con datos observados.
    df_enc["Win % Real"]            = np.nan
    df_enc["Confianza"]             = niveles
    df_enc["Evidencia"]             = evidencias
    df_enc["Tipo"]                  = TIPO_PREDICHO

    # ── Sobrescribir combos reales con sus valores observados ─────────────────
    # Asegura que el ranking incluya builds reales y use su Wilson Score real.
    if real_lookup:
        keys = list(zip(
            df_enc["Blade"].astype(str),
            df_enc["Ratchet"].astype(str),
            df_enc["Bit"].astype(str),
        ))
        mask_real = np.array([k in real_lookup for k in keys])
        if mask_real.any():
            ws_real_arr = np.array(
                [real_lookup[k][0] if k in real_lookup else 0.0 for k in keys]
            )
            n_real_arr = np.array(
                [real_lookup[k][1] if k in real_lookup else 0 for k in keys]
            )
            df_enc.loc[mask_real, "Wilson Score Predicho"] = np.round(
                ws_real_arr[mask_real], 4
            )
            wr_real_arr = np.array(
                [real_lookup[k][2] if k in real_lookup else np.nan for k in keys]
            )
            df_enc.loc[mask_real, "Win % Real"] = np.round(wr_real_arr[mask_real], 2)
            df_enc.loc[mask_real, "Confianza"] = [
                "🟢 Alta" if n >= 10 else "🟡 Media" for n in n_real_arr[mask_real]
            ]
            df_enc.loc[mask_real, "Evidencia"] = [
                f"combo real ({int(n)}p)" for n in n_real_arr[mask_real]
            ]
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