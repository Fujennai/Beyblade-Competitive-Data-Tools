"""
core/predictor.py
-----------------
Usa el modelo compartido (model.pkl) para predecir
el Wilson Score de un combo dado.
"""

import numpy as np
import pandas as pd

from core.model_loader import cargar_modelo


def predecir(blade, ratchet, bit, partidas=50):
    """
    Predice el Wilson Score de un combo y lo devuelve como winrate (%).
    """
    p        = cargar_modelo()
    model    = p["model"]
    encoders = p["encoders"]
    blade_dict   = p["blade_dict"]
    ratchet_dict = p["ratchet_dict"]
    bit_dict     = p["bit_dict"]
    ws_mean      = p["ws_mean"]

    # Verificar que las piezas son conocidas
    for col, val in [("Blade", blade), ("Ratchet", ratchet), ("Bit", bit)]:
        if val not in encoders[col].classes_:
            return None  # pieza desconocida

    row = {
        "Blade_enc":    encoders["Blade"].transform([blade])[0],
        "Ratchet_enc":  encoders["Ratchet"].transform([ratchet])[0],
        "Bit_enc":      encoders["Bit"].transform([bit])[0],
        "Partidas_log": np.log1p(partidas),
        "Blade_score":  blade_dict.get(blade, ws_mean),
        "Ratchet_score": ratchet_dict.get(ratchet, ws_mean),
        "Bit_score":    bit_dict.get(bit, ws_mean),
    }

    X = pd.DataFrame([row])[p["feature_cols"]].values.astype(float)
    pred = model.predict(X)[0]

    return round(pred * 100, 2)