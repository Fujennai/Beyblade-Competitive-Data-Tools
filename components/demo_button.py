"""
components/demo_button.py
-------------------------
Botón de demostración: rellena automáticamente los filtros/inputs de una
página con un ejemplo real del dataset, muestreado con peso proporcional
al número de Partidas.

Combos muy jugados → MUY probables.
Combos raros (pocas partidas) → casi nunca salen.
Combos predichos (sin partidas) → quedan fuera, solo se usan combos reales.
"""

import numpy as np
import streamlit as st


def _df_real(df):
    """Filtra a combos con Partidas > 0 (descarta predichos y filas vacías)."""
    if df is None or df.empty:
        return df
    if "Partidas" not in df.columns:
        return df
    return df[df["Partidas"].fillna(0) > 0].copy()


def combos_aleatorios(df, n=1, seed=None):
    """
    Devuelve hasta N combos reales del dataset, muestreados sin reemplazo,
    ponderados por Partidas. Cada combo se devuelve como dict con todas las
    columnas del DataFrame original.
    """
    df_filt = _df_real(df)
    if df_filt is None or df_filt.empty:
        return []
    pesos = df_filt["Partidas"].astype(float).values
    if pesos.sum() == 0:
        return []
    pesos = pesos / pesos.sum()
    n = min(n, len(df_filt))
    rng = np.random.default_rng(seed)
    indices = rng.choice(len(df_filt), size=n, replace=False, p=pesos)
    return [df_filt.iloc[i].to_dict() for i in indices]


def piezas_aleatorias(df, col, n=1, seed=None):
    """
    Devuelve hasta N piezas distintas de la columna `col` (Blade, Ratchet
    o Bit), muestreadas sin reemplazo, con peso proporcional a la suma de
    Partidas de los combos reales que las usan.
    """
    df_filt = _df_real(df)
    if df_filt is None or df_filt.empty or col not in df_filt.columns:
        return []
    pesos_serie = df_filt.groupby(col)["Partidas"].sum()
    pesos = pesos_serie.values.astype(float)
    if pesos.sum() == 0:
        return []
    pesos = pesos / pesos.sum()
    n = min(n, len(pesos_serie))
    rng = np.random.default_rng(seed)
    indices = rng.choice(len(pesos_serie), size=n, replace=False, p=pesos)
    return list(pesos_serie.index[indices])


def boton_demo(label="🎬 Demostración", key="demo_btn", help_text=None):
    """Renderiza el botón de demostración. Devuelve True si se pulsa."""
    return st.button(
        label,
        key=key,
        help=help_text or (
            "Rellena los filtros automáticamente con un ejemplo real del "
            "dataset (ponderado por número de partidas) para ver la "
            "funcionalidad en acción."
        ),
    )
