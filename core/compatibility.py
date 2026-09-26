"""
core/compatibility.py
---------------------
Restricciones de compatibilidad entre piezas.
Añadir aquí nuevas restricciones si aparecen en el futuro.

Un combo es (Blade, Assist, Ratchet, Bit):
  - UX / BX: el Blade es una sola pieza y el Assist va vacío (SIN_ASSIST).
  - CX: el Blade es lock chip + main blade (+ over blade en los CX Expanded)
    y el Assist es una pieza aparte, intercambiable entre CX.
"""

import re
from collections import namedtuple

import pandas as pd

# Un Ratchet válido es:
#   - Formato numérico N-N (p.ej. "1-60", "3-80", "9-70"), o
#   - Uno de los ratchets especiales con nombre: "Turbo" u "Operate".
# "Zillion" NO es un ratchet: es una Assist Blade que se cuela en el
# scraping y se descarta.
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

# ── CX y Assist ───────────────────────────────────────────────────────────────
# El scraper separa el Assist del nombre del CX: con 3 o más palabras
# (lock chip + main blade [+ over blade] + assist), la última es el Assist.
#   "Pegasus Blast Wheel"        -> Blade "Pegasus Blast",       Assist "Wheel"
#   "Brachio Whip Outer Wheel"   -> Blade "Brachio Whip Outer",  Assist "Wheel"
# Un Blade es CX si la mayoría de sus partidas llevan Assist. Igual que con
# los UX Expanded, se deduce de los datos y el umbral protege de errores de
# registro en los dos sentidos:
#   - CX registrado sin Assist ("Wizard Arc" suelto, 5 de 36 partidas).
#   - UX/BX registrado con un Assist ("Dran Sword Free", 3 de 180 partidas).
# El umbral es más bajo que en UX Expanded porque en los CX es habitual
# olvidarse del Assist al registrar ("Sol Eclipse": 13 con Assist y 4 sin él).
SIN_ASSIST = ""
PALABRAS_MIN_CX = 3
CX_SHARE_MIN = 0.5
CX_MIN_PARTIDAS = 3

KEYS = ["Blade", "Assist", "Ratchet", "Bit"]

# Blades UX Expanded y CX deducidos de un DataFrame (ver reglas_desde).
Reglas = namedtuple("Reglas", ["ux", "cx"])


def separar_blade_assist(nombre):
    """(blade, assist) a partir del nombre completo que da la SBBL."""
    palabras = str(nombre).split()
    if len(palabras) >= PALABRAS_MIN_CX:
        return " ".join(palabras[:-1]), palabras[-1]
    return str(nombre).strip(), SIN_ASSIST


def nombre_blade(blade, assist=SIN_ASSIST):
    """Nombre completo para mostrar: "Pegasus Blast" + "Wheel" -> "Pegasus Blast Wheel"."""
    assist = "" if assist is None or assist != assist else str(assist)
    return f"{blade} {assist}" if assist else str(blade)


def nombre_combo(blade, assist, ratchet, bit, sep=" "):
    return sep.join([nombre_blade(blade, assist), str(ratchet), str(bit)])


def asegurar_assist(df):
    """
    Garantiza la columna Assist (vacía = sin Assist, nunca NaN).
    Los CSV antiguos sin la columna se separan aquí con la misma regla que
    el scraper, así el histórico sin migrar sigue funcionando.
    """
    if df is None:
        return df
    df = df.copy()
    if "Assist" not in df.columns:
        if "Blade" in df.columns and not df.empty:
            partes = [separar_blade_assist(b) for b in df["Blade"]]
            df["Blade"] = [p[0] for p in partes]
            assist = [p[1] for p in partes]
        else:
            assist = SIN_ASSIST
        pos = df.columns.get_loc("Blade") + 1 if "Blade" in df.columns else 0
        df.insert(pos, "Assist", assist)
    df["Assist"] = df["Assist"].fillna(SIN_ASSIST).astype(str)
    return df


# ── Ratchets ──────────────────────────────────────────────────────────────────

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


def assists_validos(blade, assists, blades_cx):
    """
    Assists que puede llevar un Blade:
      - CX: cualquier Assist (son intercambiables entre CX).
      - UX / BX: ninguno -> [SIN_ASSIST].
    """
    if blade in blades_cx:
        return sorted({a for a in assists if a})
    return [SIN_ASSIST]


# ── Legalidad de combos ───────────────────────────────────────────────────────

def combo_valido(blade, assist, ratchet, bit, reglas):
    """Reglas de legalidad de un combo (Blade, Assist, Ratchet, Bit)."""
    if not es_ratchet_valido(ratchet):
        return False
    # UX Expanded: el Ratchet va fusionado al Blade -> relación 1 a 1
    if (blade in reglas.ux) != (ratchet == UX_EXPANDED):
        return False
    # CX: lleva Assist si y solo si el Blade es CX
    if (blade in reglas.cx) != bool(assist):
        return False
    if blade in BLADE_RATCHET_COMPAT:
        return BLADE_RATCHET_COMPAT[blade](ratchet)
    return True


def filtrar_combos_validos(df_cand, reglas):
    """Deja solo los combos legales de una tabla con columnas Blade/Assist/Ratchet/Bit."""
    if df_cand.empty:
        return df_cand
    mask = [
        combo_valido(b, a, r, t, reglas)
        for b, a, r, t in zip(df_cand["Blade"], df_cand["Assist"],
                              df_cand["Ratchet"], df_cand["Bit"])
    ]
    return df_cand[mask]


def filtrar_df(df):
    """
    Elimina del DataFrame las filas con combinaciones incompatibles o con
    Ratchets que no cumplen el formato N-N (Assist Blades coladas en
    datos históricos), los errores de registro de UX Expanded (un Blade
    normal registrado con "UX Expanded" o un UX Expanded con Ratchet normal)
    y los de CX (un CX sin Assist o un UX/BX con Assist).
    Se llama una sola vez en el loader.
    """
    df = asegurar_assist(df)
    return filtrar_combos_validos(df, reglas_desde(df))


def generar_candidatos(blades, assists, ratchets, bits, reglas):
    """
    Todos los combos LEGALES que se pueden formar con las piezas dadas.
    Se construyen ya legales (sin generar primero el producto completo):
    cada Blade solo con sus Assists y Ratchets válidos.
    `assists` son los Assists permitidos (vacíos o no); un UX/BX solo sale
    si SIN_ASSIST está entre ellos.
    """
    assists = list(assists)
    permite_sin = SIN_ASSIST in assists
    filas = []
    for b in blades:
        if b in reglas.cx:
            a_ok = [a for a in assists if a]
        else:
            a_ok = [SIN_ASSIST] if permite_sin else []
        if not a_ok:
            continue
        r_ok = ratchets_validos(b, ratchets, reglas.ux)
        for a in a_ok:
            for r in r_ok:
                for t in bits:
                    filas.append((b, a, r, t))
    return pd.DataFrame(filas, columns=KEYS)


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


def blades_cx(df):
    """
    Blades CX deducidos de los datos: al menos CX_MIN_PARTIDAS con Assist y
    al menos CX_SHARE_MIN de sus partidas con Assist.
    """
    if "Assist" not in df.columns:
        return set()
    con = df[df["Assist"].fillna(SIN_ASSIST) != SIN_ASSIST].groupby("Blade")["Partidas"].sum()
    if con.empty:
        return set()
    total = df[df["Blade"].isin(con.index)].groupby("Blade")["Partidas"].sum()
    share = con / total.reindex(con.index)
    ok = (con >= CX_MIN_PARTIDAS) & (share >= CX_SHARE_MIN)
    return set(con[ok].index)


def reglas_desde(df):
    """Reglas (Blades UX Expanded y CX) deducidas de un DataFrame de combos."""
    return Reglas(ux=blades_con_ux_expanded(df), cx=blades_cx(df))


def ratchet_repetido(ratchet, usados):
    """
    True si el Ratchet ya está usado en el deck. "UX Expanded" no cuenta:
    cada UX Expanded lleva su propio Ratchet fusionado al Blade.
    """
    return ratchet != UX_EXPANDED and ratchet in usados


# ── Piezas físicas de un Blade ────────────────────────────────────────────────
# En un deck no se puede repetir NINGUNA pieza física.
#   - UX / BX (1-2 palabras, p.ej. "Wizard Rod"): el Blade es una sola pieza.
#   - CX: cada palabra del Blade es una pieza (lock chip + main blade, más el
#     over blade en los CX Expanded) y el Assist es otra. Así,
#     "Pegasus Blast" + Heavy choca con "Pegasus Blast" + Jaggy (Pegasus,
#     Blast) y con "Phoenix Flare" + Heavy (Heavy).
# Un UX nunca choca con un CX aunque compartan palabra ("Dran Sword" vs
# "Dran Brave"): son piezas físicas distintas.

def piezas_blade(blade, assist=SIN_ASSIST, blades_cx_=None):
    """
    Conjunto de piezas físicas de un Blade (+ su Assist).
    Un Blade es CX si lleva Assist o si está en `blades_cx_` (útil en los
    selectores, cuando aún no se ha elegido el Assist).
    """
    assist = "" if assist is None or assist != assist else str(assist)
    es_cx = bool(assist) or (blades_cx_ is not None and blade in blades_cx_)
    if es_cx:
        piezas = {f"cx:{p}" for p in str(blade).split()}
        if assist:
            piezas.add(f"assist:{assist}")
        return piezas
    return {f"blade:{blade}"}


def blade_repetido(blade, assist, usados, blades_cx_=None):
    """
    True si (blade, assist) comparte alguna pieza física con algún
    (blade, assist) de `usados`.
    """
    piezas = piezas_blade(blade, assist, blades_cx_)
    return any(
        piezas & piezas_blade(b, a, blades_cx_)
        for b, a in usados if b
    )


def assist_repetido(assist, usados):
    """True si el Assist ya está usado en el deck (vacío nunca cuenta)."""
    return bool(assist) and assist in usados
