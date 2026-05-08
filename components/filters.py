import streamlit as st


def filtros_dependientes(df, key_prefix="filter"):

    st.subheader("🔎 Filtros por piezas")
    st.subheader("🔎 Filtros por piezas")

    if st.button("🔄 Resetear filtros"):

        # valores reales
        st.session_state[f"{key_prefix}_blade"] = "Todos"
        st.session_state[f"{key_prefix}_ratchet"] = "Todos"
        st.session_state[f"{key_prefix}_bit"] = "Todos"

        # widgets visuales
        st.session_state[f"{key_prefix}_blade_box"] = "Todos"
        st.session_state[f"{key_prefix}_ratchet_box"] = "Todos"
        st.session_state[f"{key_prefix}_bit_box"] = "Todos"

        # estados previos
        st.session_state[f"{key_prefix}_prev_blade"] = "Todos"
        st.session_state[f"{key_prefix}_prev_ratchet"] = "Todos"
        st.session_state[f"{key_prefix}_prev_bit"] = "Todos"

        st.rerun()

    col1, col2, col3 = st.columns(3)

    # ==================================================
    # ESTADO ACTUAL
    # ==================================================

    blade_sel = st.session_state.get(f"{key_prefix}_blade", "Todos")
    ratchet_sel = st.session_state.get(f"{key_prefix}_ratchet", "Todos")
    bit_sel = st.session_state.get(f"{key_prefix}_bit", "Todos")

    # ==================================================
    # HELPERS
    # ==================================================

    def build_options(values, counts, selected):

        options = ["Todos"]

        for val in sorted(values):

            if val == selected:
                options.append(val)
            else:
                options.append(f"{val} ({counts[val]})")

        return options

    def clean_value(display):

        if display == "Todos":
            return "Todos"

        return display.split(" (")[0]

    # ==================================================
    # BLADE
    # ==================================================

    df_blade = df.copy()

    if ratchet_sel != "Todos":
        df_blade = df_blade[df_blade["Ratchet"] == ratchet_sel]

    if bit_sel != "Todos":
        df_blade = df_blade[df_blade["Bit"] == bit_sel]

    blade_counts = df_blade["Blade"].value_counts().to_dict()

    blade_options = build_options(
        blade_counts.keys(),
        blade_counts,
        blade_sel
    )

    # ==================================================
    # RATCHET
    # ==================================================

    df_ratchet = df.copy()

    if blade_sel != "Todos":
        df_ratchet = df_ratchet[df_ratchet["Blade"] == blade_sel]

    if bit_sel != "Todos":
        df_ratchet = df_ratchet[df_ratchet["Bit"] == bit_sel]

    ratchet_counts = df_ratchet["Ratchet"].value_counts().to_dict()

    ratchet_options = build_options(
        ratchet_counts.keys(),
        ratchet_counts,
        ratchet_sel
    )

    # ==================================================
    # BIT
    # ==================================================

    df_bit = df.copy()

    if blade_sel != "Todos":
        df_bit = df_bit[df_bit["Blade"] == blade_sel]

    if ratchet_sel != "Todos":
        df_bit = df_bit[df_bit["Ratchet"] == ratchet_sel]

    bit_counts = df_bit["Bit"].value_counts().to_dict()

    bit_options = build_options(
        bit_counts.keys(),
        bit_counts,
        bit_sel
    )

    # ==================================================
    # SELECTBOXES
    # ==================================================

    blade_display = col1.selectbox(
        "Blade",
        blade_options,
        index=blade_options.index(blade_sel)
        if blade_sel in blade_options else 0,
        key=f"{key_prefix}_blade_box"
    )

    ratchet_display = col2.selectbox(
        "Ratchet",
        ratchet_options,
        index=ratchet_options.index(ratchet_sel)
        if ratchet_sel in ratchet_options else 0,
        key=f"{key_prefix}_ratchet_box"
    )

    bit_display = col3.selectbox(
        "Bit",
        bit_options,
        index=bit_options.index(bit_sel)
        if bit_sel in bit_options else 0,
        key=f"{key_prefix}_bit_box"
    )

    # ==================================================
    # LIMPIAR VALORES
    # ==================================================

    blade_sel = clean_value(blade_display)
    ratchet_sel = clean_value(ratchet_display)
    bit_sel = clean_value(bit_display)

    # guardar
    st.session_state[f"{key_prefix}_blade"] = blade_sel
    st.session_state[f"{key_prefix}_ratchet"] = ratchet_sel
    st.session_state[f"{key_prefix}_bit"] = bit_sel

    # detectar cambios
    changed = (
        blade_sel != st.session_state.get(f"{key_prefix}_prev_blade")
        or ratchet_sel != st.session_state.get(f"{key_prefix}_prev_ratchet")
        or bit_sel != st.session_state.get(f"{key_prefix}_prev_bit")
    )

    # guardar estados previos
    st.session_state[f"{key_prefix}_prev_blade"] = blade_sel
    st.session_state[f"{key_prefix}_prev_ratchet"] = ratchet_sel
    st.session_state[f"{key_prefix}_prev_bit"] = bit_sel

    # rerun inmediato
    if changed:
        st.rerun()

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