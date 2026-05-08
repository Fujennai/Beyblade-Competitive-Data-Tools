"""
core/deckbuilder.py
-------------------
Optimizador de deck para 3 beys.
- Respeta las piezas fijadas por el usuario
- Asigna piezas compartidas al bey que más se beneficia
- Optimiza: 0.6 * Wilson Score medio + 0.4 * Wilson Score mínimo (cuello de botella)
"""

import numpy as np
import pandas as pd
from itertools import product as iproduct


# ── Arquetipos ────────────────────────────────────────────────────────────────

MAP_VICTORIA = {
    -1: "⚪ Datos insuficientes",
     0: "⚫ Alta tendencia a perder",
     1: "🔵 Spin finish",
     2: "🟠 Burst / Over",
     3: "🟢 Xtreme finish"
}

MAP_DERROTA = {
    -1: "⚪ Datos insuficientes",
     0: "🟡 Alta tendencia a ganar",
     1: "🔵 Pierde por spin",
     2: "🟠 Pierde por burst/over",
     3: "🟢 Pierde por xtreme"
}


def _categorizar(valor, partidas, winrate):
    if partidas < 10:               return -1
    if winrate >= 95 and partidas < 25: return -1
    if valor < 0.5:   return 0
    elif valor < 1.5: return 1
    elif valor < 2.5: return 2
    else:             return 3


def _arquetipo(df, blade, ratchet, bit):
    """Arquetipo de un combo concreto, o estimado por piezas si no existe."""
    row = df[(df["Blade"] == blade) & (df["Ratchet"] == ratchet) & (df["Bit"] == bit)]
    if not row.empty:
        r = row.iloc[0]
        if "Arquetipo victoria" in df.columns:
            return r["Arquetipo victoria"], r["Arquetipo derrota"]
        tv = _categorizar(r["Pts Ganados/Combate"], r["Partidas"], r["Win %"])
        td = _categorizar(r["Pts Cedidos/Combate"], r["Partidas"], r["Win %"])
        return MAP_VICTORIA[tv], MAP_DERROTA[td]

    # Estimado por piezas
    pts_g, pts_c = [], []
    for col, val in [("Blade", blade), ("Ratchet", ratchet), ("Bit", bit)]:
        s = df[df[col] == val]
        if not s.empty:
            pts_g.append(s["Pts Ganados/Combate"].mean())
            pts_c.append(s["Pts Cedidos/Combate"].mean())
    if not pts_g:
        return "⚪ Datos insuficientes", "⚪ Datos insuficientes"
    tv = _categorizar(np.mean(pts_g), 30, 55)
    td = _categorizar(np.mean(pts_c), 30, 55)
    return MAP_VICTORIA[tv], MAP_DERROTA[td]


# ── Wilson Score de un combo ──────────────────────────────────────────────────

def _wilson_combo(df, blade, ratchet, bit, ws_mean):
    """Wilson Score real si existe, estimado por sinergia si no."""
    row = df[(df["Blade"] == blade) & (df["Ratchet"] == ratchet) & (df["Bit"] == bit)]
    if not row.empty:
        return float(row.iloc[0]["Wilson Score"]), True  # (score, es_real)

    # Estimado: media ponderada de Wilson Score de cada pieza
    scores = []
    for col, val in [("Blade", blade), ("Ratchet", ratchet), ("Bit", bit)]:
        s = df[df[col] == val]["Wilson Score"]
        if not s.empty:
            scores.append(s.mean())
    if not scores:
        return ws_mean, False
    return round(np.mean(scores), 4), False


# ── Score de deck ─────────────────────────────────────────────────────────────

def _score_deck(ws_list):
    """0.6 * media + 0.4 * mínimo"""
    return 0.6 * np.mean(ws_list) + 0.4 * np.min(ws_list)


# ── Optimizador principal ─────────────────────────────────────────────────────

def optimizar_deck(df, fijados):
    """
    fijados: lista de 3 dicts, cada uno con claves opcionales Blade/Ratchet/Bit.
    Ejemplo: [{"Blade": "Aero Pegasus"}, {}, {"Bit": "Elevate"}]

    Devuelve lista de 3 dicts con Blade, Ratchet, Bit, Wilson Score,
    Arquetipo victoria, Arquetipo derrota, es_real (bool por pieza).
    """
    ws_mean = df["Wilson Score"].mean()

    blades   = sorted(df["Blade"].unique())
    ratchets = sorted(df["Ratchet"].unique())
    bits     = sorted(df["Bit"].unique())

    # Candidatos por bey respetando lo fijado
    candidatos = []
    for bey in fijados:
        b_opts = [bey["Blade"]]   if "Blade"   in bey else blades
        r_opts = [bey["Ratchet"]] if "Ratchet" in bey else ratchets
        bt_opts = [bey["Bit"]]    if "Bit"     in bey else bits
        candidatos.append(list(iproduct(b_opts, r_opts, bt_opts)))

    mejor_score = -1
    mejor_deck  = None

    for combo0 in candidatos[0]:
        for combo1 in candidatos[1]:
            for combo2 in candidatos[2]:
                combos = [combo0, combo1, combo2]

                # Restricción: no repetir Blade ni Ratchet ni Bit
                blades_usadas   = [c[0] for c in combos]
                ratchets_usados = [c[1] for c in combos]
                bits_usados     = [c[2] for c in combos]

                if (len(set(blades_usadas))   < 3 or
                    len(set(ratchets_usados)) < 3 or
                    len(set(bits_usados))     < 3):
                    continue

                ws_list = [_wilson_combo(df, b, r, bt, ws_mean)[0] for b, r, bt in combos]
                score   = _score_deck(ws_list)

                if score > mejor_score:
                    mejor_score = score
                    mejor_deck  = combos

    if mejor_deck is None:
        return None

    # Construir resultado
    resultado = []
    for i, (b, r, bt) in enumerate(mejor_deck):
        ws, es_real = _wilson_combo(df, b, r, bt, ws_mean)
        arq_v, arq_d = _arquetipo(df, b, r, bt)
        fijado = fijados[i]
        resultado.append({
            "Bey":                i + 1,
            "Blade":              b,
            "Ratchet":            r,
            "Bit":                bt,
            "Wilson Score":       ws,
            "Arquetipo victoria": arq_v,
            "Arquetipo derrota":  arq_d,
            "Blade fijada":       "Blade"   in fijado,
            "Ratchet fijado":     "Ratchet" in fijado,
            "Bit fijado":         "Bit"     in fijado,
            "Combo real":         es_real,
        })

    return resultado, round(mejor_score, 4)