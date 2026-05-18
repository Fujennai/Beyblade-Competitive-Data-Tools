"""
core/meta_hidden.py
-------------------
META oculto: predice combos no jugados que podrían ser competitivos.

MEJORAS v2:
  - Usa features de interacción par-a-par (BR, BB, RB)
  - Aplica ancla bayesiana para combos con evidencia parcial
  - Filtra resultados con confianza muy baja antes de mostrarlos
"""

import pandas as pd
import numpy as np
import itertools

from core.model_loader import cargar_modelo


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
    blades   = df["Blade"].unique()
    ratchets = df["Ratchet"].unique()
    bits     = df["Bit"].unique()

    combos = list(itertools.product(blades, ratchets, bits))
    df_all = pd.DataFrame(combos, columns=["Blade", "Ratchet", "Bit"])

    df_nuevos = df_all.merge(
        df[["Blade", "Ratchet", "Bit"]],
        on=["Blade", "Ratchet", "Bit"],
        how="left",
        indicator=True,
    )
    return df_nuevos[df_nuevos["_merge"] == "left_only"].drop(columns="_merge")


# ── Predicción ────────────────────────────────────────────────────────────────
def predecir_combos_nuevos(df, muestra=2000, min_confianza="media"):
    """
    min_confianza: "baja" → muestra todo, "media" → excluye solo Baja,
                   "alta" → solo Alta y Media.
    """
    p            = cargar_modelo()
    model        = p["model"]
    encoders     = p["encoders"]
    blade_dict   = p["blade_dict"]
    ratchet_dict = p["ratchet_dict"]
    bit_dict     = p["bit_dict"]
    ws_mean      = p["ws_mean"]
    par_br       = p.get("par_br", {})
    par_bb       = p.get("par_bb", {})
    par_rb       = p.get("par_rb", {})
    combo_dict   = p.get("combo_dict", {})
    feature_cols = p["feature_cols"]

    df_nuevos = generar_combos(df)
    df_nuevos = df_nuevos.sample(min(muestra, len(df_nuevos)), random_state=42)

    # Filtrar piezas no vistas
    valid = pd.Series([True] * len(df_nuevos), index=df_nuevos.index)
    for col in ["Blade", "Ratchet", "Bit"]:
        valid &= df_nuevos[col].isin(set(encoders[col].classes_))
    df_nuevos = df_nuevos[valid].copy()

    if df_nuevos.empty:
        return pd.DataFrame()

    # Encodear
    for col in ["Blade", "Ratchet", "Bit"]:
        df_nuevos[col + "_enc"] = encoders[col].transform(df_nuevos[col].astype(str))

    # Features individuales
    df_nuevos["Partidas_log"]  = np.log1p(50)
    df_nuevos["Blade_score"]   = df_nuevos["Blade"].map(blade_dict).fillna(ws_mean)
    df_nuevos["Ratchet_score"] = df_nuevos["Ratchet"].map(ratchet_dict).fillna(ws_mean)
    df_nuevos["Bit_score"]     = df_nuevos["Bit"].map(bit_dict).fillna(ws_mean)

    # Features par-a-par
    df_nuevos["BR_score"] = df_nuevos.apply(
        lambda r: par_br.get((r["Blade"], r["Ratchet"]), ws_mean), axis=1)
    df_nuevos["BB_score"] = df_nuevos.apply(
        lambda r: par_bb.get((r["Blade"], r["Bit"]), ws_mean), axis=1)
    df_nuevos["RB_score"] = df_nuevos.apply(
        lambda r: par_rb.get((r["Ratchet"], r["Bit"]), ws_mean), axis=1)

    X = df_nuevos[feature_cols].values.astype(float)
    pred_ml = model.predict(X)

    # Ancla bayesiana por combo
    anclas      = []
    pesos_ancla = []
    confianzas  = []

    for _, row in df_nuevos.iterrows():
        evidencia_vals = []
        pesos_ev       = []
        n_reales       = 0

        for par_dict, key in [
            (par_br, (row["Blade"], row["Ratchet"])),
            (par_bb, (row["Blade"], row["Bit"])),
            (par_rb, (row["Ratchet"], row["Bit"])),
        ]:
            if key in par_dict:
                evidencia_vals.append(par_dict[key])
                pesos_ev.append(1.0)
                n_reales += 1

        evidencia_vals += [
            blade_dict.get(row["Blade"], ws_mean),
            ratchet_dict.get(row["Ratchet"], ws_mean),
            bit_dict.get(row["Bit"], ws_mean),
        ]
        pesos_ev += [0.3, 0.3, 0.3]

        ancla      = float(np.average(evidencia_vals, weights=pesos_ev))
        peso_ancla = min(n_reales / 6.0, 0.85)
        anclas.append(ancla)
        pesos_ancla.append(peso_ancla)

        if n_reales >= 2:
            confianzas.append("🟡 Media")
        elif n_reales == 1:
            confianzas.append("🟠 Baja-Media")
        else:
            confianzas.append("🔴 Baja")

    anclas      = np.array(anclas)
    pesos_ancla = np.array(pesos_ancla)

    pred_final = (1 - pesos_ancla) * pred_ml + pesos_ancla * anclas

    df_nuevos["Wilson Score Predicho"] = np.round(pred_final, 4)
    df_nuevos["Win % Predicho"]        = np.round(pred_final * 100, 2)
    df_nuevos["Confianza"]             = confianzas

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
    df_nuevos["Arquetipo victoria"] = arq.apply(lambda x: x[0])
    df_nuevos["Arquetipo derrota"]  = arq.apply(lambda x: x[1])

    return (
        df_nuevos[[
            "Blade", "Ratchet", "Bit",
            "Wilson Score Predicho", "Win % Predicho",
            "Confianza",
            "Arquetipo victoria", "Arquetipo derrota",
        ]]
        .sort_values("Wilson Score Predicho", ascending=False)
        .reset_index(drop=True)
    )