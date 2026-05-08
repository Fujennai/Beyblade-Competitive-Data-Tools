"""
core/deckbuilder.py
-------------------
Optimizador de deck basado en 3 recomendadores independientes.
Para cada bey llama al recomendador con las piezas fijadas,
luego elige la mejor combinación de 3 que no repita piezas.
Score: 0.6 * Wilson Score medio + 0.4 * Wilson Score mínimo
"""

import numpy as np
import pandas as pd

from core.recommender import recomendar_builds


def _score_deck(ws_list):
    return 0.6 * np.mean(ws_list) + 0.4 * np.min(ws_list)


def optimizar_deck(df, fijados):
    """
    fijados: lista de 3 dicts con claves opcionales Blade/Ratchet/Bit.
    Devuelve (lista de 3 beys, score_deck) o None si no hay solución.
    """
    # Obtener candidatos de cada bey via recomendador
    candidatos = []
    for bey in fijados:
        blade   = bey.get("Blade")
        ratchet = bey.get("Ratchet")
        bit     = bey.get("Bit")
        df_rec = recomendar_builds(df, blade, ratchet, bit, top_n=20)
        if df_rec.empty:
            return None
        candidatos.append(df_rec)

    mejor_score = -1
    mejor_deck  = None

    # Buscar la mejor combinación sin repetir Blade, Ratchet ni Bit
    for _, r0 in candidatos[0].iterrows():
        for _, r1 in candidatos[1].iterrows():
            if r1["Blade"] == r0["Blade"] or r1["Ratchet"] == r0["Ratchet"] or r1["Bit"] == r0["Bit"]:
                continue
            for _, r2 in candidatos[2].iterrows():
                if (r2["Blade"] in (r0["Blade"], r1["Blade"]) or
                    r2["Ratchet"] in (r0["Ratchet"], r1["Ratchet"]) or
                    r2["Bit"] in (r0["Bit"], r1["Bit"])):
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
            "Ratchet":            row["Ratchet"],
            "Bit":                row["Bit"],
            "Wilson Score":       row["Wilson Score Predicho"],
            "Arquetipo victoria": row.get("Arquetipo victoria", "—"),
            "Arquetipo derrota":  row.get("Arquetipo derrota",  "—"),
            "Tipo":               row.get("Tipo", "—"),
            "Blade fijada":       "Blade"   in fijado,
            "Ratchet fijado":     "Ratchet" in fijado,
            "Bit fijado":         "Bit"     in fijado,
        })

    return resultado, round(mejor_score, 4)