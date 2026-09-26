import streamlit as st

# Piezas filtrables. El Assist solo existe en los CX: sus opciones no incluyen
# el valor vacío (UX/BX) y elegir uno deja solo combos CX.
PIEZAS = [("blade", "Blade"), ("assist", "Assist"), ("ratchet", "Ratchet"), ("bit", "Bit")]


def filtros_dependientes(df, key_prefix="filter"):

    st.subheader("🔎 Filtros por piezas")

    if st.button("🔄 Resetear filtros"):
        for k, _ in PIEZAS:
            # valores reales, widgets visuales y estados previos
            st.session_state[f"{key_prefix}_{k}"] = "Todos"
            st.session_state[f"{key_prefix}_{k}_box"] = "Todos"
            st.session_state[f"{key_prefix}_prev_{k}"] = "Todos"
        st.rerun()

    columnas = st.columns(len(PIEZAS))

    # ==================================================
    # ESTADO ACTUAL
    # ==================================================

    sel = {k: st.session_state.get(f"{key_prefix}_{k}", "Todos") for k, _ in PIEZAS}

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

    def filtrar(d, excepto=None):
        for k, col in PIEZAS:
            if k != excepto and sel[k] != "Todos":
                d = d[d[col] == sel[k]]
        return d

    # ==================================================
    # OPCIONES (cada pieza filtrada por las demás)
    # ==================================================

    displays = {}
    for (k, col), c in zip(PIEZAS, columnas):
        valores = filtrar(df, excepto=k)[col]
        if col == "Assist":
            valores = valores[valores != ""]
        counts = valores.value_counts().to_dict()
        options = build_options(counts.keys(), counts, sel[k])

        displays[k] = c.selectbox(
            col,
            options,
            index=options.index(sel[k]) if sel[k] in options else 0,
            key=f"{key_prefix}_{k}_box",
            help="Solo CX. Con un Assist elegido solo se muestran CX." if col == "Assist" else None,
        )

    # ==================================================
    # LIMPIAR VALORES
    # ==================================================

    sel = {k: clean_value(displays[k]) for k, _ in PIEZAS}

    # guardar
    for k, _ in PIEZAS:
        st.session_state[f"{key_prefix}_{k}"] = sel[k]

    # detectar cambios
    changed = any(sel[k] != st.session_state.get(f"{key_prefix}_prev_{k}") for k, _ in PIEZAS)

    # guardar estados previos
    for k, _ in PIEZAS:
        st.session_state[f"{key_prefix}_prev_{k}"] = sel[k]

    # rerun inmediato
    if changed:
        st.rerun()

    # ==================================================
    # FILTRADO FINAL
    # ==================================================

    df_filtered = filtrar(df.copy())

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

    def _v(k):
        return None if sel[k] == "Todos" else sel[k]

    # (df, blade, ratchet, bit, assist)
    return df_filtered, _v("blade"), _v("ratchet"), _v("bit"), _v("assist")
