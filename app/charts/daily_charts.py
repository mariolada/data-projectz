"""
Daily charts: Gráficos diarios con estilo gaming para Streamlit/Plotly.
"""
import pandas as pd
import plotly.graph_objects as go


def create_readiness_chart(data, title="Readiness"):
    """Crea gráfica de readiness con estilo gaming y gradient."""
    fig = go.Figure()
    
    # Añadir zona de referencia (óptimo)
    fig.add_hrect(y0=75, y1=100, fillcolor="rgba(0, 208, 132, 0.1)", line_width=0, annotation_text="Alta", annotation_position="right")
    fig.add_hrect(y0=55, y1=75, fillcolor="rgba(255, 184, 28, 0.1)", line_width=0, annotation_text="Media", annotation_position="right")
    fig.add_hrect(y0=0, y1=55, fillcolor="rgba(255, 68, 68, 0.1)", line_width=0, annotation_text="Baja", annotation_position="right")
    
    # Línea principal con gradient
    x_vals = pd.to_datetime(data.index)
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=data.values,
        mode='lines+markers',
        name='Readiness',
        line=dict(color='#B266FF', width=3, shape='spline'),
        marker=dict(size=8, color='#B266FF', line=dict(color='#FFFFFF', width=2)),
        fill='tozeroy',
        fillcolor='rgba(178, 102, 255, 0.2)',
        hovertemplate='<b>%{x|%d/%m/%Y}</b><br>Readiness: %{y:.0f}/100<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='#B266FF', family='Orbitron')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E0E0E0'),
        xaxis=dict(showgrid=True, gridcolor='rgba(178, 102, 255, 0.1)', zeroline=False, tickformat='%d/%m/%Y'),
        yaxis=dict(showgrid=True, gridcolor='rgba(178, 102, 255, 0.1)', zeroline=False, range=[0, 105]),
        hovermode='x unified',
        margin=dict(l=40, r=40, t=40, b=40),
        height=300
    )
    
    return fig


def create_volume_chart(data, title="Volumen"):
    """Crea gráfica de volumen con estilo gaming y gradient."""
    fig = go.Figure()

    x_vals = pd.to_datetime(data.index)
    
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=data.values,
        mode='lines',
        name='Volumen',
        line=dict(color='#00D084', width=0),
        fill='tozeroy',
        fillcolor='rgba(0, 208, 132, 0.3)',
        hovertemplate='<b>%{x|%d/%m/%Y}</b><br>Volumen: %{y:,.0f} kg<extra></extra>'
    ))
    
    # Añadir línea superior para efecto
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=data.values,
        mode='lines+markers',
        name='Volumen',
        line=dict(color='#00D084', width=3, shape='spline'),
        marker=dict(size=6, color='#00D084'),
        showlegend=False,
        hovertemplate='<b>%{x|%d/%m/%Y}</b><br>Volumen: %{y:,.0f} kg<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='#00D084', family='Orbitron')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E0E0E0'),
        xaxis=dict(showgrid=True, gridcolor='rgba(0, 208, 132, 0.1)', zeroline=False, tickformat='%d/%m/%Y'),
        yaxis=dict(showgrid=True, gridcolor='rgba(0, 208, 132, 0.1)', zeroline=False),
        hovermode='x unified',
        margin=dict(l=40, r=40, t=40, b=40),
        height=300
    )
    
    return fig


def create_sleep_chart(data, title="Sueño"):
    """Crea gráfica de sueño con línea+área estilo gaming (igual que readiness)."""
    fig = go.Figure()
    
    # Zona óptima de sueño
    fig.add_hrect(y0=7, y1=9, fillcolor="rgba(0, 208, 132, 0.1)", line_width=0)
    
    colors = ['#FFB81C' if float(val) < 7 else '#00D084' for val in data.values]

    x_vals = pd.to_datetime(data.index)
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=data.values,
        mode='lines+markers',
        name='Sueño',
        line=dict(color='#4ECDC4', width=3, shape='spline'),
        marker=dict(size=8, color=colors, line=dict(color='#FFFFFF', width=2)),
        fill='tozeroy',
        fillcolor='rgba(78, 205, 196, 0.18)',
        hovertemplate='<b>%{x|%d/%m/%Y}</b><br>Sueño: %{y:.1f} h<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='#4ECDC4', family='Orbitron')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E0E0E0'),
        xaxis=dict(showgrid=True, gridcolor='rgba(78, 205, 196, 0.10)', zeroline=False, tickformat='%d/%m/%Y'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255, 184, 28, 0.1)', zeroline=False, range=[0, max(data.max() * 1.1, 10)]),
        hovermode='x unified',
        margin=dict(l=40, r=40, t=40, b=40),
        height=300
    )
    
    return fig


def create_acwr_chart(data, title="ACWR (Carga)"):
    """Crea gráfica de ACWR con zonas de riesgo."""
    fig = go.Figure()
    
    # Zonas de ACWR
    fig.add_hrect(y0=0.8, y1=1.3, fillcolor="rgba(0, 208, 132, 0.1)", line_width=0, annotation_text="Óptimo", annotation_position="right")
    fig.add_hrect(y0=1.3, y1=1.5, fillcolor="rgba(255, 184, 28, 0.1)", line_width=0)
    fig.add_hrect(y0=1.5, y1=2.5, fillcolor="rgba(255, 68, 68, 0.1)", line_width=0, annotation_text="Riesgo", annotation_position="right")
    
    # Línea óptima
    fig.add_hline(y=1.0, line_dash="dash", line_color="rgba(255, 255, 255, 0.3)", annotation_text="1.0")
    
    x_vals = pd.to_datetime(data.index)
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=data.values,
        mode='lines+markers',
        name='ACWR',
        line=dict(color='#FF6B6B', width=3, shape='spline'),
        marker=dict(size=8, color='#FF6B6B', line=dict(color='#FFFFFF', width=2)),
        hovertemplate='<b>%{x|%d/%m/%Y}</b><br>ACWR: %{y:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='#FF6B6B', family='Orbitron')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E0E0E0'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255, 107, 107, 0.1)', zeroline=False, tickformat='%d/%m/%Y'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255, 107, 107, 0.1)', zeroline=False, range=[0, max(data.max() * 1.2, 2.0) if data.max() > 0 else 2.0]),
        hovermode='x unified',
        margin=dict(l=40, r=40, t=40, b=40),
        height=300
    )
    
    return fig


def create_performance_chart(data, title="Performance Index"):
    """Crea gráfica de performance index con zona objetivo."""
    fig = go.Figure()
    
    # Zona objetivo
    fig.add_hrect(y0=0.99, y1=1.01, fillcolor="rgba(0, 208, 132, 0.1)", line_width=0)
    
    # Línea baseline
    fig.add_hline(y=1.0, line_dash="dash", line_color="rgba(255, 255, 255, 0.3)", annotation_text="Baseline")
    
    # Normalizar índice a datetime para consistencia con otros gráficos
    x_vals = pd.to_datetime(data.index)
    
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=data.values,
        mode='lines+markers',
        name='Performance',
        line=dict(color='#4ECDC4', width=3, shape='spline'),
        marker=dict(size=8, color='#4ECDC4', line=dict(color='#FFFFFF', width=2)),
        fill='tozeroy',
        fillcolor='rgba(78, 205, 196, 0.2)',
        hovertemplate='<b>%{x|%d/%m/%Y}</b><br>Performance: %{y:.3f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='#4ECDC4', family='Orbitron')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E0E0E0'),
        xaxis=dict(showgrid=True, gridcolor='rgba(78, 205, 196, 0.1)', zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(78, 205, 196, 0.1)', zeroline=False),
        hovermode='x unified',
        margin=dict(l=40, r=40, t=40, b=40),
        height=300
    )
    
    return fig


def create_strain_chart(data, title="Strain"):
    """Gráfica de strain con escala libre para valores altos."""
    fig = go.Figure()
    max_val = data.max() if len(data) > 0 else 0
    y_max = max(max_val * 1.2, 1.0)

    x_vals = pd.to_datetime(data.index)
    fig.add_trace(go.Scatter(
        x=x_vals,
        y=data.values,
        mode='lines+markers',
        name='Strain',
        line=dict(color='#FF6B6B', width=3, shape='spline'),
        marker=dict(size=8, color='#FF6B6B', line=dict(color='#FFFFFF', width=2)),
        fill='tozeroy',
        fillcolor='rgba(255, 107, 107, 0.18)',
        hovertemplate='<b>%{x|%d/%m/%Y}</b><br>Strain: %{y:,.0f}<extra></extra>'
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='#FF6B6B', family='Orbitron')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E0E0E0'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255, 107, 107, 0.12)', zeroline=False, tickformat='%d/%m/%Y'),
        yaxis=dict(showgrid=True, gridcolor='rgba(255, 107, 107, 0.12)', zeroline=False, range=[0, y_max]),
        hovermode='x unified',
        margin=dict(l=40, r=40, t=40, b=40),
        height=300
    )
    return fig
