"""
components/view_toggle.py
-------------------------
Switch reutilizable para alternar entre vista de cards y tabla.
Uso:
    from components.view_toggle import view_toggle
    modo = view_toggle(key="mi_pagina")  # devuelve "cards" o "tabla"
"""

import streamlit as st


def view_toggle(key: str = "view_mode", default: str = "cards") -> str:
    """
    Muestra un toggle 📊 / 🃏 y devuelve "cards" o "tabla".
    El estado se guarda en session_state con la key dada.
    """
    if key not in st.session_state:
        st.session_state[key] = default

    col_spacer, col_btn = st.columns([10, 1])

    with col_btn:
        modo_actual = st.session_state[key]
        label = "📊 Tabla" if modo_actual == "cards" else "🃏 Cards"
        if st.button(label, key=f"{key}_btn"):
            st.session_state[key] = "tabla" if modo_actual == "cards" else "cards"
            st.rerun()

    return st.session_state[key]