import plotly.graph_objects as go
import streamlit as st


def plot_evolucion(df_evo, key=None):
    """Barras: partidas nuevas por semana. Línea (eje derecho): cuota de uso %."""
    fig = go.Figure()
    fig.add_bar(
        x=df_evo["periodo"], y=df_evo["partidas"], name="Partidas nuevas",
        marker_color="#6EC1E4", opacity=0.6,
        hovertemplate="%{x|%d/%m}<br>%{y:.0f} partidas<extra></extra>",
    )
    fig.add_scatter(
        x=df_evo["periodo"], y=df_evo["cuota"], name="Cuota %", yaxis="y2",
        mode="lines+markers", line=dict(color="#F39C12", width=2), connectgaps=False,
        hovertemplate="%{x|%d/%m}<br>%{y:.1f}% de las partidas<extra></extra>",
    )
    fig.update_layout(
        yaxis=dict(title="Partidas nuevas", rangemode="tozero"),
        yaxis2=dict(title="Cuota %", overlaying="y", side="right", rangemode="tozero", showgrid=False),
        legend=dict(orientation="h", y=1.1),
        margin=dict(t=30, b=10),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True, key=key)
