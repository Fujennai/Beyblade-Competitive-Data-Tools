import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans


def calcular_arquetipos(df, n_clusters=3):

    features = df[[
        "Pts Ganados/Combate",
        "Pts Cedidos/Combate"
    ]].dropna()

    scaler = StandardScaler()
    X = scaler.fit_transform(features)

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X)

    df_out = df.loc[features.index].copy()
    df_out["cluster"] = clusters

    return df_out


def etiquetar_arquetipos(df):

    resumen = df.groupby("cluster").agg({
        "Pts Ganados/Combate": "mean",
        "Pts Cedidos/Combate": "mean"
    })

    etiquetas = {}

    for cluster, row in resumen.iterrows():

        atk = row["Pts Ganados/Combate"]
        defn = row["Pts Cedidos/Combate"]

        if atk > defn + 0.3:
            etiquetas[cluster] = "🔥 Agresivo"

        elif defn > atk + 0.3:
            etiquetas[cluster] = "🛡️ Defensivo"

        else:
            etiquetas[cluster] = "⚖️ Equilibrado"

    df["arquetipo"] = df["cluster"].map(etiquetas)

    return df