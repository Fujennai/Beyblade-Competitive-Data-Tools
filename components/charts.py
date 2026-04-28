import plotly.express as px
import streamlit as st

def plot_winrate(df_plot, key=None):

    import plotly.express as px

    fig = px.line(
        df_plot,
        x="fecha",
        y="Win %",
        markers=True
    )

    st.plotly_chart(fig, use_container_width=True, key=key)