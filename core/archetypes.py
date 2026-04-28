import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans


def calcular_arquetipos(df, n_clusters=4):

    features = df[[
        "Win %",
        "Pts Ganados/Combate",
        "Pts Cedidos/Combate",
        "Eficiencia"
    ]].dropna()

    # Escalar
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(features)

    # Clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)

    df_clustered = df.loc[features.index].copy()
    df_clustered["cluster"] = clusters

    return df_clustered, kmeans

    def etiquetar_arquetipos(df):

    resumen = df.groupby("cluster").agg({
        "Win %": "mean",
        "Pts Ganados/Combate": "mean",
        "Pts Cedidos/Combate": "mean"
    })

    etiquetas = {}

    for cluster, row in resumen.iterrows():

        atk = row["Pts Ganados/Combate"]
        defn = row["Pts Cedidos/Combate"]
        wr = row["Win %"]

        if atk > 1.4 and defn > 1.4:
            etiquetas[cluster] = "🔥 Agresivo"
        elif defn < 1.2:
            etiquetas[cluster] = "🛡️ Defensivo"
        elif abs(atk - defn) < 0.2:
            etiquetas[cluster] = "⚖️ Equilibrado"
        elif wr > 75 and atk > 1.3:
            etiquetas[cluster] = "🎲 High Risk / High Reward"
        else:
            etiquetas[cluster] = "🔄 Híbrido"

    df["arquetipo"] = df["cluster"].map(etiquetas)

    return df