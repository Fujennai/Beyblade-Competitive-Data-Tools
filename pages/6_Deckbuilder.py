import streamlit as st

from data.loader import load_data
from core.deckbuilder import recomendar_combo

st.set_page_config(layout="wide")

st.title("🧩 Deckbuilder interactivo")

df = load_data()

st.info(
    "Construye un deck de 3 beys sin repetir piezas.\n"
    "Las recomendaciones se adaptan dinámicamente."
)

# ----------------------------
# Estado
# ----------------------------

if "deck" not in st.session_state:
    st.session_state.deck = [
        {"Blade": None, "Ratchet": None, "Bit": None},
        {"Blade": None, "Ratchet": None, "Bit": None},
        {"Blade": None, "Ratchet": None, "Bit": None},
    ]


# ----------------------------
# UI selección
# ----------------------------

st.subheader("🎯 Construcción del deck")

for i in range(3):

    st.markdown(f"### Bey {i+1}")

    col1, col2, col3 = st.columns(3)

    with col1:
        blade = st.selectbox(
            f"Blade {i+1}",
            [""] + sorted(df["Blade"].unique()),
            key=f"blade_{i}"
        )

    with col2:
        ratchet = st.selectbox(
            f"Ratchet {i+1}",
            [""] + sorted(df["Ratchet"].unique()),
            key=f"ratchet_{i}"
        )

    with col3:
        bit = st.selectbox(
            f"Bit {i+1}",
            [""] + sorted(df["Bit"].unique()),
            key=f"bit_{i}"
        )

    st.session_state.deck[i] = {
        "Blade": blade or None,
        "Ratchet": ratchet or None,
        "Bit": bit or None
    }

st.divider()

# ----------------------------
# Preparar usados
# ----------------------------

usados = {
    "Blade": [d["Blade"] for d in st.session_state.deck if d["Blade"]],
    "Ratchet": [d["Ratchet"] for d in st.session_state.deck if d["Ratchet"]],
    "Bit": [d["Bit"] for d in st.session_state.deck if d["Bit"]],
}

# ----------------------------
# Recomendaciones
# ----------------------------

st.subheader("💡 Recomendaciones")

df_rec = recomendar_combo(df, usados)

if df_rec.empty:
    st.warning("No hay combinaciones disponibles")
else:
    st.dataframe(
        df_rec[[
            "Blade",
            "Ratchet",
            "Bit",
            "Win %",
            "Partidas"
        ]],
        use_container_width=True,
        hide_index=True
    )