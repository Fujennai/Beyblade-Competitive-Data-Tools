"""
core/model_loader.py
--------------------
Punto único de carga del modelo compartido.
Todas las pestañas importan desde aquí.

Si no existe model.pkl (o es de un formato anterior, p.ej. sin Assist),
entrena en memoria con el MISMO código que train_model.py
(construir_payload), para no tener dos entrenamientos distintos (y que el
fallback no reintroduzca la fuga de información).
"""

import os
import pickle

import pandas as pd

MODEL_PATH = "model.pkl"
CSV_PATH = "beyblade_stats.csv"

_cache = {}


def cargar_modelo():
    """
    Devuelve el payload completo:
      {
        model, encoders, feature_cols,
        blade_dict, assist_dict, ratchet_dict, bit_dict, ws_mean, ...
      }
    """
    if "payload" not in _cache:
        from train_model import construir_payload, FORMATO_PAYLOAD

        payload = None
        if os.path.exists(MODEL_PATH):
            with open(MODEL_PATH, "rb") as f:
                payload = pickle.load(f)
            if payload.get("formato") != FORMATO_PAYLOAD:
                payload = None  # model.pkl antiguo: se reentrena abajo

        if payload is None:
            if not os.path.exists(CSV_PATH):
                raise FileNotFoundError(
                    "No se encontró model.pkl ni beyblade_stats.csv. "
                    "Ejecuta scraper.py y train_model.py."
                )
            payload = construir_payload(
                pd.read_csv(CSV_PATH), evaluar=False, verbose=False
            )
        _cache["payload"] = payload

    return _cache["payload"]
