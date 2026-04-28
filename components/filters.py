import streamlit as st

import streamlit as st

def filtros_dependientes(df):

    col1, col2, col3 = st.columns(3)

    df_temp = df.copy()

    # ----------------------------
    # Blade
    # ----------------------------
    blade_options = sorted(df["Blade"].dropna().unique())

    blade_sel = col1.selectbox(
        "Blade",
        blade_options,
        index=None,
        placeholder="Selecciona Blade"
    )

    if blade_sel:
        df_temp = df_temp[df_temp["Blade"] == blade_sel]

    # ----------------------------
    # Ratchet
    # ----------------------------
    ratchet_options = sorted(df_temp["Ratchet"].dropna().unique())

    ratchet_sel = col2.selectbox(
        "Ratchet",
        ratchet_options,
        index=None,
        placeholder="Selecciona Ratchet"
    )

    if ratchet_sel:
        df_temp = df_temp[df_temp["Ratchet"] == ratchet_sel]

    # ----------------------------
    # Bit
    # ----------------------------
    bit_options = sorted(df_temp["Bit"].dropna().unique())

    bit_sel = col3.selectbox(
        "Bit",
        bit_options,
        index=None,
        placeholder="Selecciona Bit"
    )

    if bit_sel:
        df_temp = df_temp[df_temp["Bit"] == bit_sel]

    
    return df_temp, blade_sel, ratchet_sel, bit_sel