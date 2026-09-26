"""
components/deck_io.py
---------------------
Bloque "Importar / exportar" de un deck en formato texto tipo Showdown
(ver core/deck_format.py). Lee y escribe los selectbox de la página a través
de `slot_key(pieza, i)`, que devuelve la clave de session_state del
selectbox de esa pieza ("blade", "assist", "ratchet", "bit") en el bey i.
"""

import streamlit as st

from core.deck_format import catalogo_desde, importar, exportar, PIEZAS

VACIO = "—"


def beys_actuales(slot_key, n):
    """Lo que hay seleccionado ahora mismo en los selectbox."""
    return [
        {p: st.session_state.get(slot_key(p.lower(), i), VACIO) for p in PIEZAS}
        for i in range(n)
    ]


def _importar(df, reglas, key, slot_key, n):
    beys, avisos = importar(st.session_state.get(f"{key}_txt", ""),
                            catalogo_desde(df, reglas), n_max=n)
    if not any(beys):
        st.session_state[f"{key}_avisos"] = avisos or ["No se ha reconocido ningún bey."]
        return
    # Reemplaza el deck entero: lo que no venga en el texto queda vacío
    for i in range(n):
        bey = beys[i] if i < len(beys) else {}
        for p in PIEZAS:
            st.session_state[slot_key(p.lower(), i)] = bey.get(p) or VACIO
    st.session_state[f"{key}_avisos"] = avisos
    st.toast("📥 Deck importado" + (" con avisos" if avisos else ""), icon="✅")


def deck_io(df, reglas, key, slot_key, n=3, titulo="📋 Importar / exportar"):
    """Expander con el texto del deck actual y un cuadro para pegar uno."""
    with st.expander(titulo):
        texto = exportar(beys_actuales(slot_key, n))
        st.caption("Exportar (copia con el botón de la esquina):")
        st.code(texto or "# Deck vacío", language=None)

        st.text_area(
            "Importar", key=f"{key}_txt", height=180,
            placeholder="Wizard Rod\nRatchet: 1-60\nBit: Ball\n\n"
                        "Pegasus Blast @ Wheel\nRatchet: 3-60\nBit: Hexa",
            help="Un bloque por bey separado por una línea en blanco. También vale "
                 "un combo por línea: «Wizard Rod 1-60 Ball». Las piezas que no "
                 "pongas quedan libres.",
        )
        st.button("📥 Importar", key=f"{key}_btn", on_click=_importar,
                  args=(df, reglas, key, slot_key, n))
        for aviso in st.session_state.get(f"{key}_avisos", []):
            st.warning(aviso, icon="⚠️")
