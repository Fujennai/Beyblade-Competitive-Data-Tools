"""
core/predictor.py
-----------------
Usa el modelo compartido (model.pkl) para predecir
el Wilson Score de un combo dado.

MEJORAS v2:
  - Usa features de interacción par-a-par (BR, BB, RB)
  - Aplica ancla bayesiana: blend ML + evidencia real ponderada por volumen
"""

import numpy as np
import pandas as pd

from core.model_loader import cargar_modelo


def _ancla_bayesiana(p, blade, ratchet, bit, partidas):
    """
    Mezcla la predicción ML con la evidencia histórica real.
    Cuanta más evidencia real haya (combo completo > pares > piezas),
    más peso se le da al historial y menos al ML puro.
    """
    combo_dict   = p["combo_dict"]
    par_br       = p["par_br"]
    par_bb       = p["par_bb"]
    par_rb       = p["par_rb"]
    blade_dict   = p["blade_dict"]
    ratchet_dict = p["ratchet_dict"]
    bit_dict     = p["bit_dict"]
    ws_mean      = p["ws_mean"]

    evidencia = []
    pesos     = []

    # Combo completo real
    if (blade, ratchet, bit) in combo_dict:
        ws_real, n_real = combo_dict[(blade, ratchet, bit)]
        w = min(n_real / 30.0, 1.0)
        evidencia.append(ws_real)
        pesos.append(w * 3.0)

    # Pares observados
    for par_dict, key in [
        (par_br, (blade, ratchet)),
        (par_bb, (blade, bit)),
        (par_rb, (ratchet, bit)),
    ]:
        if key in par_dict:
            evidencia.append(par_dict[key])
            pesos.append(1.0)

    # Piezas individuales
    evidencia.append(blade_dict.get(blade, ws_mean))
    evidencia.append(ratchet_dict.get(ratchet, ws_mean))
    evidencia.append(bit_dict.get(bit, ws_mean))
    pesos.extend([0.3, 0.3, 0.3])

    ancla      = np.average(evidencia, weights=pesos)
    # Peso del ancla: sube con más evidencia real (combo > pares)
    peso_ancla = min(sum(pesos[:len(evidencia) - 3]) / 6.0, 0.85)

    return float(ancla), float(peso_ancla)


def predecir(blade, ratchet, bit, partidas=50):
    """
    Predice el Wilson Score de un combo y lo devuelve como winrate (%).
    Aplica ancla bayesiana sobre la predicción ML.
    """
    p        = cargar_modelo()
    model    = p["model"]
    encoders = p["encoders"]
    blade_dict   = p["blade_dict"]
    ratchet_dict = p["ratchet_dict"]
    bit_dict     = p["bit_dict"]
    ws_mean      = p["ws_mean"]
    par_br = p.get("par_br", {})
    par_bb = p.get("par_bb", {})
    par_rb = p.get("par_rb", {})

    # Verificar que las piezas son conocidas
    for col, val in [("Blade", blade), ("Ratchet", ratchet), ("Bit", bit)]:
        if val not in encoders[col].classes_:
            return None

    row = {
        "Blade_enc":    encoders["Blade"].transform([blade])[0],
        "Ratchet_enc":  encoders["Ratchet"].transform([ratchet])[0],
        "Bit_enc":      encoders["Bit"].transform([bit])[0],
        "Partidas_log": np.log1p(partidas),
        "Blade_score":  blade_dict.get(blade, ws_mean),
        "Ratchet_score": ratchet_dict.get(ratchet, ws_mean),
        "Bit_score":    bit_dict.get(bit, ws_mean),
        # Features de interacción par-a-par
        "BR_score": par_br.get((blade, ratchet), ws_mean),
        "BB_score": par_bb.get((blade, bit),     ws_mean),
        "RB_score": par_rb.get((ratchet, bit),   ws_mean),
    }

    feature_cols = p["feature_cols"]
    X = pd.DataFrame([row])[feature_cols].values.astype(float)
    pred_ml = float(model.predict(X)[0])

    # Ancla bayesiana
    ancla, peso_ancla = _ancla_bayesiana(p, blade, ratchet, bit, partidas)

    # Blend final: más peso al ancla si hay evidencia real
    pred_final = (1 - peso_ancla) * pred_ml + peso_ancla * ancla

    return round(pred_final * 100, 2)