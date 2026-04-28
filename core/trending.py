import numpy as np

def calcular_trending(df_history):

    df_history["combo"] = (
        df_history["Blade"] + " | " +
        df_history["Ratchet"] + " | " +
        df_history["Bit"]
    )

    df_sorted = df_history.sort_values("fecha")

    latest = df_sorted.groupby("combo").tail(1)
    previous = df_sorted.groupby("combo").nth(-2)

    merged = latest.merge(previous, on="combo", suffixes=("_new", "_old"))

    merged["delta_partidas"] = merged["Partidas_new"] - merged["Partidas_old"]

    merged["growth_pct"] = (
        merged["delta_partidas"] / merged["Partidas_old"]
    ).replace([np.inf, -np.inf], 0).fillna(0)

    merged["trending_score"] = (
        merged["growth_pct"] *
        np.log1p(merged["Partidas_new"]) *
        (merged["Win %_new"] / 100)
    )

    return merged.sort_values("trending_score", ascending=False)