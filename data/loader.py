import pandas as pd
import os
import streamlit as st

from core.compatibility import filtrar_df, asegurar_assist


# Versión del formato de datos. Súbela cuando cambie la forma de los datos
# (columnas nuevas, reglas de filtrado...): forma parte de la clave de la
# caché, así Streamlit Cloud no sirve DataFrames con el formato antiguo tras
# un despliegue (la caché sobrevive al redeploy y solo mira el código de la
# propia función, no el de filtrar_df).
FORMATO_DATOS = 2  # 2: columna Assist separada del Blade en los CX


def load_data():
    return _load_data(FORMATO_DATOS)


def load_history():
    return _load_history(FORMATO_DATOS)


@st.cache_data(ttl=3600)
def _load_data(formato):
    df = pd.read_csv("beyblade_stats.csv")
    return filtrar_df(df)


@st.cache_data(ttl=3600)
def _load_history(formato):
    files = sorted(os.listdir("history"))
    dfs = []

    for file in files:
        if file.endswith(".csv"):
            # asegurar_assist: capturas sin columna Assist se separan al vuelo
            df = asegurar_assist(pd.read_csv(f"history/{file}"))
            df["fecha"] = file.replace("beyblade_stats_", "").replace(".csv", "")
            dfs.append(df)

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
