"""
core/deck_format.py
-------------------
Importar / exportar decks en texto, al estilo de Pokémon Showdown.

Formato de exportación (un bloque por bey, separados por una línea en blanco):

    Wizard Rod
    Ratchet: 1-60
    Bit: Ball

    Pegasus Blast @ Wheel
    Ratchet: 3-60
    Bit: Hexa

  - Cabecera: el Blade y, en los CX, "@ Assist" (como el objeto en Showdown).
  - Líneas "Clave: valor" para Assist, Ratchet y Bit. Todas son opcionales
    (un bey puede llevar solo el Blade, como un Pokémon sin movimientos).

Al importar se acepta además:
  - "Assist: Wheel" en vez de "@ Wheel", o el nombre completo de la SBBL en
    la cabecera ("Pegasus Blast Wheel").
  - Combos en una sola línea, con o sin "/": "Wizard Rod 1-60 Ball",
    "Pegasus Blast Wheel / 3-60 / Hexa". Varias líneas seguidas así son
    varios beys (no hace falta línea en blanco entre ellos).
  - Bloques sin cabecera (solo "Ratchet: 3-60"), útiles en el Deckbuilder.
  - Mayúsculas/minúsculas y espacios indiferentes, comentarios con "#" y
    líneas "=== título ===" (se ignoran).

No depende de Streamlit.
"""

import re
from collections import namedtuple

from core.compatibility import (
    SIN_ASSIST, ratchets_validos, blade_repetido, ratchet_repetido,
    assist_repetido,
)

PIEZAS = ["Blade", "Assist", "Ratchet", "Bit"]
_CLAVE = re.compile(r"^\s*(blade|assist|ratchet|bit)\s*:\s*(.*)$", re.IGNORECASE)

# Nombres válidos de cada pieza (minúsculas normalizadas -> nombre canónico)
# y reglas UX Expanded / CX deducidas de los datos.
Catalogo = namedtuple("Catalogo", ["blades", "assists", "ratchets", "bits", "reglas"])


def _norm(s):
    return " ".join(str(s).split()).lower()


def catalogo_desde(df, reglas):
    def idx(col):
        return {_norm(v): v for v in df[col].dropna().unique() if str(v).strip()}
    return Catalogo(idx("Blade"), idx("Assist"), idx("Ratchet"), idx("Bit"), reglas)


# ── Exportar ──────────────────────────────────────────────────────────────────

def _valor(bey, pieza):
    v = bey.get(pieza)
    if v is None or v != v or str(v).strip() in ("", "—"):
        return ""
    return str(v).strip()


def exportar(beys):
    """Texto del deck. `beys`: lista de dicts con Blade/Assist/Ratchet/Bit (opcionales)."""
    bloques = []
    for bey in beys:
        blade, assist = _valor(bey, "Blade"), _valor(bey, "Assist")
        ratchet, bit = _valor(bey, "Ratchet"), _valor(bey, "Bit")
        lineas = []
        if blade:
            lineas.append(f"{blade} @ {assist}" if assist else blade)
        elif assist:
            lineas.append(f"Assist: {assist}")
        if ratchet:
            lineas.append(f"Ratchet: {ratchet}")
        if bit:
            lineas.append(f"Bit: {bit}")
        if lineas:
            bloques.append("\n".join(lineas))
    return "\n\n".join(bloques)


# ── Importar ──────────────────────────────────────────────────────────────────

def _prefijo(tokens, i, indice, max_len):
    """Coincidencia más larga de tokens[i:] en `indice`. Devuelve (nombre, nuevo_i)."""
    for n in range(min(max_len, len(tokens) - i), 0, -1):
        cand = " ".join(tokens[i:i + n]).lower()
        if cand in indice:
            return indice[cand], i + n
    return None, i


def _parsear_cabecera(texto, cat, avisos, n_bey):
    """Cabecera o combo en una línea -> dict parcial."""
    bey = {}
    izq, _, der = texto.partition("@")
    tokens = izq.replace("/", " ").split()
    resto = der.replace("/", " ").split()

    i = 0
    blade, i = _prefijo(tokens, i, cat.blades, 4)
    if blade is None:
        avisos.append(f"Bey {n_bey}: Blade desconocido en «{texto.strip()}».")
        return bey
    bey["Blade"] = blade
    es_cx = blade in cat.reglas.cx

    # Lo que va tras "@" empieza por el Assist; sin "@", el Assist va pegado al Blade (nombre SBBL)
    tokens = tokens[i:] + resto
    i = 0
    if tokens and (es_cx or der):
        assist, j = _prefijo(tokens, i, cat.assists, 1)
        if assist is not None:
            bey["Assist"], i = assist, j
        elif der:
            avisos.append(f"Bey {n_bey}: Assist desconocido «{der.strip()}».")
            return bey

    if i < len(tokens):
        ratchet, j = _prefijo(tokens, i, cat.ratchets, 2)
        if ratchet is not None:
            bey["Ratchet"], i = ratchet, j
    if i < len(tokens):
        bit, j = _prefijo(tokens, i, cat.bits, 3)
        if bit is not None:
            bey["Bit"], i = bit, j
    if i < len(tokens):
        avisos.append(f"Bey {n_bey}: no se reconoce «{' '.join(tokens[i:])}».")
    return bey


def _bloques(texto):
    """Agrupa las líneas en beys: [(cabecera o None, [(clave, valor), ...]), ...]."""
    beys, actual = [], None
    for linea in texto.splitlines():
        linea = linea.split("#", 1)[0].strip()
        if not linea or (linea.startswith("===") and linea.endswith("===")):
            if linea == "":
                actual = None
            continue
        m = _CLAVE.match(linea)
        if m:
            if actual is None:
                actual = [None, []]
                beys.append(actual)
            actual[1].append((m.group(1).capitalize(), m.group(2).strip()))
        else:
            # Cabecera: abre un bey nuevo salvo que el bloque aún no tenga una
            if actual is None or actual[0] is not None or actual[1]:
                actual = [linea, []]
                beys.append(actual)
            else:
                actual[0] = linea
    return beys


def importar(texto, cat, n_max=3):
    """
    Lee un deck en texto. Devuelve (beys, avisos):
      - beys: lista de dicts parciales con Blade/Assist/Ratchet/Bit.
      - avisos: textos para mostrar. Las piezas desconocidas, ilegales o
        repetidas se descartan (el resto del bey se conserva).
    """
    indices = {"Blade": cat.blades, "Assist": cat.assists,
               "Ratchet": cat.ratchets, "Bit": cat.bits}
    avisos, beys = [], []

    for n_bey, (cabecera, attrs) in enumerate(_bloques(texto), start=1):
        bey = _parsear_cabecera(cabecera, cat, avisos, n_bey) if cabecera else {}
        for clave, valor in attrs:
            canon = indices[clave].get(_norm(valor))
            if canon is None:
                avisos.append(f"Bey {n_bey}: {clave} desconocido «{valor}».")
            else:
                bey[clave] = canon
        if bey:
            beys.append(_validar(bey, cat, avisos, n_bey))

    if len(beys) > n_max:
        avisos.append(f"Hay {len(beys)} beys; solo se importan los {n_max} primeros.")
        beys = beys[:n_max]

    _quitar_repetidas(beys, cat, avisos)
    return beys, avisos


def _validar(bey, cat, avisos, n_bey):
    """Descarta las piezas incompatibles con el Blade."""
    blade = bey.get("Blade")
    if not blade:
        return bey
    if bey.get("Assist") and blade not in cat.reglas.cx:
        avisos.append(f"Bey {n_bey}: {blade} no es CX, se quita el Assist {bey['Assist']}.")
        bey.pop("Assist")
    r = bey.get("Ratchet")
    if r and not ratchets_validos(blade, [r], cat.reglas.ux):
        avisos.append(f"Bey {n_bey}: el Ratchet {r} no es compatible con {blade}, se quita.")
        bey.pop("Ratchet")
    return bey


def _quitar_repetidas(beys, cat, avisos):
    """En un deck no se repite ninguna pieza física: se queda la primera aparición."""
    blades, assists, ratchets, bits = [], [], [], []
    for n_bey, bey in enumerate(beys, start=1):
        b, a = bey.get("Blade"), bey.get("Assist", SIN_ASSIST)
        if b and blade_repetido(b, a, blades, cat.reglas.cx):
            avisos.append(f"Bey {n_bey}: {b} repite pieza con otro bey, se quita.")
            bey.pop("Blade")
            bey.pop("Assist", None)
        elif a and assist_repetido(a, assists):
            avisos.append(f"Bey {n_bey}: Assist {a} repetido, se quita.")
            bey.pop("Assist")
        r, t = bey.get("Ratchet"), bey.get("Bit")
        if r and ratchet_repetido(r, ratchets):
            avisos.append(f"Bey {n_bey}: Ratchet {r} repetido, se quita.")
            bey.pop("Ratchet")
        if t and t in bits:
            avisos.append(f"Bey {n_bey}: Bit {t} repetido, se quita.")
            bey.pop("Bit")
        if bey.get("Blade"):
            blades.append((bey["Blade"], bey.get("Assist", SIN_ASSIST)))
        if bey.get("Assist"):
            assists.append(bey["Assist"])
        if bey.get("Ratchet"):
            ratchets.append(bey["Ratchet"])
        if bey.get("Bit"):
            bits.append(bey["Bit"])
