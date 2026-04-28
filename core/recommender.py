import pandas as pd
import numpy as np

def recomendar_builds(df, blade=None, ratchet=None, bit=None, top_n=5):

    df_temp = df.copy()

    if blade:
        df_temp = df_temp[df_temp["Blade"] == blade]

    if ratchet:
        df_temp = df_temp[df_temp["Ratchet"] == ratchet]

    if bit:
        df_temp = df_temp[df_temp["Bit"] == bit]

    if df_temp.empty:
        return pd.DataFrame()

    ranking = (
        df_temp.groupby(["Blade", "Ratchet", "Bit"])
        .agg({
            "Win %": "mean",
            "Partidas": "sum"
        })
        .reset_index()
    )

    ranking["score"] = ranking["Win %"] * np.log1p(ranking["Partidas"])

    return ranking.sort_values("score", ascending=False).head(top_n)