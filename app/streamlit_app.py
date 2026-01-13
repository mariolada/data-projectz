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
    default_profile = {
        'archetype': {'archetype': 'unknown', 'confidence': 0, 'reason': ''},
        'adjustment_factors': {
            'sleep_weight': 0.25,
            'performance_weight': 0.25,
            'fatigue_sensitivity': 1.0,
            'stress_sensitivity': 1.0,
            'recovery_speed': 1.0,
            'sleep_responsive': True,
        },
        'sleep_responsiveness': {},
        'insights': [],
        'data_quality': {},
    }

    if not p.exists():
        return default_profile
    try:
        with p.open('r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception:
        return default_profile


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
    caffeine=0, alcohol=False, sick_level=0, perceived_readiness=None,
    baselines=None, adjustment_factors=None
):
    """
    Versión CONTEXTUAL AVANZADA: 
    - Inputs subjetivos (cómo te sientes)
    - Baselines históricas (cómo acostumbras estar)
    - Factores personalizados (cómo te afecta cada cosa)
    - Sleep responsiveness (eres sensible al sueño?)
    
    Retorna: (readiness_score, breakdown_dict) para visibilidad
    """
    
    if baselines is None:
        baselines = {}
    if adjustment_factors is None:
        adjustment_factors = {
            'sleep_weight': 0.30,
            'fatigue_sensitivity': 1.0,
            'stress_sensitivity': 1.0,
            'sleep_responsive': True
        }
    
    # === 1. PERCEPCIÓN PERSONAL (anclaje inicial) ===
    if perceived_readiness is not None:
        perceived_score = perceived_readiness / 10
        perceived_component = 0.25 * perceived_score
        base_weight_multiplier = 0.75
    else:
        perceived_component = 0
        base_weight_multiplier = 1.0
    
    breakdown = {
        'perceived_component': perceived_component * 100 if perceived_readiness else 0,
        'components': {},
        'context_adjustments': {},
        'notes': []
    }
    
    # === 2. RECUPERACIÓN (SÍ/NO ERES SENSIBLE AL SUEÑO) ===
    sleep_hours_score = np.clip((sleep_hours - 6.0) / (7.5 - 6.0), 0, 1)
    sleep_quality_score = (sleep_quality - 1) / 4
    
    # PERSONALIZACIÓN: Comparar contra tu baseline
    sleep_context_bonus = 0
    if baselines.get('sleep', {}).get('p50'):
        your_baseline = baselines['sleep']['p50']
        delta_sleep = sleep_hours - your_baseline
        
        # Si dormiste por debajo de tu promedio
        if delta_sleep < 0:
            sleep_deficit = abs(delta_sleep)
            # Si eres sleep_responsive, esto impacta más
            if adjustment_factors.get('sleep_responsive', True):
                sleep_context_bonus = -0.05 * sleep_deficit  # -5% por cada hora bajo tu media
                breakdown['notes'].append(f"⚠️ Déficit de sueño: {sleep_deficit:.1f}h bajo tu media ({your_baseline:.1f}h). Eres sensible → impacto alto")
            else:
                sleep_context_bonus = -0.02 * sleep_deficit  # -2% si no eres sensible
                breakdown['notes'].append(f"ℹ️ Sueño bajo tu media pero NO eres muy sensible → impacto moderado")
        else:
            # Si dormiste por encima, bonus
            sleep_bonus = delta_sleep * 0.03
            sleep_context_bonus = min(sleep_bonus, 0.10)  # Cap en +10%
            breakdown['notes'].append(f"✅ Extra sueño: {delta_sleep:.1f}h sobre tu media → pequeño bonus")
    
    # Bonus siesta
    nap_bonus = 0
    if nap_mins == 20:
        nap_bonus = 0.05
    elif nap_mins == 45:
        nap_bonus = 0.08
    elif nap_mins == 90:
        nap_bonus = 0.10
    
    # Penalizaciones
    disruption_penalty = 0.15 if sleep_disruptions else 0
    alcohol_penalty = 0.20 if alcohol else 0
    
    sleep_weight = adjustment_factors.get('sleep_weight', 0.30)
    sleep_component = base_weight_multiplier * (
        sleep_weight * (sleep_hours_score + sleep_quality_score * 0.5 + nap_bonus + sleep_context_bonus)
        - disruption_penalty - alcohol_penalty
    )
    breakdown['components']['sleep'] = sleep_component * 100
    
    # === 3. ESTADO (FATIGA, ESTRÉS, SORENESS CON SENSIBILIDADES PERSONALES) ===
    # Fatiga
    fatigue_score = 1 - (fatigue / 10)
    fatigue_sensitivity = adjustment_factors.get('fatigue_sensitivity', 1.0)
    
    # Contexto: ¿Estás anormalmente fatigado para ti?
    fatigue_context = 0
    if baselines.get('readiness', {}).get('mean') and baselines.get('readiness', {}).get('std'):
        mean_readiness = baselines['readiness']['mean']
        std_readiness = baselines['readiness']['std']
        # Si fatiga > 6, es alto. ¿Es anormalmente alto para ti?
        if fatigue > 6 and fatigue_sensitivity > 1.0:
            fatigue_context = -0.08  # Extra penalización si eres sensible y está alto
            breakdown['notes'].append(f"⚠️ Fatiga alta + eres sensible → penalización extra")
    
    stress_score = 1 - (stress / 10)
    stress_sensitivity = adjustment_factors.get('stress_sensitivity', 1.0)
    
    energy_score = energy / 10
    soreness_score = 1 - (soreness / 10)
    stiffness_penalty = (stiffness / 10) * 0.10
    
    state_component = base_weight_multiplier * (
        0.12 * fatigue_score * fatigue_sensitivity +
        0.08 * stress_score * stress_sensitivity +
        0.10 * energy_score +
        0.05 * soreness_score
        - stiffness_penalty + fatigue_context
    )
    breakdown['components']['state'] = state_component * 100
    
    # === 4. MOTIVACIÓN ===
    motivation_score = motivation / 10
    motivation_component = base_weight_multiplier * 0.15 * motivation_score
    breakdown['components']['motivation'] = motivation_component * 100
    
    # === 5. PENALIZACIONES FLAGS ===
    pain_penalty = 0.25 if pain_flag else 0
    
    sick_penalty_map = {0: 0.0, 1: 0.10, 2: 0.15, 3: 0.25, 4: 0.35, 5: 0.50}
    sick_penalty = sick_penalty_map.get(sick_level, 0.0)
    
    caffeine_mask = 0
    if caffeine >= 2 and fatigue >= 6:
        caffeine_mask = 0.08
        breakdown['notes'].append(f"☕ Cafeína alta + fatiga → posible enmascaramiento")
    
    breakdown['context_adjustments'] = {
        'pain_penalty': -pain_penalty * 100,
        'sick_penalty': -sick_penalty * 100,
        'caffeine_mask': -caffeine_mask * 100
    }
    
    # === FÓRMULA FINAL ===
    readiness_0_1 = (perceived_component + sleep_component + state_component + motivation_component 
                    - pain_penalty - sick_penalty - caffeine_mask)
    
    readiness_0_1 = np.clip(readiness_0_1, 0, 1)
    readiness_score = int(round(readiness_0_1 * 100))
    
    breakdown['final_score'] = readiness_score
    
    return readiness_score, breakdown


def generate_personalized_insights(baselines, adjustment_factors, user_profile, df_daily):
    """
    Genera insights específicos sobre cómo variables afectan a ESTE usuario.
    Basado en evidencia histórica, no en promedios poblacionales.
    
    Retorna: dict con insights actionables
    """
    insights = {
        'sleep': '',
        'fatigue': '',
        'stress': '',
        'recovery': '',
        'archetype': ''
    }
    
    # Sleep insights
    if adjustment_factors.get('sleep_responsive'):
        sleep_baseline = baselines.get('sleep', {}).get('p50', 7.5)
        insights['sleep'] = f"TU PATRÓN: Eres SENSIBLE al sueño. Tu media es {sleep_baseline:.1f}h. Cada hora bajo este punto penaliza tu readiness. Recomendación: Prioriza 7.5-8h consistentemente."
    else:
        insights['sleep'] = "TU PATRÓN: NO eres muy sensible al sueño (algunos días rindes bien con <7h). Pero cuidado: mala CALIDAD sí afecta. Enfócate en dormir sin interrupciones."
    
    # Fatigue sensitivity
    fatigue_sens = adjustment_factors.get('fatigue_sensitivity', 1.0)
    if fatigue_sens > 1.2:
        insights['fatigue'] = "ERES HIPERSENSIBLE A LA FATIGA. Tu readiness cae rápido con volumen alto. Estrategia: Deloads cada 4-5 semanas, no cada 6."
    elif fatigue_sens < 0.8:
        insights['fatigue'] = "TOLERAS BIEN LA FATIGA. Puedes hacer bloques de alta carga sin colapsar. Pero no la ignores: acumula igual, solo lo ves después."
    else:
        insights['fatigue'] = "SENSIBILIDAD NORMAL a fatiga. Sigue protocolos estándar de periodización."
    
    # Recovery pattern
    if baselines.get('readiness', {}).get('std', 0) > 15:
        insights['recovery'] = "TU READINESS ES VARIABLE (fluctúa mucho). Indica: sensibilidad a carga semanal. Recomienda: tracking diario de carga + sleep + estrés."
    else:
        insights['recovery'] = "TU READINESS ES ESTABLE. Buen patrón de recuperación o poca variabilidad en entrenamientos. Mantén consistencia."
    
    # Archetype
    user_arch = user_profile.get('archetype', {}).get('archetype', 'unknown')
    if user_arch == 'short_sleeper':
        insights['archetype'] = "📌 Eres SHORT SLEEPER: Rindes bien con <7h. Aprovechia para máximo volumen, pero cuidado con fatiga acumulada."
    elif user_arch == 'acwr_sensitive':
        insights['archetype'] = "📌 Eres ACWR-SENSIBLE: ACWR alto (>1.5) te reduce readiness rápido. Monitorea ACWR semanal."
    elif user_arch == 'consistent_performer':
        insights['archetype'] = "📌 Eres CONSISTENT: Tu readiness es predecible. Ventaja: puedes planificar bloques con confianza."
    
    return insights


def get_readiness_zone(readiness):
    """Retorna (zone_text, emoji, color) basado en readiness score."""
    if readiness is None or pd.isna(readiness):
        return "N/D", "❓", "#999999"
    
    readiness = float(readiness)
    
    if readiness >= 80:
        return "Alta", "🟢", "#00D084"
    elif readiness >= 55:
        return "Media", "🟡", "#FFB81C"
    else:
        return "Muy baja", "🔴", "#FF6B6B"


def get_days_until_acwr(df_daily, selected_date):
    """Retorna días disponibles para el cálculo de ACWR (necesita 28 días para precisión)."""
    sorted_df = df_daily.sort_values('date')
    selected_idx = sorted_df[sorted_df['date'] == selected_date].index
    
    if len(selected_idx) == 0:
        return 0
    
    idx = selected_idx[0]
    # Contar desde el primer registro hasta selected_date
    days_count = idx + 1  # +1 porque es 0-indexed
    return min(days_count, 28)  # Max 28 para ACWR


def format_acwr_display(acwr_value, days_available):
    """Formatea el valor de ACWR con advertencia de confianza según días disponibles."""
    if acwr_value is None or pd.isna(acwr_value):
        return "—"
    
    acwr_str = f"{acwr_value:.2f}"
    
    if days_available < 7:
        return f"{acwr_str} ⚠️"  # Muy pocos datos
    elif days_available < 28:
        return f"{acwr_str} ℹ️"  # Datos limitados
    else:
        return acwr_str  # Confianza alta


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
    pain_flag=False, pain_severity=0, stiffness=0, sick_level=0, 
    last_hard=False, baselines=None, days_high_strain=0
):
    """Versión mejorada con pain_severity, stiffness, sick_level."""
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
    
    # Sick level (enfermo = riesgo escalonado: 0=nada, 1-2=leve, 3-4=moderado, 5=grave)
    if sick_level >= 5:
        extra_score += 35
        extra_factors.append(f'⚠️ Estado grave de enfermedad (nivel {sick_level}/5)')
    elif sick_level >= 3:
        extra_score += 25
        extra_factors.append(f'⚠️ Estado moderado de enfermedad (nivel {sick_level}/5)')
    elif sick_level >= 1:
        extra_score += 10
        extra_factors.append(f'Estado leve de enfermedad (nivel {sick_level}/5)')
    
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
    fatigue, soreness, stiffness, sick_level, session_goal, fatigue_analysis
):
    """Versión mejorada: genera plan ultra-específico con pain_zone y fatigue_type."""
    
    plan = []
    rules = []
    zone_display = ""
    
    # Override si enfermo (nivel >= 3 es significativo)
    if sick_level >= 3:
        zone_display = "ENFERMO - NO ENTRENAR"
        plan.append(f"🤒 **Estado**: Enfermo (nivel {sick_level}/5)")
        plan.append("⛔ **Recomendación**: DESCANSO TOTAL hasta recuperación")
        plan.append("💊 Prioriza: hidratación, sueño, nutrición")
        rules.append("❌ NO entrenar bajo ninguna circunstancia")
        rules.append("❌ Evita ejercicio hasta estar 100% sano")
        return zone_display, plan, rules
    elif sick_level >= 1:
        # Enfermo leve: advertencia pero puede hacer deload muy suave
        plan.append(f"⚠️ Malestar leve detectado (nivel {sick_level}/5)")
        plan.append("Considera deload o descanso si empeora")
    
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
        
        /* CTA button styling (Streamlit primary button) */
        div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"],
        button[data-testid="stBaseButton-primary"] {
            width: 100% !important;
            min-height: 56px !important;
            border-radius: 14px !important;
            background: linear-gradient(135deg, #00D084 0%, #00c070 100%) !important;
            color: #0B0E11 !important;
            border: none !important;
            font-weight: 900 !important;
            letter-spacing: 0.06em !important;
            text-transform: uppercase !important;
            font-size: 1.02rem !important;
            transition: 0.25s ease !important;
        }

        div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"]:hover,
        button[data-testid="stBaseButton-primary"]:hover {
            box-shadow: 0 0 18px rgba(0, 208, 132, 0.55) !important;
            transform: translateY(-1px) !important;
            background: linear-gradient(135deg, #00e094 0%, #00d080 100%) !important;
        }
        
        /* ===== RADIO STYLES (SCOPED) ===== */

        /* Mode toggle (Rápido / Preciso) — scoped by key (BaseWeb radios)
           Your DOM is: label > div(indicator) + input + div(text)
        */

        /* Track */
        .st-key-mode_toggle div[role="radiogroup"] {
            position: relative;
            display: inline-flex;
            gap: 0;
            padding: 6px;
            border-radius: 9999px;
            background: rgba(10,25,41,0.75);
            border: 1px solid rgba(255,255,255,0.12);
            box-shadow: 0 10px 30px rgba(0,0,0,0.25);
        }

        /* Sliding highlight (best-effort; supported in modern Chrome/Edge) */
        .st-key-mode_toggle div[role="radiogroup"]::before {
            content: "";
            position: absolute;
            top: 6px;
            bottom: 6px;
            left: 6px;
            width: calc(50% - 0px);
            border-radius: 9999px;
            background: linear-gradient(135deg, #00D084 0%, #4ECDC4 100%);
            box-shadow: 0 0 0 2px rgba(0,208,132,0.18), 0 10px 26px rgba(0,0,0,0.25);
            transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1), background 0.35s ease, box-shadow 0.35s ease;
        }

        .st-key-mode_toggle div[role="radiogroup"]:has(label[data-baseweb="radio"]:nth-child(2) input:checked)::before {
            transform: translateX(100%);
            background: linear-gradient(135deg, #B266FF 0%, #9D4EDD 100%);
            box-shadow: 0 0 0 2px rgba(178,102,255,0.20), 0 10px 26px rgba(0,0,0,0.25);
        }

        .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"] {
            position: relative !important;
            z-index: 1 !important;
            flex: 1 1 0 !important;
            margin: 0 !important;
            padding: 0 !important;
            border: 0 !important;
            background: transparent !important;
            cursor: pointer !important;
        }

        /* Hide BaseWeb indicator block (first div inside label) */
        .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child {
            display: none !important;
        }

        /* Hide the real input but keep checked state */
        .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"] > input {
            position: absolute !important;
            opacity: 0 !important;
            width: 1px !important;
            height: 1px !important;
            pointer-events: none !important;
        }

        /* Surface for label text (kept transparent so the slider is visible)
           Fallback rules below still support per-pill highlight if :has() isn't supported.
        */
        .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"] > input + div,
        .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"] input + div {
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            padding: 12px 26px !important;
            border-radius: 9999px !important;
            border: 2px solid transparent !important;
            background: transparent !important;
            font-weight: 900 !important;
            letter-spacing: 0.04em !important;
            white-space: nowrap !important;
            transition: color 0.25s ease, transform 0.25s ease !important;
        }

        /* Any SVG artifacts inside the labels */
        .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"] svg {
            display: none !important;
        }

        /* Inactive colors by position */
        .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"]:nth-child(1) > input + div {
            color: rgba(111, 231, 255, 0.60) !important;
        }
        .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"]:nth-child(2) > input + div {
            color: rgba(255, 106, 213, 0.60) !important;
        }

        /* Checked text color (works with or without slider) */
        .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"] > input:checked + div,
        .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"] input:checked + div {
            transform: translateY(-1px) !important;
            color: #0a1929 !important;
        }

        /* Fallback: if :has() isn't supported, highlight the checked pill directly */
        .st-key-mode_toggle div[role="radiogroup"]:not(:has(label[data-baseweb="radio"] input)) label[data-baseweb="radio"] > input:checked + div {
            border-color: transparent !important;
        }
        .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"]:nth-child(1) > input:checked + div {
            background: linear-gradient(135deg, #00D084 0%, #4ECDC4 100%) !important;
            box-shadow: 0 0 0 2px rgba(0,208,132,0.18), 0 10px 26px rgba(0,0,0,0.25) !important;
        }
        .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"]:nth-child(2) > input:checked + div {
            background: linear-gradient(135deg, #B266FF 0%, #9D4EDD 100%) !important;
            box-shadow: 0 0 0 2px rgba(178,102,255,0.20), 0 10px 26px rgba(0,0,0,0.25) !important;
        }

        .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"]:hover > input + div {
            border-color: rgba(255,255,255,0.22) !important;
        }

        /* Sidebar view toggle (Día / Modo Hoy / Semana) — scoped by key */
        .st-key-view_mode div[data-testid="stRadio"] > div {
            display: flex;
            flex-direction: column;
            gap: 10px;
            padding: 10px;
            border-radius: 16px;
            background: rgba(255,255,255,0.04);
            border: 1px solid rgba(255,255,255,0.10);
        }

        .st-key-view_mode div[role="radiogroup"] input { display: none !important; }
        .st-key-view_mode div[role="radio"] svg { display: none !important; }
        .st-key-view_mode div[role="radio"] > div:first-child { display: none !important; }

        .st-key-view_mode div[role="radiogroup"] label {
            cursor: pointer;
            padding: 12px 14px;
            border-radius: 14px;
            border: 1px solid rgba(255,255,255,0.10);
            background: rgba(10,25,41,0.35);
            transition: all 0.25s ease;
        }

        .st-key-view_mode div[role="radio"][aria-checked="true"] {
            background: linear-gradient(135deg, #00D084 0%, #4ECDC4 100%) !important;
            color: #0a1929 !important;
            border-color: transparent !important;
            box-shadow: 0 0 0 2px rgba(0, 208, 132, 0.25), 0 10px 24px rgba(0,0,0,0.25) !important;
        }

        .st-key-view_mode div[role="radiogroup"] label:hover {
            border-color: rgba(255,255,255,0.22);
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
        
        /* === CUSTOM CARD ANIMATIONS === */
        @keyframes neonPulse {
            0%, 100% { box-shadow: 0 0 20px var(--card-accent)40, 0 0 40px var(--card-accent)20, inset 0 0 60px rgba(0,0,0,0.3); }
            50% { box-shadow: 0 0 30px var(--card-accent)60, 0 0 60px var(--card-accent)30, inset 0 0 60px rgba(0,0,0,0.3); }
        }
        
        @keyframes cardSlideIn {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        /* Card hover effect via CSS */
        div[style*="border: 2px solid"] {
            animation: cardSlideIn 0.4s ease-out;
        }
        
        /* Input sections styling */
        .input-section {
            background: linear-gradient(135deg, rgba(20,20,30,0.6) 0%, rgba(30,30,45,0.4) 100%);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
            border-left: 3px solid var(--purple);
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        
        .section-sleep {
            border-left-color: var(--aqua);
        }
        
        .section-state {
            border-left-color: var(--amber);
        }
        
        .section-flags {
            border-left-color: var(--coral);
        }
        
        .section-header {
            font-family: 'Orbitron', sans-serif;
            font-weight: 900;
            font-size: 1.15rem;
            color: var(--text);
            letter-spacing: 0.08em;
            margin-bottom: 12px;
            text-transform: uppercase;
            text-shadow: 0 0 10px rgba(178, 102, 255, 0.3);
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
    
    # DEBUG: Verificar performance_index y performance_7d_mean ANTES del merge
    with st.expander("🔍 DEBUG: daily.csv (df_metrics) - ANTES del merge", expanded=False):
        st.write("**Columnas df_metrics:**", list(df_metrics.columns))
        
        # Debug performance_index
        if 'performance_index' in df_metrics.columns:
            perf_count = int(df_metrics['performance_index'].notna().sum())
            st.write(f"**Performance_index non-null en daily.csv:** {perf_count} de {len(df_metrics)}")
            if perf_count > 0:
                st.write("**Ejemplos performance_index (últimas 15 filas):**")
                st.dataframe(df_metrics[['date', 'performance_index']].tail(15))
            else:
                st.warning("⚠️ daily.csv tiene la columna performance_index pero todos los valores son NaN")
        else:
            st.warning("❌ daily.csv NO tiene la columna performance_index")
        
        # Debug performance_7d_mean
        st.write("---")
        st.write(f"**DEBUG performance_7d_mean non-null:** {int(df_metrics['performance_7d_mean'].notna().sum())}")
        st.write("**DEBUG performance_7d_mean ejemplos (últimas 15 filas):**")
        st.dataframe(df_metrics[['date', 'performance_7d_mean']].tail(15))
    
    try:
        df_recommendations = load_csv(reco_path)  # recommendations_daily.csv contiene TODO: métricas + readiness + recomendaciones
    except FileNotFoundError:
        st.warning("❌ Falta recommendations_daily.csv. Ejecuta `decision_engine` primero.")
        st.stop()

    # Combinar métricas base (daily.csv) con readiness/recomendaciones (recommendations_daily.csv)
    df_metrics['date'] = pd.to_datetime(df_metrics['date']).dt.date
    df_recommendations['date'] = pd.to_datetime(df_recommendations['date']).dt.date

    # Eliminar columnas de df_metrics que están en recommendations (para evitar duplicados)
    # Columnas que queremos usar de recommendations en lugar de daily
    cols_to_drop_from_metrics = []
    for col in ['readiness_score', 'recommendation', 'reason', 'action_intensity', 'reason_codes']:
        if col in df_recommendations.columns and col in df_metrics.columns:
            cols_to_drop_from_metrics.append(col)
    
    if cols_to_drop_from_metrics:
        df_metrics = df_metrics.drop(columns=cols_to_drop_from_metrics)
    
    # Ahora hacer el merge sin conflictos
    merge_cols = ['date']
    for col in ['readiness_score', 'recommendation', 'reason', 'action_intensity', 'reason_codes']:
        if col in df_recommendations.columns:
            merge_cols.append(col)
    
    df_daily = df_metrics.merge(
        df_recommendations[merge_cols], on='date', how='left'
    )
    
    # DEBUG: Verificar performance_index DESPUÉS del merge
    with st.expander("🔍 DEBUG: df_daily - DESPUÉS del merge", expanded=False):
        st.write(f"**Shape df_daily:** {df_daily.shape}")
        st.write("**Columnas df_daily:**", list(df_daily.columns))
        if 'performance_index' in df_daily.columns:
            perf_count = int(df_daily['performance_index'].notna().sum())
            st.write(f"**Performance non-null en df_daily:** {perf_count} de {len(df_daily)}")
            if perf_count > 0:
                st.write("**Ejemplos performance_index (últimas 15 filas):**")
                st.dataframe(df_daily[['date', 'performance_index']].tail(15))
            else:
                st.warning("⚠️ df_daily tiene la columna pero todos los valores son NaN después del merge")
        else:
            st.error("❌ df_daily NO tiene la columna performance_index después del merge (se perdió!)")
    
    # Agregar columnas faltantes si no existen (para compatibilidad)
    if 'action_intensity' not in df_daily.columns:
        df_daily['action_intensity'] = 'Normal'
    if 'reason_codes' not in df_daily.columns:
        df_daily['reason_codes'] = ''

    # Load optional files
    df_exercises = None
    try:
        df_exercises = load_csv(daily_ex_path)
    except:
        pass

    df_weekly = None
    try:
        df_weekly = load_csv(weekly_path)
    except Exception as e:
        st.warning(f"❌ No pude cargar weekly.csv: {e}")
        df_weekly = None

    # Sidebar: view selector (day/week/today)
    st.sidebar.markdown("<div class='sidebar-title'>Configuración</div>", unsafe_allow_html=True)
    view_mode = st.sidebar.radio("Vista", ["Día", "Modo Hoy", "Semana", "Perfil Personal"], key="view_mode")

    # Sidebar: date range filter - Solo mostrar en modo Día
    dates = sorted(df_daily['date'].unique())
    if dates:
        max_date = dates[-1]
        min_date = max(max_date - datetime.timedelta(days=6), dates[0])
    else:
        max_date = datetime.date.today()
        min_date = max_date - datetime.timedelta(days=6)

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
    
    if view_mode == "Día":
        selected_date = st.sidebar.selectbox("Selecciona fecha", options=dates_filtered, 
                                            index=dates_filtered.index(default_date) if default_date in dates_filtered else 0) if dates_filtered else None
    else:
        selected_date = default_date

    # ============== DAY VIEW ==============
    if view_mode == "Día":
        try:
            selected_date_label = pd.to_datetime(selected_date).strftime('%d/%m/%Y')
        except Exception:
            selected_date_label = selected_date
        render_section_title(f"Panel Diario — {selected_date_label}", accent="#B266FF")
        
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
        # === GAMING-DARK THEME + CUSTOM COMPONENTS ===
        st.markdown(
            """
            <style>
            /* Gaming-dark theme */
            .stApp {
                background: linear-gradient(135deg, #0a0e27 0%, #1a1a2e 100%);
            }
            
            /* Mode Toggle */
            .mode-toggle-container {
                background: rgba(178, 102, 255, 0.08);
                border-radius: 16px;
                padding: 8px;
                margin: 20px 0;
                border: 2px solid rgba(178, 102, 255, 0.3);
                box-shadow: 0 0 20px rgba(178, 102, 255, 0.15);
            }
            
            /* Section cards */
            .input-section {
                background: rgba(255, 255, 255, 0.03);
                border-radius: 12px;
                padding: 20px;
                margin: 16px 0;
                border-left: 4px solid;
                box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
                transition: all 0.3s ease;
            }
            .input-section:hover {
                box-shadow: 0 6px 30px rgba(0, 0, 0, 0.4);
                transform: translateY(-2px);
            }
            .section-recovery { border-left-color: #00D084; }
            .section-state { border-left-color: #B266FF; }
            .section-flags { border-left-color: #FF6B6B; }
            
            /* Section titles */
            .section-header {
                font-size: 1.3rem;
                font-weight: 700;
                margin-bottom: 12px;
                letter-spacing: 0.5px;
            }
            .section-recovery .section-header { color: #00D084; }
            .section-state .section-header { color: #B266FF; }
            .section-flags .section-header { color: #FF6B6B; }
            
            /* Live feedback panel */
            .live-feedback {
                position: sticky;
                top: 20px;
                background: linear-gradient(135deg, rgba(0, 208, 132, 0.1) 0%, rgba(78, 205, 196, 0.1) 100%);
                border: 2px solid rgba(0, 208, 132, 0.3);
                border-radius: 16px;
                padding: 20px;
                margin: 20px 0;
                box-shadow: 0 8px 32px rgba(0, 208, 132, 0.2);
            }
            
            /* Readiness circle */
            .readiness-circle {
                width: 120px;
                height: 120px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 16px;
                font-size: 2.5rem;
                font-weight: 800;
                background: conic-gradient(from 0deg, #00D084 var(--progress), rgba(0, 208, 132, 0.1) var(--progress));
                box-shadow: 0 0 30px rgba(0, 208, 132, 0.4);
                animation: pulse-glow 2s ease-in-out infinite;
            }
            @keyframes pulse-glow {
                0%, 100% { box-shadow: 0 0 30px rgba(0, 208, 132, 0.4); }
                50% { box-shadow: 0 0 50px rgba(0, 208, 132, 0.6); }
            }
            
            /* Action button */
            .action-button {
                background: linear-gradient(90deg, #00D084 0%, #4ECDC4 100%);
                color: #0b0b0b;
                font-weight: 800;
                font-size: 1.2rem;
                padding: 18px 32px;
                border-radius: 12px;
                border: none;
                width: 100%;
                cursor: pointer;
                box-shadow: 0 6px 20px rgba(0, 208, 132, 0.4);
                transition: all 0.3s ease;
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            .action-button:hover {
                transform: translateY(-2px);
                box-shadow: 0 8px 30px rgba(0, 208, 132, 0.6);
            }
            
            /* Slider dynamic colors */
            .stSlider > div > div > div[data-baseweb="slider"] > div:first-child {
                background: linear-gradient(90deg, #FF6B6B 0%, #FFB81C 50%, #00D084 100%) !important;
            }
            
            /* Compact output card */
            .compact-card {
                background: linear-gradient(135deg, rgba(178, 102, 255, 0.1) 0%, rgba(0, 208, 132, 0.1) 100%);
                border: 2px solid rgba(178, 102, 255, 0.3);
                border-radius: 16px;
                padding: 24px;
                margin: 20px 0;
                box-shadow: 0 8px 32px rgba(178, 102, 255, 0.2);
            }
            
            /* Badges enhanced */
            .badge-dynamic {
                display: inline-block;
                padding: 6px 14px;
                border-radius: 20px;
                font-size: 0.85rem;
                font-weight: 600;
                margin: 4px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            }
            .badge-green { background: rgba(0, 208, 132, 0.2); color: #00D084; border: 1px solid #00D084; }
            .badge-yellow { background: rgba(255, 184, 28, 0.2); color: #FFB81C; border: 1px solid #FFB81C; }
            .badge-red { background: rgba(255, 107, 107, 0.2); color: #FF6B6B; border: 1px solid #FF6B6B; }
            </style>
            """,
            unsafe_allow_html=True,
        )
        
        # === HEADER ===
        st.markdown(
            """
            <div style='text-align:center;margin:20px 0 40px'>
                <h1 style='font-size:2.5rem;font-weight:800;background:linear-gradient(90deg,#00D084,#4ECDC4);
                -webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px'>
                    Ready Check
                </h1>
                <p style='color:#B266FF;font-size:1.1rem;font-weight:600'>
                    Tu puntuación y plan personalizado en segundos
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # UI helpers
        def _badge(text:str, level:str):
            cls = {"ok":"badge-green","mid":"badge-yellow","low":"badge-red"}.get(level,"badge-yellow")
            st.markdown(f"<span class='badge-dynamic {cls}'>{text}</span>", unsafe_allow_html=True)
        
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
        
        # === MODE TOGGLE (PILL STYLE) ===
        col_toggle, col_reset = st.columns([4, 1])
        with col_toggle:
            mode = st.radio(
                "Modo",
                ["Rápido", "Preciso"],
                horizontal=True,
                label_visibility="collapsed",
                key="mode_toggle"
            )
        
        with col_reset:
            if st.button("🔄"):
                for key in list(st.session_state.keys()):
                    if key.startswith('mood_'):
                        del st.session_state[key]
                st.rerun()
        
        quick_mode = mode == "Rápido"
        
        # === INPUTS ORGANIZADOS POR SECCIONES ===
        st.markdown("<div style='margin-top:32px'></div>", unsafe_allow_html=True)
        
        # SECCIÓN A: RECUPERACIÓN (siempre visible)
        st.markdown(
            """
            <div class='input-section section-recovery'>
                <div class='section-header'>A. RECUPERACIÓN</div>
                <p style='color:rgba(255,255,255,0.6);font-size:0.95rem;margin-bottom:16px'>
                    Sueño y descanso
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
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
        st.markdown(
            """
            <div class='input-section section-state'>
                <div class='section-header'>B. ESTADO</div>
                <p style='color:rgba(255,255,255,0.6);font-size:0.95rem;margin-bottom:16px'>
                    Cómo te sientes ahora mismo
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # PERCEPCIÓN PERSONAL (siempre visible, input clave)
        st.markdown("**● Sensación Personal** — Tu intuición sobre readiness hoy")
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
            if not quick_mode:
                soreness = st.slider("Agujetas/DOMS", 0, 10, st.session_state.get('mood_soreness', 2), 
                                    help="Dolor muscular general post-entreno", key="input_soreness")
                txt, lvl = _soreness_level(soreness)
                _badge(txt, lvl)
            else:
                soreness = 2  # Valor por defecto en modo rápido
        
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
        st.markdown(
            """
            <div class='input-section section-flags'>
                <div class='section-header'>C. FLAGS / BANDERAS ROJAS</div>
                <p style='color:rgba(255,255,255,0.6);font-size:0.95rem;margin-bottom:16px'>
                    ⚠️ Señales que afectan tu capacidad de entrenar
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        col_flag1, col_flag2, col_flag3 = st.columns(3)
        
        with col_flag1:
            if not quick_mode:
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
            else:
                # Modo rápido: sin dolor localizado
                pain_flag = False
                pain_zone = None
                pain_side = None
                pain_severity = 0
                pain_type = None
                pain_location = ""
            
        with col_flag2:
            st.write("**🤒 Enfermo/Resfriado**")
            sick_flag = st.checkbox(
                "Estoy enfermo/resfriado",
                value=st.session_state.get('mood_sick_flag', False),
                key="input_sick_flag"
            )
            if sick_flag:
                sick_level = st.slider(
                    "Nivel de malestar", 0, 5,
                    st.session_state.get('mood_sick_level', 0),
                    help="0=Sano, 1-2=Leve (mocos, ligera tos), 3-4=Moderado (malestar), 5=Grave (fiebre, muy mal)",
                    key="input_sick_level"
                )
                sick_labels = {
                    0: "Sano",
                    1: "Leve",
                    2: "Leve-Moderado",
                    3: "Moderado",
                    4: "Moderado-Grave",
                    5: "Grave"
                }
                st.caption(f"Estado: {sick_labels[sick_level]}")
            else:
                sick_level = 0
                st.caption("Estado: Sano")
            
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
            
        # === ACTION BUTTON ===
        st.markdown("<div style='margin:40px 0 20px'></div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style='text-align:center'>
                <p style='color:rgba(255,255,255,0.5);font-size:0.9rem;margin-bottom:12px'>
                    Obtén tu puntuación y plan personalizado
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        submitted = st.button(
            "⚡ CALCULAR READINESS & PLAN",
            use_container_width=True,
            key="submit_readiness",
            type="primary",
        )

        # Cheat sheet de métricas clave (ayuda rápida)
        with st.expander("📘 ¿Qué significa cada métrica?"):
            st.markdown(
                """
**Volumen**: trabajo total (sets × reps × carga); sube lento, no de golpe.

**Readiness (0-100)**: disponibilidad hoy; >80 empuja, 65-79 normal, <50 descarga.

**ACWR (7d/28d)**: carga aguda vs crónica; 0.8-1.3 rango seguro, >1.5 ojo con fatiga.

**Monotonía**: media/variación del volumen semanal; >2 indica poca variación (más riesgo).

**Strain**: volumen × monotonía; alto strain = más estrés sistémico, pide recuperación.

**Performance Index (≈1.00)**: rendimiento relativo vs tu baseline; 1.01+ mejora, <0.98 posible fatiga.
                """
            )
        
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
            st.session_state.mood_sick_level = sick_level
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
            sick_level = st.session_state.get('mood_sick_level', 0)
            last_hard = st.session_state.get('mood_last_hard', False)
            session_goal = st.session_state.mood_session_goal
            time_available = st.session_state.get('mood_time_available', 60)
            
            st.markdown("<div style='margin:40px 0 20px'></div>", unsafe_allow_html=True)
            
            # === PERSONALIZATION ENGINE: Baselines + adjustment factors ===
            baselines = calculate_personal_baselines(df_daily)
            user_profile = load_user_profile()
            adjustment_factors = user_profile.get('adjustment_factors', {})
            sleep_resp = user_profile.get('sleep_responsiveness', {})
            
            # Si no hay adjustment_factors, usar defaults
            if not adjustment_factors:
                adjustment_factors = {
                    'sleep_weight': 0.30,
                    'fatigue_sensitivity': 1.0,
                    'stress_sensitivity': 1.0,
                    'sleep_responsive': sleep_resp.get('sleep_responsive', True)
                }
            
            # Calculate readiness with context
            readiness_instant, readiness_breakdown = calculate_readiness_from_inputs_v2(
                sleep_h, sleep_q, fatigue, soreness, stress, motivation, pain_flag,
                nap_mins, sleep_disruptions, energy, stiffness, caffeine, alcohol, sick_level,
                perceived_readiness=perceived_readiness,
                baselines=baselines,
                adjustment_factors=adjustment_factors
            )
            
            # Get zone
            zone, emoji, _ = get_readiness_zone(readiness_instant)
            
            # === PERSONALIZATION ENGINE ===
            # Baselines ya calculadas arriba, ahora contextualizamos
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
                sick_level=sick_level,
                last_hard=last_hard,
                baselines=baselines,
                days_high_strain=0
            )
            
            # Generate plan - ahora con pain_zone, pain_type, sick_level
            zone_display, plan, rules = generate_actionable_plan_v2(
                readiness_instant, pain_flag, pain_zone, pain_severity, pain_type, 
                fatigue, soreness, stiffness, sick_level, session_goal, fatigue_analysis
            )
            
            # Display results - TWO MODES
            st.markdown("---")
            
            # ===== DESGLOSE PERSONALIZADO =====
            render_section_title("Desglose Personalizado de tu Readiness", accent="#FFB81C")
            
            col_bd1, col_bd2 = st.columns([2, 1.5])
            
            with col_bd1:
                # Mostrar componentes
                st.write("**Componentes del cálculo:**")
                components = readiness_breakdown.get('components', {})
                adjustments = readiness_breakdown.get('context_adjustments', {})
                
                # Crear tabla visual
                comp_data = []
                for key, val in components.items():
                    if key == 'sleep':
                        label = "🛏️ Sueño"
                    elif key == 'state':
                        label = "⚡ Estado (Fatiga/Estrés)"
                    elif key == 'motivation':
                        label = "🔥 Motivación"
                    else:
                        label = key.capitalize()
                    
                    comp_data.append({'Componente': label, 'Aporte': f'{val:.1f}%'})
                
                if comp_data:
                    df_comp = pd.DataFrame(comp_data)
                    st.dataframe(df_comp, use_container_width=True, hide_index=True)
                
                # Penalizaciones
                if adjustments and any(v != 0 for v in adjustments.values()):
                    st.write("**Penalizaciones/Ajustes:**")
                    adj_data = []
                    for key, val in adjustments.items():
                        if val != 0:
                            if key == 'pain_penalty':
                                label = "🩹 Dolor"
                            elif key == 'sick_penalty':
                                label = "🤒 Enfermedad"
                            elif key == 'caffeine_mask':
                                label = "☕ Cafeína"
                            else:
                                label = key
                            adj_data.append({'Ajuste': label, 'Impacto': f'{val:.1f}%'})
                    
                    if adj_data:
                        df_adj = pd.DataFrame(adj_data)
                        st.dataframe(df_adj, use_container_width=True, hide_index=True)
            
            with col_bd2:
                st.write("**Contexto Personal:**")
                
                # Sleep responsiveness
                if adjustment_factors.get('sleep_responsive'):
                    st.info("🎯 **ERES SENSIBLE AL SUEÑO**\nPrioriza dormir bien para optimizar readiness", icon="💤")
                else:
                    st.success("💪 **NO ERES TAN SENSIBLE AL SUEÑO**\nTienes flexibilidad con horas, pero calidad importa", icon="🎯")
                
                # Baseline comparison
                if baselines.get('readiness', {}).get('p50'):
                    p50 = baselines['readiness']['p50']
                    delta = readiness_instant - p50
                    if delta > 5:
                        st.success(f"📈 Hoy +{delta:.0f} vs tu media ({p50:.0f})", icon="✅")
                    elif delta > -5:
                        st.info(f"📊 Hoy ~igual a media ({p50:.0f})", icon="ℹ️")
                    else:
                        st.warning(f"📉 Hoy {delta:.0f} vs media ({p50:.0f})", icon="⚠️")
            
            # Notas contextuales
            if readiness_breakdown.get('notes'):
                st.markdown("---")
                st.write("**Notas del analisis:**")
                for note in readiness_breakdown['notes']:
                    st.caption(note)
            
            # ===== INFORMACIÓN COMPLETA (MODO RÁPIDO Y PRECISO) =====
            if True:  # Show full output in both modes
                # ===== MODO PRECISO: Output completo con gráficos =====
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

                def render_card(title: str, lines: list[str], accent: str = "#4ECDC4", icon: str = ""):
                    # Calcular color de sombra (más oscuro que accent)
                    card_style = (
                        "position: relative; "
                        "border-radius: 16px; "
                        "padding: 24px; "
                        "margin-bottom: 20px; "
                        "background: linear-gradient(135deg, rgba(20,20,30,0.95) 0%, rgba(30,30,45,0.85) 100%); "
                        "border: 2px solid " + accent + "; "
                        "box-shadow: 0 0 20px " + accent + "40, "
                        "0 0 40px " + accent + "20, "
                        "inset 0 0 60px rgba(0,0,0,0.3); "
                        "transition: all 0.3s ease; "
                        "backdrop-filter: blur(10px);"
                    )
                    title_style = (
                        "display: flex; "
                        "align-items: center; "
                        "gap: 12px; "
                        "font-weight: 800; "
                        "font-size: 1.1rem; "
                        "text-transform: uppercase; "
                        "letter-spacing: 1.5px; "
                        f"color: {accent}; "
                        "margin-bottom: 16px; "
                        f"text-shadow: 0 0 10px {accent}80, 0 0 20px {accent}40; "
                        "font-family: 'Courier New', monospace;"
                    )
                    # filter out empty/whitespace lines to avoid blank bullets
                    safe_lines = [str(l).strip() for l in lines if str(l).strip()]
                    bullet_html = "".join([
                        f"<div style='margin-bottom:8px; padding-left:8px; border-left:2px solid {accent}50; padding-top:4px; padding-bottom:4px;'>"
                        f"<span style='color:{accent}; margin-right:8px; font-weight:bold;'>▸</span>"
                        f"<span style='color:#e0e0e0;'>{l}</span></div>" 
                        for l in safe_lines
                    ])
                    icon_html = f"<span style='font-size:1.3rem; filter: drop-shadow(0 0 8px {accent});'>{icon}</span>" if icon else f"<span style='width:6px; height:6px; background:{accent}; display:inline-block; border-radius:50%; box-shadow: 0 0 8px {accent};'></span>"
                    st.markdown(
                        f"<div style='{card_style}'>"
                        f"<div style='{title_style}'>{icon_html}{title}</div>"
                        f"<div style='font-size:0.95rem; line-height:1.6;'>" + bullet_html + "</div>"
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
                        accent="#FFB81C"
                    )

                with col_b:
                    plan_clean = [s for s in (_clean_line(p) for p in plan) if s]
                    render_card("Plan accionable", plan_clean, accent="#FFB81C")

                rules_clean = [s for s in (_clean_line(r) for r in rules) if s]
                render_card("Reglas de hoy", rules_clean, accent="#FF6B6B")
            
            # Save option (both modes now show full output)
            if not quick_mode:
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
            chart_data['date'] = pd.to_datetime(chart_data['date'])
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
    elif view_mode == "Semana":
        render_section_title("Semana — Macro", accent="#4ECDC4")
        
        # Check if weekly data exists and is valid
        if df_weekly is None:
            st.error("❌ weekly.csv no se cargó. Revisa si existe data/processed/weekly.csv")
            st.stop()
        
        if df_weekly.empty:
            st.warning("⚠️ weekly.csv está vacío")
            st.stop()
        
        # === DEBUG SECTION (solo lectura, no modifica datos) ===
        with st.expander("🔍 DEBUG: Diagnóstico de datos semanales", expanded=False):
            st.write("**df_weekly es None?:**", False)
            st.write(f"**Filas df_weekly:** {df_weekly.shape[0]}")
            st.write(f"**Columnas df_weekly:** {list(df_weekly.columns)}")
            st.dataframe(df_weekly.head(5))
            
            if 'week_start' in df_weekly.columns:
                # Analyze without modifying original
                temp_df = df_weekly.copy()
                temp_df['week_start'] = pd.to_datetime(temp_df['week_start'], errors='coerce')
                nat_count = temp_df['week_start'].isna().sum()
                st.write(f"**NaT en week_start:** {int(nat_count)}")
                st.write(f"**Rango week_start:** {temp_df['week_start'].min()} -> {temp_df['week_start'].max()}")
            else:
                st.error("❌ weekly.csv NO tiene la columna 'week_start'")
            
            # Check for volume columns
            volume_col = None
            for c in ['volume_week', 'volume', 'weekly_volume', 'total_volume', 'volumen']:
                if c in df_weekly.columns:
                    volume_col = c
                    st.success(f"✅ Columna de volumen encontrada: '{volume_col}'")
                    break
            if volume_col is None:
                st.warning("⚠️ No encuentro columna de volumen (volume_week, volume, etc.)")
        
        st.markdown("---")
        
        if df_weekly is not None and not df_weekly.empty:
            # Mantener week_start como datetime para gráficos
            df_weekly['week_start'] = pd.to_datetime(df_weekly['week_start'], errors='coerce')
            # Use last 12 weeks for weekly view instead of daily 7-day filter
            max_week = df_weekly['week_start'].max()
            start_week = max_week - pd.Timedelta(weeks=12)
            df_weekly_filtered = df_weekly[df_weekly['week_start'] >= start_week].copy()
            
            if df_weekly_filtered.empty:
                st.warning(f"⚠️ Sin datos en el rango (últimas 12 semanas desde {max_week.strftime('%d/%m/%Y')}). Mostrando todas las semanas disponibles:")
                df_weekly_filtered = df_weekly.copy()
            
            # Calcular readiness promedio por semana desde df_daily
            df_weekly_display = df_weekly_filtered.sort_values('week_start', ascending=False).copy()
            
            # Crear una columna separada para el display formateado
            df_weekly_display_formatted = df_weekly_display.copy()
            df_weekly_display_formatted['Semana (inicio)'] = df_weekly_display['week_start'].dt.strftime('%d/%m/%Y')
            
            # Calcular readiness promedio por semana desde df_daily
            try:
                if 'readiness_score' in df_daily.columns:
                    df_daily_copy = df_daily.copy()
                    # Convertir date objects a datetime
                    df_daily_copy['date'] = pd.to_datetime(df_daily_copy['date'])
                    # Calcular week_start normalizando al lunes
                    df_daily_copy['week_start'] = df_daily_copy['date'] - pd.to_timedelta(df_daily_copy['date'].dt.dayofweek, unit='D')
                    
                    weekly_readiness = df_daily_copy.groupby('week_start')['readiness_score'].mean().reset_index()
                    weekly_readiness.columns = ['week_start', 'readiness_avg']
                    
                    # Merge con la tabla semanal (ambos datetime)
                    df_weekly_display_formatted = df_weekly_display.merge(
                        weekly_readiness,
                        on='week_start',
                        how='left'
                    )
                else:
                    df_weekly_display_formatted = df_weekly_display.copy()
                    df_weekly_display_formatted['readiness_avg'] = None
            except Exception as e:
                st.warning(f"⚠️ Error al calcular readiness semanal: {e}")
                df_weekly_display_formatted = df_weekly_display.copy()
                df_weekly_display_formatted['readiness_avg'] = None
            
            # Formatear para display (FUERA del try/except)
            df_weekly_display_formatted['Semana (inicio)'] = df_weekly_display_formatted['week_start'].dt.strftime('%d/%m/%Y')
            df_weekly_display_formatted = df_weekly_display_formatted.rename(columns={
                'days': 'Días',
                'volume_week': 'Volumen',
                'effort_week_mean': 'Esfuerzo medio',
                'rir_week_mean': 'RIR medio',
                'monotony': 'Monotonía',
                'strain': 'Strain',
                'readiness_avg': 'Readiness'
            })
            
            # Seleccionar columnas para mostrar
            display_cols = ['Semana (inicio)', 'Días', 'Volumen', 'Esfuerzo medio', 'RIR medio', 'Monotonía', 'Strain', 'Readiness']
            display_cols = [c for c in display_cols if c in df_weekly_display_formatted.columns]
            df_weekly_table = df_weekly_display_formatted[display_cols].copy()
            
            # Formatear números
            for col in ['Volumen', 'Strain']:
                if col in df_weekly_table.columns:
                    df_weekly_table[col] = df_weekly_table[col].round(0).astype('Int64')
            for col in ['Esfuerzo medio', 'RIR medio', 'Monotonía', 'Readiness']:
                if col in df_weekly_table.columns:
                    df_weekly_table[col] = df_weekly_table[col].round(1)
            if 'Días' in df_weekly_table.columns:
                df_weekly_table['Días'] = df_weekly_table['Días'].astype('Int64')
            
            st.dataframe(df_weekly_table, use_container_width=True)
            
            # === MÉTRICAS PRINCIPALES ===
            render_section_title("📊 Métricas Semanales", accent="#00D084")
            col1, col2 = st.columns(2)
            with col1:
                if 'volume_week' in df_weekly_filtered.columns:
                    vol_data = (
                        df_weekly_filtered.set_index('week_start')['volume_week']
                        .pipe(pd.to_numeric, errors='coerce')
                        .dropna()
                        .sort_index()
                    )
                    if not vol_data.empty:
                        fig = create_weekly_volume_chart(vol_data, "Volumen Semanal")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Sin datos válidos para Volumen Semanal")
                    
                    with st.expander("❓ ¿Qué significa Volumen Semanal?"):
                        st.write("""
**Qué mide:** Suma de todos los sets × reps × kg de la semana. Es tu trabajo total acumulado.

**Tendencia deseable:** Progresión gradual (+5-10% semana a semana) con deloads cada 4-6 semanas.

**Interpretación:**
- **Picos bruscos (>20% aumento):** Riesgo de fatiga/lesión
- **Descensos:** Deload planeado (bien) o fatiga (revisar readiness)
- **Mesetas largas:** Posible estancamiento, considera variación

**Errores comunes:** Subir volumen sin subir readiness → acumulación fatiga.
                        """)
            
            with col2:
                if 'strain' in df_weekly_filtered.columns:
                    strain_data = (
                        df_weekly_filtered.set_index('week_start')['strain']
                        .pipe(pd.to_numeric, errors='coerce')
                        .dropna()
                        .sort_index()
                    )
                    if not strain_data.empty:
                        fig = create_weekly_strain_chart(strain_data, "Strain Semanal")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Sin datos válidos para Strain Semanal")
                    
                    with st.expander("❓ ¿Qué significa Strain?"):
                        st.write("""
**Qué mide:** Volumen × Monotonía. Es la carga ajustada por variabilidad.

**Tendencia deseable:** Variabilidad controlada con picos estratégicos.

**Interpretación:**
- **Strain alto + monotonía alta:** Riesgo de burnout mental/físico
- **Strain alto + monotonía baja:** Carga alta bien distribuida (OK)
- **Strain bajo persistente:** Posible destraining

**Regla práctica:** Si strain sube >30% en una semana, readiness debería estar >70. Si no, deload obligatorio.
                        """)
            
            # === READINESS Y PERFORMANCE ===
            st.markdown("---")
            render_section_title("🎯 Readiness & Performance", accent="#B266FF")
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
                            marker=dict(size=8),
                            fill='tozeroy',
                            fillcolor='rgba(178, 102, 255, 0.2)'
                        ))
                        fig.add_hline(y=75, line_dash="dash", line_color="#00D084", annotation_text="Óptimo (75+)")
                        fig.add_hline(y=55, line_dash="dash", line_color="#FFB81C", annotation_text="Mínimo (55)")
                        fig.update_layout(
                            title="Readiness Promedio Semanal",
                            xaxis_title="Semana",
                            yaxis_title="Readiness (0-100)",
                            template="plotly_dark",
                            hovermode='x unified',
                            height=350
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        with st.expander("❓ ¿Cómo interpretar Readiness Semanal?"):
                            st.write("""
**Qué mide:** Promedio de tu readiness diaria en la semana.

**Zonas:**
- **>75:** Zona óptima, puedes programar bloques de alta intensidad
- **55-75:** Zona mantenimiento, cuidado con volumen alto
- **<55:** Zona crítica, deload obligatorio

**Patrón sano:** Pequeñas fluctuaciones (±10 puntos) con recuperación rápida post-picos de carga.

**Red flag:** Descenso sostenido >3 semanas = fatiga acumulada no resuelta.
                            """)
            
            with col4:
                # Performance Index semanal
                if 'performance_index' in df_weekly_filtered.columns:
                    perf_data = df_weekly_filtered.set_index('week_start')['performance_index'].sort_index()
                    
                    if not perf_data.empty and perf_data.notna().any():
                        fig = create_performance_chart(perf_data, "Performance Index Semanal")
                        st.plotly_chart(fig, use_container_width=True)
                        
                        with st.expander("❓ ¿Performance Index Semanal?"):
                            st.write("""
**Qué mide:** Promedio de tu rendimiento relativo en lifts principales vs baseline (1.00 = normal).

**Tendencia deseable:** Ligeramente ascendente a largo plazo (1.00 → 1.05 en 12 semanas = progreso real).

**Interpretación:**
- **>1.02 persistente:** Progreso sólido, puedes aumentar carga base
- **0.98-1.02:** Mantenimiento, todo OK
- **<0.98 + strain alto:** Fatiga enmascarada, considera deload

**Uso práctico:** Si performance cae pero readiness está alta, posible problema de técnica o programa (no fatiga).
                            """)
            
            # === ESFUERZO Y MONOTONÍA ===
            st.markdown("---")
            render_section_title("⚙️ Esfuerzo & Monotonía", accent="#FF6B6B")
            col5, col6 = st.columns(2)
            
            with col5:
                # Esfuerzo promedio semanal
                if 'effort_week_mean' in df_weekly_filtered.columns:
                    effort_data = df_weekly_filtered.set_index('week_start')['effort_week_mean'].sort_index()
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=effort_data.index,
                        y=effort_data.values,
                        name='Esfuerzo',
                        marker=dict(
                            color='#FF6B6B',
                            line=dict(color='rgba(255, 107, 107, 0.8)', width=2),
                            opacity=0.85
                        )
                    ))
                    fig.add_hline(y=8.0, line_dash="dash", line_color="orange", annotation_text="Esfuerzo Alto")
                    fig.update_layout(
                        title="Esfuerzo Promedio Semanal (RPE)",
                        xaxis_title="Semana",
                        yaxis_title="Esfuerzo (1-10)",
                        template="plotly_dark",
                        height=350
                    )
                    st.plotly_chart(fig, use_container_width=True)
                    
                    with st.expander("❓ ¿Qué significa Esfuerzo Semanal?"):
                        st.write("""
**Qué mide:** Promedio de RPE (Rate of Perceived Exertion) de todos los sets de la semana.

**Zonas:**
- **7-8:** Zona óptima para hipertrofia/fuerza
- **>8.5:** Zona de riesgo (fatiga acumulada rápida)
- **<6:** Probablemente no estás generando adaptaciones

**Patrón ideal:** Mayoría de semanas en 7-8, con picos ocasionales >8 seguidos de deload.

**Error común:** Todas las semanas >8.5 → colapso inevitable en 4-6 semanas.
                        """)
            
            with col6:
                # Monotonía semanal
                if 'monotony' in df_weekly_filtered.columns:
                    monotony_data = df_weekly_filtered.set_index('week_start')['monotony'].sort_index()
                    
                    if not monotony_data.empty:
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=monotony_data.index,
                            y=monotony_data.values,
                            mode='lines+markers',
                            name='Monotonía',
                            line=dict(color='#FFB81C', width=3),
                            marker=dict(size=8)
                        ))
                        fig.add_hline(y=2.0, line_dash="dash", line_color="red", annotation_text="Límite (2.0)")
                        fig.add_hline(y=1.5, line_dash="dot", line_color="orange", annotation_text="Advertencia (1.5)")
                        fig.update_layout(
                            title="Monotonía Semanal",
                            xaxis_title="Semana",
                            yaxis_title="Monotonía",
                            template="plotly_dark",
                            hovermode='x unified',
                            height=350
                        )
                        st.plotly_chart(fig, use_container_width=True)
                        
                        with st.expander("❓ ¿Qué significa Monotonía?"):
                            st.write("""
**Qué mide:** Ratio entre promedio de carga y desviación estándar. Indica cuán repetitivos son tus entrenamientos.

**Zonas:**
- **<1.5:** Variabilidad alta (ideal para prevenir burnout)
- **1.5-2.0:** Zona de advertencia
- **>2.0:** Riesgo de fatiga mental y estancamiento

**Por qué importa:** Monotonía alta + volumen alto = strain explosivo → lesión/burnout.

**Solución:** Variar intensidades, ejercicios, rangos de reps cada 2-3 semanas.

**Ejemplo práctico:** Si haces 4×8@80% todos los días, monotonía será alta. Intercala 3×5@85% y 5×10@70%.
                            """)
            
            # === SUEÑO Y FATIGA ===
            st.markdown("---")
            render_section_title("😴 Sueño & Fatiga", accent="#4ECDC4")
            col7, col8 = st.columns(2)
            
            with col7:
                # Sueño promedio semanal
                if 'avg_sleep' in df_weekly_filtered.columns:
                    sleep_data = df_weekly_filtered.set_index('week_start')['avg_sleep'].sort_index()
                    
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=sleep_data.index,
                        y=sleep_data.values,
                        mode='lines+markers',
                        name='Sueño Promedio',
                        line=dict(color='#4ECDC4', width=3),
                        marker=dict(size=8),
                        fill='tozeroy',
                        fillcolor='rgba(78, 205, 196, 0.2)'
                    ))
                    fig.add_hrect(y0=7, y1=9, fillcolor="rgba(0, 208, 132, 0.1)", line_width=0, annotation_text="Óptimo")
                    fig.update_layout(
                        title="Sueño Promedio Semanal",
                        xaxis_title="Semana",
                        yaxis_title="Horas",
                        template="plotly_dark",
                        height=350
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            with col8:
                # Días con fatiga flag por semana
                if 'fatigue_days' in df_weekly_filtered.columns:
                    fatigue_data = df_weekly_filtered.set_index('week_start')['fatigue_days'].sort_index()
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=fatigue_data.index,
                        y=fatigue_data.values,
                        name='Días con Fatiga',
                        marker=dict(color='#FF6B6B')
                    ))
                    fig.add_hline(y=3, line_dash="dash", line_color="orange", annotation_text="Límite Recomendado")
                    fig.update_layout(
                        title="Días con Fatiga Alta (por semana)",
                        xaxis_title="Semana",
                        yaxis_title="Días",
                        template="plotly_dark",
                        height=350
                    )
                    st.plotly_chart(fig, use_container_width=True)
            
            # === WEEKLY SUGGESTION ===
            st.markdown("---")
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

    if 'date' in display_df.columns:
        display_df['date'] = (
            pd.to_datetime(display_df['date'], errors='coerce')
            .dt.strftime('%d/%m/%Y')
            .fillna(display_df['date'].astype(str))
        )
    
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
            # DEBUG: mostrar info sobre performance_index
            if 'performance_index' in df_filtered.columns:
                with st.expander("🔍 Debug: Performance Index", expanded=False):
                    st.write(f"**df_filtered filas:** {df_filtered.shape[0]}")
                    st.write(f"**Rango filtrado:** {df_filtered['date'].min()} a {df_filtered['date'].max()}")
                    perf_non_null = int(df_filtered['performance_index'].notna().sum())
                    st.write(f"**Performance non-null en rango:** {perf_non_null}")
                    if perf_non_null > 0:
                        st.write("**Ejemplos (últimas 15):**")
                        st.dataframe(df_filtered[['date','performance_index']].tail(15))
                    else:
                        st.write("⚠️ Todos los valores son NaN en el rango filtrado")
                        st.write("**Verificando df_daily completo:**")
                        perf_total = int(df_daily['performance_index'].notna().sum())
                        st.write(f"**Performance non-null en TODO df_daily:** {perf_total}")
                        if perf_total > 0:
                            st.write("**Últimas 10 del histórico completo:**")
                            st.dataframe(df_daily[['date','performance_index']].tail(10))
            
            if 'performance_index' in df_filtered.columns:
                # Convertir a numérico, limpiar NaN, y ordenar
                pi = (df_filtered
                      .set_index('date')['performance_index']
                      .pipe(pd.to_numeric, errors='coerce')
                      .dropna()
                      .sort_index())
                
                if not pi.empty:
                    fig = create_performance_chart(pi, "Performance Index")
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    # Si no hay datos en el rango filtrado, intentar mostrar TODO el histórico disponible
                    pi_all = (df_daily
                             .set_index('date')['performance_index']
                             .pipe(pd.to_numeric, errors='coerce')
                             .dropna()
                             .sort_index())
                    
                    if not pi_all.empty:
                        st.info("💡 Sin datos en el rango seleccionado. Mostrando histórico completo:")
                        fig = create_performance_chart(pi_all, "Performance Index (Histórico Completo)")
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("📊 Performance Index sin datos disponibles. Verifica que daily.csv tenga la columna 'performance_index' con valores numéricos o ejecuta el pipeline que lo calcule.")
            else:
                st.warning("📊 Performance Index no existe en los datos (falta la columna performance_index).")
                
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
        st.caption("La app muestra datos ya procesados. Ejecuta el pipeline para recalcular.")
    
    
    # ============== PERFIL PERSONAL VIEW ==============
    elif view_mode == "Perfil Personal":
        st.markdown("<div style='margin-top:32px'></div>", unsafe_allow_html=True)
        render_section_title("Tu Perfil Personalizado", accent="#B266FF")
        
        # Cargar datos necesarios
        baselines = calculate_personal_baselines(df_daily)
        user_profile = load_user_profile()
        adjustment_factors = user_profile.get('adjustment_factors', {})
        
        if not baselines or baselines.get('_data_quality', {}).get('total_days', 0) < 7:
            st.info("Necesitas al menos 7 días de datos para generar tu perfil personalizado. Sigue registrando entrenamientos.")
        else:
            # Generar insights
            personalized_insights = generate_personalized_insights(baselines, adjustment_factors, user_profile, df_daily)
            data_quality = baselines.get('_data_quality', {})
            total_days = data_quality.get('total_days', 0)
            last_date = data_quality.get('last_date')

            # RESUMEN EJECUTIVO
            st.markdown("---")
            st.subheader("Resumen ejecutivo")
            col_res1, col_res2, col_res3 = st.columns(3)
            with col_res1:
                st.metric("Días con datos", f"{total_days}")
                if last_date:
                    st.caption(f"Último registro: {pd.to_datetime(last_date).strftime('%d/%m/%Y')}")
            with col_res2:
                arch = user_profile.get('archetype', {}).get('archetype', '?')
                st.metric("Arquetipo detectado", arch.upper() if arch else "—")
            with col_res3:
                sleep_resp_flag = user_profile.get('sleep_responsiveness', {}).get('sleep_responsive', None)
                label = "Sensibilidad al sueño" if sleep_resp_flag is not None else "Sensibilidad al sueño"
                val = "Alta" if sleep_resp_flag else ("Baja" if sleep_resp_flag is not None else "N/D")
                st.metric(label, val)

            if personalized_insights:
                st.markdown("**Claves personalizadas:**")
                for k, v in personalized_insights.items():
                    if isinstance(v, dict):
                        bullet = v.get('summary') or v.get('recommendation') or v.get('insight')
                        if bullet:
                            st.write(f"• {bullet}")
                    elif isinstance(v, str):
                        st.write(f"• {v}")
            
            # SECCIÓN 1: ARQUETIPO
            st.markdown("---")
            st.subheader("Tu Arquetipo de Atleta")
            
            archetype = user_profile.get('archetype', {})
            if archetype.get('confidence', 0) > 0.5:
                col_arch1, col_arch2 = st.columns([2, 1])
                with col_arch1:
                    st.write(f"**Arquetipo: {archetype.get('archetype', '?').upper()}**")
                    st.caption(archetype.get('reason', ''))
                with col_arch2:
                    st.metric("Confianza", f"{archetype.get('confidence', 0):.0%}")
            
            # SECCIÓN 2: RESPONSIVIDAD AL SUEÑO
            st.markdown("---")
            st.subheader("Responsividad al Sueño")
            
            sleep_resp = user_profile.get('sleep_responsiveness', {})
            col_sleep1, col_sleep2, col_sleep3 = st.columns(3)
            
            with col_sleep1:
                is_responsive = sleep_resp.get('sleep_responsive')
                if is_responsive is None:
                    st.info("Datos insuficientes")
                elif is_responsive:
                    st.success("ERES SENSIBLE AL SUEÑO")
                else:
                    st.warning("No eres muy sensible al sueño")
            
            with col_sleep2:
                corr = sleep_resp.get('correlation', 0)
                st.metric("Correlacion Sueño-Readiness", f"{corr:.2f}", 
                         help="Rango -1 a 1. Cercano a 1 = sueño afecta mucho")
            
            with col_sleep3:
                strength = sleep_resp.get('strength', 'unknown')
                st.metric("Fuerza", strength.upper())
            
            st.caption(sleep_resp.get('interpretation', ''))
            
            # SECCIÓN 3: FACTORES DE PERSONALIZACIÓN
            st.markdown("---")
            st.subheader("Factores de Personalización")
            
            col_f1, col_f2, col_f3, col_f4 = st.columns(4)
            
            with col_f1:
                st.metric("Sleep Weight", f"{adjustment_factors.get('sleep_weight', 0.25):.2f}",
                         delta=f"{adjustment_factors.get('sleep_weight', 0.25) - 0.25:+.2f} vs default")
            
            with col_f2:
                st.metric("Fatigue Sensitivity", f"{adjustment_factors.get('fatigue_sensitivity', 1.0):.2f}x")
            
            with col_f3:
                st.metric("Stress Sensitivity", f"{adjustment_factors.get('stress_sensitivity', 1.0):.2f}x")
            
            with col_f4:
                st.metric("Recovery Speed", f"{adjustment_factors.get('recovery_speed', 1.0):.2f}x")

            # SECCIÓN 5: BASELINES PERSONALES
            st.markdown("---")
            st.subheader("Tus Baselines Historicas")
            
            col_base1, col_base2, col_base3 = st.columns(3)
            
            with col_base1:
                if baselines.get('readiness'):
                    r_base = baselines['readiness']
                    st.metric("Readiness Mediana", f"{r_base.get('p50', 0):.0f}/100")
                    st.caption(f"Desv Est: {r_base.get('std', 0):.1f}")
            
            with col_base2:
                if baselines.get('sleep'):
                    s_base = baselines['sleep']
                    st.metric("Sueño Mediano", f"{s_base.get('p50', 0):.1f}h")
                    st.caption(f"Rango: {s_base.get('p25', 0):.1f} - {s_base.get('p50', 0):.1f}h")
            
            with col_base3:
                if baselines.get('volume'):
                    v_base = baselines['volume']
                    st.metric("Volumen Mediano", f"{v_base.get('p50', 0):.0f}")
            
            # SECCIÓN 5: INSIGHTS CLAVE
            st.markdown("---")
            st.subheader("Insights Clave")
            
            col_ins1, col_ins2 = st.columns(2)
            
            with col_ins1:
                st.write("**Sueño**")
                st.caption(personalized_insights['sleep'])
            
            with col_ins2:
                st.write("**Fatiga**")
                st.caption(personalized_insights['fatigue'])
            
            col_ins3, col_ins4 = st.columns(2)
            
            with col_ins3:
                st.write("**Recuperacion**")
                st.caption(personalized_insights['recovery'])
            
            with col_ins4:
                st.write("**Patron Observado**")
                st.caption(personalized_insights['archetype'])
            
            # SECCIÓN 6: RECOMENDACIONES
            st.markdown("---")
            st.subheader("Recomendaciones Personalizadas")
            
            if adjustment_factors.get('sleep_responsive'):
                st.info("Prioriza SIEMPRE dormir 7.5-8h. Cada hora bajo tu media penaliza readiness significativamente.")
            
            if adjustment_factors.get('fatigue_sensitivity', 1.0) > 1.2:
                st.warning("Eres hipersensible a fatiga. Deloads cada 4-5 semanas, no cada 6.")
            
            if baselines.get('readiness', {}).get('std', 0) > 15:
                st.info("Tu readiness es variable. Recomendacion: tracking diario de carga, sueño y estrés.")
            else:
                st.success("Tu readiness es estable. Puedes planificar con confianza.")
            
            # Información de calidad de datos
            st.markdown("---")
            data_quality = baselines.get('_data_quality', {})
            st.caption(f"Datos disponibles: {data_quality.get('total_days', 0)} dias. Minimo recomendado: {data_quality.get('min_required', 7)} dias.")


if __name__ == '__main__':
    main()
