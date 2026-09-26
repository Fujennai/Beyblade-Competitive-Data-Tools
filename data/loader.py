import pandas as pd
import os
import streamlit as st

from core.compatibility import filtrar_df, asegurar_assist


@st.cache_data(ttl=3600)
def load_data():
    df = pd.read_csv("beyblade_stats.csv")
    return filtrar_df(df)


@st.cache_data(ttl=3600)
def load_history():
    files = sorted(os.listdir("history"))
    dfs = []

    for file in files:
        if file.endswith(".csv"):
            # asegurar_assist: capturas sin columna Assist se separan al vuelo
            df = asegurar_assist(pd.read_csv(f"history/{file}"))
            df["fecha"] = file.replace("beyblade_stats_", "").replace(".csv", "")
            dfs.append(df)

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
