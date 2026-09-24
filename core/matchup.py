"""
core/matchup.py
---------------
Lógica de matchup 1v1 y deck match.
La probabilidad de victoria usa Wilson Score ponderado por el peso
real de cada pieza (calculado en train_model.py y guardado en model.pkl).
"""

import numpy as np

# Pesos por defecto si no hay model.pkl (estimación conservadora)
DEFAULT_WEIGHTS = {"Blade": 0.60, "Ratchet": 0.20, "Bit": 0.20}


def _cargar_pesos():
    try:
        from core.model_loader import cargar_modelo
        return cargar_modelo().get("piece_weights", DEFAULT_WEIGHTS)
    except Exception:
        return DEFAULT_WEIGHTS


def ws_ponderado(ws_blade, ws_ratchet, ws_bit):
    """Wilson Score ponderado por importancia real de cada pieza."""
    w = _cargar_pesos()
    return (
        w["Blade"]   * ws_blade +
        w["Ratchet"] * ws_ratchet +
        w["Bit"]     * ws_bit
    )


def prob_victoria(ws_a, ws_b):
    """P(A gana un combate) basado en Wilson Score relativo."""
    total = ws_a + ws_b
    if total == 0:
        return 0.5
    return ws_a / total


def pts_esperados(ws_a, ws_b, pts_ganados_a, pts_ganados_b):
    p_a = prob_victoria(ws_a, ws_b)
    return round(p_a * pts_ganados_a, 3), round((1 - p_a) * pts_ganados_b, 3)
