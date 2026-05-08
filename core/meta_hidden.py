"""
core/meta_hidden.py
-------------------
Usa el modelo compartido (model.pkl) para descubrir
combos no explorados con alto Wilson Score predicho.
"""

import numpy as np
import pandas as pd
import itertools

from core.model_loader import cargar_modelo


def generar_combos(df):
    combos = list(itertools.product(
        df["Blade"].unique(),
        df["Ratchet"].unique(),
        df["Bit"].unique()
    ))
    df_all = pd.DataFrame(combos, columns=["Blade", "Ratchet", "Bit"])
    df_nuevos = df_all.merge(
        df[["Blade", "Ratchet", "Bit"]],
        on=["Blade", "Ratchet", "Bit"],
        how="left",
        indicator=True
    )
    return df_nuevos[df_nuevos["_merge"] == "left_only"].drop(columns="_merge")


def predecir_combos_nuevos(df, muestra=2000):
    """
    Genera combos no vistos, predice su Wilson Score
    y devuelve el ranking ordenado.
    """
    p        = cargar_modelo()
    model    = p["model"]
    encoders = p["encoders"]
    blade_dict   = p["blade_dict"]
    ratchet_dict = p["ratchet_dict"]
    bit_dict     = p["bit_dict"]
    ws_mean      = p["ws_mean"]

    df_nuevos = generar_combos(df)
    df_nuevos = df_nuevos.sample(min(muestra, len(df_nuevos)), random_state=42)

    # Filtrar piezas no vistas por el encoder
    valid = pd.Series([True] * len(df_nuevos), index=df_nuevos.index)
    for col in ["Blade", "Ratchet", "Bit"]:
        valid &= df_nuevos[col].isin(set(encoders[col].classes_))
    df_nuevos = df_nuevos[valid].copy()

    if df_nuevos.empty:
        return pd.DataFrame()

    # Encoding
    for col in ["Blade", "Ratchet", "Bit"]:
        df_nuevos[col + "_enc"] = encoders[col].transform(df_nuevos[col].astype(str))

    df_nuevos["Partidas_log"]  = np.log1p(50)
    df_nuevos["Blade_score"]   = df_nuevos["Blade"].map(blade_dict).fillna(ws_mean)
    df_nuevos["Ratchet_score"] = df_nuevos["Ratchet"].map(ratchet_dict).fillna(ws_mean)
    df_nuevos["Bit_score"]     = df_nuevos["Bit"].map(bit_dict).fillna(ws_mean)

    X = df_nuevos[p["feature_cols"]].values.astype(float)
    df_nuevos["Win % predicho"] = np.round(model.predict(X) * 100, 2)

    return (
        df_nuevos[["Blade", "Ratchet", "Bit", "Win % predicho"]]
        .sort_values("Win % predicho", ascending=False)
        .reset_index(drop=True)
    )