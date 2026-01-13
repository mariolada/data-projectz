"""
Weekly charts: Gráficos semanales (bar charts) con estilo gaming para Streamlit/Plotly.
"""
import pandas as pd
import plotly.graph_objects as go


def create_weekly_volume_chart(data, title="Volumen Semanal"):
    """Bar chart semanal con estilo consistente y efectos neon."""
    fig = go.Figure()
    x = [pd.to_datetime(d).strftime("%d/%m/%Y") for d in data.index]
    
    fig.add_trace(go.Bar(
        x=x,
        y=data.values,
        marker=dict(
            color='#00D084',
            line=dict(color='rgba(0, 208, 132, 0.8)', width=2),
            opacity=0.85
        ),
        hovertemplate='<b>%{x}</b><br>Volumen: %{y:,.0f} kg<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=18, color='#00D084', family='Orbitron, sans-serif'),
            x=0.05
        ),
        paper_bgcolor='rgba(7, 9, 15, 0.95)',
        plot_bgcolor='rgba(15, 20, 32, 0.9)',
        font=dict(color='#E0E0E0', family='system-ui'),
        xaxis=dict(
            type='category',
            showgrid=False,
            color='#9CA3AF',
            linecolor='rgba(0, 208, 132, 0.3)'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(0, 208, 132, 0.15)',
            gridwidth=1,
            zeroline=False,
            color='#9CA3AF',
            linecolor='rgba(0, 208, 132, 0.3)'
        ),
        bargap=0.3,
        hovermode='x unified',
        margin=dict(l=50, r=30, t=60, b=50),
        height=350,
        hoverlabel=dict(
            bgcolor='rgba(15, 20, 32, 0.95)',
            font_size=13,
            font_family='system-ui',
            bordercolor='#00D084'
        )
    )
    return fig


def create_weekly_strain_chart(data, title="Strain"):
    """Bar chart semanal para strain con estilo consistente y efectos neon."""
    fig = go.Figure()
    x = [pd.to_datetime(d).strftime("%d/%m/%Y") for d in data.index]
    
    fig.add_trace(go.Bar(
        x=x,
        y=data.values,
        marker=dict(
            color='#FF6B6B',
            line=dict(color='rgba(255, 107, 107, 0.8)', width=2),
            opacity=0.85
        ),
        hovertemplate='<b>%{x}</b><br>Strain: %{y:,.0f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=18, color='#FF6B6B', family='Orbitron, sans-serif'),
            x=0.05
        ),
        paper_bgcolor='rgba(7, 9, 15, 0.95)',
        plot_bgcolor='rgba(15, 20, 32, 0.9)',
        font=dict(color='#E0E0E0', family='system-ui'),
        xaxis=dict(
            type='category',
            showgrid=False,
            color='#9CA3AF',
            linecolor='rgba(255, 107, 107, 0.3)'
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor='rgba(255, 107, 107, 0.15)',
            gridwidth=1,
            zeroline=False,
            color='#9CA3AF',
            linecolor='rgba(255, 107, 107, 0.3)'
        ),
        bargap=0.3,
        hovermode='x unified',
        margin=dict(l=50, r=30, t=60, b=50),
        height=350,
        hoverlabel=dict(
            bgcolor='rgba(15, 20, 32, 0.95)',
            font_size=13,
            font_family='system-ui',
            bordercolor='#FF6B6B'
        )
    )
    return fig
