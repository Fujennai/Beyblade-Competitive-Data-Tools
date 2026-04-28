import streamlit as st
import plotly.express as px
from data.loader import load_data
from core.archetypes import calcular_arquetipos, etiquetar_arquetipos

st.set_page_config(layout="wide")
st.title("🧠 Arquetipos del META")

df = load_data()

df_clustered, _ = calcular_arquetipos(df)
df_clustered = etiquetar_arquetipos(df_clustered)

st.dataframe(
    df_clustered[["Blade", "Ratchet", "Bit", "arquetipo"]],
    use_container_width=True,
    hide_index=True
)



fig = px.scatter(
    df_clustered,
    x="Pts Ganados/Combate",
    y="Pts Cedidos/Combate",
    color="arquetipo",
    hover_data=["Blade", "Ratchet", "Bit"]
)

st.plotly_chart(fig, use_container_width=True)

tipo = st.selectbox(
    "Filtrar por arquetipo",
    ["Todos"] + sorted(df_clustered["arquetipo"].unique())
)

if tipo != "Todos":
    df_clustered = df_clustered[df_clustered["arquetipo"] == tipo]