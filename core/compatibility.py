"""
core/compatibility.py
---------------------
Restricciones de compatibilidad entre piezas.
Añadir aquí nuevas restricciones si aparecen en el futuro.
"""

# Dict: Blade -> función que devuelve True si el Ratchet es compatible
BLADE_RATCHET_COMPAT = {
    "Clock Mirage": lambda ratchet: ratchet.endswith("5"),
}


def ratchets_validos(blade, ratchets):
    """Filtra la lista de ratchets compatibles con una Blade dada."""
    if blade in BLADE_RATCHET_COMPAT:
        return [r for r in ratchets if BLADE_RATCHET_COMPAT[blade](r)]
    return ratchets


def filtrar_df(df):
    """
    Elimina del DataFrame las filas con combinaciones incompatibles.
    Se llama una sola vez en el loader.
    """
    mask = df.apply(
        lambda row: row["Ratchet"] not in BLADE_RATCHET_COMPAT.get(
            row["Blade"], {}
        ) or BLADE_RATCHET_COMPAT[row["Blade"]](row["Ratchet"]),
        axis=1
    )
    return df[mask]