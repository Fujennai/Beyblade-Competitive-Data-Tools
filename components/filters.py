import streamlit as st


def render_piece_filters(df, key_prefix="filter"):

    st.subheader("🔎 Filtros por piezas")

    col1, col2, col3 = st.columns(3)

    df_temp = df.copy()

    # ----------------------------
    # Blade
    # ----------------------------

    blade_counts = (
        df_temp["Blade"]
        .value_counts()
        .sort_index()
    )

    blade_map = {
        f"{blade} ({count})": blade
        for blade, count in blade_counts.items()
    }

    blade_options = ["Todos"] + list(blade_map.keys())

    blade_display = col1.selectbox(
        "Blade",
        blade_options,
        key=f"{key_prefix}_blade"
    )

    blade_sel = None if blade_display == "Todos" else blade_map[blade_display]

    if blade_sel:
        df_temp = df_temp[df_temp["Blade"] == blade_sel]

    # ----------------------------
    # Ratchet
    # ----------------------------

    ratchet_counts = (
        df_temp["Ratchet"]
        .value_counts()
        .sort_index()
    )

    ratchet_map = {
        f"{ratchet} ({count})": ratchet
        for ratchet, count in ratchet_counts.items()
    }

    ratchet_options = ["Todos"] + list(ratchet_map.keys())

    ratchet_display = col2.selectbox(
        "Ratchet",
        ratchet_options,
        key=f"{key_prefix}_ratchet"
    )

    ratchet_sel = None if ratchet_display == "Todos" else ratchet_map[ratchet_display]

    if ratchet_sel:
        df_temp = df_temp[df_temp["Ratchet"] == ratchet_sel]

    # ----------------------------
    # Bit
    # ----------------------------

    bit_counts = (
        df_temp["Bit"]
        .value_counts()
        .sort_index()
    )

    bit_map = {
        f"{bit} ({count})": bit
        for bit, count in bit_counts.items()
    }

    bit_options = ["Todos"] + list(bit_map.keys())

    bit_display = col3.selectbox(
        "Bit",
        bit_options,
        key=f"{key_prefix}_bit"
    )

    bit_sel = None if bit_display == "Todos" else bit_map[bit_display]

    if bit_sel:
        df_temp = df_temp[df_temp["Bit"] == bit_sel]

    # ----------------------------
    # Información dinámica
    # ----------------------------

    if len(df_temp) == 0:

        st.warning("No hay resultados")

    else:

        winrate_medio = round(df_temp["Win %"].mean(), 1)
        partidas_totales = int(df_temp["Partidas"].sum())

        st.caption(
            f"📊 {len(df_temp)} combinaciones | "
            f"Winrate medio: {winrate_medio}% | "
            f"Partidas totales: {partidas_totales}"
        )

    return df_temp, blade_sel, ratchet_sel, bit_sel