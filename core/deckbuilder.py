"""
core/deckbuilder.py
-------------------
Optimizador de deck basado en 3 recomendadores independientes.
Para cada bey llama al recomendador con las piezas fijadas,
luego elige la mejor combinación de 3 que no repita piezas.
Score: 0.6 * Wilson Score medio + 0.4 * Wilson Score mínimo
"""

import numpy as np

from core.recommender import recomendar_builds
from core.compatibility import ratchet_repetido, blade_repetido


def _score_deck(ws_list):
    return 0.6 * np.mean(ws_list) + 0.4 * np.min(ws_list)


def _choca(r, otros):
    """True si el combo `r` repite alguna pieza física de los combos `otros`."""
    return (
        blade_repetido(r["Blade"], r["Assist"], [(o["Blade"], o["Assist"]) for o in otros])
        or ratchet_repetido(r["Ratchet"], [o["Ratchet"] for o in otros])
        or r["Bit"] in [o["Bit"] for o in otros]
    )


def optimizar_deck(df, fijados):
    """
    fijados: lista de 3 dicts con claves opcionales Blade/Assist/Ratchet/Bit.
    Devuelve (lista de 3 beys, score_deck) o None si no hay solución.
    """
    # Obtener candidatos de cada bey via recomendador
    candidatos = []
    for bey in fijados:
        df_rec = recomendar_builds(
            df, bey.get("Blade"), bey.get("Ratchet"), bey.get("Bit"),
            top_n=20, assist=bey.get("Assist"),
        )
        if df_rec.empty:
            return None
        candidatos.append([r for _, r in df_rec.iterrows()])

    mejor_score = -1
    mejor_deck  = None

    # Buscar la mejor combinación sin repetir ninguna pieza física
    for r0 in candidatos[0]:
        for r1 in candidatos[1]:
            if _choca(r1, [r0]):
                continue
            for r2 in candidatos[2]:
                if _choca(r2, [r0, r1]):
                    continue

                ws_list = [r0["Wilson Score Predicho"], r1["Wilson Score Predicho"], r2["Wilson Score Predicho"]]
                score   = _score_deck(ws_list)

                if score > mejor_score:
                    mejor_score = score
                    mejor_deck  = [r0, r1, r2]

    if mejor_deck is None:
        return None

    resultado = []
    for i, row in enumerate(mejor_deck):
        fijado = fijados[i]
        resultado.append({
            "Bey":                i + 1,
            "Blade":              row["Blade"],
            "Assist":             row["Assist"],
            "Ratchet":            row["Ratchet"],
            "Bit":                row["Bit"],
            "Wilson Score":       row["Wilson Score Predicho"],
            "Arquetipo victoria": row.get("Arquetipo victoria", "—"),
            "Arquetipo derrota":  row.get("Arquetipo derrota",  "—"),
            "Tipo":               row.get("Tipo", "—"),
            "Blade fijada":       "Blade"   in fijado,
            "Assist fijado":      "Assist"  in fijado,
            "Ratchet fijado":     "Ratchet" in fijado,
            "Bit fijado":         "Bit"     in fijado,
        })

    return resultado, round(mejor_score, 4)
