"""Weekly charts - Volume and strain summaries."""
import pandas as pd
import plotly.graph_objects as go


def create_weekly_volume_chart(data, title="Volumen Semanal"):
    """Bar chart semanal para volumen."""
    fig = go.Figure()
    x = [pd.to_datetime(d).strftime("%d/%m/%Y") for d in data.index]
    fig.add_trace(go.Bar(x=x, y=data.values, marker_color='#00D084',
        marker_line=dict(color='#FFFFFF', width=1),
        hovertemplate='<b>%{x}</b><br>Volumen: %{y:,.0f} kg<extra></extra>'))
    fig.update_layout(title=dict(text=title, font=dict(size=16, color='#00D084', family='Orbitron')),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#E0E0E0'),
        xaxis=dict(type='category', showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(0, 208, 132, 0.12)', zeroline=False),
        bargap=0.6, hovermode='x unified', margin=dict(l=40, r=40, t=40, b=40), height=300)
    return fig


def create_weekly_strain_chart(data, title="Strain"):
    """Bar chart semanal para strain."""
    fig = go.Figure()
    x = [pd.to_datetime(d).strftime("%d/%m/%Y") for d in data.index]
    fig.add_trace(go.Bar(x=x, y=data.values, marker_color='#FF6B6B',
        marker_line=dict(color='#FFFFFF', width=1),
        hovertemplate='<b>%{x}</b><br>Strain: %{y:,.0f}<extra></extra>'))
    fig.update_layout(title=dict(text=title, font=dict(size=16, color='#FF6B6B', family='Orbitron')),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font=dict(color='#E0E0E0'),
        xaxis=dict(type='category', showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255, 107, 107, 0.12)', zeroline=False),
        bargap=0.6, hovermode='x unified', margin=dict(l=40, r=40, t=40, b=40), height=300)
    return fig
