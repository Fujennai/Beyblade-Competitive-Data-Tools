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

    # Pre-calcular Wilson Score de todos los combos posibles en una sola pasada
    ws_cache = {}
    for _, row in df.iterrows():
        ws_cache[(row["Blade"], row["Ratchet"], row["Bit"])] = float(row["Wilson Score"])

    # Score por pieza individual para estimaciones rápidas
    blade_ws   = df.groupby("Blade")["Wilson Score"].mean().to_dict()
    ratchet_ws = df.groupby("Ratchet")["Wilson Score"].mean().to_dict()
    bit_ws     = df.groupby("Bit")["Wilson Score"].mean().to_dict()

    def _ws_fast(b, r, bt):
        if (b, r, bt) in ws_cache:
            return ws_cache[(b, r, bt)]
        scores = [blade_ws.get(b, ws_mean), ratchet_ws.get(r, ws_mean), bit_ws.get(bt, ws_mean)]
        return round(np.mean(scores), 4)

    # Candidatos por bey respetando lo fijado
    candidatos = []
    for bey in fijados:
        b_opts  = [bey["Blade"]]   if "Blade"   in bey else blades
        r_opts  = [bey["Ratchet"]] if "Ratchet" in bey else ratchets
        bt_opts = [bey["Bit"]]     if "Bit"     in bey else bits
        candidatos.append(list(iproduct(b_opts, r_opts, bt_opts)))

    mejor_score = -1
    mejor_deck  = None

    for combo0 in candidatos[0]:
        b0, r0, bt0 = combo0
        for combo1 in candidatos[1]:
            b1, r1, bt1 = combo1
            # Podar temprano: Blade o Ratchet o Bit repetido con combo0
            if b1 == b0 or r1 == r0 or bt1 == bt0:
                continue
            for combo2 in candidatos[2]:
                b2, r2, bt2 = combo2
                # Podar temprano
                if b2 in (b0, b1) or r2 in (r0, r1) or bt2 in (bt0, bt1):
                    continue

                ws_list = [_ws_fast(b0,r0,bt0), _ws_fast(b1,r1,bt1), _ws_fast(b2,r2,bt2)]
                score   = _score_deck(ws_list)

                if score > mejor_score:
                    mejor_score = score
                    mejor_deck  = [combo0, combo1, combo2]

    if mejor_deck is None:
        return None

    # Construir resultado
    resultado = []
    for i, (b, r, bt) in enumerate(mejor_deck):
        es_real = (b, r, bt) in ws_cache
        ws = _ws_fast(b, r, bt)
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