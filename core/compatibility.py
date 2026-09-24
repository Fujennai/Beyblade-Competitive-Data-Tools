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
# Ratchet ficticio de la SBBL para los UX Expanded (Blade + Ratchet fusionados).
# Solo es compatible con los Blades que tienen versión UX Expanded.
UX_EXPANDED = "UX Expanded"
RATCHETS_ESPECIALES.add(UX_EXPANDED)
ASSIST_BLADES = {"Zillion"}

# Un Blade se considera UX Expanded si la gran mayoría de sus partidas son con
# el Ratchet ficticio "UX Expanded". Se deduce de los datos (sin listas
# manuales) y el umbral de proporción protege frente a errores de registro:
# una partida mal registrada en un Blade normal no lo convierte en UX Expanded.
UX_SHARE_MIN = 0.8
UX_MIN_PARTIDAS = 3


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


def ratchets_validos(blade, ratchets, blades_ux_expanded=None):
    """
    Filtra la lista de ratchets compatibles con una Blade dada.
    Si se pasa `blades_ux_expanded`:
      - un Blade UX Expanded solo admite "UX Expanded" (solo se cambia el Bit),
      - el resto de Blades nunca admite "UX Expanded".
    """
    ratchets = [r for r in ratchets if es_ratchet_valido(r)]
    if blades_ux_expanded is not None:
        if blade in blades_ux_expanded:
            return [r for r in ratchets if r == UX_EXPANDED]
        ratchets = [r for r in ratchets if r != UX_EXPANDED]
    if blade in BLADE_RATCHET_COMPAT:
        return [r for r in ratchets if BLADE_RATCHET_COMPAT[blade](r)]
    return ratchets


def combo_valido(blade, ratchet, bit, blades_ux_expanded):
    """Reglas de legalidad de un combo (Blade, Ratchet, Bit)."""
    if not es_ratchet_valido(ratchet):
        return False
    # UX Expanded: el Ratchet va fusionado al Blade -> relación 1 a 1
    if (blade in blades_ux_expanded) != (ratchet == UX_EXPANDED):
        return False
    if blade in BLADE_RATCHET_COMPAT:
        return BLADE_RATCHET_COMPAT[blade](ratchet)
    return True


def filtrar_combos_validos(df_cand, blades_ux_expanded):
    """Deja solo los combos legales de una tabla con columnas Blade/Ratchet/Bit."""
    if df_cand.empty:
        return df_cand
    mask = [
        combo_valido(b, r, t, blades_ux_expanded)
        for b, r, t in zip(df_cand["Blade"], df_cand["Ratchet"], df_cand["Bit"])
    ]
    return df_cand[mask]


def filtrar_df(df):
    """
    Elimina del DataFrame las filas con combinaciones incompatibles o con
    Ratchets que no cumplen el formato N-N (Assist Blades coladas en
    datos históricos), y los errores de registro de UX Expanded (un Blade
    normal registrado con "UX Expanded" o un UX Expanded con Ratchet normal).
    Se llama una sola vez en el loader.
    """
    return filtrar_combos_validos(df, blades_con_ux_expanded(df))


def blades_con_ux_expanded(df):
    """
    Blades UX Expanded deducidos de los datos: al menos UX_MIN_PARTIDAS con
    "UX Expanded" y al menos UX_SHARE_MIN de sus partidas con él.
    """
    ux = df[df["Ratchet"] == UX_EXPANDED].groupby("Blade")["Partidas"].sum()
    if ux.empty:
        return set()
    total = df[df["Blade"].isin(ux.index)].groupby("Blade")["Partidas"].sum()
    share = ux / total.reindex(ux.index)
    ok = (ux >= UX_MIN_PARTIDAS) & (share >= UX_SHARE_MIN)
    return set(ux[ok].index)


def ratchet_repetido(ratchet, usados):
    """
    True si el Ratchet ya está usado en el deck. "UX Expanded" no cuenta:
    cada UX Expanded lleva su propio Ratchet fusionado al Blade.
    """
    return ratchet != UX_EXPANDED and ratchet in usados


# ── Piezas físicas de un Blade ────────────────────────────────────────────────
# En un deck no se puede repetir NINGUNA pieza física.
#   - UX / BX (1-2 palabras, p.ej. "Wizard Rod"): el Blade es una sola pieza.
#   - CX (3 palabras: lock chip + main blade + assist blade, p.ej.
#     "Pegasus Blast Wheel") y CX Expanded (4 palabras: + over blade):
#     cada palabra es una pieza distinta. Así, "Pegasus Blast Heavy" choca con
#     "Pegasus Blast Jaggy" (Pegasus, Blast) y con "Phoenix Flare Heavy" (Heavy).
# Un UX nunca choca con un CX aunque compartan palabra ("Dran Sword" vs
# "Dran Brave Slash"): son piezas físicas distintas.

def piezas_blade(blade):
    """Conjunto de piezas físicas que componen un Blade."""
    palabras = str(blade).split()
    if len(palabras) >= 3:
        return {f"cx:{p}" for p in palabras}
    return {f"blade:{blade}"}


def blade_repetido(blade, usados):
    """True si `blade` comparte alguna pieza física con algún Blade de `usados`."""
    piezas = piezas_blade(blade)
    return any(piezas & piezas_blade(u) for u in usados if u)
