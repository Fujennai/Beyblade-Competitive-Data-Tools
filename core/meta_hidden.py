"""
core/meta_hidden.py
-------------------
Usa el modelo compartido (model.pkl) para descubrir
combos no explorados con alto Wilson Score predicho.
Incluye arquetipos esperados para cada combo.
"""

import numpy as np
import pandas as pd
import itertools

from core.model_loader import cargar_modelo

MAP_VICTORIA = {
    -1: "⚪ Datos insuficientes",
     0: "⚫ Alta tendencia a perder",
     1: "🔵 Spin finish",
     2: "🟠 Burst / Over",
     3: "🟢 Xtreme finish"
}

MAP_DERROTA = {
    -1: "⚪ Datos insuficientes",
     0: "🟡 Alta tendencia a ganar",
     1: "🔵 Pierde por spin",
     2: "🟠 Pierde por burst/over",
     3: "🟢 Pierde por xtreme"
}


def _categorizar(valor, partidas, winrate):
    if partidas < 10:        return -1
    if winrate >= 95 and partidas < 25: return -1
    if valor < 0.5:          return 0
    elif valor < 1.5:        return 1
    elif valor < 2.5:        return 2
    else:                    return 3


def _arquetipos_esperados(df, blade, ratchet, bit):
    """
    Estima el arquetipo de un combo no visto usando la media de
    Pts Ganados/Cedidos de los combos existentes de cada pieza.
    """
    pts_g = []
    pts_c = []

    for col, val in [("Blade", blade), ("Ratchet", ratchet), ("Bit", bit)]:
        subset = df[df[col] == val]
        if not subset.empty:
            pts_g.append(subset["Pts Ganados/Combate"].mean())
            pts_c.append(subset["Pts Cedidos/Combate"].mean())

    if not pts_g:
        return "⚪ Desconocido", "⚪ Desconocido"

    pts_g_mean = np.mean(pts_g)
    pts_c_mean = np.mean(pts_c)

    # Usamos partidas=50 y winrate=60 como valores neutros para el categorizar
    tv = _categorizar(pts_g_mean, 50, 60)
    td = _categorizar(pts_c_mean, 50, 60)

    return MAP_VICTORIA.get(tv, "⚪ Desconocido"), MAP_DERROTA.get(td, "⚪ Desconocido")


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

    for col in ["Blade", "Ratchet", "Bit"]:
        df_nuevos[col + "_enc"] = encoders[col].transform(df_nuevos[col].astype(str))

    df_nuevos["Partidas_log"]  = np.log1p(50)
    df_nuevos["Blade_score"]   = df_nuevos["Blade"].map(blade_dict).fillna(ws_mean)
    df_nuevos["Ratchet_score"] = df_nuevos["Ratchet"].map(ratchet_dict).fillna(ws_mean)
    df_nuevos["Bit_score"]     = df_nuevos["Bit"].map(bit_dict).fillna(ws_mean)

    X = df_nuevos[p["feature_cols"]].values.astype(float)
    df_nuevos["Wilson Score Predicho"] = np.round(model.predict(X), 4)
    df_nuevos["Win % Predicho"]        = np.round(df_nuevos["Wilson Score Predicho"] * 100, 2)

    # Arquetipos esperados
    arq = df_nuevos.apply(
        lambda r: _arquetipos_esperados(df, r["Blade"], r["Ratchet"], r["Bit"]),
        axis=1
    )
    df_nuevos["Arquetipo victoria"] = arq.apply(lambda x: x[0])
    df_nuevos["Arquetipo derrota"]  = arq.apply(lambda x: x[1])

    return (
        df_nuevos[[
            "Blade", "Ratchet", "Bit",
            "Wilson Score Predicho", "Win % Predicho",
            "Arquetipo victoria", "Arquetipo derrota"
        ]]
        .sort_values("Wilson Score Predicho", ascending=False)
        .reset_index(drop=True)
    )