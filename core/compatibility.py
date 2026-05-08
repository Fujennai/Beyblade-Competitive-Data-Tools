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
    def es_compatible(row):
        blade = row["Blade"]
        if blade in BLADE_RATCHET_COMPAT:
            return BLADE_RATCHET_COMPAT[blade](row["Ratchet"])
        return True

    return df[df.apply(es_compatible, axis=1)]