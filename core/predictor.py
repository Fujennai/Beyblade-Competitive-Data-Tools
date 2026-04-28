import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor

from core.metrics import wilson


# ----------------------------
# Utils
# ----------------------------

def calcular_score_pieza(df, columna):
    stats = df.groupby(columna).agg({
        "Wins": "sum",
        "Partidas": "sum"
    }).reset_index()

    stats["score"] = stats.apply(
        lambda row: wilson(row["Wins"], row["Partidas"]),
        axis=1
    )

    return dict(zip(stats[columna], stats["score"]))


# ----------------------------
# Preparación de datos
# ----------------------------

def preparar_datos(df):

    df = df.copy()

    # ------------------------
    # Target robusto (Wilson)
    # ------------------------

    df["Wilson Score"] = df.apply(
        lambda row: wilson(row["Wins"], row["Partidas"]),
        axis=1
    )

    # ------------------------
    # Volumen
    # ------------------------

    df["Partidas_log"] = np.log1p(df["Partidas"])

    # ------------------------
    # Scores por pieza
    # ------------------------

    blade_dict = calcular_score_pieza(df, "Blade")
    ratchet_dict = calcular_score_pieza(df, "Ratchet")
    bit_dict = calcular_score_pieza(df, "Bit")

    df["Blade_score"] = df["Blade"].map(blade_dict)
    df["Ratchet_score"] = df["Ratchet"].map(ratchet_dict)
    df["Bit_score"] = df["Bit"].map(bit_dict)

    return df


# ----------------------------
# Entrenamiento
# ----------------------------

def entrenar_modelo(df):

    df = preparar_datos(df)

    # Categóricas
    X_cat = pd.get_dummies(df[["Blade", "Ratchet", "Bit"]])

    # Features finales
    X = X_cat.copy()
    X["Partidas_log"] = df["Partidas_log"]
    X["Blade_score"] = df["Blade_score"]
    X["Ratchet_score"] = df["Ratchet_score"]
    X["Bit_score"] = df["Bit_score"]

    # Target
    y = df["Wilson Score"]

    model = RandomForestRegressor(
        n_estimators=300,
        max_depth=None,
        random_state=42
    )

    model.fit(X, y)

    return model, X.columns


# ----------------------------
# Predicción
# ----------------------------

def predecir(model, columns, blade, ratchet, bit, partidas=50, df_ref=None):

    input_df = pd.DataFrame([{
        "Blade": blade,
        "Ratchet": ratchet,
        "Bit": bit
    }])

    input_encoded = pd.get_dummies(input_df)
    input_encoded = input_encoded.reindex(columns=columns, fill_value=0)

    # Volumen
    if "Partidas_log" in columns:
        input_encoded["Partidas_log"] = np.log1p(partidas)

    # ------------------------
    # Scores de piezas (IMPORTANTE)
    # ------------------------

    if df_ref is not None:

        blade_dict = calcular_score_pieza(df_ref, "Blade")
        ratchet_dict = calcular_score_pieza(df_ref, "Ratchet")
        bit_dict = calcular_score_pieza(df_ref, "Bit")

        input_encoded["Blade_score"] = blade_dict.get(blade, 0)
        input_encoded["Ratchet_score"] = ratchet_dict.get(ratchet, 0)
        input_encoded["Bit_score"] = bit_dict.get(bit, 0)

    pred = model.predict(input_encoded)[0]

    return round(pred * 100, 2)