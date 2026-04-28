import plotly.express as px
import streamlit as st

def plot_winrate(df_plot):

    y_min = df_plot["Win %"].min()
    y_max = df_plot["Win %"].max()
    padding = (y_max - y_min) * 0.2 if y_max != y_min else 1

    fig = px.line(
        df_plot,
        x="fecha",
        y="Win %",
        markers=True
    )

    fig.update_layout(
        yaxis=dict(range=[y_min - padding, y_max + padding])
    )

    st.plotly_chart(fig, use_container_width=True)