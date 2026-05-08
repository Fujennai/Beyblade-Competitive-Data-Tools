"""
core/recommender.py
-------------------
Usa el modelo compartido (model.pkl) para recomendar
builds NO existentes en el dataset.
"""

import numpy as np
import pandas as pd
from itertools import product

from core.model_loader import cargar_modelo


def _combos_no_vistos(df, blade=None, ratchet=None, bit=None):
    blades   = [blade]   if blade   else sorted(df["Blade"].unique())
    ratchets = [ratchet] if ratchet else sorted(df["Ratchet"].unique())
    bits     = [bit]     if bit     else sorted(df["Bit"].unique())

    existing = set(zip(df["Blade"].astype(str), df["Ratchet"].astype(str), df["Bit"].astype(str)))

    rows = [
        (b, r, bt)
        for b, r, bt in product(blades, ratchets, bits)
        if (str(b), str(r), str(bt)) not in existing
    ]
    return pd.DataFrame(rows, columns=["Blade", "Ratchet", "Bit"])


def recomendar_builds(df, blade=None, ratchet=None, bit=None, top_n=20):
    if df.empty or "Wilson Score" not in df.columns:
        return pd.DataFrame()

    p        = cargar_modelo()
    model    = p["model"]
    encoders = p["encoders"]
    blade_dict   = p["blade_dict"]
    ratchet_dict = p["ratchet_dict"]
    bit_dict     = p["bit_dict"]
    ws_mean      = p["ws_mean"]

    df_nuevas = _combos_no_vistos(df, blade, ratchet, bit)
    if df_nuevas.empty:
        return pd.DataFrame()

    df_enc = df_nuevas.copy()

    # Filtrar piezas no vistas por el encoder
    valid = pd.Series([True] * len(df_enc), index=df_enc.index)
    for col in ["Blade", "Ratchet", "Bit"]:
        valid &= df_enc[col].isin(set(encoders[col].classes_))
    df_enc = df_enc[valid].copy()
    if df_enc.empty:
        return pd.DataFrame()

    # Encoding
    for col in ["Blade", "Ratchet", "Bit"]:
        df_enc[col + "_enc"] = encoders[col].transform(df_enc[col].astype(str))

    df_enc["Partidas_log"]  = np.log1p(50)  # volumen neutro para combos nuevos
    df_enc["Blade_score"]   = df_enc["Blade"].map(blade_dict).fillna(ws_mean)
    df_enc["Ratchet_score"] = df_enc["Ratchet"].map(ratchet_dict).fillna(ws_mean)
    df_enc["Bit_score"]     = df_enc["Bit"].map(bit_dict).fillna(ws_mean)

    X = df_enc[p["feature_cols"]].values.astype(float)
    df_enc["Wilson Score Predicho"] = np.round(model.predict(X), 4)

    # Confianza por Wilson Score histórico de cada pieza
    def confianza(row):
        ws = (
            blade_dict.get(row["Blade"], ws_mean)
            + ratchet_dict.get(row["Ratchet"], ws_mean)
            + bit_dict.get(row["Bit"], ws_mean)
        ) / 3
        if ws >= ws_mean + 0.05:
            return "🟢 Alta"
        elif ws >= ws_mean - 0.05:
            return "🟡 Media"
        else:
            return "🔴 Baja"

    df_enc["Confianza"] = df_enc.apply(confianza, axis=1)

    # Referencia más cercana
    ws_reales = df["Wilson Score"].values
    def ref_cercana(ws_pred):
        idx = np.argmin(np.abs(ws_reales - ws_pred))
        r = df.iloc[idx]
        return f"{r['Blade']} / {r['Ratchet']} / {r['Bit']} ({r['Wilson Score']:.4f})"

    df_enc["Referencia más cercana"] = df_enc["Wilson Score Predicho"].apply(ref_cercana)

    return (
        df_enc[["Blade", "Ratchet", "Bit", "Wilson Score Predicho", "Confianza", "Referencia más cercana"]]
        .sort_values("Wilson Score Predicho", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )