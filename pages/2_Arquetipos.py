import streamlit as st
import plotly.express as px

from data.loader import load_data
from core.archetypes import calcular_arquetipos, etiquetar_arquetipos


st.set_page_config(layout="wide")

st.title("🧠 Arquetipos del META")

# ----------------------------
# Explicación
# ----------------------------

st.info(
    "Los arquetipos se calculan automáticamente en base al comportamiento real en partida.\n\n"
    "Eje X = puntos ganados por combate (daño que haces)\n"
    "Eje Y = puntos cedidos por combate (daño que recibes)"
)

# ----------------------------
# Datos
# ----------------------------

df = load_data()

df_clustered = calcular_arquetipos(df)
df_clustered = etiquetar_arquetipos(df_clustered)

# ----------------------------
# Filtro
# ----------------------------

tipos = ["Todos"] + sorted(df_clustered["arquetipo"].dropna().unique())

tipo_sel = st.selectbox(
    "Filtrar por arquetipo",
    tipos
)

if tipo_sel != "Todos":
    df_filtered = df_clustered[df_clustered["arquetipo"] == tipo_sel]
else:
    df_filtered = df_clustered

# ----------------------------
# Gráfico (LO PRINCIPAL)
# ----------------------------

fig = px.scatter(
    df_filtered,
    x="Pts Ganados/Combate",
    y="Pts Cedidos/Combate",
    color="arquetipo",
    hover_data=["Blade", "Ratchet", "Bit"],
    opacity=0.7
)

fig.update_layout(
    xaxis_title="Pts Ganados/Combate",
    yaxis_title="Pts Cedidos/Combate"
)

st.plotly_chart(fig, use_container_width=True)

# ----------------------------
# Tabla (secundaria)
# ----------------------------

with st.expander("Ver combos"):
    st.dataframe(
        df_filtered[["Blade", "Ratchet", "Bit", "arquetipo"]],
        use_container_width=True,
        hide_index=True
    )