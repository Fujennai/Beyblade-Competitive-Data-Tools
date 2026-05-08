"""
core/recommender.py
-------------------
Modelo predictivo con Gradient Boosting para recomendar builds de Beyblade
que NO existen en el dataset, estimando su Wilson Score esperado.
"""

import pandas as pd
import numpy as np
from itertools import product
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import LabelEncoder

# ── Caché de modelo entrenado ─────────────────────────────────────────────────
_model_cache: dict = {}


def _entrenar_modelo(df: pd.DataFrame):
    cache_key = id(df)
    if cache_key in _model_cache:
        return _model_cache[cache_key]

    df = df.copy()

    encoders = {}
    for col in ["Blade", "Ratchet", "Bit"]:
        le = LabelEncoder()
        df[col + "_enc"] = le.fit_transform(df[col].astype(str))
        encoders[col] = le

    feature_cols = ["Blade_enc", "Ratchet_enc", "Bit_enc"]
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

    _model_cache[cache_key] = (model, encoders)
    return model, encoders


def _combos_no_vistos(df: pd.DataFrame, blade=None, ratchet=None, bit=None) -> pd.DataFrame:
    blades   = [blade]   if blade   else sorted(df["Blade"].unique())
    ratchets = [ratchet] if ratchet else sorted(df["Ratchet"].unique())
    bits     = [bit]     if bit     else sorted(df["Bit"].unique())

    existing = set(
        zip(df["Blade"].astype(str), df["Ratchet"].astype(str), df["Bit"].astype(str))
    )

    rows = [
        (b, r, bt)
        for b, r, bt in product(blades, ratchets, bits)
        if (str(b), str(r), str(bt)) not in existing
    ]

    return pd.DataFrame(rows, columns=["Blade", "Ratchet", "Bit"])


def recomendar_builds(df, blade=None, ratchet=None, bit=None, top_n=20):
    if df.empty or "Wilson Score" not in df.columns:
        return pd.DataFrame()

    model, encoders = _entrenar_modelo(df)

    df_nuevas = _combos_no_vistos(df, blade, ratchet, bit)

    if df_nuevas.empty:
        return pd.DataFrame()

    df_enc = df_nuevas.copy()
    valid_mask = pd.Series([True] * len(df_enc), index=df_enc.index)

    for col in ["Blade", "Ratchet", "Bit"]:
        le = encoders[col]
        known = set(le.classes_)
        valid_mask &= df_enc[col].isin(known)

    df_enc = df_enc[valid_mask].copy()

    if df_enc.empty:
        return pd.DataFrame()

    for col in ["Blade", "Ratchet", "Bit"]:
        le = encoders[col]
        df_enc[col + "_enc"] = le.transform(df_enc[col].astype(str))

    X_pred = df_enc[["Blade_enc", "Ratchet_enc", "Bit_enc"]].values.astype(float)
    y_pred = model.predict(X_pred)
    df_enc["Wilson Score Predicho"] = np.round(y_pred, 4)

    # Confianza basada en Wilson Score histórico promedio de cada pieza
    ws_blade   = df.groupby("Blade")["Wilson Score"].mean().to_dict()
    ws_ratchet = df.groupby("Ratchet")["Wilson Score"].mean().to_dict()
    ws_bit     = df.groupby("Bit")["Wilson Score"].mean().to_dict()

    ws_global_mean = df["Wilson Score"].mean()
    umbral_alto  = ws_global_mean + 0.05
    umbral_medio = ws_global_mean - 0.05

    def confianza(row):
        ws_medio = (
            ws_blade.get(row["Blade"], ws_global_mean)
            + ws_ratchet.get(row["Ratchet"], ws_global_mean)
            + ws_bit.get(row["Bit"], ws_global_mean)
        ) / 3
        if ws_medio >= umbral_alto:
            return "🟢 Alta"
        elif ws_medio >= umbral_medio:
            return "🟡 Media"
        else:
            return "🔴 Baja"

    df_enc["Confianza"] = df_enc.apply(confianza, axis=1)

    # Referencia más cercana en el dataset
    ws_reales = df["Wilson Score"].values

    def referencia_cercana(ws_pred):
        idx = np.argmin(np.abs(ws_reales - ws_pred))
        row = df.iloc[idx]
        return f"{row['Blade']} / {row['Ratchet']} / {row['Bit']} ({row['Wilson Score']:.4f})"

    df_enc["Referencia más cercana"] = df_enc["Wilson Score Predicho"].apply(referencia_cercana)

    return (
        df_enc[["Blade", "Ratchet", "Bit", "Wilson Score Predicho", "Confianza", "Referencia más cercana"]]
        .sort_values("Wilson Score Predicho", ascending=False)
        .head(top_n)
        .reset_index(drop=True)
    )