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
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder

from core.model_loader import cargar_modelo

COLS_SALIDA = [
    "Blade", "Ratchet", "Bit",
    "Wilson Score Predicho", "Win % Predicho",
    "Confianza", "Evidencia",
]

_model_cache: dict = {}


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


# ── Modelo local (fallback si no hay model.pkl) ───────────────────────────────

def _entrenar_modelo_local(df: pd.DataFrame, ws_mean: float,
                            par_br: dict, par_bb: dict, par_rb: dict):
    cache_key = id(df)
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    df = df.copy()
    encoders = {}
    for col in ["Blade", "Ratchet", "Bit"]:
        le = LabelEncoder()
        df[col + "_enc"] = le.fit_transform(df[col].astype(str))
        encoders[col] = le

    blade_dict   = df.groupby("Blade")["Wilson Score"].mean().to_dict()
    ratchet_dict = df.groupby("Ratchet")["Wilson Score"].mean().to_dict()
    bit_dict     = df.groupby("Bit")["Wilson Score"].mean().to_dict()

    df["BR_score"] = df.apply(lambda r: par_br.get((r["Blade"], r["Ratchet"]), ws_mean), axis=1)
    df["BB_score"] = df.apply(lambda r: par_bb.get((r["Blade"], r["Bit"]),     ws_mean), axis=1)
    df["RB_score"] = df.apply(lambda r: par_rb.get((r["Ratchet"], r["Bit"]),   ws_mean), axis=1)

    feature_cols = [
        "Blade_enc", "Ratchet_enc", "Bit_enc",
        "Blade_score", "Ratchet_score", "Bit_score",
        "BR_score", "BB_score", "RB_score",
    ]
    df["Blade_score"]   = df["Blade"].map(blade_dict)
    df["Ratchet_score"] = df["Ratchet"].map(ratchet_dict)
    df["Bit_score"]     = df["Bit"].map(bit_dict)

    X = df[feature_cols].values.astype(float)
    y = df["Wilson Score"].values

    model = GradientBoostingRegressor(
        n_estimators=400, learning_rate=0.04, max_depth=4,
        subsample=0.8, min_samples_leaf=3, random_state=42,
    )
    model.fit(X, y)
    _model_cache[cache_key] = (model, encoders, feature_cols,
                                blade_dict, ratchet_dict, bit_dict)
    return model, encoders, feature_cols, blade_dict, ratchet_dict, bit_dict


# ── Función principal ─────────────────────────────────────────────────────────

def recomendar_builds(df, blade=None, ratchet=None, bit=None, top_n=20,
                      solo_confiables=False):
    """
    Recomienda combos con Wilson Score predicho.

    solo_confiables=True → filtra resultados con confianza 🔴 Baja
    """
    if df.empty or "Wilson Score" not in df.columns:
        return pd.DataFrame()

    # Intentar cargar modelo compartido
    try:
        p = cargar_modelo()
        model        = p["model"]
        encoders     = p["encoders"]
        feature_cols = p["feature_cols"]
        blade_dict   = p["blade_dict"]
        ratchet_dict = p["ratchet_dict"]
        bit_dict     = p["bit_dict"]
        ws_mean      = p["ws_mean"]
        par_br       = p.get("par_br", _calcular_score_par(df, "Blade", "Ratchet"))
        par_bb       = p.get("par_bb", _calcular_score_par(df, "Blade", "Bit"))
        par_rb       = p.get("par_rb", _calcular_score_par(df, "Ratchet", "Bit"))
        combo_dict   = p.get("combo_dict", {})
    except FileNotFoundError:
        ws_mean  = float(df["Wilson Score"].mean())
        par_br   = _calcular_score_par(df, "Blade", "Ratchet")
        par_bb   = _calcular_score_par(df, "Blade", "Bit")
        par_rb   = _calcular_score_par(df, "Ratchet", "Bit")
        combo_dict = {
            (r["Blade"], r["Ratchet"], r["Bit"]): (r["Wilson Score"], int(r["Partidas"]))
            for _, r in df.iterrows()
        }
        model, encoders, feature_cols, blade_dict, ratchet_dict, bit_dict = \
            _entrenar_modelo_local(df, ws_mean, par_br, par_bb, par_rb)

    # Generar combos candidatos (no vistos)
    blades   = [blade]   if blade   else sorted(df["Blade"].unique())
    ratchets = [ratchet] if ratchet else sorted(df["Ratchet"].unique())
    bits     = [bit]     if bit     else sorted(df["Bit"].unique())

    existing = set(zip(df["Blade"].astype(str), df["Ratchet"].astype(str), df["Bit"].astype(str)))
    rows = [
        (b, r, bt) for b, r, bt in product(blades, ratchets, bits)
        if (str(b), str(r), str(bt)) not in existing
    ]
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
    df_enc["Win % Predicho"]        = np.round(pred_final * 100, 2)
    df_enc["Confianza"]             = niveles
    df_enc["Evidencia"]             = evidencias

    if solo_confiables:
        df_enc = df_enc[df_enc["Confianza"] != "🔴 Baja"]

    return (
        df_enc[COLS_SALIDA]
        .sort_values("Wilson Score Predicho", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )