import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor

from core.metrics import wilson


# ----------------------------
# Preparación de datos
# ----------------------------

def preparar_datos(df):

    df = df.copy()

    # Wilson Score (fiabilidad)
    df["Wilson Score"] = df.apply(
        lambda row: wilson(row["Wins"], row["Partidas"]),
        axis=1
    )

    # Feature adicional: volumen (log)
    df["Partidas_log"] = np.log1p(df["Partidas"])

    return df


# ----------------------------
# Entrenamiento
# ----------------------------

def entrenar_modelo(df):

    df = preparar_datos(df)

    # Features categóricas
    X_cat = pd.get_dummies(df[["Blade", "Ratchet", "Bit"]])

    # Feature numérica
    X = X_cat.copy()
    X["Partidas_log"] = df["Partidas_log"]

    # Target robusto
    y = df["Wilson Score"]

    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=None,
        random_state=42
    )

    model.fit(X, y)

    return model, X.columns


# ----------------------------
# Predicción
# ----------------------------

def predecir(model, columns, blade, ratchet, bit, partidas=50):

    input_df = pd.DataFrame([{
        "Blade": blade,
        "Ratchet": ratchet,
        "Bit": bit
    }])

    # encoding
    input_encoded = pd.get_dummies(input_df)
    input_encoded = input_encoded.reindex(columns=columns, fill_value=0)

    # añadir volumen
    if "Partidas_log" in columns:
        input_encoded["Partidas_log"] = np.log1p(partidas)

    pred = model.predict(input_encoded)[0]

    # convertir a %
    return round(pred * 100, 2)