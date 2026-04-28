import pandas as pd
import os

def load_data():
    return pd.read_csv("beyblade_stats.csv")

def load_history():
    files = sorted(os.listdir("history"))
    dfs = []

    for file in files:
        if file.endswith(".csv"):
            df = pd.read_csv(f"history/{file}")
            df["fecha"] = file.replace("beyblade_stats_", "").replace(".csv", "")
            dfs.append(df)

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()