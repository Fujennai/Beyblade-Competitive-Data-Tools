import streamlit as st


def filtros_dependientes(df, key_prefix="filter"):

    st.subheader("🔎 Filtros por piezas")

    col1, col2, col3 = st.columns(3)

    # ----------------------------
    # Estado actual
    # ----------------------------

    blade_sel = st.session_state.get(f"{key_prefix}_blade", "Todos")
    ratchet_sel = st.session_state.get(f"{key_prefix}_ratchet", "Todos")
    bit_sel = st.session_state.get(f"{key_prefix}_bit", "Todos")

    # ==================================================
    # BLADE OPTIONS
    # ==================================================

    df_blade = df.copy()

    if ratchet_sel != "Todos":
        df_blade = df_blade[df_blade["Ratchet"] == ratchet_sel]

    if bit_sel != "Todos":
        df_blade = df_blade[df_blade["Bit"] == bit_sel]

    blade_values = sorted(df_blade["Blade"].dropna().unique())

    blade_options = ["Todos"]

    for blade in blade_values:

        if blade == blade_sel:
            blade_options.append(blade)
        else:
            count = len(df_blade[df_blade["Blade"] == blade])
            blade_options.append(f"{blade} ({count})")

    # ==================================================
    # RATCHET OPTIONS
    # ==================================================

    df_ratchet = df.copy()

    if blade_sel != "Todos":
        df_ratchet = df_ratchet[df_ratchet["Blade"] == blade_sel]

    if bit_sel != "Todos":
        df_ratchet = df_ratchet[df_ratchet["Bit"] == bit_sel]

    ratchet_values = sorted(df_ratchet["Ratchet"].dropna().unique())

    ratchet_options = ["Todos"]

    for ratchet in ratchet_values:

        if ratchet == ratchet_sel:
            ratchet_options.append(ratchet)
        else:
            count = len(df_ratchet[df_ratchet["Ratchet"] == ratchet])
            ratchet_options.append(f"{ratchet} ({count})")

    # ==================================================
    # BIT OPTIONS
    # ==================================================

    df_bit = df.copy()

    if blade_sel != "Todos":
        df_bit = df_bit[df_bit["Blade"] == blade_sel]

    if ratchet_sel != "Todos":
        df_bit = df_bit[df_bit["Ratchet"] == ratchet_sel]

    bit_values = sorted(df_bit["Bit"].dropna().unique())

    bit_options = ["Todos"]

    for bit in bit_values:

        if bit == bit_sel:
            bit_options.append(bit)
        else:
            count = len(df_bit[df_bit["Bit"] == bit])
            bit_options.append(f"{bit} ({count})")

    # ==================================================
    # SELECTBOXES
    # ==================================================

    blade_display = col1.selectbox(
        "Blade",
        blade_options,
        key=f"{key_prefix}_blade_display"
    )

    ratchet_display = col2.selectbox(
        "Ratchet",
        ratchet_options,
        key=f"{key_prefix}_ratchet_display"
    )

    bit_display = col3.selectbox(
        "Bit",
        bit_options,
        key=f"{key_prefix}_bit_display"
    )

    # ----------------------------
    # limpiar "(X)"
    # ----------------------------

    blade_sel = blade_display.split(" (")[0]
    ratchet_sel = ratchet_display.split(" (")[0]
    bit_sel = bit_display.split(" (")[0]

    # guardar estado
    st.session_state[f"{key_prefix}_blade"] = blade_sel
    st.session_state[f"{key_prefix}_ratchet"] = ratchet_sel
    st.session_state[f"{key_prefix}_bit"] = bit_sel

    # ==================================================
    # FILTRADO FINAL
    # ==================================================

    df_filtered = df.copy()

    if blade_sel != "Todos":
        df_filtered = df_filtered[df_filtered["Blade"] == blade_sel]

    if ratchet_sel != "Todos":
        df_filtered = df_filtered[df_filtered["Ratchet"] == ratchet_sel]

    if bit_sel != "Todos":
        df_filtered = df_filtered[df_filtered["Bit"] == bit_sel]

    # ==================================================
    # INFO
    # ==================================================

    if len(df_filtered) == 0:

        st.warning("No hay resultados")

    else:

        winrate_medio = round(df_filtered["Win %"].mean(), 1)
        partidas_totales = int(df_filtered["Partidas"].sum())

        st.caption(
            f"📊 {len(df_filtered)} combinaciones | "
            f"Winrate medio: {winrate_medio}% | "
            f"Partidas totales: {partidas_totales}"
        )

    return (
        df_filtered,
        None if blade_sel == "Todos" else blade_sel,
        None if ratchet_sel == "Todos" else ratchet_sel,
        None if bit_sel == "Todos" else bit_sel
    )