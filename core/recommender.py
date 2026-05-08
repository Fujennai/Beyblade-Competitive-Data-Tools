"""
core/recommender.py
-------------------
Recomendador basado en arquetipos:
1. Detecta el arquetipo de la Blade seleccionada
2. Encuentra Ratchets y Bits que funcionan en Blades del mismo arquetipo
3. Devuelve combos reales ordenados por Wilson Score con su arquetipo
4. Rellena con predicciones del modelo cuando hay pocos combos reales
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


# ── Arquetipos (misma lógica que 2_Arquetipos.py) ────────────────────────────

def _categorizar(valor, partidas, winrate):
    if partidas < 10:
        return -1
    if winrate >= 95 and partidas < 25:
        return -1
    if valor < 0.5:
        return 0
    elif valor < 1.5:
        return 1
    elif valor < 2.5:
        return 2
    else:
        return 3


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
    combos_blade = df[
        (df["Blade"] == blade) &
        (df["tipo_victoria"] != -1) &
        (df["tipo_derrota"] != -1)
    ]
    if combos_blade.empty:
        return None, None

    tv = combos_blade["tipo_victoria"].mode()
    td = combos_blade["tipo_derrota"].mode()

    return (
        int(tv.iloc[0]) if not tv.empty else None,
        int(td.iloc[0]) if not td.empty else None,
    )


# ── Función principal ─────────────────────────────────────────────────────────

def recomendar_builds(df, blade=None, ratchet=None, bit=None, top_n=20):
    if df.empty or "Wilson Score" not in df.columns:
        return pd.DataFrame()

    df = _asignar_arquetipos(df)

    COLS_SALIDA = ["Blade", "Ratchet", "Bit", "Wilson Score Predicho",
                   "Partidas", "Arquetipo victoria", "Arquetipo derrota", "Tipo"]

    # ── 1. Sin Blade fija: top Wilson Score global ────────────────────────────
    if blade is None:
        df_fil = df.copy()
        if ratchet:
            df_fil = df_fil[df_fil["Ratchet"] == ratchet]
        if bit:
            df_fil = df_fil[df_fil["Bit"] == bit]

        df_fil = df_fil.rename(columns={"Wilson Score": "Wilson Score Predicho"})
        df_fil["Tipo"] = "✅ Real"

        return (
            df_fil[COLS_SALIDA]
            .sort_values("Wilson Score Predicho", ascending=False)
            .head(top_n)
            .reset_index(drop=True)
        )

    # ── 2. Con Blade fija ─────────────────────────────────────────────────────

    tv_blade, td_blade = _arquetipo_blade(df, blade)

    df_blade = df[df["Blade"] == blade].copy()
    if ratchet:
        df_blade = df_blade[df_blade["Ratchet"] == ratchet]
    if bit:
        df_blade = df_blade[df_blade["Bit"] == bit]

    df_blade = df_blade.sort_values("Wilson Score", ascending=False)
    reales = df_blade.rename(columns={"Wilson Score": "Wilson Score Predicho"}).copy()
    reales["Tipo"] = "✅ Real"
    reales = reales[COLS_SALIDA]

    # ── 3. Piezas del mismo arquetipo (otras Blades) ──────────────────────────
    if tv_blade is not None and td_blade is not None:
        mismo_arq = df[
            (df["Blade"] != blade) &
            (df["tipo_victoria"] == tv_blade) &
            (df["tipo_derrota"] == td_blade) &
            (df["tipo_victoria"] != -1)
        ]
    else:
        mismo_arq = df[df["Blade"] != blade]

    top_ratchets = (
        mismo_arq.groupby("Ratchet")["Wilson Score"].mean()
        .sort_values(ascending=False)
        .head(10).index.tolist()
    )
    top_bits = (
        mismo_arq.groupby("Bit")["Wilson Score"].mean()
        .sort_values(ascending=False)
        .head(10).index.tolist()
    )

    if ratchet:
        top_ratchets = [ratchet]
    if bit:
        top_bits = [bit]

    existentes = set(zip(df_blade["Ratchet"], df_blade["Bit"]))
    candidatos = [
        (blade, r, b)
        for r, b in product(top_ratchets, top_bits)
        if (r, b) not in existentes
    ]

    if not candidatos:
        return reales.head(top_n).reset_index(drop=True)

    # ── 4. Predecir con el modelo ─────────────────────────────────────────────
    try:
        p        = cargar_modelo()
        model    = p["model"]
        encoders = p["encoders"]
        blade_dict   = p["blade_dict"]
        ratchet_dict = p["ratchet_dict"]
        bit_dict     = p["bit_dict"]
        ws_mean      = p["ws_mean"]

        df_cand = pd.DataFrame(candidatos, columns=["Blade", "Ratchet", "Bit"])

        valid = pd.Series([True] * len(df_cand), index=df_cand.index)
        for col in ["Blade", "Ratchet", "Bit"]:
            valid &= df_cand[col].isin(set(encoders[col].classes_))
        df_cand = df_cand[valid].copy()

        if not df_cand.empty:
            for col in ["Blade", "Ratchet", "Bit"]:
                df_cand[col + "_enc"] = encoders[col].transform(df_cand[col].astype(str))

            df_cand["Partidas_log"]  = np.log1p(10)
            df_cand["Blade_score"]   = df_cand["Blade"].map(blade_dict).fillna(ws_mean)
            df_cand["Ratchet_score"] = df_cand["Ratchet"].map(ratchet_dict).fillna(ws_mean)
            df_cand["Bit_score"]     = df_cand["Bit"].map(bit_dict).fillna(ws_mean)

            X = df_cand[p["feature_cols"]].values.astype(float)
            df_cand["Wilson Score Predicho"] = np.round(model.predict(X), 4)
            df_cand["Partidas"] = 0
            df_cand["Tipo"] = "🔮 Predicho"

            # Arquetipo esperado para los predichos (el de la Blade)
            df_cand["Arquetipo victoria"] = MAP_VICTORIA.get(tv_blade, "⚪ Datos insuficientes")
            df_cand["Arquetipo derrota"]  = MAP_DERROTA.get(td_blade, "⚪ Datos insuficientes")

            predichos = df_cand[COLS_SALIDA]
        else:
            predichos = pd.DataFrame()

    except FileNotFoundError:
        predichos = pd.DataFrame()

    # ── 5. Combinar: reales primero, predichos de relleno ────────────────────
    necesarios = max(0, top_n - len(reales))
    relleno = predichos.sort_values("Wilson Score Predicho", ascending=False).head(necesarios)

    return pd.concat([reales, relleno], ignore_index=True).head(top_n)