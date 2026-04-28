import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


def encontrar_mejor_k(X_scaled, k_range=(2, 5)):

    resultados = []

    for k in range(k_range[0], k_range[1] + 1):

        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X_scaled)

        # evitar errores si solo hay un cluster real
        if len(set(labels)) > 1:
            score = silhouette_score(X_scaled, labels)
            resultados.append((k, score))

    # ordenar por mejor score
    resultados.sort(key=lambda x: x[1], reverse=True)

    return resultados


def calcular_arquetipos(df, n_clusters=None):

    features = df[[
        "Pts Ganados/Combate",
        "Pts Cedidos/Combate"
    ]].dropna()

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(features)

    # elegir k automáticamente si no se pasa
    if n_clusters is None:
        resultados = encontrar_mejor_k(X_scaled)
        n_clusters = resultados[0][0] if resultados else 3

    kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)

    df_out = df.loc[features.index].copy()
    df_out["cluster"] = clusters

    return df_out, kmeans, n_clusters


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