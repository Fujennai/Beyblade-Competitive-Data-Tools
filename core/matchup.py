"""
core/matchup.py
---------------
Lógica de matchup 1v1 y deck match.
La probabilidad de victoria usa Wilson Score ponderado por el peso
real de cada pieza (calculado en train_model.py y guardado en model.pkl).
"""

import numpy as np
from itertools import permutations

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


# ── Simulación Montecarlo deck match ─────────────────────────────────────────

def simular_deck_match(deck_a, deck_b, n_sims=10_000, seed=42):
    rng = np.random.default_rng(seed)
    victorias_a = 0

    probs = np.array([
        [prob_victoria(a["ws"], b["ws"]) for b in deck_b]
        for a in deck_a
    ])

    for _ in range(n_sims):
        score_a = 0
        score_b = 0
        bey_a = 0
        bey_b = 0

        while score_a < 4 and score_b < 4 and bey_a < 3 and bey_b < 3:
            p = probs[bey_a][bey_b]
            if rng.random() < p:
                score_a += deck_a[bey_a]["pts_ganados"]
                if score_a < 4 and score_b < 4:
                    bey_b += 1
            else:
                score_b += deck_b[bey_b]["pts_ganados"]
                if score_a < 4 and score_b < 4:
                    bey_a += 1

        if score_a >= 4:
            victorias_a += 1

    return round(victorias_a / n_sims, 4)


def orden_optimo(mi_deck, rival_deck, n_sims=5_000):
    mis_perms   = list(permutations(range(3)))
    rival_perms = list(permutations(range(3)))
    resultados  = []

    for mi_perm in mis_perms:
        mi_orden = [mi_deck[i] for i in mi_perm]
        probs_vs_rival = []

        for rival_perm in rival_perms:
            rival_orden = [rival_deck[i] for i in rival_perm]
            p = simular_deck_match(mi_orden, rival_orden, n_sims=n_sims)
            probs_vs_rival.append(p)

        prob_media = round(np.mean(probs_vs_rival), 4)
        resultados.append((mi_perm, mi_orden, prob_media))

    return sorted(resultados, key=lambda x: x[2], reverse=True)