"""
core/compatibility.py
---------------------
Restricciones de compatibilidad entre piezas.
Añadir aquí nuevas restricciones si aparecen en el futuro.
"""

import re

# Un Ratchet válido es:
#   - Formato numérico N-N (p.ej. "1-60", "3-80", "9-70"), o
#   - Uno de los ratchets especiales con nombre: "Turbo" u "Operate".
# "Zillion" NO es un ratchet: es una Assist Blade (parte del Blade) que se
# cuela en el scraping y se descarta.
RATCHET_REGEX = re.compile(r"^\d+-\d+$")
RATCHETS_ESPECIALES = {"Turbo", "Operate"}
ASSIST_BLADES = {"Zillion"}


def es_ratchet_valido(ratchet):
    """True si el Ratchet es N-N o un especial reconocido (Turbo/Operate)."""
    if ratchet is None:
        return False
    s = str(ratchet).strip()
    if s in ASSIST_BLADES:
        return False
    return bool(RATCHET_REGEX.match(s)) or s in RATCHETS_ESPECIALES


# Dict: Blade -> función que devuelve True si el Ratchet es compatible
BLADE_RATCHET_COMPAT = {
    "Clock Mirage": lambda ratchet: ratchet.endswith("5"),
}


def ratchets_validos(blade, ratchets):
    """Filtra la lista de ratchets compatibles con una Blade dada."""
    ratchets = [r for r in ratchets if es_ratchet_valido(r)]
    if blade in BLADE_RATCHET_COMPAT:
        return [r for r in ratchets if BLADE_RATCHET_COMPAT[blade](r)]
    return ratchets


def filtrar_df(df):
    """
    Elimina del DataFrame las filas con combinaciones incompatibles o con
    Ratchets que no cumplen el formato N-N (Assist Blades coladas en
    datos históricos).
    Se llama una sola vez en el loader.
    """
    def es_compatible(row):
        ratchet = row["Ratchet"]
        if not es_ratchet_valido(ratchet):
            return False
        blade = row["Blade"]
        if blade in BLADE_RATCHET_COMPAT:
            return BLADE_RATCHET_COMPAT[blade](ratchet)
        return True

    return df[df.apply(es_compatible, axis=1)]