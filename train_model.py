"""
train_model.py
--------------
Entrena UN SOLO modelo GradientBoosting compartido por:
  - core/recommender.py  (recomendador)
  - core/predictor.py    (predictor)
  - core/meta_hidden.py  (META oculto)

Guarda model.pkl con todo lo necesario para inferencia.
Se ejecuta desde GitHub Actions tras el scraping.
"""

import pickle
import math
import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder

CSV_PATH   = "beyblade_stats.csv"
MODEL_PATH = "model.pkl"


# ── Wilson Score ──────────────────────────────────────────────────────────────
def wilson(w, n, z=1.96):
    if n == 0:
        return 0.0
    p = w / n
    return (p + z**2/(2*n) - z*((p*(1-p)+z**2/(4*n))/n)**0.5) / (1 + z**2/n)


# ── Score por pieza ───────────────────────────────────────────────────────────
def calcular_score_pieza(df, columna):
    stats = df.groupby(columna).agg({"Wins": "sum", "Partidas": "sum"}).reset_index()
    stats["score"] = stats.apply(lambda r: wilson(r["Wins"], r["Partidas"]), axis=1)
    return dict(zip(stats[columna], stats["score"]))


# ── Entrenamiento ─────────────────────────────────────────────────────────────
def entrenar_y_guardar():
    df = pd.read_csv(CSV_PATH)

    if df.empty or "Wilson Score" not in df.columns:
        raise ValueError("CSV vacío o sin columna Wilson Score")

    print(f"Filas cargadas: {len(df)}")

    # Label encoders
    encoders = {}
    for col in ["Blade", "Ratchet", "Bit"]:
        le = LabelEncoder()
        df[col + "_enc"] = le.fit_transform(df[col].astype(str))
        encoders[col] = le

    # Features adicionales (mejoran la precisión)
    df["Partidas_log"] = np.log1p(df["Partidas"])

    blade_dict   = calcular_score_pieza(df, "Blade")
    ratchet_dict = calcular_score_pieza(df, "Ratchet")
    bit_dict     = calcular_score_pieza(df, "Bit")

    df["Blade_score"]   = df["Blade"].map(blade_dict)
    df["Ratchet_score"] = df["Ratchet"].map(ratchet_dict)
    df["Bit_score"]     = df["Bit"].map(bit_dict)

    feature_cols = [
        "Blade_enc", "Ratchet_enc", "Bit_enc",
        "Partidas_log",
        "Blade_score", "Ratchet_score", "Bit_score",
    ]

    X = df[feature_cols].values
    y = df["Wilson Score"].values

    model = GradientBoostingRegressor(
        n_estimators=300,
        learning_rate=0.05,
        max_depth=4,
        subsample=0.8,
        random_state=42,
    )
    model.fit(X, y)

    payload = {
        "model":        model,
        "encoders":     encoders,
        "feature_cols": feature_cols,
        "blade_dict":   blade_dict,
        "ratchet_dict": ratchet_dict,
        "bit_dict":     bit_dict,
        "ws_mean":      float(df["Wilson Score"].mean()),
    }

    # ----------------------------
    # Pesos de cada pieza
    # ----------------------------
    # Correlación de Spearman entre Wilson Score medio de cada pieza
    # y Wilson Score del combo → proxy del peso real de cada pieza

    from scipy.stats import spearmanr

    df["blade_ws_mean"]   = df["Blade"].map(blade_dict)
    df["ratchet_ws_mean"] = df["Ratchet"].map(ratchet_dict)
    df["bit_ws_mean"]     = df["Bit"].map(bit_dict)

    corr_blade,   _ = spearmanr(df["blade_ws_mean"],   df["Wilson Score"])
    corr_ratchet, _ = spearmanr(df["ratchet_ws_mean"], df["Wilson Score"])
    corr_bit,     _ = spearmanr(df["bit_ws_mean"],     df["Wilson Score"])

    # Normalizar para que sumen 1 (usar abs por si alguna correlación es negativa)
    total = abs(corr_blade) + abs(corr_ratchet) + abs(corr_bit)
    piece_weights = {
        "Blade":   round(abs(corr_blade)   / total, 4),
        "Ratchet": round(abs(corr_ratchet) / total, 4),
        "Bit":     round(abs(corr_bit)     / total, 4),
    }

    print(f"Pesos estimados por pieza: {piece_weights}")

    payload["piece_weights"] = piece_weights

    with open(MODEL_PATH, "wb") as f:
        pickle.dump(payload, f)

    print(f"✅ model.pkl guardado con {len(df)} filas y {len(feature_cols)} features")


if __name__ == "__main__":
    entrenar_y_guardar()