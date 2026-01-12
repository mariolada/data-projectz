import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
import datetime
import sys
import json
sys.path.append(str(Path(__file__).parent.parent / 'src'))
from personalization_engine import (
    calculate_personal_baselines,
    contextualize_readiness,
    detect_fatigue_type,
    calculate_injury_risk_score,
    suggest_weekly_sequence
)


@st.cache_data
def load_csv(path: str):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No existe: {path}")
    df = pd.read_csv(p)
    # normalize date column to Timestamp
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    return df


@st.cache_data
def load_user_profile(profile_path: str = "data/processed/user_profile.json"):
    """Carga el perfil personalizado del usuario desde JSON."""
    p = Path(profile_path)
    if not p.exists():
        return {
            'archetype': {'archetype': 'unknown', 'confidence': 0},
            'adjustment_factors': {
                'sleep_weight': 0.25,
                'performance_weight': 0.25,
                'acwr_weight': 0.15,
                'fatigue_sensitivity': 1.0,
                'recovery_speed': 1.0
            },
            'sleep_responsiveness': {'sleep_responsive': None},
            'insights': ['No hay datos suficientes aún para personalización'],
            'data_quality': {'total_days': 0}
        }
    
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}



def get_readiness_zone(readiness):
    """Retorna (zona, emoji, color) basado en readiness score."""
    if pd.isna(readiness):
        return ("N/D", "❓", "#999999")
    if readiness >= 75:
        return ("Alta", "🟢", "#00D084")
    elif readiness >= 55:
        return ("Media", "🟡", "#FFB81C")
    else:
        return ("Muy baja", "🔴", "#FF4444")


def get_days_until_acwr(df_daily, selected_date):
    """Calcula cuántos días de histórico hay hasta la fecha seleccionada."""
    filtered = df_daily[df_daily['date'] <= selected_date]
    return len(filtered)


def format_acwr_display(acwr, days_available):
    """Formatea ACWR: muestra valor o 'Pendiente (x/28 días)'."""
    if pd.isna(acwr) or acwr == '—':
        return f"Pendiente ({days_available}/28 días)"
    return f"{round(float(acwr), 3)}"


def get_confidence_level(df_daily, selected_date):
    """Retorna nivel de confianza basado en días de histórico."""
    filtered = df_daily[df_daily['date'] <= selected_date].copy()
    days_available = len(filtered)
    
    if days_available < 7:
        return "Baja (pocos datos)", "⚠️"
    elif days_available < 28:
        return f"Media ({days_available} días)", "ℹ️"
    else:
        return "Alta (>28 días)", "✅"
    """Retorna nivel de confianza basado en días de histórico."""
    filtered = df_daily[df_daily['date'] <= selected_date].copy()
    days_available = len(filtered)
    
    if days_available < 7:
        return "Baja (pocos datos)", "⚠️"
    elif days_available < 28:
        return f"Media ({days_available} días)", "ℹ️"
    else:
        return "Alta (>28 días)", "✅"


def get_anti_fatigue_flag(df_daily, selected_date):
    """Detecta si hay 2+ días seguidos de HIGH_STRAIN_DAY."""
    # Para simplificar: usamos readiness < 50 como proxy de HIGH_STRAIN_DAY
    if 'readiness_score' not in df_daily.columns:
        return False
    
    sorted_df = df_daily.sort_values('date')
    selected_idx = sorted_df[sorted_df['date'] == selected_date].index
    
    if len(selected_idx) == 0:
        return False
    
    idx = selected_idx[0]
    if idx == 0:
        return False
    
    # Check if current and previous day are both low readiness
    current_readiness = sorted_df.loc[idx, 'readiness_score']
    prev_readiness = sorted_df.loc[idx - 1, 'readiness_score']
    
    return pd.notna(current_readiness) and pd.notna(prev_readiness) and current_readiness < 50 and prev_readiness < 50


def format_reason_codes(reason_codes_str):
    """Convierte string de reason codes a lista legible."""
    if pd.isna(reason_codes_str) or reason_codes_str == '':
        return []
    codes = str(reason_codes_str).split('|')
    
    code_map = {
        'LOW_SLEEP': '😴 Sueño insuficiente',
        'HIGH_ACWR': '📈 Carga aguda muy alta',
        'PERF_DROP': '📉 Rendimiento en caída',
        'HIGH_EFFORT': '💪 Esfuerzo muy alto',
        'FATIGA': '⚠️ Fatiga detectada'
    }
    
    return [code_map.get(c.strip(), c.strip()) for c in codes if c.strip()]


def load_daily_exercise_for_date(path, selected_date):
    """Carga ejercicios del día seleccionado desde daily_exercise.csv."""
    try:
        df = load_csv(path)
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df[df['date'] == selected_date].sort_values('volume', ascending=False)
    except:
        return pd.DataFrame()


def get_lift_recommendations(df_exercises, readiness_score, readiness_zone):
    """Genera recomendaciones por lift basadas en readiness."""
    if df_exercises.empty:
        return []
    
    recs = []
    for idx, row in df_exercises.head(3).iterrows():
        exercise = row['exercise']
        
        if readiness_zone == "Alta":
            action = f"+2.5% o +1 rep @ RIR2"
        elif readiness_zone == "Media":
            action = f"Mantener, técnica, RIR2–3"
        else:
            action = f"-10% sets, RIR3–4"
        
        recs.append(f"**{exercise}**: {action}")
    
    return recs


def calculate_readiness_from_inputs(sleep_hours, sleep_quality, fatigue, soreness, stress, motivation, pain_flag):
    """Calcula readiness instantáneamente desde inputs del usuario (versión legacy)."""
    
    # Normalizar inputs a 0-1
    sleep_hours_score = np.clip((sleep_hours - 6.0) / (7.5 - 6.0), 0, 1)
    sleep_quality_score = (sleep_quality - 1) / 4
    
    # Fatiga: 0 (sin cansancio) → 1, 10 (muy cansado) → 0
    fatigue_score = 1 - (fatigue / 10)
    
    # Soreness: 0 (sin dolor) → 1, 10 (mucho dolor) → 0
    soreness_score = 1 - (soreness / 10)
    
    # Stress: 0 (sin estrés) → 1, 10 (mucho estrés) → 0
    stress_score = 1 - (stress / 10)
    
    # Motivation: 0–10 mapear a 0–1
    motivation_score = motivation / 10
    
    # Pain flag penaliza
    pain_penalty = 0.3 if pain_flag else 0
    
    # Fórmula ponderada
    readiness_0_1 = (
        0.25 * sleep_hours_score +
        0.15 * sleep_quality_score +
        0.15 * fatigue_score +
        0.15 * soreness_score +
        0.15 * stress_score +
        0.15 * motivation_score
    ) - pain_penalty
    
    readiness_0_1 = np.clip(readiness_0_1, 0, 1)
    readiness_score = int(round(readiness_0_1 * 100))
    
    return readiness_score


def calculate_readiness_from_inputs_v2(
    sleep_hours, sleep_quality, fatigue, soreness, stress, motivation, pain_flag,
    nap_mins=0, sleep_disruptions=False, energy=7, stiffness=2, 
    caffeine=0, alcohol=False, sick_flag=False, perceived_readiness=None
):
    """Versión mejorada: considera nap, energía, rigidez, cafeína, alcohol, enfermo, y PERCEPCIÓN PERSONAL."""
    
    # === PERCEPCIÓN PERSONAL (25% si está presente) ===
    # Este es el factor clave: cómo TE SIENTES realmente, puede sobreescribir métricas objetivas
    if perceived_readiness is not None:
        perceived_score = perceived_readiness / 10
        perceived_component = 0.25 * perceived_score
        # Reducimos el peso de otros componentes proporcionalmente
        base_weight_multiplier = 0.75  # Los demás componentes suman 75%
    else:
        perceived_component = 0
        base_weight_multiplier = 1.0  # Si no hay percepción, pesos originales
    
    # === RECUPERACIÓN (30% del score si hay percepción, 40% si no) ===
    # Sueño base
    sleep_hours_score = np.clip((sleep_hours - 6.0) / (7.5 - 6.0), 0, 1)
    sleep_quality_score = (sleep_quality - 1) / 4
    
    # Bonus siesta (20-90 min suman)
    nap_bonus = 0
    if nap_mins == 20:
        nap_bonus = 0.05
    elif nap_mins == 45:
        nap_bonus = 0.08
    elif nap_mins == 90:
        nap_bonus = 0.10
    
    # Penalización sueño fragmentado
    disruption_penalty = 0.15 if sleep_disruptions else 0
    
    # Penalización alcohol (afecta recuperación)
    alcohol_penalty = 0.20 if alcohol else 0
    
    sleep_component = base_weight_multiplier * (0.25 * sleep_hours_score + 0.15 * sleep_quality_score + nap_bonus 
                      - disruption_penalty - alcohol_penalty)
    
    # === ESTADO (26% del score si hay percepción, 35% si no) ===
    fatigue_score = 1 - (fatigue / 10)
    stress_score = 1 - (stress / 10)
    energy_score = energy / 10
    soreness_score = 1 - (soreness / 10)
    
    # Rigidez penaliza movilidad (importante para sesiones técnicas)
    stiffness_penalty = (stiffness / 10) * 0.10
    
    state_component = base_weight_multiplier * (0.12 * fatigue_score + 0.08 * stress_score + 
                      0.10 * energy_score + 0.05 * soreness_score - stiffness_penalty)
    
    # === MOTIVACIÓN (11% del score si hay percepción, 15% si no) ===
    motivation_score = motivation / 10
    motivation_component = base_weight_multiplier * 0.15 * motivation_score
    
    # === PENALIZACIONES FLAGS ===
    pain_penalty = 0.25 if pain_flag else 0
    sick_penalty = 0.35 if sick_flag else 0  # Enfermo es muy grave
    
    # Cafeína: si es alta, puede estar enmascarando fatiga
    caffeine_mask = 0
    if caffeine >= 2 and fatigue >= 6:
        caffeine_mask = 0.08  # "te sientes bien pero es cafeína"
    
    # === FÓRMULA FINAL ===
    readiness_0_1 = (perceived_component + sleep_component + state_component + motivation_component 
                    - pain_penalty - sick_penalty - caffeine_mask)
    
    readiness_0_1 = np.clip(readiness_0_1, 0, 1)
    readiness_score = int(round(readiness_0_1 * 100))
    
    return readiness_score


def generate_actionable_plan(readiness, pain_flag, pain_location, fatigue, soreness, session_goal="fuerza"):
    """Genera un plan accionable basado en readiness y condiciones."""
    
    plan = []
    rules = []
    
    if readiness >= 80:
        zone = "Alta"
        emoji = "🟢"
        reco = "Push day"
        intensity_rir = "RIR 1–2 (máximo 1–2 reps de reserva)"
        volume_adjust = "+10% sets en lifts clave"
    elif readiness >= 55:
        zone = "Media"
        emoji = "🟡"
        reco = "Normal"
        intensity_rir = "RIR 2–3 (técnica impecable)"
        volume_adjust = "Mantén volumen, prioriza técnica"
    else:
        zone = "Muy baja"
        emoji = "🔴"
        reco = "Reduce / Deload"
        intensity_rir = "RIR 3–5 (conservador)"
        volume_adjust = "-20% sets, accesorio ligero"
    
    plan.append(f"**Recomendación:** {reco}")
    plan.append(f"**Intensidad:** {intensity_rir}")
    plan.append(f"**Volumen:** {volume_adjust}")
    
    # Reglas concretas
    if readiness >= 80:
        rules.append("✅ Busca PRs o máximos hoy")
        rules.append("✅ Siente libertad de empujar en los 3 últimos sets")
    elif readiness >= 55:
        rules.append("⚖️ Mantén intensidad, cuida forma")
        rules.append("⚖️ Si algo duele, sustituye el ejercicio")
    else:
        rules.append("⛔ Evita RIR≤1 hoy")
        rules.append("⛔ Recorta 1–2 series por ejercicio")
    
    # Pain management
    if pain_flag and pain_location:
        rules.append(f"🩹 Dolor en {pain_location}: evita movimientos bruscos, sustituye si es necesario")
    
    # Fatiga management
    if fatigue >= 7:
        rules.append("😴 Fatiga alta: reduce volumen en 20%, alarga descansos")
    
    # Soreness management
    if soreness >= 7:
        rules.append("🤕 Agujetas: calentamiento largo, movimiento ligero, accesorios >12 reps")
    
    return f"{emoji} {zone}", plan, rules


def save_mood_to_csv(date, sleep_hours, sleep_quality, fatigue, soreness, stress, motivation, pain_flag, pain_location, readiness):
    """Guarda los datos del "Modo Hoy" a un CSV de histórico (para persistencia manual)."""
    mood_data = {
        'date': [date],
        'sleep_hours': [sleep_hours],
        'sleep_quality': [sleep_quality],
        'fatigue': [fatigue],
        'soreness': [soreness],
        'stress': [stress],
        'motivation': [motivation],
        'pain_flag': [pain_flag],
        'pain_location': [pain_location if pain_location else '—'],
        'readiness_instant': [readiness]
    }
    
    df_mood = pd.DataFrame(mood_data)
    mood_path = Path("data/processed/mood_daily.csv")
    
    # Si existe, append; si no, crea
    if mood_path.exists():
        df_existing = pd.read_csv(mood_path)
        df_mood = pd.concat([df_existing, df_mood], ignore_index=True)
    
    df_mood.to_csv(mood_path, index=False)
    return True


def create_readiness_chart(data, title="Readiness"):
    """Crea gráfica de readiness con estilo gaming y gradient."""
    fig = go.Figure()
    
    # Añadir zona de referencia (óptimo)
    fig.add_hrect(y0=75, y1=100, fillcolor="rgba(0, 208, 132, 0.1)", line_width=0, annotation_text="Alta", annotation_position="right")
    fig.add_hrect(y0=55, y1=75, fillcolor="rgba(255, 184, 28, 0.1)", line_width=0, annotation_text="Media", annotation_position="right")
    fig.add_hrect(y0=0, y1=55, fillcolor="rgba(255, 68, 68, 0.1)", line_width=0, annotation_text="Baja", annotation_position="right")
    
    # Línea principal con gradient
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data.values,
        mode='lines+markers',
        name='Readiness',
        line=dict(color='#B266FF', width=3, shape='spline'),
        marker=dict(size=8, color='#B266FF', line=dict(color='#FFFFFF', width=2)),
        fill='tozeroy',
        fillcolor='rgba(178, 102, 255, 0.2)',
        hovertemplate='<b>%{x}</b><br>Readiness: %{y:.0f}/100<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='#B266FF', family='Orbitron')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E0E0E0'),
        xaxis=dict(showgrid=True, gridcolor='rgba(178, 102, 255, 0.1)', zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(178, 102, 255, 0.1)', zeroline=False, range=[0, 105]),
        hovermode='x unified',
        margin=dict(l=40, r=40, t=40, b=40),
        height=300
    )
    
    return fig


def create_volume_chart(data, title="Volumen"):
    """Crea gráfica de volumen con estilo gaming y gradient."""
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data.values,
        mode='lines',
        name='Volumen',
        line=dict(color='#00D084', width=0),
        fill='tozeroy',
        fillcolor='rgba(0, 208, 132, 0.3)',
        hovertemplate='<b>%{x}</b><br>Volumen: %{y:,.0f} kg<extra></extra>'
    ))
    
    # Añadir línea superior para efecto
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data.values,
        mode='lines+markers',
        name='Volumen',
        line=dict(color='#00D084', width=3, shape='spline'),
        marker=dict(size=6, color='#00D084'),
        showlegend=False,
        hovertemplate='<b>%{x}</b><br>Volumen: %{y:,.0f} kg<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='#00D084', family='Orbitron')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E0E0E0'),
        xaxis=dict(showgrid=True, gridcolor='rgba(0, 208, 132, 0.1)', zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(0, 208, 132, 0.1)', zeroline=False),
        hovermode='x unified',
        margin=dict(l=40, r=40, t=40, b=40),
        height=300
    )
    
    return fig


def create_sleep_chart(data, title="Sueño"):
    """Crea gráfica de sueño con barras estilo gaming."""
    fig = go.Figure()
    
    # Zona óptima de sueño
    fig.add_hrect(y0=7, y1=9, fillcolor="rgba(0, 208, 132, 0.1)", line_width=0)
    
    colors = ['#FFB81C' if val < 7 else '#00D084' for val in data.values]
    
    fig.add_trace(go.Bar(
        x=data.index,
        y=data.values,
        name='Sueño',
        marker=dict(
            color=colors,
            line=dict(color='#FFFFFF', width=1)
        ),
        hovertemplate='<b>%{x}</b><br>Sueño: %{y:.1f}h<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='#FFB81C', family='Orbitron')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E0E0E0'),
        xaxis=dict(showgrid=False, zeroline=False),
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
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data.values,
        mode='lines+markers',
        name='ACWR',
        line=dict(color='#FF6B6B', width=3, shape='spline'),
        marker=dict(size=8, color='#FF6B6B', line=dict(color='#FFFFFF', width=2)),
        hovertemplate='<b>%{x}</b><br>ACWR: %{y:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='#FF6B6B', family='Orbitron')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E0E0E0'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255, 107, 107, 0.1)', zeroline=False),
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
    
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data.values,
        mode='lines+markers',
        name='Performance',
        line=dict(color='#4ECDC4', width=3, shape='spline'),
        marker=dict(size=8, color='#4ECDC4', line=dict(color='#FFFFFF', width=2)),
        fill='tozeroy',
        fillcolor='rgba(78, 205, 196, 0.2)',
        hovertemplate='<b>%{x}</b><br>Performance: %{y:.3f}<extra></extra>'
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
    fig.add_trace(go.Scatter(
        x=data.index,
        y=data.values,
        mode='lines+markers',
        name='Strain',
        line=dict(color='#FF6B6B', width=3, shape='spline'),
        marker=dict(size=8, color='#FF6B6B', line=dict(color='#FFFFFF', width=2)),
        fill='tozeroy',
        fillcolor='rgba(255, 107, 107, 0.18)',
        hovertemplate='<b>%{x}</b><br>Strain: %{y:,.0f}<extra></extra>'
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='#FF6B6B', family='Orbitron')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E0E0E0'),
        xaxis=dict(showgrid=True, gridcolor='rgba(255, 107, 107, 0.12)', zeroline=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255, 107, 107, 0.12)', zeroline=False, range=[0, y_max]),
        hovermode='x unified',
        margin=dict(l=40, r=40, t=40, b=40),
        height=300
    )
    return fig


def create_weekly_volume_chart(data, title="Volumen Semanal"):
    """Bar chart semanal para ver claro un único punto o pocos puntos."""
    fig = go.Figure()
    x = [d.strftime("%Y-%m-%d") for d in data.index]  # Convert to string for categorical axis
    fig.add_trace(go.Bar(
        x=x,
        y=data.values,
        marker_color='#00D084',
        marker_line=dict(color='#FFFFFF', width=1),
        hovertemplate='<b>%{x}</b><br>Volumen: %{y:,.0f} kg<extra></extra>'
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='#00D084', family='Orbitron')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E0E0E0'),
        xaxis=dict(type='category', showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(0, 208, 132, 0.12)', zeroline=False),
        bargap=0.6,
        hovermode='x unified',
        margin=dict(l=40, r=40, t=40, b=40),
        height=300
    )
    return fig


def create_weekly_strain_chart(data, title="Strain"):
    """Bar chart semanal para strain, útil con muestras cortas."""
    fig = go.Figure()
    x = [d.strftime("%Y-%m-%d") for d in data.index]  # Convert to string for categorical axis
    fig.add_trace(go.Bar(
        x=x,
        y=data.values,
        marker_color='#FF6B6B',
        marker_line=dict(color='#FFFFFF', width=1),
        hovertemplate='<b>%{x}</b><br>Strain: %{y:,.0f}<extra></extra>'
    ))
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color='#FF6B6B', family='Orbitron')),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#E0E0E0'),
        xaxis=dict(type='category', showgrid=False),
        yaxis=dict(showgrid=True, gridcolor='rgba(255, 107, 107, 0.12)', zeroline=False),
        bargap=0.6,
        hovermode='x unified',
        margin=dict(l=40, r=40, t=40, b=40),
        height=300
    )
    return fig


def render_section_title(text, accent="#B266FF"):
    """Renderiza títulos de sección con el mismo look & feel de las gráficas."""
    st.markdown(f"""
    <div class="section-title" style="--accent: {accent};">
        <div class="section-pill"></div>
        <span>{text}</span>
    </div>
    """, unsafe_allow_html=True)


def calculate_injury_risk_score_v2(
    readiness_score, acwr, sleep_hours, performance_index, effort_level,
    pain_flag=False, pain_severity=0, stiffness=0, sick_flag=False, 
    last_hard=False, baselines=None, days_high_strain=0
):
    """Versión mejorada con pain_severity, stiffness, sick_flag."""
    # calculate_injury_risk_score ya está importado al inicio del archivo
    
    # Usar función base
    base_risk = calculate_injury_risk_score(
        readiness_score, acwr, sleep_hours, performance_index, effort_level,
        pain_flag, baselines, days_high_strain
    )
    
    # Añadir factores nuevos
    extra_score = 0
    extra_factors = []
    
    # Pain severity (más severo = más riesgo)
    if pain_severity >= 7:
        extra_score += 15
        extra_factors.append(f'Dolor severo ({pain_severity}/10)')
    elif pain_severity >= 5:
        extra_score += 8
        extra_factors.append(f'Dolor moderado ({pain_severity}/10)')
    
    # Stiffness (rigidez alta = movilidad limitada)
    if stiffness >= 7:
        extra_score += 10
        extra_factors.append(f'Rigidez articular alta ({stiffness}/10)')
    
    # Sick flag (enfermo = riesgo altísimo)
    if sick_flag:
        extra_score += 25
        extra_factors.append('⚠️ Estado de enfermedad detectado')
    
    # Last hard session (fatiga acumulada)
    if last_hard:
        extra_score += 8
        extra_factors.append('Último entreno muy exigente (48h)')
    
    # Combinar
    new_score = min(base_risk['score'] + extra_score, 100)
    
    # Re-clasificar
    if new_score >= 60:
        level = 'high'
        emoji = '🔴'
        action = 'DELOAD OBLIGATORIO. Reduce volumen -30%, evita máximos.'
    elif new_score >= 35:
        level = 'medium'
        emoji = '🟡'
        action = 'Precaución. Entrena pero sin buscar máximos. Foco en técnica.'
    else:
        level = 'low'
        emoji = '🟢'
        action = 'Bajo riesgo. Puedes entrenar normal.'
    
    return {
        'risk_level': level,
        'score': new_score,
        'emoji': emoji,
        'factors': base_risk['factors'] + extra_factors,
        'confidence': base_risk['confidence'],
        'action': action
    }


def generate_actionable_plan_v2(
    readiness, pain_flag, pain_zone, pain_severity, pain_type,
    fatigue, soreness, stiffness, sick_flag, session_goal, fatigue_analysis
):
    """Versión mejorada: genera plan ultra-específico con pain_zone y fatigue_type."""
    
    plan = []
    rules = []
    zone_display = ""
    
    # Override si enfermo
    if sick_flag:
        zone_display = "ENFERMO - NO ENTRENAR"
        plan.append("🤒 **Estado**: Enfermo detectado")
        plan.append("⛔ **Recomendación**: DESCANSO TOTAL hasta recuperación")
        plan.append("💊 Prioriza: hidratación, sueño, nutrición")
        rules.append("❌ NO entrenar bajo ninguna circunstancia")
        rules.append("❌ Evita ejercicio hasta estar 100% sano")
        return zone_display, plan, rules
    
    # Clasificar readiness
    if readiness >= 80:
        zone_display = "🟢 ALTA"
        reco = "Push day - busca PRs"
        intensity_rir = "RIR 1–2"
        volume_adjust = "+10% sets"
    elif readiness >= 55:
        zone_display = "🟡 MEDIA"
        reco = "Normal - mantén técnica"
        intensity_rir = "RIR 2–3"
        volume_adjust = "Volumen estándar"
    else:
        zone_display = "🔴 BAJA"
        reco = "Deload - reduce carga"
        intensity_rir = "RIR 3–5"
        volume_adjust = "-20% sets"
    
    plan.append(f"**Zona**: {zone_display}")
    plan.append(f"**Recomendación base**: {reco}")
    plan.append(f"**Intensidad**: {intensity_rir}")
    plan.append(f"**Volumen**: {volume_adjust}")
    
    # Adaptar por tipo de fatiga
    plan.append("")
    plan.append(f"**Tipo de fatiga**: {fatigue_analysis['type'].upper()}")
    plan.append(f"**Split recomendado**: {fatigue_analysis['target_split'].upper()}")
    
    # Dolor localizado - RECOMENDACIONES MUY ESPECÍFICAS
    if pain_flag and pain_zone:
        plan.append("")
        plan.append(f"🩹 **Dolor detectado**: {pain_zone} ({pain_severity}/10, {pain_type})")
        
        # Mapear zona → ejercicios evitar/OK
        avoid_movements = []
        ok_movements = []
        
        if pain_zone in ["Hombro"]:
            avoid_movements = ["Press banca", "Press militar", "Fondos", "Dominadas"]
            ok_movements = ["Sentadilla", "Peso muerto", "Curl piernas", "Prensa"]
        elif pain_zone in ["Codo", "Muñeca"]:
            avoid_movements = ["Press banca agarre cerrado", "Curl", "Extensiones tríceps"]
            ok_movements = ["Pierna completa", "Sentadilla", "Peso muerto (trap bar)"]
        elif pain_zone in ["Espalda baja"]:
            avoid_movements = ["Peso muerto convencional", "Buenos días", "Sentadilla baja"]
            ok_movements = ["Prensa", "Extensiones cuádriceps", "Curl femoral", "Press banca"]
        elif pain_zone in ["Rodilla"]:
            avoid_movements = ["Sentadilla profunda", "Extensiones", "Saltos"]
            ok_movements = ["Tren superior completo", "Curl femoral (con precaución)"]
        elif pain_zone in ["Tobillo"]:
            avoid_movements = ["Sentadilla", "Peso muerto", "Gemelos de pie"]
            ok_movements = ["Tren superior", "Prensa (ángulo reducido)"]
        else:
            avoid_movements = ["Movimientos que generen dolor"]
            ok_movements = ["Patrones opuestos a la zona afectada"]
        
        plan.append(f"❌ **Evita hoy**: {', '.join(avoid_movements)}")
        plan.append(f"✅ **Puedes hacer**: {', '.join(ok_movements)}")
        
        if pain_severity >= 7:
            plan.append(f"⚠️ **Severidad alta**: considera fisio o valoración médica")
    
    # Rigidez articular
    if stiffness >= 7:
        plan.append("")
        plan.append(f"🦴 **Rigidez alta** ({stiffness}/10): añade +15 min calentamiento")
        plan.append("🔥 Foam roll + movilidad dinámica obligatoria")
    
    # === REGLAS BASE (siempre visibles) ===
    rules.append("✅ Calienta progresivamente (5-10 min mínimo)")
    rules.append("✅ Respeta RIR indicado, no lo fuerces")
    rules.append("✅ Hidratación constante durante sesión")
    
    # Reglas específicas según condiciones
    if pain_flag and pain_severity >= 5:
        rules.append(f"❌ STOP inmediato si dolor {pain_zone} empeora durante ejercicio")
        rules.append("✅ Movilidad suave post-sesión (15 min)")
    
    if fatigue >= 8:
        rules.append("⚠️ Fatiga muy alta: reduce volumen -30% mínimo")
        rules.append("⚠️ Si empiezas a notar mareo/náusea, termina sesión")
    
    if stiffness >= 7:
        rules.append("🧊 Considera terapia de frío/calor pre-sesión")
        rules.append("⚠️ No fuerces ROM (rango de movimiento) limitado")
    
    if readiness < 55:
        rules.append("⚠️ Prioriza técnica sobre carga hoy")
        rules.append("✅ Reduce tempo (más lento = menos estrés CNS)")
    
    return zone_display, plan, rules


def main():
    st.set_page_config(page_title="Trainer Readiness Dashboard", layout="wide")
    
    # Custom CSS + hero to que todo respire como las gráficas
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
        
        :root {
            --bg: #07090f;
            --panel: #0f1420;
            --panel-2: #111827;
            --purple: #B266FF;
            --green: #00D084;
            --aqua: #4ECDC4;
            --coral: #FF6B6B;
            --amber: #FFB81C;
            --text: #E0E0E0;
            --muted: #9CA3AF;
        }
        
        .main {
            background: radial-gradient(circle at 20% 20%, rgba(178, 102, 255, 0.08), transparent 20%),
                        radial-gradient(circle at 80% 0%, rgba(0, 208, 132, 0.08), transparent 25%),
                        linear-gradient(180deg, #0b0e14 0%, #07090f 80%);
            color: var(--text);
        }
        
        /* Hero */
        .hero {
            background: linear-gradient(135deg, rgba(178, 102, 255, 0.12), rgba(0, 208, 132, 0.08));
            border: 1px solid rgba(178, 102, 255, 0.25);
            border-radius: 12px;
            padding: 18px 20px;
            margin-bottom: 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.25);
        }
        .hero h1 {
            font-family: 'Orbitron', sans-serif;
            color: var(--text);
            text-shadow: 0 0 16px rgba(178, 102, 255, 0.25);
            margin: 0;
            font-size: 2.1em;
            letter-spacing: 0.04em;
        }
        .hero .eyebrow {
            text-transform: uppercase;
            color: var(--muted);
            letter-spacing: 0.2em;
            font-size: 0.8em;
            margin: 0 0 4px 0;
        }
        .hero .sub {
            color: var(--muted);
            margin: 6px 0 0 0;
        }
        .hero .badge-row {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        }
        .badge {
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 0.85em;
            font-weight: 700;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            color: #0b0e11;
            background: linear-gradient(135deg, var(--green), #00c070);
            box-shadow: 0 0 14px rgba(0, 208, 132, 0.3);
        }
        .badge.purple { background: linear-gradient(135deg, var(--purple), #8f4dff); color: #f8f8ff; box-shadow: 0 0 14px rgba(178, 102, 255, 0.35); }
        .badge.coral { background: linear-gradient(135deg, var(--coral), #ff7f7f); color: #fff; box-shadow: 0 0 14px rgba(255, 107, 107, 0.35); }
        .badge.aqua { background: linear-gradient(135deg, var(--aqua), #27d7c4); color: #0b0e11; box-shadow: 0 0 14px rgba(78, 205, 196, 0.35); }
        
        /* Section titles */
        .section-title {
            display: flex;
            align-items: center;
            gap: 10px;
            font-family: 'Orbitron', sans-serif;
            color: var(--text);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-size: 1.25em;
            margin: 20px 0 12px 0;
        }
        .section-title .section-pill {
            width: 36px;
            height: 6px;
            border-radius: 999px;
            background: linear-gradient(90deg, var(--accent), rgba(255,255,255,0));
            box-shadow: 0 0 16px rgba(178, 102, 255, 0.35);
        }
        .section-title span {
            color: var(--accent);
            text-shadow: 0 0 12px rgba(178, 102, 255, 0.35);
        }
        
        /* Panels */
        [data-testid="stSidebar"] {
            background: #0f1420;
            border-right: 1px solid rgba(178, 102, 255, 0.18);
            color: var(--text);
        }
        .sidebar-title {
            font-family: 'Orbitron', sans-serif;
            color: var(--purple);
            letter-spacing: 0.08em;
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 10px;
        }
        
        /* Metric styling */
        [data-testid="metric-container"] {
            background: linear-gradient(135deg, #161d2b 0%, #1f1630 100%);
            border: 1px solid rgba(0, 208, 132, 0.2);
            border-radius: 10px;
            padding: 16px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.25);
        }
        
        /* Alert boxes */
        [data-testid="stAlert"] {
            border-left: 4px solid var(--amber);
            border-radius: 8px;
            background: rgba(255, 184, 28, 0.12);
        }
        
        /* Info boxes */
        [data-testid="stInfo"] {
            border-left: 4px solid var(--green);
            border-radius: 8px;
            background: rgba(0, 208, 132, 0.12);
        }
        
        /* Sidebar radio tweaks */
        .stRadio label {
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 0.03em;
        }
        
        /* Button styling */
        button, .stButton>button {
            border-radius: 8px;
            background: linear-gradient(135deg, var(--green) 0%, #00c070 100%);
            color: #0B0E11;
            border: none;
            font-weight: 800;
            letter-spacing: 0.04em;
            transition: 0.25s ease;
        }
        
        button:hover, .stButton>button:hover {
            box-shadow: 0 0 18px rgba(0, 208, 132, 0.55);
            transform: translateY(-1px);
        }
        
        /* Divider */
        hr {
            border: none;
            border-top: 1px solid rgba(178, 102, 255, 0.18);
            margin: 18px 0;
        }
        
        /* Text styling */
        p, label, span {
            color: var(--text);
        }
        
        /* Caption */
        .caption {
            color: var(--muted);
            font-size: 0.85em;
        }
        
        /* DataFrames and Tables - Gaming Style */
        [data-testid="stDataFrame"] {
            border: 1px solid rgba(178, 102, 255, 0.25) !important;
            border-radius: 8px !important;
            overflow: hidden !important;
            box-shadow: 0 0 20px rgba(178, 102, 255, 0.15) !important;
            background: linear-gradient(135deg, #0f1420 0%, #1a1530 100%) !important;
        }
        
        /* Table header styling */
        [data-testid="stDataFrame"] thead {
            background: linear-gradient(90deg, rgba(178, 102, 255, 0.3), rgba(0, 208, 132, 0.1)) !important;
            border-bottom: 2px solid rgba(178, 102, 255, 0.4) !important;
        }
        
        [data-testid="stDataFrame"] thead th {
            color: #E0E0E0 !important;
            font-weight: 700 !important;
            font-family: 'Orbitron', sans-serif !important;
            letter-spacing: 0.05em !important;
            padding: 14px 10px !important;
            text-transform: uppercase !important;
            font-size: 0.85em !important;
            border-right: 1px solid rgba(178, 102, 255, 0.2) !important;
            text-shadow: 0 0 8px rgba(178, 102, 255, 0.25) !important;
            background: linear-gradient(180deg, rgba(178, 102, 255, 0.25), rgba(178, 102, 255, 0.1)) !important;
        }
        
        [data-testid="stDataFrame"] thead th:last-child {
            border-right: none !important;
        }
        
        /* Table rows styling */
        [data-testid="stDataFrame"] tbody tr {
            border-bottom: 1px solid rgba(178, 102, 255, 0.12) !important;
            transition: all 0.2s ease !important;
        }
        
        [data-testid="stDataFrame"] tbody tr:nth-child(odd) {
            background-color: rgba(15, 20, 32, 0.5) !important;
        }
        
        [data-testid="stDataFrame"] tbody tr:nth-child(even) {
            background-color: rgba(26, 21, 48, 0.3) !important;
        }
        
        [data-testid="stDataFrame"] tbody tr:hover {
            background-color: rgba(178, 102, 255, 0.12) !important;
            box-shadow: inset 0 0 15px rgba(178, 102, 255, 0.1) !important;
        }
        
        /* Table cells styling */
        [data-testid="stDataFrame"] td {
            color: var(--text) !important;
            padding: 12px 10px !important;
            font-size: 0.9em !important;
            border-right: 1px solid rgba(178, 102, 255, 0.08) !important;
        }
        
        [data-testid="stDataFrame"] td:last-child {
            border-right: none !important;
        }
        
        /* Colored cells (readiness_score) */
        [data-testid="stDataFrame"] td[style*="background-color: #00D084"] {
            background-color: rgba(0, 208, 132, 0.25) !important;
            color: #00D084 !important;
            font-weight: 700 !important;
            text-shadow: 0 0 8px rgba(0, 208, 132, 0.4) !important;
            box-shadow: inset 0 0 12px rgba(0, 208, 132, 0.1) !important;
        }
        
        [data-testid="stDataFrame"] td[style*="background-color: #FFB81C"] {
            background-color: rgba(255, 184, 28, 0.2) !important;
            color: #FFB81C !important;
            font-weight: 700 !important;
            text-shadow: 0 0 8px rgba(255, 184, 28, 0.4) !important;
            box-shadow: inset 0 0 12px rgba(255, 184, 28, 0.08) !important;
        }
        
        [data-testid="stDataFrame"] td[style*="background-color: #FF4444"] {
            background-color: rgba(255, 68, 68, 0.2) !important;
            color: #FF6B6B !important;
            font-weight: 700 !important;
            text-shadow: 0 0 8px rgba(255, 107, 107, 0.4) !important;
            box-shadow: inset 0 0 12px rgba(255, 107, 107, 0.08) !important;
        }
        
        /* Scrollbar styling */
        [data-testid="stDataFrame"] ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        
        [data-testid="stDataFrame"] ::-webkit-scrollbar-track {
            background: rgba(178, 102, 255, 0.05);
            border-radius: 10px;
        }
        
        [data-testid="stDataFrame"] ::-webkit-scrollbar-thumb {
            background: linear-gradient(180deg, #B266FF, #00D084);
            border-radius: 10px;
            box-shadow: 0 0 10px rgba(178, 102, 255, 0.3);
        }
        
        [data-testid="stDataFrame"] ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(180deg, #00D084, #B266FF);
            box-shadow: 0 0 15px rgba(0, 208, 132, 0.4);
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown("""
    <div class="hero">
        <div>
            <p class="eyebrow">Adventure Mode</p>
            <h1>Trainer — Readiness</h1>
            <p class="sub">Decide tu plan del día con las mismas vibes que las gráficas.</p>
        </div>
        <div class="badge-row">
            <span class="badge purple">Readiness</span>
            <span class="badge">Volumen</span>
            <span class="badge aqua">Sueño</span>
            <span class="badge coral">ACWR</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    daily_path = Path("data/processed/daily.csv")
    reco_path = Path("data/processed/recommendations_daily.csv")
    daily_ex_path = Path("data/processed/daily_exercise.csv")
    weekly_path = Path("data/processed/weekly.csv")

    # Load main data files
    df_metrics = None
    df_recommendations = None
    
    try:
        df_metrics = load_csv(daily_path)  # daily.csv solo tiene métricas base
    except FileNotFoundError:
        st.warning("❌ Falta daily.csv. Ejecuta el `pipeline` primero.")
        st.stop()
    
    try:
        df_recommendations = load_csv(reco_path)  # recommendations_daily.csv contiene TODO: métricas + readiness + recomendaciones
    except FileNotFoundError:
        st.warning("❌ Falta recommendations_daily.csv. Ejecuta `decision_engine` primero.")
        st.stop()

    # Usar directamente recommendations_daily.csv como df_daily (ya tiene todas las columnas)
    df_daily = df_recommendations.copy()
    df_daily['date'] = pd.to_datetime(df_daily['date']).dt.date

    # Load optional files
    df_exercises = None
    try:
        df_exercises = load_csv(daily_ex_path)
    except:
        pass

    df_weekly = None
    try:
        df_weekly = load_csv(weekly_path)
    except:
        pass

    # Sidebar: view selector (day/week/today)
    st.sidebar.markdown("<div class='sidebar-title'>Configuración</div>", unsafe_allow_html=True)
    view_mode = st.sidebar.radio("Vista", ["Día", "Modo Hoy", "Semana"])

    # Sidebar: date range filter - Solo mostrar en modo Día
    dates = sorted(df_daily['date'].unique())
    if dates:
        max_date = dates[-1]
        min_date = max_date - datetime.timedelta(days=6)  # Última semana (7 días)
        # Si no hay datos hace 7 días, mostrar todos
        if min_date < dates[0]:
            min_date = dates[0]
    else:
        min_date = max_date = datetime.date.today()

    if view_mode == "Día":
        st.sidebar.markdown("### Filtro de fechas")
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input("Desde", value=min_date, key="start_date")
        with col2:
            end_date = st.date_input("Hasta", value=max_date, key="end_date")
        df_filtered = df_daily[(df_daily['date'] >= start_date) & (df_daily['date'] <= end_date)].copy()
    else:
        start_date = min_date
        end_date = max_date
        df_filtered = df_daily[(df_daily['date'] >= start_date) & (df_daily['date'] <= end_date)].copy()

    # Date selector - Por defecto selecciona hoy o la última fecha disponible
    dates_filtered = sorted(df_filtered['date'].unique(), reverse=True)
    today = datetime.date.today()
    default_date = today if today in dates_filtered else (dates_filtered[0] if dates_filtered else None)
    
    if view_mode == "📅 Día":
        selected_date = st.sidebar.selectbox("Selecciona fecha", options=dates_filtered, 
                                            index=dates_filtered.index(default_date) if default_date in dates_filtered else 0) if dates_filtered else None
    else:
        selected_date = default_date

    # ============== DAY VIEW ==============
    if view_mode == "📅 Día":
        render_section_title(f"Panel Diario — {selected_date}", accent="#B266FF")
        
        if selected_date is None:
            st.info("No hay datos para mostrar.")
        else:
            row = df_filtered[df_filtered['date'] == selected_date]
            if row.empty:
                st.info("No hay datos para la fecha seleccionada.")
            else:
                r = row.iloc[0]
                readiness = r.get('readiness_score', None)
                zone, emoji, color = get_readiness_zone(readiness)
                
                # ALERTS
                alerts = []
                if get_anti_fatigue_flag(df_daily, selected_date):
                    alerts.append("⚠️ **Consecutivos de alta exigencia**: considera descanso parcial hoy")
                if pd.notna(r.get('sleep_hours', None)) and r['sleep_hours'] < 6.5:
                    alerts.append("😴 **Sueño bajo**: reduce volumen hoy")
                if pd.notna(r.get('acwr_7_28', None)) and r['acwr_7_28'] > 1.5:
                    alerts.append("📈 **Carga aguda muy alta**: evita máximos hoy")
                
                for alert in alerts:
                    st.warning(alert)
                
                # READINESS WITH ZONE
                col1, col2, col3, col4 = st.columns([1.5, 1.2, 1.2, 1.2])
                
                with col1:
                    readiness_text = f"{emoji} {int(readiness) if pd.notna(readiness) else 'N/D'}/100"
                    st.markdown(f"### {readiness_text}")
                    st.markdown(f"*{zone}*")
                
                perf = r.get('performance_index', None)
                acwr = r.get('acwr_7_28', None)
                sleep_h = r.get('sleep_hours', None)
                
                with col2:
                    st.metric("Performance", f"{round(perf, 3)}" if pd.notna(perf) else "—")
                with col3:
                    days_avail = get_days_until_acwr(df_daily, selected_date)
                    acwr_display = format_acwr_display(acwr, days_avail)
                    st.metric("ACWR", acwr_display)
                with col4:
                    st.metric("Sueño", f"{round(sleep_h, 1)}h" if pd.notna(sleep_h) else "—")
                
                # CONFIDENCE PANEL
                conf_text, conf_emoji = get_confidence_level(df_daily, selected_date)
                st.info(f"{conf_emoji} **Confianza del modelo:** {conf_text}")
                
                # RECOMMENDATION
                render_section_title("Recomendación", accent="#FFB81C")
                reco = r.get('recommendation', 'N/D')
                action = r.get('action_intensity', 'N/D')
                st.markdown(f"### {reco} — {action}")
                
                # REASON CODES AS BULLETS
                reason_codes = r.get('reason_codes', '')
                reasons = format_reason_codes(reason_codes)
                if reasons:
                    st.write("**Por qué:**")
                    for reason in reasons:
                        st.write(f"• {reason}")
                
                explanation = r.get('explanation', '')
                if explanation and explanation != '':
                    st.write(f"**Detalles:** {explanation}")
                
                # LIFT RECOMMENDATIONS
                if df_exercises is not None:
                    df_lifts = load_daily_exercise_for_date(daily_ex_path, selected_date)
                    if not df_lifts.empty:
                        render_section_title("Qué hacer hoy", accent="#00D084")
                        st.write("**Lifts clave - plan accionable:**")
                        lift_recs = get_lift_recommendations(df_lifts, readiness, zone)
                        for rec in lift_recs:
                            st.markdown(rec)
                        
                        # Expander con explicación
                        with st.expander("Cómo interpretar estas recomendaciones"):
                            st.write("""
- **Intensidad**: porcentaje de carga o reps en reserva (RIR)
- **Volumen**: sets totales en el lift principal
- **RIR**: repeticiones que podrías hacer más (RIR2 = 2 reps más hasta fallo)

**Zona Alta (Readiness ≥75)**: tu cuerpo está listo, busca progreso
**Zona Media (55–74)**: mantén técnica impecable, evita máximos
**Zona Muy Baja (<55)**: técnica y movimiento, descarga obligatoria
                            """)


    # ============== MODE TODAY (INSTANT) ==============
    elif view_mode == "Modo Hoy":
        render_section_title("Modo Hoy — Ready Check", accent="#B266FF")
        st.write("Introduce cómo te sientes **ahora mismo** y obtén recomendaciones instantáneas.")
        
        # UI helpers: badges + button styling
        st.markdown(
            """
            <style>
            .badge {display:inline-block;padding:2px 8px;border-radius:8px;font-size:0.8rem;margin-left:6px}
            .badge-green{background:#00D08420;color:#00D084;border:1px solid #00D084}
            .badge-yellow{background:#FFB81C20;color:#FFB81C;border:1px solid #FFB81C}
            .badge-red{background:#FF6B6B20;color:#FF6B6B;border:1px solid #FF6B6B}
            div[data-testid="stFormSubmitButton"] button, .stButton>button{
              background:linear-gradient(90deg,#00D084,#4ECDC4);color:#0b0b0b;font-weight:700;border:0;border-radius:8px}
            </style>
            """,
            unsafe_allow_html=True,
        )
        
        def _badge(text:str, level:str):
            cls = {"ok":"badge-green","mid":"badge-yellow","low":"badge-red"}.get(level,"badge-yellow")
            st.markdown(f"<span class='badge {cls}'>{text}</span>", unsafe_allow_html=True)
        
        def _sleep_h_level(h:float):
            if h >= 7.5: return ("Excelente", "ok")
            if h >= 6.5: return ("Moderado", "mid")
            return ("Crítico", "low")
        def _sleep_q_level(q:int):
            mapping = {1:("Muy malo","low"),2:("Malo","mid"),3:("Regular","mid"),4:("Bueno","ok"),5:("Perfecto","ok")}
            return mapping.get(q,("Regular","mid"))
        def _fatigue_level(x:int):
            if x <= 3: return ("Baja","ok")
            if x <= 6: return ("Media","mid")
            return ("Alta","low")
        def _stress_level(x:int):
            if x <= 3: return ("Bajo","ok")
            if x <= 6: return ("Medio","mid")
            return ("Alto","low")
        def _soreness_level(x:int):
            if x <= 2: return ("Ligera","ok")
            if x <= 5: return ("Moderada","mid")
            return ("Alta","low")
        def _energy_level(x:int):
            if x >= 7: return ("Alta","ok")
            if x >= 4: return ("Media","mid")
            return ("Baja","low")
        def _perceived_level(val):
            if val >= 8: return ("Me siento genial", "ok")
            elif val >= 6: return ("Me siento bien", "mid")
            elif val >= 4: return ("Regular", "mid")
            else: return ("Me siento mal", "low")
        
        # === CARGAR PERFIL PERSONALIZADO ===
        user_profile = load_user_profile()
        
        # Mostrar insights personalizados si hay
        if user_profile.get('insights') and user_profile['data_quality'].get('total_days', 0) > 7:
            with st.expander("Tu Perfil Personal", expanded=False):
                col_arch, col_sleep = st.columns(2)
                
                with col_arch:
                    archetype = user_profile.get('archetype', {})
                    if archetype.get('confidence', 0) > 0.5:
                        st.markdown(f"**Arquetipo:** {archetype.get('archetype', '?').upper()}")
                        st.caption(f"{archetype.get('reason', '')}")
                        st.caption(f"Confianza: {archetype.get('confidence', 0):.0%}")
                
                with col_sleep:
                    sleep_resp = user_profile.get('sleep_responsiveness', {})
                    if sleep_resp.get('sleep_responsive') is not None:
                        st.markdown(f"**Sueño te afecta:** {'Mucho ✅' if sleep_resp['sleep_responsive'] else 'Poco ⚠️'}")
                        st.caption(f"Correlación: {sleep_resp.get('correlation', 0):.2f}")
                
                # Mostrar insights clave
                st.markdown("**Insights:**")
                for insight in user_profile.get('insights', []):
                    st.write(f"• {insight}")
                
                # Mostrar adjustment factors
                factors = user_profile.get('adjustment_factors', {})
                if factors:
                    st.markdown("**Factores de personalización:**")
                    col_f1, col_f2, col_f3 = st.columns(3)
                    with col_f1:
                        st.metric("Sleep Weight", f"{factors.get('sleep_weight', 0.25):.2f}", 
                                 delta=f"{factors.get('sleep_weight', 0.25) - 0.25:+.2f} vs default")
                    with col_f2:
                        st.metric("Performance Weight", f"{factors.get('performance_weight', 0.25):.2f}",
                                 delta=f"{factors.get('performance_weight', 0.25) - 0.25:+.2f} vs default")
                    with col_f3:
                        st.metric("Fatigue Sensitivity", f"{factors.get('fatigue_sensitivity', 1.0):.2f}x",
                                 delta=f"{factors.get('fatigue_sensitivity', 1.0) - 1.0:+.2f}x vs normal")
        
        # Modo toggle
        col_mode, col_reset = st.columns([3, 1])
        with col_mode:
            input_mode = st.radio("", ["▸ Modo Rápido (20s)", "▸ Modo Completo"], horizontal=True, key="input_mode_selector")
        with col_reset:
            if st.button("🔄 Reset"):
                for key in list(st.session_state.keys()):
                    if key.startswith('mood_'):
                        del st.session_state[key]
                st.rerun()
        
        quick_mode = "Rápido" in input_mode
        
        # === BLOQUE A: RECUPERACIÓN ===
        render_section_title("A. Recuperación", accent="#00D084")
        col_rec1, col_rec2, col_rec3 = st.columns(3)
        
        with col_rec1:
            sleep_h = st.number_input("Horas de sueño ⏰", min_value=0.0, max_value=12.0, value=st.session_state.get('mood_sleep_h', 7.5), step=0.5,
                                     help="Horas totales de sueño en las últimas 24h", key="input_sleep_h")
            st.caption("Más horas = mejor recuperación")
            txt, lvl = _sleep_h_level(sleep_h)
            _badge(txt, lvl)
        
        with col_rec2:
            sleep_q = st.slider("Calidad del sueño", 1, 5, st.session_state.get('mood_sleep_q', 4), 
                               help="1=Muy malo (despertares constantes), 5=Perfecto", key="input_sleep_q")
            quality_labels = {1: "Horrible", 2: "Malo", 3: "Regular", 4: "Bueno", 5: "Perfecto"}
            st.caption("Fatiga alta puede reducir tu readiness")
            txt, lvl = _sleep_q_level(sleep_q)
            _badge(txt, lvl)
            
        with col_rec3:
            if not quick_mode:
                nap_mins = st.selectbox("Siesta hoy", [0, 20, 45, 90], 
                                       index=[0, 20, 45, 90].index(st.session_state.get('mood_nap_mins', 0)),
                                       help="Minutos de siesta. 20=power nap, 90=ciclo completo", key="input_nap")
                sleep_disruptions = st.checkbox("Sueño fragmentado (3+ despertares)", 
                                               value=st.session_state.get('mood_sleep_disruptions', False), key="input_disruptions")
            else:
                nap_mins = 0
                sleep_disruptions = False
            
        # === BLOQUE B: ESTADO (SENSACIONES) ===
        st.write("")
        render_section_title("B. Estado", accent="#FFB81C")
        
        # PERCEPCIÓN PERSONAL (nuevo input clave)
        st.markdown("**● Sensación Personal** — Cómo te sientes realmente")
        perceived_readiness = st.slider(
            "De 0 (fatal) a 10 (increíble)", 0, 10, 
            st.session_state.get('mood_perceived_readiness', 7),
            help="Tu percepción general HOY. Puede no coincidir con métricas objetivas (ej: dormiste poco pero te sientes bien). Esto tiene un peso del 25% en el cálculo.",
            key="input_perceived_readiness"
        )
        txt, lvl = _perceived_level(perceived_readiness)
        _badge(txt, lvl)
        st.write("")
        
        col_st1, col_st2, col_st3, col_st4 = st.columns(4)
        
        with col_st1:
            fatigue = st.slider("Fatiga/Cansancio", 0, 10, st.session_state.get('mood_fatigue', 3), 
                               help="0=Fresco, 5=Normal, >=7 afecta rendimiento", key="input_fatigue")
            txt, lvl = _fatigue_level(fatigue)
            _badge(txt, lvl)
        
        with col_st2:
            stress = st.slider("Estrés mental", 0, 10, st.session_state.get('mood_stress', 3), 
                              help="0=Relajado, >=7 suele bajar rendimiento en básicos", key="input_stress")
            txt, lvl = _stress_level(stress)
            _badge(txt, lvl)
        
        with col_st3:
            soreness = st.slider("Agujetas/DOMS", 0, 10, st.session_state.get('mood_soreness', 2), 
                                help="Dolor muscular general post-entreno", key="input_soreness")
            txt, lvl = _soreness_level(soreness)
            _badge(txt, lvl)
        
        with col_st4:
            if not quick_mode:
                energy = st.slider("Energía general", 0, 10, st.session_state.get('mood_energy', 7), 
                                  help="Sensación de vitalidad (a veces 'fatiga' no captura todo)", key="input_energy")
                txt, lvl = _energy_level(energy)
                _badge(txt, lvl)
            else:
                energy = 10 - fatigue  # Derivar del fatigue
            
        # Fila 2 de Estado (solo modo completo)
        if not quick_mode:
            col_st5, col_st6, col_st7, col_st8 = st.columns(4)
            
            with col_st5:
                motivation = st.slider("Motivación/Ganas", 0, 10, st.session_state.get('mood_motivation', 7), 
                                      help="0=Ninguna, 10=Máxima", key="input_motivation")
                st.caption(f"🔥 {motivation}/10")
            
            with col_st6:
                stiffness = st.slider("Rigidez articular", 0, 10, st.session_state.get('mood_stiffness', 2), 
                                     help="Movilidad limitada, calentar costará más", key="input_stiffness")
                st.caption(f"🦴 {stiffness}/10")
            
            with col_st7:
                caffeine = st.selectbox("Cafeína (últimas 6h)", [0, 1, 2, 3], 
                                       index=st.session_state.get('mood_caffeine', 0),
                                       help="Cafés/energéticos consumidos", key="input_caffeine")
                st.caption(f"☕ {caffeine} dosis")
            
            with col_st8:
                alcohol = st.checkbox("Alcohol anoche", 
                                     value=st.session_state.get('mood_alcohol', False),
                                     help="Consumo de alcohol en las últimas 12-24h", key="input_alcohol")
        else:
            motivation = 7
            stiffness = 2
            caffeine = 0
            alcohol = False
            
        # === BLOQUE C: FLAGS (BANDERAS ROJAS) ===
        st.write("")
        render_section_title("C. Flags / Banderas Rojas", accent="#FF6B6B")
        alert_card = "border-radius:12px;padding:12px;margin-bottom:8px;background:rgba(255,107,107,0.06);border-left:4px solid #FF6B6B;"
        st.markdown(f"<div style='{alert_card}'>⚠️ Revisa estas señales antes de decidir la intensidad.</div>", unsafe_allow_html=True)
        
        col_flag1, col_flag2, col_flag3 = st.columns(3)
        
        with col_flag1:
            st.write("**🩹 Dolor localizado**")
            pain_flag = st.checkbox("Tengo dolor localizado", value=st.session_state.get('mood_pain_flag', False), key="pain_checkbox")
                
            if pain_flag:
                zones = ["Hombro", "Codo", "Muñeca", "Espalda alta", "Espalda baja", "Cadera", "Rodilla", "Tobillo", "Otra"]
                pain_zone = st.selectbox("Zona", zones, 
                                        index=zones.index(st.session_state.get('mood_pain_zone', 'Hombro')) if st.session_state.get('mood_pain_zone') in zones else 0,
                                        key="pain_zone_select")
                sides = ["Izquierdo", "Derecho", "Ambos"]
                pain_side = st.radio("Lado", sides, horizontal=True,
                                    index=sides.index(st.session_state.get('mood_pain_side', 'Izquierdo')) if st.session_state.get('mood_pain_side') in sides else 0,
                                    key="pain_side_radio")
                pain_severity = st.slider("Severidad", 0, 10, st.session_state.get('mood_pain_severity', 5), key="pain_severity_slider",
                                         help="0=Molestia, 5=Duele pero puedo, 10=No puedo moverlo")
                types = ["Punzante", "Molestia", "Rigidez", "Ardor"]
                pain_type = st.selectbox("Tipo", types,
                                        index=types.index(st.session_state.get('mood_pain_type', 'Punzante')) if st.session_state.get('mood_pain_type') in types else 0,
                                        key="pain_type_select")
                
                # Generar pain_location descriptivo
                pain_location = f"{pain_zone} {pain_side.lower()} ({pain_type}, {pain_severity}/10)"
            else:
                pain_zone = None
                pain_side = None
                pain_severity = 0
                pain_type = None
                pain_location = ""
            
        with col_flag2:
            st.write("**🤒 Estado general**")
            sick_flag = st.checkbox("Enfermo/resfriado", 
                                   value=st.session_state.get('mood_sick_flag', False),
                                   help="Fiebre, tos, malestar general", key="input_sick")
            last_hard = st.checkbox("Último entreno muy exigente", 
                                   value=st.session_state.get('mood_last_hard', False),
                                   help="Sesión de alta intensidad/volumen en últimas 48h", key="input_lasthard")
        
        with col_flag3:
            if not quick_mode:
                st.write("**Objetivo de hoy**")
                goals = ["fuerza", "hipertrofia", "técnica", "cardio", "descanso"]
                session_goal = st.selectbox("", goals,
                                           index=goals.index(st.session_state.get('mood_session_goal', 'fuerza')) if st.session_state.get('mood_session_goal') in goals else 0,
                                           key="session_goal_select")
                time_available = st.number_input("Minutos disponibles", 
                                                min_value=0, max_value=180, value=st.session_state.get('mood_time_available', 60), step=5,
                                                key="time_avail_input")
            else:
                session_goal = "fuerza"
                time_available = 60
            
        # Nota: se elimina la vista previa en tiempo real; se mostrará solo tras calcular
        st.caption("Pulsa calcular para ver tu puntuación y plan")
        submitted = st.button("▸ Calcular Readiness & Plan", use_container_width=True, type="primary")
        
        # Persist inputs immediately on button click
        if submitted:
            st.session_state.mood_sleep_h = sleep_h
            st.session_state.mood_sleep_q = sleep_q
            st.session_state.mood_nap_mins = nap_mins
            st.session_state.mood_sleep_disruptions = sleep_disruptions
            st.session_state.mood_perceived_readiness = perceived_readiness
            st.session_state.mood_fatigue = fatigue
            st.session_state.mood_soreness = soreness
            st.session_state.mood_stress = stress
            st.session_state.mood_energy = energy
            st.session_state.mood_motivation = motivation
            st.session_state.mood_stiffness = stiffness
            st.session_state.mood_caffeine = caffeine
            st.session_state.mood_alcohol = alcohol
            st.session_state.mood_pain_flag = pain_flag
            st.session_state.mood_pain_location = pain_location
            st.session_state.mood_pain_zone = pain_zone
            st.session_state.mood_pain_side = pain_side
            st.session_state.mood_pain_severity = pain_severity
            st.session_state.mood_pain_type = pain_type
            st.session_state.mood_sick_flag = sick_flag
            st.session_state.mood_last_hard = last_hard
            st.session_state.mood_session_goal = session_goal
            st.session_state.mood_time_available = time_available
            st.session_state.mood_calculated = True
        
        # Gráficas históricas (mostrar SOLO si aún no se ha calculado)
        # IMPORTANTE: Usar df_daily, NO df_filtered, para mostrar los últimos 7 días completos
        if not st.session_state.get('mood_calculated', False):
            st.markdown("---")
            render_section_title("Tendencia histórica (últimos 7 días)", accent="#4ECDC4")
            
            # Get last 7 days data (sin incluir hoy)
            today = datetime.date.today()
            last_7_days = df_daily[df_daily['date'] < today].sort_values('date', ascending=True).tail(7).copy()
            
            if not last_7_days.empty:
                col_hist1, col_hist2 = st.columns(2)
                
                with col_hist1:
                    if 'readiness_score' in last_7_days.columns:
                        readiness_hist = last_7_days.set_index('date')['readiness_score']
                        fig = create_readiness_chart(readiness_hist, "Readiness")
                        st.plotly_chart(fig, use_container_width=True)
                
                with col_hist2:
                    if 'volume' in last_7_days.columns:
                        volume_hist = last_7_days.set_index('date')['volume']
                        fig = create_volume_chart(volume_hist, "Volumen")
                        st.plotly_chart(fig, use_container_width=True)
                
                col_hist3, col_hist4 = st.columns(2)
                
                with col_hist3:
                    if 'sleep_hours' in last_7_days.columns:
                        sleep_hist = last_7_days.set_index('date')['sleep_hours']
                        fig = create_sleep_chart(sleep_hist, "Sueño (horas)")
                        st.plotly_chart(fig, use_container_width=True)
                
                with col_hist4:
                    if 'acwr_7_28' in last_7_days.columns:
                        acwr_hist = last_7_days.set_index('date')['acwr_7_28']
                        fig = create_acwr_chart(acwr_hist, "ACWR (Carga)")
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("📅 No hay datos históricos disponibles aún.")
        # Inputs already persisted above if submitted
        
        # Show results if calculated
        if st.session_state.get('mood_calculated', False):
            # === MINI RESUMEN PRE-CÁLCULO ===
            st.markdown("---")
            render_section_title("Resumen de tus inputs", accent="#FFB81C")
            
            # Retrieve from session_state
            sleep_h = st.session_state.mood_sleep_h
            sleep_q = st.session_state.mood_sleep_q
            nap_mins = st.session_state.get('mood_nap_mins', 0)
            sleep_disruptions = st.session_state.get('mood_sleep_disruptions', False)
            perceived_readiness = st.session_state.get('mood_perceived_readiness', 7)
            fatigue = st.session_state.mood_fatigue
            soreness = st.session_state.mood_soreness
            stress = st.session_state.mood_stress
            energy = st.session_state.get('mood_energy', 7)
            motivation = st.session_state.get('mood_motivation', 7)
            stiffness = st.session_state.get('mood_stiffness', 2)
            caffeine = st.session_state.get('mood_caffeine', 0)
            alcohol = st.session_state.get('mood_alcohol', False)
            pain_flag = st.session_state.mood_pain_flag
            pain_location = st.session_state.mood_pain_location
            pain_zone = st.session_state.get('mood_pain_zone')
            pain_severity = st.session_state.get('mood_pain_severity', 0)
            pain_type = st.session_state.get('mood_pain_type')
            sick_flag = st.session_state.get('mood_sick_flag', False)
            last_hard = st.session_state.get('mood_last_hard', False)
            session_goal = st.session_state.mood_session_goal
            time_available = st.session_state.get('mood_time_available', 60)
            
            # Chips de resumen
            chips = []
            
            # Sueño
            if sleep_h >= 7.5:
                chips.append(f"Sueño: {sleep_h}h (OK)")
            elif sleep_h >= 6.5:
                chips.append(f"Sueño: {sleep_h}h (Regular)")
            else:
                chips.append(f"Sueño: {sleep_h}h (Bajo)")
            
            # Fatiga
            if fatigue <= 4:
                chips.append(f"Fatiga: {fatigue}/10")
            else:
                chips.append(f"Fatiga: {fatigue}/10 (Alta)")
            
            # Estrés
            if stress <= 4:
                chips.append(f"Estrés: {stress}/10")
            else:
                chips.append(f"Estrés: {stress}/10 (Alto)")
            
            # Dolor
            if pain_flag:
                chips.append(f"Dolor: {pain_zone} ({pain_severity}/10)")
            else:
                chips.append("Dolor: No")
            
            # Enfermo
            if sick_flag:
                chips.append("Enfermo: Sí")
            
            # Alcohol
            if alcohol:
                chips.append("Alcohol: Sí (anoche)")
            
            st.markdown(" • ".join(chips))
            
            st.markdown("---")
            
            # Calculate readiness (ahora con nuevos factores + PERCEPCIÓN PERSONAL)
            readiness_instant = calculate_readiness_from_inputs_v2(
                sleep_h, sleep_q, fatigue, soreness, stress, motivation, pain_flag,
                nap_mins, sleep_disruptions, energy, stiffness, caffeine, alcohol, sick_flag,
                perceived_readiness=perceived_readiness
            )
            
            # Get zone
            zone, emoji, _ = get_readiness_zone(readiness_instant)
            
            # === PERSONALIZATION ENGINE ===
            # 1. Calculate personal baselines
            baselines = calculate_personal_baselines(df_daily)
            readiness_context, readiness_rec, readiness_delta = contextualize_readiness(readiness_instant, baselines)
            
            # 2. Detect fatigue type (central vs peripheral) - ahora recibe readiness para coordinación
            fatigue_analysis = detect_fatigue_type(
                sleep_h, sleep_q, stress, fatigue, soreness, pain_flag, pain_location, baselines,
                readiness_instant=readiness_instant
            )
            
            # 3. Calculate injury risk - ahora considera pain_severity, stiffness, sick
            # Obtener último performance_index válido (con fallback a 1.0 si no hay datos)
            perf_vals = df_daily['performance_index'].dropna() if 'performance_index' in df_daily.columns else pd.Series()
            last_perf = perf_vals.iloc[-1] if len(perf_vals) > 0 else 1.0
            
            # Obtener último acwr válido (con fallback a 1.0 si no hay datos)
            acwr_vals = df_daily['acwr_7_28'].dropna() if 'acwr_7_28' in df_daily.columns else pd.Series()
            last_acwr = acwr_vals.iloc[-1] if len(acwr_vals) > 0 else 1.0
            
            injury_risk = calculate_injury_risk_score_v2(
                readiness_instant, last_acwr, sleep_h, last_perf, 
                effort_level=max(stress, fatigue),
                pain_flag=pain_flag,
                pain_severity=pain_severity,
                stiffness=stiffness,
                sick_flag=sick_flag,
                last_hard=last_hard,
                baselines=baselines,
                days_high_strain=0
            )
            
            # Generate plan - ahora con pain_zone, pain_type, sick_flag
            zone_display, plan, rules = generate_actionable_plan_v2(
                readiness_instant, pain_flag, pain_zone, pain_severity, pain_type, 
                fatigue, soreness, stiffness, sick_flag, session_goal, fatigue_analysis
            )
            
            # Display results
            st.markdown("---")
            render_section_title("Tu Readiness HOY", accent="#00D084")
            
            col_result1, col_result2, col_result3 = st.columns([2, 1.5, 1.5])
            with col_result1:
                readiness_text = f"{emoji} {readiness_instant}/100"
                st.markdown(f"# {readiness_text}")
            with col_result2:
                st.write("")
                render_section_title("Contexto Personal", accent="#00D084")
                # Mostrar delta visual
                if baselines.get('readiness', {}).get('p50'):
                    p50 = baselines['readiness']['p50']
                    p75 = baselines['readiness']['p75']
                    delta = readiness_instant - p50
                    
                    if delta >= 0:
                        delta_color = "🟢"
                    else:
                        delta_color = "🔴"
                    
                    st.markdown(f"**Tu media:** {p50:.0f} | **Alto (p75):** {p75:.0f}")
                    st.markdown(f"{delta_color} **Hoy:** {delta:+.0f} vs media")
                    
                    # Barra de comparación visual
                    progress_val = max(0, min(100, (readiness_instant / 100)))
                    st.progress(progress_val)
                    
                    # Nota sobre comparación si hay suficientes datos
                    n_days = baselines.get('readiness', {}).get('n', 0)
                    if n_days < 14:
                        st.caption(f"⏳ Basado en {n_days} días (más historia = mejor contexto)")
                else:
                    st.write("⏳ *Necesita más historia*")
                    st.caption("(Mínimo 7 días para calcular tu baseline)")
            with col_result3:
                st.write("")
                render_section_title("Riesgo de Lesión", accent="#FF6B6B")
                st.write(f"{injury_risk['emoji']} **{injury_risk['risk_level'].upper()}**")
                st.caption(f"Score: {injury_risk['score']:.0f}/100\n({injury_risk['confidence']} confianza)")
            
            # Show injury risk factors if not low
            if injury_risk['risk_level'] != 'low':
                st.warning(f"⚠️ **{injury_risk['action']}**")
                with st.expander("Factores de riesgo"):
                    for factor in injury_risk['factors']:
                        st.write(f"• {factor}")
            
            # Advice Cards (compact UI)
            st.markdown("---")
            render_section_title("Consejos de hoy", accent="#FFB81C")

            def render_card(title: str, lines: list[str], accent: str = "#4ECDC4"):
                card_style = (
                    "border-radius:12px; padding:16px; margin-bottom:12px; "
                    "background-color: rgba(255,255,255,0.03); "
                    "border-left: 4px solid " + accent + ";"
                )
                title_style = (
                    "display:flex; align-items:center; gap:8px; "
                    "font-weight:700; text-transform:uppercase; letter-spacing:0.5px; "
                    f"color:{accent}; margin-bottom:10px;"
                )
                # filter out empty/whitespace lines to avoid blank bullets
                safe_lines = [str(l).strip() for l in lines if str(l).strip()]
                bullet_html = "".join([f"<div>• {l}</div>" for l in safe_lines])
                st.markdown(
                    f"<div style='{card_style}'>"
                    f"<div style='{title_style}'><span style='width:14px;height:3px;background:{accent};display:inline-block;border-radius:2px'></span>{title}</div>"
                    f"<div style='font-size:0.95rem;color:#eaeaea;'>" + bullet_html + "</div>"
                    + "</div>",
                    unsafe_allow_html=True,
                )

            def _clean_line(s: str) -> str:
                s = str(s).strip()
                # remove leading markdown bullets
                if s.startswith("- ") or s.startswith("• "):
                    s = s[2:].strip()
                # remove bold markers
                s = s.replace("**", "")
                return s

            col_a, col_b = st.columns(2)

            with col_a:
                fatigue_lines = [
                    f"Diagnóstico: {fatigue_analysis['reason']}",
                    f"Split recomendado: {fatigue_analysis['target_split'].upper()}",
                ]
                if 'intensity_hint' in fatigue_analysis:
                    fatigue_lines.append(f"Intensidad sugerida: {fatigue_analysis['intensity_hint']}")
                fatigue_lines.append("Acciones específicas:")
                fatigue_lines.extend(fatigue_analysis.get('recommendations', []))
                render_card(
                    f"Tipo de Fatiga: {fatigue_analysis['type'].upper()}",
                    fatigue_lines,
                    accent="#FFB81C",
                )

            with col_b:
                plan_clean = [s for s in (_clean_line(p) for p in plan) if s]
                render_card("Plan accionable", plan_clean, accent="#FFB81C")

            rules_clean = [s for s in (_clean_line(r) for r in rules) if s]
            render_card("Reglas de hoy", rules_clean, accent="#FF6B6B")
            
            # Save option
            st.markdown("---")
            col_save1, col_save2 = st.columns([3, 1])
            with col_save1:
                st.write("**Guardar este día en el histórico** para que el motor lo aprenda y recalcule tendencias.")
            with col_save2:
                if st.button("💾 Guardar", use_container_width='stretch'):
                    today = datetime.date.today()
                    save_mood_to_csv(
                        today, sleep_h, sleep_q, fatigue, soreness, stress, motivation,
                        pain_flag, pain_location, readiness_instant
                    )
                    st.success(f"✅ Guardado para {today}")
                    st.info("💡 **Próximo paso:** ejecuta el pipeline para que se regenere el histórico con estos datos.")
                    st.session_state.mood_calculated = False  # Reset after save
            
            # Charts - Last 7 days + TODAY
            st.markdown("---")
            render_section_title("Predicción con tu readiness hoy", accent="#00D084")
            
            # Get last 7 days data, excluding today if it exists
            # IMPORTANTE: Usar df_daily, NO df_filtered, para mostrar datos completos
            today = datetime.date.today()
            last_7_days_pred = df_daily[df_daily['date'] < today].sort_values('date', ascending=True).tail(7).copy()
            
            # Create today's row with calculated readiness and form inputs
            # Solo incluir columnas que existen en last_7_days_pred para mantener coherencia
            today_row = pd.DataFrame({
                'date': [today],
                'readiness_score': [readiness_instant],
                'volume': [np.nan],  # Hoy aún no hay volumen registrado; se apunta tras entrenar
                'sleep_hours': [sleep_h],
                'acwr_7_28': [np.nan]  # Hoy aún no hay datos de entrenamiento, así que ACWR es NaN
            })
            
            # Combine last 7 days + today
            chart_data = pd.concat([last_7_days_pred, today_row], ignore_index=True)
            chart_data['date'] = pd.to_datetime(chart_data['date']).dt.date
            chart_data = chart_data.sort_values('date', ascending=True)
            
            if not chart_data.empty:
                # Readiness Chart with TODAY highlighted
                col_chart1, col_chart2 = st.columns(2)
                
                with col_chart1:
                    readiness_chart = chart_data.set_index('date')['readiness_score']
                    fig = create_readiness_chart(readiness_chart, "Readiness")
                    st.plotly_chart(fig, use_container_width=True)
                
                # Volume Chart
                with col_chart2:
                    volume_chart = chart_data.set_index('date')['volume']
                    fig = create_volume_chart(volume_chart, "Volumen")
                    st.plotly_chart(fig, use_container_width=True)
                
                col_chart3, col_chart4 = st.columns(2)
                
                # Sleep Chart
                with col_chart3:
                    sleep_chart = chart_data.set_index('date')['sleep_hours']
                    fig = create_sleep_chart(sleep_chart, "Sueño (horas)")
                    st.plotly_chart(fig, use_container_width=True)
                
                # ACWR Chart
                with col_chart4:
                    acwr_chart = chart_data.set_index('date')['acwr_7_28']
                    fig = create_acwr_chart(acwr_chart, "ACWR (Carga)")
                    st.plotly_chart(fig, use_container_width=True)

    # ============== WEEK VIEW ==============
    else:
        render_section_title("Semana — Macro", accent="#4ECDC4")
        
        if df_weekly is not None:
            df_weekly['week_start'] = pd.to_datetime(df_weekly['week_start']).dt.date
            # Use last 12 weeks for weekly view instead of daily 7-day filter
            max_week = df_weekly['week_start'].max()
            start_week = max_week - datetime.timedelta(weeks=12)
            df_weekly_filtered = df_weekly[df_weekly['week_start'] >= start_week].copy()
            
            if df_weekly_filtered.empty:
                st.info("No hay datos semanales disponibles.")
            else:
                # Calcular readiness promedio por semana desde df_daily
                df_weekly_display = df_weekly_filtered.sort_values('week_start', ascending=False).copy()
                
                if 'readiness_score' in df_daily.columns:
                    df_daily_copy = df_daily.copy()
                    df_daily_copy['date'] = pd.to_datetime(df_daily_copy['date'])
                    df_daily_copy['week_start'] = df_daily_copy['date'] - pd.to_timedelta(df_daily_copy['date'].dt.dayofweek, unit='D')
                    
                    weekly_readiness = df_daily_copy.groupby('week_start')['readiness_score'].mean().reset_index()
                    weekly_readiness.columns = ['week_start', 'readiness_avg']
                    
                    # Convertir week_start a string para hacer match
                    weekly_readiness['week_start'] = pd.to_datetime(weekly_readiness['week_start']).astype(str)
                    df_weekly_display['week_start_str'] = pd.to_datetime(df_weekly_display['week_start']).astype(str)
                    
                    # Merge con la tabla semanal
                    df_weekly_display = df_weekly_display.merge(
                        weekly_readiness,
                        left_on='week_start_str',
                        right_on='week_start',
                        how='left'
                    )
                    df_weekly_display = df_weekly_display.drop('week_start_str', axis=1)
                else:
                    df_weekly_display['readiness_avg'] = None
                
                df_weekly_display = df_weekly_display.rename(columns={
                    'week_start': 'Semana (inicio)',
                    'days': 'Días',
                    'volume_week': 'Volumen',
                    'effort_week_mean': 'Esfuerzo medio',
                    'rir_week_mean': 'RIR medio',
                    'monotony': 'Monotonía',
                    'strain': 'Strain',
                    'readiness_avg': 'Readiness'
                })
                for col in ['Volumen', 'Strain']:
                    if col in df_weekly_display.columns:
                        df_weekly_display[col] = df_weekly_display[col].round(0).astype('Int64')
                for col in ['Esfuerzo medio', 'RIR medio', 'Monotonía', 'Readiness']:
                    if col in df_weekly_display.columns:
                        df_weekly_display[col] = df_weekly_display[col].round(1)
                if 'Días' in df_weekly_display.columns:
                    df_weekly_display['Días'] = df_weekly_display['Días'].astype('Int64')
                st.dataframe(df_weekly_display, use_container_width=True)
                
                # Charts
                col1, col2 = st.columns(2)
                with col1:
                    if 'volume_week' in df_weekly_filtered.columns:
                        vol_data = df_weekly_filtered.set_index('week_start')['volume_week'].sort_index()
                        fig = create_weekly_volume_chart(vol_data, "Volumen Semanal")
                        st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    if 'strain' in df_weekly_filtered.columns:
                        strain_data = df_weekly_filtered.set_index('week_start')['strain'].sort_index()
                        fig = create_weekly_strain_chart(strain_data, "Strain")
                        st.plotly_chart(fig, use_container_width=True)
                
                # === READINESS SEMANAL ===
                st.markdown("---")
                col3, col4 = st.columns(2)
                
                with col3:
                    # Calcular readiness promedio por semana desde df_daily
                    if 'readiness_score' in df_daily.columns:
                        df_daily_copy = df_daily.copy()
                        df_daily_copy['date'] = pd.to_datetime(df_daily_copy['date'])
                        df_daily_copy['week_start'] = df_daily_copy['date'] - pd.to_timedelta(df_daily_copy['date'].dt.dayofweek, unit='D')
                        
                        weekly_readiness = df_daily_copy.groupby('week_start')['readiness_score'].mean().sort_index()
                        
                        if not weekly_readiness.empty:
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(
                                x=weekly_readiness.index,
                                y=weekly_readiness.values,
                                mode='lines+markers',
                                name='Readiness Promedio',
                                line=dict(color='#B266FF', width=3),
                                marker=dict(size=8)
                            ))
                            fig.add_hline(y=65, line_dash="dash", line_color="orange", annotation_text="Óptimo")
                            fig.update_layout(
                                title="Readiness Promedio Semanal",
                                xaxis_title="Semana",
                                yaxis_title="Readiness (0-100)",
                                template="plotly_dark",
                                hovermode='x unified',
                                height=350
                            )
                            st.plotly_chart(fig, use_container_width=True)
                
                with col4:
                    # Esfuerzo promedio semanal
                    if 'effort_week_mean' in df_weekly_filtered.columns:
                        effort_data = df_weekly_filtered.set_index('week_start')['effort_week_mean'].sort_index()
                        
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            x=effort_data.index,
                            y=effort_data.values,
                            name='Esfuerzo',
                            marker=dict(color='#FF6B6B')
                        ))
                        fig.update_layout(
                            title="Esfuerzo Promedio Semanal",
                            xaxis_title="Semana",
                            yaxis_title="Esfuerzo",
                            template="plotly_dark",
                            height=350
                        )
                        st.plotly_chart(fig, use_container_width=True)
                
                # === WEEKLY SUGGESTION ===
                render_section_title("📋 Secuencia Sugerida (Próxima Semana)", accent="#00D084")
                last_week = df_weekly_filtered.sort_values('week_start', ascending=False).iloc[0]
                last_7_strain = [last_week['strain']]
                last_7_monotony = last_week.get('monotony', 0.5)
                last_readiness_mean = df_daily['readiness_score'].dropna().mean() if 'readiness_score' in df_daily.columns else 65
                
                # Calcular strain_p75 desde df_weekly para baselines correctos
                baselines_weekly = {}
                if 'strain' in df_weekly_filtered.columns:
                    strain_series = df_weekly_filtered['strain'].dropna()
                    if len(strain_series) >= 4:  # mínimo 4 semanas
                        baselines_weekly['_strain_p75'] = float(strain_series.quantile(0.75))
                        baselines_weekly['_strain_p50'] = float(strain_series.quantile(0.5))
                
                weekly_suggestion = suggest_weekly_sequence(
                    last_7_strain,
                    last_7_monotony,
                    last_readiness_mean,
                    baselines=baselines_weekly
                )
                
                st.write(f"**Razonamiento:** {weekly_suggestion['reasoning']}")
                
                # Show sequence as timeline
                cols = st.columns(7)
                for i, day_plan in enumerate(weekly_suggestion['sequence']):
                    with cols[i]:
                        st.markdown(f"""
                        <div style="text-align: center; padding: 8px; border: 1px solid #B266FF; border-radius: 4px; background: rgba(178,102,255,0.1);">
                            <b>{day_plan['day']}</b><br>
                            <span style="font-size:0.8em; color:#00D084;">{day_plan['type'].upper()}</span><br>
                            <span style="font-size:0.7em; color:#E0E0E0;">{day_plan['description']}</span>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.info("Archivo weekly.csv no disponible.")

    # ============== HISTORICAL TABLE ==============
    render_section_title("Histórico", accent="#B266FF")
    hist_cols = ['date', 'readiness_score', 'recommendation', 'action_intensity', 'reason_codes']
    hist_cols_existing = [c for c in hist_cols if c in df_filtered.columns]
    
    display_df = df_filtered[hist_cols_existing].sort_values('date', ascending=False).reset_index(drop=True)
    display_df = display_df.fillna('—')
    
    # Apply conditional formatting BEFORE converting to string
    def color_readiness(val):
        if pd.isna(val) or val == '—':
            return ''
        try:
            val_num = float(val)
            if val_num >= 75:
                return 'background-color: #00D084'
            elif val_num >= 55:
                return 'background-color: #FFB81C'
            else:
                return 'background-color: #FF4444'
        except:
            return ''
    
    # Apply styling with numeric values (avoid deprecated applymap)
    styled = display_df.style.map(color_readiness, subset=['readiness_score']) if 'readiness_score' in display_df.columns else display_df.style
    
    # Format readiness_score without decimals AFTER styling
    if 'readiness_score' in display_df.columns:
        display_df['readiness_score'] = display_df['readiness_score'].apply(
            lambda x: f"{int(float(x))}" if isinstance(x, (int, float)) and x == x else '—'
        )
        # Recreate styled with formatted values
        styled = display_df.style.map(color_readiness, subset=['readiness_score'])
    
    st.dataframe(styled, use_container_width=True)
    # ============== CHARTS ==============
    # Solo mostrar esta sección si NO estamos en Modo Hoy (para evitar duplicación)
    if view_mode != "Modo Hoy":
        render_section_title("Gráficas", accent="#FF6B6B")
        col1, col2 = st.columns(2)

        with col1:
            if 'readiness_score' in df_filtered.columns:
                rts = df_filtered.set_index('date')['readiness_score'].sort_index()
                fig = create_readiness_chart(rts, "Readiness")
                st.plotly_chart(fig, use_container_width=True)
                
                with st.expander("❓ ¿Qué significa Readiness?"):
                    st.write("""
**Qué mide:** Tu preparación hoy (0–100) combinando sueño, rendimiento reciente y señales de carga/fatiga.

**Tendencia deseable:** Que oscile, pero con media estable.

**Interpretación rápida:**
- **80+:** Buen momento para empujar (intensidad alta, nuevos máximos)
- **65–79:** Normal, entrena como siempre
- **50–64:** Recorta volumen, mantén intensidad
- **<50:** Descarga/descanso obligatorio

**Cómo usarlo:** Guía la agresividad del entrenamiento, NO tu motivación.

**Errores comunes:** Perseguir 90+ todos los días → suele acabar en fatiga.
                    """)

        with col2:
            if 'performance_index' in df_filtered.columns:
                pi = df_filtered.set_index('date')['performance_index'].sort_index()
                fig = create_performance_chart(pi, "Performance Index")
                st.plotly_chart(fig, use_container_width=True)
                
                with st.expander("❓ ¿Qué significa Performance Index?"):
                    st.write("""
**Qué mide:** Tu rendimiento relativo en lifts clave respecto a tu baseline (1.00 = normal).

**Tendencia deseable:** Ligeramente ascendente a largo plazo con pequeñas caídas.

**Interpretación rápida:**
- **1.01+:** Progreso, estás mejorando
- **0.99–1.01:** Mantenimiento, todo OK
- **<0.98 + esfuerzo alto:** Posible fatiga acumulada

**Cómo usarlo:** Mira 7 días, no el día aislado.

**Errores comunes:** Leer una caída puntual como "estoy peor" sin contexto.
                    """)

        if 'volume' in df_filtered.columns:
            vol = df_filtered.set_index('date')['volume'].sort_index()
            fig = create_volume_chart(vol, "Volumen")
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("❓ ¿Qué significa Volumen?"):
                st.write("""
**Qué mide:** Carga total (sets × reps × kg). Es tu "trabajo acumulado".

**Tendencia deseable:** Subidas en bloques + descargas periódicas.

**Interpretación rápida:**
- **Picos bruscos:** Riesgo de fatiga/lesión
- **Progresión gradual:** Adaptaciones positivas
- **Descensos:** Descargas planeadas (bien) o fatiga (revisar)

**Regla práctica:** Volumen alto ≠ mejor si el rendimiento cae y el sueño empeora.

**Errores comunes:** Ignorar descargas → acumulación innecesaria de fatiga.
                """)

        st.markdown("---")
        st.caption("🔄 La app muestra datos ya procesados. Ejecuta el pipeline para recalcular.")


if __name__ == '__main__':
    main()
