"""
core/recommender.py
-------------------
Recomendador basado en sinergia par a par:
1. Para la Blade dada, calcula el Wilson Score de cada Ratchet/Bit
   usando SOLO los combos que incluyen esa Blade (datos directos)
2. Si hay pocos datos directos, busca Blades del mismo arquetipo
   y usa sus stats como proxy, ponderadas por similitud de arquetipo
3. Devuelve combos reales primero, predichos de relleno marcados
"""

import numpy as np
import pandas as pd
from itertools import product

from core.model_loader import cargar_modelo


# ── Labels (mismos que 2_Arquetipos.py) ──────────────────────────────────────

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

MIN_PARTIDAS_DIRECTAS = 5   # mínimo para considerar dato directo fiable
MIN_COMBOS_DIRECTOS   = 3   # si la Blade tiene menos combos, buscar proxies


# ── Arquetipos ────────────────────────────────────────────────────────────────

def _categorizar(valor, partidas, winrate):
    if partidas < 10:
        return -1
    if winrate >= 95 and partidas < 25:
        return -1
    if valor < 0.5:   return 0
    elif valor < 1.5: return 1
    elif valor < 2.5: return 2
    else:             return 3


def _asignar_arquetipos(df):
    df = df.copy()
    df["tipo_victoria"] = df.apply(
        lambda r: _categorizar(r["Pts Ganados/Combate"], r["Partidas"], r["Win %"]), axis=1
    )
    df["tipo_derrota"] = df.apply(
        lambda r: _categorizar(r["Pts Cedidos/Combate"], r["Partidas"], r["Win %"]), axis=1
    )
    df["Arquetipo victoria"] = df["tipo_victoria"].map(MAP_VICTORIA)
    df["Arquetipo derrota"]  = df["tipo_derrota"].map(MAP_DERROTA)
    return df


def _arquetipo_blade(df, blade):
    combos = df[
        (df["Blade"] == blade) &
        (df["tipo_victoria"] != -1)
    ]
    if combos.empty:
        return None, None
    tv = combos["tipo_victoria"].mode()
    td = combos["tipo_derrota"].mode()
    return (
        int(tv.iloc[0]) if not tv.empty else None,
        int(td.iloc[0]) if not td.empty else None,
    )


# ── Sinergia par a par ────────────────────────────────────────────────────────

def _score_pieza_con_blade(df, blade, col_pieza, peso_proxy=0.5):
    """
    Calcula el Wilson Score medio de cada valor de col_pieza (Ratchet o Bit)
    cuando se combina con la Blade dada.

    Si hay pocos datos directos, complementa con datos de Blades del mismo
    arquetipo, ponderados por peso_proxy (0-1, menor = menos influencia).

    Devuelve dict {pieza: score_ponderado}
    """
    # Datos directos: solo combos con esta Blade
    directos = df[df["Blade"] == blade].groupby(col_pieza).agg(
        ws_directo=("Wilson Score", "mean"),
        n_directos=("Partidas", "sum")
    ).reset_index()

    # Arquetipo de la Blade para buscar proxies
    tv, td = _arquetipo_blade(df, blade)

    if tv is not None and td is not None:
        proxies_df = df[
            (df["Blade"] != blade) &
            (df["tipo_victoria"] == tv) &
            (df["tipo_derrota"] == td) &
            (df["tipo_victoria"] != -1)
        ]
    else:
        proxies_df = df[df["Blade"] != blade]

    proxies = proxies_df.groupby(col_pieza).agg(
        ws_proxy=("Wilson Score", "mean"),
        n_proxies=("Partidas", "sum")
    ).reset_index()

    # Combinar
    merged = directos.merge(proxies, on=col_pieza, how="outer")

    scores = {}
    for _, row in merged.iterrows():
        pieza = row[col_pieza]
        tiene_directo = (
            pd.notna(row.get("ws_directo")) and
            row.get("n_directos", 0) >= MIN_PARTIDAS_DIRECTAS
        )
        tiene_proxy = pd.notna(row.get("ws_proxy"))

        if tiene_directo and tiene_proxy:
            # Blend: más peso a datos directos
            scores[pieza] = row["ws_directo"] * (1 - peso_proxy) + row["ws_proxy"] * peso_proxy
        elif tiene_directo:
            scores[pieza] = row["ws_directo"]
        elif tiene_proxy:
            scores[pieza] = row["ws_proxy"] * peso_proxy  # penalizado por ser solo proxy
        # si no hay nada, no se incluye

    return scores


# ── Función principal ─────────────────────────────────────────────────────────

COLS_SALIDA = [
    "Blade", "Ratchet", "Bit",
    "Wilson Score Predicho", "Partidas",
    "Arquetipo victoria", "Arquetipo derrota", "Tipo"
]


def recomendar_builds(df, blade=None, ratchet=None, bit=None, top_n=20):
    if df.empty or "Wilson Score" not in df.columns:
        return pd.DataFrame()

    df = _asignar_arquetipos(df)

    # ── Sin Blade fija: top Wilson Score global ───────────────────────────────
    if blade is None:
        df_fil = df.copy()
        if ratchet: df_fil = df_fil[df_fil["Ratchet"] == ratchet]
        if bit:     df_fil = df_fil[df_fil["Bit"] == bit]
        df_fil = df_fil.rename(columns={"Wilson Score": "Wilson Score Predicho"})
        df_fil["Tipo"] = "✅ Real"
        return (
            df_fil[COLS_SALIDA]
            .sort_values("Wilson Score Predicho", ascending=False)
            .head(top_n)
            .reset_index(drop=True)
        )

    # ── Con Blade fija ────────────────────────────────────────────────────────

    tv_blade, td_blade = _arquetipo_blade(df, blade)

    # Combos reales de esa Blade
    df_blade = df[df["Blade"] == blade].copy()
    if ratchet: df_blade = df_blade[df_blade["Ratchet"] == ratchet]
    if bit:     df_blade = df_blade[df_blade["Bit"] == bit]

    reales = df_blade.rename(columns={"Wilson Score": "Wilson Score Predicho"}).copy()
    reales["Tipo"] = "✅ Real"
    reales = reales[COLS_SALIDA].sort_values("Wilson Score Predicho", ascending=False)

    # ── Scores de sinergia par a par ──────────────────────────────────────────
    ratchet_scores = _score_pieza_con_blade(df, blade, "Ratchet")
    bit_scores     = _score_pieza_con_blade(df, blade, "Bit")

    # Filtrar por selección opcional
    if ratchet: ratchet_scores = {ratchet: ratchet_scores.get(ratchet, 0)}
    if bit:     bit_scores     = {bit: bit_scores.get(bit, 0)}

    # Top 10 Ratchets y Bits por sinergia con esta Blade
    top_ratchets = sorted(ratchet_scores, key=ratchet_scores.get, reverse=True)[:10]
    top_bits     = sorted(bit_scores,     key=bit_scores.get,     reverse=True)[:10]

    # Combos candidatos no vistos
    existentes = set(zip(df_blade["Ratchet"], df_blade["Bit"]))
    candidatos = [
        (blade, r, b)
        for r, b in product(top_ratchets, top_bits)
        if (r, b) not in existentes
    ]

    if not candidatos:
        return reales.head(top_n).reset_index(drop=True)

    # ── Score estimado para candidatos (media sinergia Ratchet + Bit) ─────────
    df_cand = pd.DataFrame(candidatos, columns=["Blade", "Ratchet", "Bit"])
    df_cand["Wilson Score Predicho"] = df_cand.apply(
        lambda r: round(
            (ratchet_scores.get(r["Ratchet"], 0) + bit_scores.get(r["Bit"], 0)) / 2, 4
        ),
        axis=1
    )
    df_cand["Partidas"] = 0
    df_cand["Tipo"] = "🔮 Predicho"
    df_cand["Arquetipo victoria"] = MAP_VICTORIA.get(tv_blade, "⚪ Datos insuficientes")
    df_cand["Arquetipo derrota"]  = MAP_DERROTA.get(td_blade,  "⚪ Datos insuficientes")

    # ── Intentar refinar predichos con el modelo si existe ───────────────────
    try:
        p        = cargar_modelo()
        model    = p["model"]
        encoders = p["encoders"]
        ws_mean  = p["ws_mean"]

        valid = pd.Series([True] * len(df_cand), index=df_cand.index)
        for col in ["Blade", "Ratchet", "Bit"]:
            valid &= df_cand[col].isin(set(encoders[col].classes_))
        df_enc = df_cand[valid].copy()

        if not df_enc.empty:
            for col in ["Blade", "Ratchet", "Bit"]:
                df_enc[col + "_enc"] = encoders[col].transform(df_enc[col].astype(str))

            df_enc["Partidas_log"]  = np.log1p(10)
            df_enc["Blade_score"]   = df_enc["Blade"].map(p["blade_dict"]).fillna(ws_mean)
            df_enc["Ratchet_score"] = df_enc["Ratchet"].map(p["ratchet_dict"]).fillna(ws_mean)
            df_enc["Bit_score"]     = df_enc["Bit"].map(p["bit_dict"]).fillna(ws_mean)

            X = df_enc[p["feature_cols"]].values.astype(float)
            ml_preds = np.round(model.predict(X), 4)

            # Blend: 60% sinergia par a par + 40% modelo ML
            df_cand.loc[df_enc.index, "Wilson Score Predicho"] = np.round(
                df_cand.loc[df_enc.index, "Wilson Score Predicho"] * 0.6 + ml_preds * 0.4, 4
            )
    except FileNotFoundError:
        pass

    # ── Combinar: reales primero, predichos de relleno ────────────────────────
    necesarios = max(0, top_n - len(reales))
    relleno = (
        df_cand[COLS_SALIDA]
        .sort_values("Wilson Score Predicho", ascending=False)
        .head(necesarios)
    )

    return pd.concat([reales, relleno], ignore_index=True).head(top_n)