"""
core/model_loader.py
--------------------
Punto único de carga del modelo compartido.
Todas las pestañas importan desde aquí.
"""

import pickle
import os

MODEL_PATH = "model.pkl"

_cache = {}


def cargar_modelo():
    """
    Carga model.pkl y lo cachea en memoria.
    Devuelve el payload completo:
      {
        model, encoders, feature_cols,
        blade_dict, ratchet_dict, bit_dict, ws_mean
      }
    """
    if "payload" not in _cache:
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                "No se encontró model.pkl. "
                "Ejecuta train_model.py o lanza el GitHub Action."
            )
        with open(MODEL_PATH, "rb") as f:
            _cache["payload"] = pickle.load(f)

    return _cache["payload"]