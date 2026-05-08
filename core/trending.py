import numpy as np


def calcular_trending(df_history):
    df_history = df_history.copy()

    df_history["combo"] = (
        df_history["Blade"] + " | " +
        df_history["Ratchet"] + " | " +
        df_history["Bit"]
    )

    df_sorted = df_history.sort_values("fecha")

    latest   = df_sorted.groupby("combo").tail(1)
    previous = df_sorted.groupby("combo").nth(-2)

    merged = latest.merge(previous, on="combo", suffixes=("_new", "_old"))

    # Crecimiento absoluto y relativo en partidas
    merged["delta_partidas"] = merged["Partidas_new"] - merged["Partidas_old"]

    merged["growth_pct"] = (
        merged["delta_partidas"] / merged["Partidas_old"]
    ).replace([np.inf, -np.inf], 0).fillna(0)

    # Trending score: crecimiento relativo ponderado por volumen actual
    # log1p(partidas) evita que combos con pocas partidas dominen por % alto
    merged["trending_score"] = (
        merged["growth_pct"] * np.log1p(merged["Partidas_new"])
    ).round(4)

    # Cambio en winrate como métrica adicional (no afecta al ranking)
    merged["delta_winrate"] = (
        merged["Win %_new"] - merged["Win %_old"]
    ).round(2)

    return merged.sort_values("trending_score", ascending=False)