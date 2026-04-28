import pandas as pd
import numpy as np

from core.metrics import wilson


# ----------------------------
# Utils
# ----------------------------

def extraer_wheel(blade):
    return blade.split(" ")[-1] if isinstance(blade, str) else None


# ----------------------------
# Filtrar piezas disponibles
# ----------------------------

def filtrar_disponibles(df, usados):

    df = df.copy()

    usados_blade = usados["Blade"]
    usados_ratchet = usados["Ratchet"]
    usados_bit = usados["Bit"]

    usados_wheel = [extraer_wheel(b) for b in usados_blade if b]

    # filtrar solo si hay valores
    if usados_blade:
        df = df[~df["Blade"].isin(usados_blade)]

    if usados_ratchet:
        df = df[~df["Ratchet"].isin(usados_ratchet)]

    if usados_bit:
        df = df[~df["Bit"].isin(usados_bit)]

    # evitar repetir wheel
    df = df[~df["Blade"].apply(lambda b: extraer_wheel(b) in usados_wheel)]

    return df


# ----------------------------
# Medias por pieza (para sinergia)
# ----------------------------

def calcular_medias(df):

    blade_mean = df.groupby("Blade")["Win %"].mean().to_dict()
    ratchet_mean = df.groupby("Ratchet")["Win %"].mean().to_dict()
    bit_mean = df.groupby("Bit")["Win %"].mean().to_dict()

    return blade_mean, ratchet_mean, bit_mean


# ----------------------------
# Sinergia
# ----------------------------

def calcular_sinergia(row, blade_mean, ratchet_mean, bit_mean):

    base = (
        blade_mean.get(row["Blade"], 0) +
        ratchet_mean.get(row["Ratchet"], 0) +
        bit_mean.get(row["Bit"], 0)
    ) / 3

    return row["Win %"] - base


# ----------------------------
# Score robusto
# ----------------------------

def score_combo(df_disp, df_full):

    df = df_disp.copy()

    # ------------------------
    # Wilson Score
    # ------------------------

    df["wilson"] = df.apply(
        lambda row: wilson(row["Wins"], row["Partidas"]),
        axis=1
    )

    # ------------------------
    # Sinergia (usar dataset completo)
    # ------------------------

    blade_mean, ratchet_mean, bit_mean = calcular_medias(df_full)

    df["sinergia"] = df.apply(
        lambda row: calcular_sinergia(row, blade_mean, ratchet_mean, bit_mean),
        axis=1
    )

    # ------------------------
    # Score final
    # ------------------------

    df["score"] = (
        df["wilson"] * 100 * np.log1p(df["Partidas"]) +
        df["sinergia"] * 50
    )

    return df.sort_values("score", ascending=False)


# ----------------------------
# Recomendar combos
# ----------------------------

def recomendar_combo(df, usados, top_n=10):

    # filtro base (evitar basura)
    df = df[df["Partidas"] >= 5]

    df_disp = filtrar_disponibles(df, usados)

    if df_disp.empty:
        return pd.DataFrame()

    df_rank = score_combo(df_disp, df)

    return df_rank.head(top_n)