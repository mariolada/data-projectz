import streamlit as st
import streamlit.components.v1 as components
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

# ===== IMPORTS DE MÓDULOS REFACTORIZADOS =====
# Config
from config import COLORS, READINESS_ZONES, DEFAULT_READINESS_WEIGHTS, DAILY_PATH, USER_PROFILE_PATH

# UI
from ui.theme import get_theme_css
from ui.components import render_section_title

# Charts
from charts.daily_charts import (
    create_readiness_chart,
    create_volume_chart,
    create_sleep_chart,
    create_acwr_chart,
    create_performance_chart,
    create_strain_chart
)
from charts.weekly_charts import create_weekly_volume_chart, create_weekly_strain_chart

# Calculations
from calculations.readiness_calc import (
    calculate_readiness_from_inputs_v2,
    calculate_readiness_from_inputs
)
from calculations.injury_risk import calculate_injury_risk_score_v2, calculate_injury_risk_score
from calculations.plans import generate_actionable_plan_v2, generate_actionable_plan

# Data
from data.loader import load_csv, load_user_profile
from data.formatters import (
    get_readiness_zone,
    get_days_until_acwr,
    get_confidence_level,
    format_acwr_display
)

# ===== IMPORTS EXTERNOS (src) =====
sys.path.append(str(Path(__file__).parent.parent / 'src'))
from personalization_engine import (
    calculate_personal_baselines,
    calculate_personal_adjustment_factors,
    contextualize_readiness,
    detect_fatigue_type,
    suggest_weekly_sequence
)


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


def render_today_mode(df_daily):
    """Renderiza el modo interactivo 'Modo Hoy' para calcular readiness al instante."""
    render_section_title("Modo Hoy — Ready Check", accent="#00D084")
    
    # Initialize session state
    if 'mood_calculated' not in st.session_state:
        st.session_state.mood_calculated = False
    
    # Create two columns: left for inputs, right for live feedback
    col_input, col_feedback = st.columns([3, 2])
    
    with col_input:
        st.markdown('<div class="eyebrow" style="margin-bottom:12px;">📋 DATOS DE HOY</div>', unsafe_allow_html=True)

        mode = st.radio("Modo", ["Rápido", "Preciso"], horizontal=True, key="input_mode")
        
        # === RECUPERACIÓN (SUEÑO) ===
        with st.expander("💤 Sueño & Recuperación", expanded=True):
            sleep_h = st.slider("Horas de sueño anoche", 4.0, 12.0, 7.5, 0.5, 
                               help="Tiempo total de sueño", key="input_sleep_h")
            sleep_q = st.select_slider("Calidad del sueño", options=[1,2,3,4,5], value=3,
                                       format_func=lambda x: {1:"😴 Muy malo", 2:"😕 Malo", 3:"😐 Regular", 4:"🙂 Bueno", 5:"😊 Excelente"}[x],
                                       key="input_sleep_q")
            if mode == "Preciso":
                nap_mins = st.selectbox("Siesta", [0, 20, 45, 90], index=0, help="Minutos de siesta", key="input_nap")
                sleep_disruptions = st.checkbox("Sueño fragmentado (3+ despertares)", value=False, key="input_disruptions")
            else:
                nap_mins = 0
                sleep_disruptions = False
        
        # === ESTADO FÍSICO ===
        with st.expander("💪 Estado Físico & Mental", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                perceived = st.slider("¿Cómo te sientes hoy? (0-10)", 0, 10, 7,
                                    help="Tu intuición general sobre tu estado", key="input_perceived")
                fatigue = st.slider("Fatiga/Cansancio (0-10)", 0, 10, 3, key="input_fatigue")
                stress = st.slider("Estrés mental (0-10)", 0, 10, 3, key="input_stress")
            
            with col2:
                if mode == "Preciso":
                    soreness = st.slider("Agujetas/DOMS (0-10)", 0, 10, 2, key="input_soreness")
                else:
                    soreness = 2
                motivation = st.slider("Motivación (0-10)", 0, 10, 7, key="input_motivation")
                energy = st.slider("Nivel de energía (0-10)", 0, 10, 7, key="input_energy")

        if mode == "Preciso":
            col_adv1, col_adv2, col_adv3 = st.columns(3)
            with col_adv1:
                stiffness = st.slider("Rigidez articular", 0, 10, 2, help="Movilidad limitada", key="input_stiffness")
            with col_adv2:
                caffeine = st.selectbox("Cafeína (últimas 6h)", [0,1,2,3], index=0, key="input_caffeine")
            with col_adv3:
                alcohol = st.checkbox("Alcohol anoche", value=False, key="input_alcohol")
        else:
            stiffness = 2
            caffeine = 0
            alcohol = False
        
        # === BANDERAS ROJAS ===
        pain_flag = False
        pain_location = ""
        pain_zone = None
        pain_severity = 0
        pain_type = None
        sick_flag = False
        last_hard = False
        session_goal = "fuerza"
        time_available = 60

        if mode == "Preciso":
            with st.expander("⚠️ Alertas & Dolor", expanded=False):
                pain_flag = st.checkbox("¿Tienes dolor/molestias hoy?", value=False, key="input_pain")
                if pain_flag:
                    zones = ["Hombro", "Codo", "Muñeca", "Espalda alta", "Espalda baja", "Cadera", "Rodilla", "Tobillo", "Otra"]
                    pain_zone = st.selectbox("Zona", zones, index=6, key="input_pain_zone")
                    pain_severity = st.slider("Severidad", 0, 10, 5, key="input_pain_sev")
                    pain_type = st.selectbox("Tipo", ["Punzante", "Molestia", "Rigidez", "Ardor"], index=1, key="input_pain_type")
                    pain_location = st.text_input("Detalle", value="", key="input_pain_loc")
                sick_flag = st.checkbox("¿Te sientes enfermo/a? (resfriado, malestar...)", value=False, key="input_sick")
                last_hard = st.checkbox("Último entreno muy exigente (48h)", value=False, key="input_last_hard")
                session_goal = st.selectbox("Objetivo de hoy", ["fuerza","hipertrofia","técnica","cardio","descanso"], index=0, key="input_goal")
                time_available = st.number_input("Minutos disponibles", min_value=0, max_value=180, value=60, step=5, key="input_time")
        
        # === BOTÓN CALCULAR ===
        st.markdown("<br>", unsafe_allow_html=True)
        calculate_btn = st.button("🚀 CALCULAR MI READINESS", type="primary", use_container_width=True)
        
        if calculate_btn:
            st.session_state.mood_calculated = True
            st.session_state.mood_mode = mode
            st.session_state.mood_sleep_h = sleep_h
            st.session_state.mood_sleep_q = sleep_q
            st.session_state.mood_perceived = perceived
            st.session_state.mood_fatigue = fatigue
            st.session_state.mood_stress = stress
            st.session_state.mood_soreness = soreness
            st.session_state.mood_motivation = motivation
            st.session_state.mood_energy = energy
            st.session_state.mood_pain_flag = pain_flag
            st.session_state.mood_pain_location = pain_location
            st.session_state.mood_sick_flag = sick_flag
            st.session_state.mood_nap_mins = nap_mins
            st.session_state.mood_sleep_disruptions = sleep_disruptions
            st.session_state.mood_stiffness = stiffness
            st.session_state.mood_caffeine = caffeine
            st.session_state.mood_alcohol = alcohol
            st.session_state.mood_pain_zone = pain_zone
            st.session_state.mood_pain_severity = pain_severity
            st.session_state.mood_pain_type = pain_type
            st.session_state.mood_last_hard = last_hard
            st.session_state.mood_session_goal = session_goal
            st.session_state.mood_time_available = time_available
    
    # === PANEL DE FEEDBACK EN VIVO ===
    with col_feedback:
        if st.session_state.get('mood_calculated', False):
            # Retrieve values
            sleep_h = st.session_state.mood_sleep_h
            sleep_q = st.session_state.mood_sleep_q
            perceived = st.session_state.mood_perceived
            fatigue = st.session_state.mood_fatigue
            stress = st.session_state.mood_stress
            soreness = st.session_state.mood_soreness
            motivation = st.session_state.mood_motivation
            energy = st.session_state.mood_energy
            pain_flag = st.session_state.mood_pain_flag
            pain_location = st.session_state.mood_pain_location
            sick_flag = st.session_state.mood_sick_flag
            mode = st.session_state.get('mood_mode', 'Rápido')
            nap_mins = st.session_state.get('mood_nap_mins', 0)
            sleep_disruptions = st.session_state.get('mood_sleep_disruptions', False)
            stiffness = st.session_state.get('mood_stiffness', 2)
            caffeine = st.session_state.get('mood_caffeine', 0)
            alcohol = st.session_state.get('mood_alcohol', False)
            pain_zone = st.session_state.get('mood_pain_zone')
            pain_severity = st.session_state.get('mood_pain_severity', 0)
            pain_type = st.session_state.get('mood_pain_type')
            last_hard = st.session_state.get('mood_last_hard', False)
            session_goal = st.session_state.get('mood_session_goal', 'fuerza')
            time_available = st.session_state.get('mood_time_available', 60)
            
            # Calculate readiness (base)
            readiness_raw = calculate_readiness_from_inputs_v2(
                sleep_h, sleep_q, fatigue, soreness, stress, motivation, pain_flag,
                nap_mins=nap_mins, sleep_disruptions=sleep_disruptions, energy=energy, 
                stiffness=stiffness, caffeine=caffeine, alcohol=alcohol, sick_flag=sick_flag,
                perceived_readiness=perceived
            )

            # Personal adjustments only in precise mode
            baselines = calculate_personal_baselines(df_daily) if mode == "Preciso" else {}
            if mode == "Preciso":
                adj_factors = calculate_personal_adjustment_factors(df_daily)
                recovery_boost = (adj_factors.get('recovery_speed', 1.0) - 1.0) * 8
                fatigue_penalty = (adj_factors.get('fatigue_sensitivity', 1.0) - 1.0) * 10
                readiness = np.clip(readiness_raw + recovery_boost - fatigue_penalty, 0, 100)
                readiness_context = contextualize_readiness(int(readiness), baselines) if baselines and '_data_quality' in baselines else None
            else:
                readiness = readiness_raw
                readiness_context = None
            
            zone, emoji, color = get_readiness_zone(readiness)
            
            # Display readiness circle
            circle_color = {"Alta": "#00D084", "Media": "#FFB81C", "Baja": "#FF6B6B"}.get(zone, "#9CA3AF")
            context_html = f"<div style='color:#9CA3AF; font-size:0.9rem;'>Contexto personal: {readiness_context[0]}</div>" if readiness_context else ""

            gauge_html = f"""
<div class="hero" style="display:flex; flex-direction:column; align-items:center; text-align:center; padding:20px; gap:6px;">
    <div class="eyebrow">READINESS SCORE</div>
    <div style="position: relative; width: 130px; height: 130px; margin: 15px auto;">
        <svg width="130" height="130" viewBox="0 0 130 130">
            <circle cx="65" cy="65" r="55" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="10"/>
            <circle cx="65" cy="65" r="55" fill="none" stroke="{circle_color}" stroke-width="10" stroke-dasharray="{readiness * 3.45} 345" stroke-linecap="round" transform="rotate(-90 65 65)"/>
        </svg>
        <div style="position:absolute; top:50%; left:50%; transform:translate(-50%,-50%); text-align:center;">
            <div style="font-size:2.8rem; font-weight:800; color:{circle_color};">{int(readiness)}</div>
            <div style="font-size:0.75rem; color:#9CA3AF; margin-top:-5px;">/ 100</div>
        </div>
    </div>
    <div style="font-size: 1.3rem; font-weight: 700; color: {circle_color}; margin-top:6px;">{emoji} ZONA {zone.upper()}</div>
    <div class="sub" style="margin-top:2px;">Zona: <strong>{zone}</strong></div>
    {context_html}
</div>
"""
            st.markdown(gauge_html, unsafe_allow_html=True)
            
            # Generate plan
            # Fatigue analysis solo en preciso
            if mode == "Preciso":
                fatigue_analysis = detect_fatigue_type(
                    sleep_h, sleep_q, stress, fatigue, soreness, pain_flag, pain_location, baselines,
                    readiness_instant=readiness
                )
                perf_vals = df_daily['performance_index'].dropna() if 'performance_index' in df_daily.columns else pd.Series()
                last_perf = perf_vals.iloc[-1] if len(perf_vals) > 0 else 1.0
                acwr_vals = df_daily['acwr_7_28'].dropna() if 'acwr_7_28' in df_daily.columns else pd.Series()
                last_acwr = acwr_vals.iloc[-1] if len(acwr_vals) > 0 else 1.0
                injury_risk = calculate_injury_risk_score_v2(
                    readiness, last_acwr, sleep_h, last_perf,
                    effort_level=max(stress, fatigue),
                    pain_flag=pain_flag, pain_severity=pain_severity, stiffness=stiffness,
                    sick_flag=sick_flag, last_hard=last_hard, baselines=baselines, days_high_strain=0
                )
                zone_display, plan, rules = generate_actionable_plan_v2(
                    readiness, pain_flag, pain_zone, pain_severity, pain_type,
                    fatigue, soreness, stiffness, sick_flag, session_goal, fatigue_analysis
                )
            else:
                fatigue_analysis = None
                injury_risk = None
                zone_display, plan, rules = generate_actionable_plan(
                    readiness, pain_flag, pain_location, fatigue, soreness
                )

            # Seleccionar nivel de detalle
            plan_lines = plan if mode == "Preciso" else plan[:3]
            rule_lines = rules if mode == "Preciso" else rules[:2]

            # Tarjeta estilizada para el plan del día
            def _clean_line(txt: str) -> str:
                s = str(txt).strip()
                # remove leading markdown bullets and common emoji markers
                for prefix in ["- ", "• ", "🟢 ", "🟡 ", "🔴 ", "✅ ", "⚠️ ", "⛔ ", "🤒 ", "🩹 ", "🦴 ", "🔥 ", "💊 "]:
                    if s.startswith(prefix):
                        s = s[len(prefix):].strip()
                s = s.replace("**", "")
                return s

            def _as_list(items):
                if not items:
                    return "<div style='color:#9CA3AF;'>Sin datos</div>"
                rows = []
                for itm in items:
                    safe_txt = _clean_line(itm)
                    if not safe_txt:
                        continue
                    rows.append(f"<div style='margin-bottom:6px;'>• {safe_txt}</div>")
                return "".join(rows)

            st.markdown("---")
            render_section_title("Plan de Entrenamiento", accent="#FFB81C")
            zone_color = {"Alta": "#00D084", "Media": "#FFB81C", "Baja": "#FF6B6B"}.get(zone, "#9CA3AF")

            summary_html = ""
            if mode == "Preciso":
                summary_html = f"""
<div style='margin-top:12px; padding:12px; border-radius:12px; background:linear-gradient(135deg, rgba(0,208,132,0.20), rgba(78,205,196,0.08)); border:1px solid rgba(0,208,132,0.35); box-shadow:0 8px 20px rgba(0,208,132,0.18);'>
<div style='display:flex; flex-wrap:wrap; gap:10px;'>
<span style='color:{zone_color}; font-weight:900; letter-spacing:0.05em;'>Zona: {zone_display}</span>
<span style='color:#FFB81C; font-weight:800; text-transform:uppercase;'>Fatiga: {(fatigue_analysis.get('type','fresh')).upper() if fatigue_analysis else 'FRESH'}</span>
<span style='color:#E5E7EB; font-weight:800; text-transform:uppercase;'>Split: {(fatigue_analysis.get('target_split','N/A')).upper() if fatigue_analysis else 'N/A'}</span>
<span style='color:#9CA3AF; font-weight:700;'>Intensidad: {fatigue_analysis.get('intensity_hint','RIR 2–3') if fatigue_analysis else 'RIR 2–3'}</span>
</div>
</div>
"""

            plan_html = f"""
<div style="background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 10px; padding: 18px; box-shadow: 0 8px 24px rgba(0,0,0,0.25);">
<div class="eyebrow" style="color: #FFB81C; margin-bottom: 10px;">PLAN DE HOY ({mode.upper()})</div>
{summary_html}
<div style="margin-top: 12px; color: #E5E7EB; line-height: 1.6;">{_as_list(plan_lines)}</div>
<div style="margin-top: 12px; color: #9CA3AF; font-weight: 700;">Reglas clave</div>
<div style="margin-top: 6px; color: #CBD5E1; line-height: 1.6;">{_as_list(rule_lines)}</div>
</div>
"""

            st.markdown(plan_html, unsafe_allow_html=True)

            if mode == "Preciso" and injury_risk is not None:
                risk_color = {"low": "#00D084", "medium": "#FFB81C", "high": "#FF6B6B"}.get(injury_risk['risk_level'], "#9CA3AF")
                factors_html = "".join([f"<div>• {_clean_line(f)}</div>" for f in injury_risk.get('factors', [])])
                render_section_title("Riesgo de Lesión", accent="#FF6B6B")
                st.markdown(f"""
                <div class="hero" style="border-left: 4px solid {risk_color};">
                    <div style="display:flex; align-items:center; gap:16px;">
                        <div style="width:60px; height:60px; border-radius:50%; background:{risk_color}; opacity:0.85;"></div>
                        <div>
                            <div class="eyebrow">NIVEL DE RIESGO</div>
                            <h2 style="color:{risk_color}; margin:4px 0; text-transform:uppercase;">{injury_risk['risk_level']}</h2>
                            <div class="sub">Score: {injury_risk['score']:.0f}/100 • {injury_risk['confidence']}</div>
                        </div>
                    </div>
                    <div style="margin-top:12px; color:#E5E7EB;">{_clean_line(injury_risk['action'])}</div>
                    <div style="margin-top:8px; color:#9CA3AF; font-size:0.9rem;">{factors_html}</div>
                </div>
                """, unsafe_allow_html=True)

            if mode == "Preciso" and fatigue_analysis is not None:
                render_section_title("Análisis de Fatiga", accent="#4ECDC4")
                st.markdown(f"""
                <div class="hero">
                    <div class="eyebrow">TIPO DE FATIGA DETECTADA</div>
                    <h2 style="color:#4ECDC4; margin:4px 0;">{fatigue_analysis.get('type','').upper()}</h2>
                    <div class="sub">{_clean_line(fatigue_analysis.get('reason',''))}</div>
                    <div style="margin-top:10px; color:#FFB81C; font-weight:600;">Split recomendado: {fatigue_analysis.get('target_split','').upper()}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # Reset button
            if st.button("🔄 Nueva Evaluación", use_container_width=True):
                st.session_state.mood_calculated = False
                st.rerun()
        else:
            st.info("👈 Completa los datos en el panel izquierdo y presiona el botón para calcular tu readiness.")


def render_day_view(df_filtered, selected_date, user_profile, daily_ex_path):
    """Renderiza la vista diaria completa con métricas, gráficas y recomendaciones."""
    try:
        selected_date_label = pd.to_datetime(selected_date).strftime('%d/%m/%Y')
    except Exception:
        selected_date_label = selected_date
    render_section_title(f"Panel Diario — {selected_date_label}", accent="#B266FF")
    
    if selected_date is None:
        st.info("No hay datos para mostrar.")
        return
        
    row = df_filtered[df_filtered['date'] == selected_date]
    if row.empty:
        st.warning(f"No hay datos para {selected_date_label}")
        return
    
    row = row.iloc[0]
    readiness = row['readiness_score']
    zona, emoji, color = get_readiness_zone(readiness)
    days_available = get_days_until_acwr(df_filtered, selected_date)
    conf_text, conf_icon = get_confidence_level(df_filtered, selected_date)
    
    anti_fatigue = get_anti_fatigue_flag(df_filtered, selected_date)
    
    # Hero card con métricas
    col_hero_left, col_hero_right = st.columns([2, 1])
    with col_hero_left:
        anti_fatigue_badge = '<div class="badge coral">⚠️ Anti-Fatigue</div>' if anti_fatigue else ''
        st.markdown(f"""
        <div class="hero">
            <div>
                <div class="eyebrow">Readiness Score</div>
                <h1 style="margin: 4px 0;">{emoji} {int(readiness)}/100</h1>
                <div class="sub">Zona: <strong>{zona}</strong></div>
            </div>
            <div class="badge-row">
                <div class="badge purple">{conf_icon} {conf_text}</div>
                {anti_fatigue_badge}
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_hero_right:
        acwr = row['acwr_7_28']
        acwr_display = format_acwr_display(acwr, days_available)
        perf_index = row.get('performance_index', None)
        perf_display = f"{perf_index:.3f}" if pd.notna(perf_index) else "—"
        
        st.markdown(f"""
        <div style="background: rgba(255,255,255,0.04); padding: 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.08);">
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                <span style="color: #9CA3AF; font-size: 0.9em;">ACWR</span>
                <span style="color: #FFB81C; font-weight: 700;">{acwr_display}</span>
            </div>
            <div style="display: flex; justify-content: space-between;">
                <span style="color: #9CA3AF; font-size: 0.9em;">Performance</span>
                <span style="color: #4ECDC4; font-weight: 700;">{perf_display}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    # Desglose de métricas
    render_section_title("Desglose", accent="#FFB81C")
    c1, c2, c3, c4 = st.columns(4)
    sleep_hours = row.get('sleep_hours', None)
    c1.metric("💤 Sueño (h)", f"{sleep_hours:.1f}" if pd.notna(sleep_hours) else "—")
    sleep_quality = row.get('sleep_quality', None)
    c2.metric("🎯 Calidad sueño", f"{int(sleep_quality)}/5" if pd.notna(sleep_quality) else "—")
    fatigue = row.get('fatigue', None)
    c3.metric("😴 Fatiga", f"{int(fatigue)}/10" if pd.notna(fatigue) else "—")
    soreness = row.get('soreness', None)
    c4.metric("🤕 Soreness", f"{int(soreness)}/10" if pd.notna(soreness) else "—")
    
    c5, c6, c7, c8 = st.columns(4)
    stress = row.get('stress', None)
    c5.metric("😰 Estrés", f"{int(stress)}/10" if pd.notna(stress) else "—")
    motivation = row.get('motivation', None)
    c6.metric("🔥 Motivación", f"{int(motivation)}/10" if pd.notna(motivation) else "—")
    effort = row.get('effort_level', None)
    c7.metric("💪 Esfuerzo", f"{int(effort)}/10" if pd.notna(effort) else "—")
    pain = "Sí" if row.get('pain_flag', False) else "No"
    c8.metric("⚠️ Dolor", pain)
    
    # Razones readiness
    reasons = row.get('reason_codes', '')
    if pd.notna(reasons) and reasons != '':
        from data.formatters import format_reason_codes
        reason_list = format_reason_codes(reasons)
        if reason_list:
            st.info("**Razones de readiness baja:** " + " • ".join(reason_list))
    
    # Injury Risk
    render_section_title("🩹 Riesgo de Lesión", accent="#FF6B6B")
    baselines = calculate_personal_baselines(df_filtered)
    pain_flag = row.get('pain_flag', False)
    days_high = 0  # placeholder
    
    sleep_hours = row.get('sleep_hours', None)
    injury_risk = calculate_injury_risk_score(
        readiness, acwr if pd.notna(acwr) else 1.0,
        sleep_hours if pd.notna(sleep_hours) else 7.0, 
        perf_index if pd.notna(perf_index) else 1.0,
        effort if pd.notna(effort) else 5,
        pain_flag, baselines, days_high
    )
    
    col_risk1, col_risk2 = st.columns([1, 2])
    with col_risk1:
        risk_color_map = {'low': '#00D084', 'medium': '#FFB81C', 'high': '#FF6B6B'}
        risk_color = risk_color_map.get(injury_risk['risk_level'], '#9CA3AF')
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(255,107,107,0.12), rgba(0,0,0,0.05)); padding: 18px; border-radius: 10px; border: 1px solid rgba(255,107,107,0.25); text-align: center;">
            <div style="font-size: 3em; margin-bottom: 8px;">{injury_risk['emoji']}</div>
            <div style="color: {risk_color}; font-weight: 700; font-size: 1.3em; text-transform: uppercase; letter-spacing: 0.05em;">{injury_risk['risk_level'].upper()}</div>
            <div style="color: #9CA3AF; margin-top: 6px;">Score: {injury_risk['score']}/100</div>
            <div style="color: #9CA3AF; font-size: 0.85em; margin-top: 4px;">{injury_risk['confidence']}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_risk2:
        st.markdown(f"**Acción recomendada:** {injury_risk['action']}")
        if injury_risk['factors']:
            st.markdown("**Factores de riesgo detectados:**")
            for factor in injury_risk['factors']:
                st.markdown(f"- {factor}")
    
    # Plan accionable
    render_section_title("📋 Plan de Entrenamiento", accent="#00D084")
    
    pain_location = row.get('pain_location', None) if pain_flag else None
    fatigue = row.get('fatigue', 5)  # Default moderado
    soreness = row.get('soreness', 3)  # Default bajo
    zone_display, plan, rules = generate_actionable_plan(
        readiness, pain_flag, pain_location,
        fatigue if pd.notna(fatigue) else 5,
        soreness if pd.notna(soreness) else 3
    )
    
    col_plan1, col_plan2 = st.columns([1, 1])
    with col_plan1:
        st.markdown("### 🎯 Recomendación")
        for line in plan:
            st.markdown(line)
    
    with col_plan2:
        st.markdown("### ⚖️ Reglas de Hoy")
        for rule in rules:
            st.markdown(f"- {rule}")
    
    # Lifts del día
    if daily_ex_path:
        df_lifts = load_daily_exercise_for_date(daily_ex_path, selected_date)
        if not df_lifts.empty:
            render_section_title("🏋️ Levantamientos del Día", accent="#B266FF")
            recs = get_lift_recommendations(df_lifts, readiness, zona)
            if recs:
                for rec in recs:
                    st.markdown(rec)
            
            with st.expander("📊 Ver detalle de lifts"):
                # Verificar qué columnas existen
                available_cols = []
                for col in ['exercise', 'sets', 'reps', 'weight', 'volume']:
                    if col in df_lifts.columns:
                        available_cols.append(col)
                
                if available_cols:
                    st.dataframe(df_lifts[available_cols], use_container_width=True)
                else:
                    st.dataframe(df_lifts, use_container_width=True)
    
    # Gráficas de tendencias
    render_section_title("📈 Tendencias (últimos 7 días)", accent="#4ECDC4")
    
    chart_data = df_filtered[df_filtered['date'] <= selected_date].tail(7).copy()
    if not chart_data.empty:
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            readiness_chart = chart_data.set_index('date')['readiness_score']
            fig = create_readiness_chart(readiness_chart, "Readiness")
            st.plotly_chart(fig, use_container_width=True)
        
        with col_chart2:
            sleep_chart = chart_data.set_index('date')['sleep_hours']
            fig = create_sleep_chart(sleep_chart, "Sueño")
            st.plotly_chart(fig, use_container_width=True)
        
        col_chart3, col_chart4 = st.columns(2)
        with col_chart3:
            if 'volume_total' in chart_data.columns:
                volume_chart = chart_data.set_index('date')['volume_total']
                fig = create_volume_chart(volume_chart, "Volumen")
                st.plotly_chart(fig, use_container_width=True)
        
        with col_chart4:
            acwr_chart = chart_data.set_index('date')['acwr_7_28']
            fig = create_acwr_chart(acwr_chart, "ACWR (Carga)")
            st.plotly_chart(fig, use_container_width=True)


def render_week_view(df_filtered, df_weekly, user_profile):
    """Renderiza la vista semanal con métricas macro y planificación."""
    render_section_title("Semana — Macro", accent="#4ECDC4")
    
    if df_weekly is None:
        st.info("No hay datos semanales disponibles.")
        return
        
    df_weekly['week_start'] = pd.to_datetime(df_weekly['week_start']).dt.date
    max_week = df_weekly['week_start'].max()
    start_week = max_week - datetime.timedelta(weeks=12)
    df_weekly_filtered = df_weekly[df_weekly['week_start'] >= start_week].copy()
    
    if df_weekly_filtered.empty:
        st.info("No hay datos semanales disponibles.")
        return
    
    df_weekly_display = df_weekly_filtered.sort_values('week_start', ascending=False).copy()
    
    if 'readiness_score' in df_filtered.columns:
        readiness_by_week = df_filtered.groupby(pd.to_datetime(df_filtered['date']).dt.to_period('W').dt.start_time)['readiness_score'].mean().reset_index()
        readiness_by_week.columns = ['week_start', 'avg_readiness']
        readiness_by_week['week_start'] = readiness_by_week['week_start'].dt.date
        df_weekly_display = df_weekly_display.merge(readiness_by_week, on='week_start', how='left')
    
    # Verificar qué columnas existen
    available_cols = ['week_start']
    optional_cols = ['volume_total', 'sets_total', 'strain', 'acwr_7_28', 'avg_readiness']
    for col in optional_cols:
        if col in df_weekly_display.columns:
            available_cols.append(col)
    
    if len(available_cols) > 1:
        st.dataframe(df_weekly_display[available_cols].head(12), use_container_width=True)
    else:
        st.warning("No hay suficientes columnas disponibles en los datos semanales.")
    
    render_section_title("📊 Tendencias Semanales", accent="#FFB81C")
    col_w1, col_w2 = st.columns(2)
    
    with col_w1:
        if 'volume_total' in df_weekly_display.columns:
            weekly_volume = df_weekly_display.set_index('week_start')['volume_total'].tail(12)
            fig = create_weekly_volume_chart(weekly_volume, "Volumen Semanal")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Columna 'volume_total' no disponible")
    
    with col_w2:
        if 'strain' in df_weekly_display.columns:
            weekly_strain = df_weekly_display.set_index('week_start')['strain'].tail(12)
            fig = create_weekly_strain_chart(weekly_strain, "Strain Semanal")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Columna 'strain' no disponible")
    
    render_section_title("🧠 Personalización & Insights", accent="#B266FF")
    
    archetype = user_profile.get('archetype', {}).get('archetype', 'unknown')
    confidence = user_profile.get('archetype', {}).get('confidence', 0)
    
    col_p1, col_p2 = st.columns([1, 2])
    with col_p1:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, rgba(178,102,255,0.15), rgba(0,0,0,0.05)); padding: 16px; border-radius: 10px; border: 1px solid rgba(178,102,255,0.3); text-align: center;">
            <div style="font-size: 2.5em; margin-bottom: 8px;">🧬</div>
            <div style="color: #B266FF; font-weight: 700; font-size: 1.2em; text-transform: uppercase;">{archetype}</div>
            <div style="color: #9CA3AF; margin-top: 6px;">Confianza: {confidence:.0%}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col_p2:
        insights = user_profile.get('insights', [])
        if insights:
            st.markdown("**Insights personalizados:**")
            for insight in insights[:5]:
                st.markdown(f"- {insight}")
        else:
            st.info("No hay insights suficientes aún. Más datos = mejor personalización.")
    
    render_section_title("🔮 Análisis de Fatiga & Planificación", accent="#4ECDC4")
    
    baselines = calculate_personal_baselines(df_filtered)
    latest_row = df_filtered.iloc[-1] if not df_filtered.empty else None
    
    if latest_row is not None:
        fatigue_analysis = detect_fatigue_type(
            latest_row['readiness_score'],
            latest_row['sleep_hours'],
            latest_row.get('performance_index', 1.0),
            latest_row['fatigue'],
            latest_row['motivation'],
            baselines
        )
        
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.markdown(f"""
            **Tipo de fatiga:** {fatigue_analysis['type'].upper()}  
            **Confianza:** {fatigue_analysis['confidence']}  
            **Severidad:** {fatigue_analysis['severity']}
            """)
        
        with col_f2:
            st.markdown("**Indicadores detectados:**")
            for indicator in fatigue_analysis['indicators']:
                st.markdown(f"- {indicator}")
        
        st.markdown("**Split recomendado:**")
        split = fatigue_analysis['target_split'].upper()
        split_emoji = {"UPPER": "💪", "LOWER": "🦵", "REST": "😴", "LIGHT": "🚶"}.get(split, "🏋️")
        st.markdown(f"{split_emoji} **{split}** — {fatigue_analysis['reasoning']}")
        
        weekly_plan = suggest_weekly_sequence(df_filtered, baselines)
        if weekly_plan:
            render_section_title("📅 Plan Semanal Sugerido", accent="#00D084")
            st.markdown("**Secuencia óptima para los próximos 7 días:**")
            for day_plan in weekly_plan:
                day_num = day_plan.get('day', '?')
                split_type = day_plan.get('split', 'rest').upper()
                intensity = day_plan.get('intensity', 'moderate')
                reason = day_plan.get('reason', '')
                
                day_emoji = {"UPPER": "💪", "LOWER": "🦵", "FULL": "🏋️", "REST": "😴", "LIGHT": "🚶"}.get(split_type, "🏋️")
                st.markdown(f"**Día {day_num}:** {day_emoji} {split_type} ({intensity}) — {reason}")
    
    render_section_title("📚 Contexto & Educación", accent="#FFB81C")
    
    with st.expander("ℹ️ ¿Qué es ACWR?"):
        st.markdown("""
**ACWR (Acute:Chronic Workload Ratio)** compara tu carga de trabajo reciente (7 días) con tu carga crónica (28 días).

- **ACWR < 0.8:** Subcarga → riesgo de pérdida de forma.
- **ACWR 0.8–1.3:** Zona óptima → progreso seguro.
- **ACWR > 1.3:** Sobrecarga → riesgo de lesión.

**Cómo usarlo:** Si tu ACWR está >1.5, considera reducir volumen 10-20% esta semana.
        """)
    
    with st.expander("🧬 ¿Qué son los arquetipos?"):
        st.markdown("""
El sistema analiza tus patrones de recuperación y los clasifica en arquetipos:

- **Sleep Responsive:** Te recuperas principalmente con sueño de calidad.
- **High Capacity:** Toleras mucho volumen sin fatiga excesiva.
- **Fragile:** Necesitas más días de recuperación entre sesiones intensas.
- **Balanced:** Respondes de forma estándar a todos los factores.

**Beneficio:** El dashboard ajusta las recomendaciones según tu arquetipo detectado.
        """)
    
    with st.expander("⚠️ Errores comunes en gestión de carga"):
        st.markdown("""
**1. Ignorar el readiness score:**  
Entrenar duro con readiness <50 aumenta el riesgo de lesión 3-4x.

**2. No respetar descargas:**  
Semanas de descarga (40-60% volumen) cada 3-4 semanas son esenciales.

**3. Subir volumen >10% por semana:**  
El cuerpo necesita adaptarse gradualmente. Incrementos bruscos = lesión.

**Errores comunes:** Ignorar descargas → acumulación innecesaria de fatiga.
        """)
    
    st.markdown("---")
    st.caption("🔄 La app muestra datos ya procesados. Ejecuta el pipeline para recalcular.")


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
    view_mode = st.sidebar.radio("Vista", ["Día", "Modo Hoy", "Semana"], key="view_mode")

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
    
    if view_mode == "Día":
        selected_date = st.sidebar.selectbox("Selecciona fecha", options=dates_filtered, 
                                            index=dates_filtered.index(default_date) if default_date in dates_filtered else 0) if dates_filtered else None
    else:
        selected_date = default_date

    # === CARGAR PERFIL PERSONALIZADO ===
    user_profile = load_user_profile()

    # ============== ROUTING TO VIEWS ==============
    if view_mode == "Día":
        render_day_view(df_filtered, selected_date, user_profile, daily_ex_path if daily_ex_path.exists() else None)
    
    elif view_mode == "Semana":
        render_week_view(df_filtered, df_weekly, user_profile)
    
    elif view_mode == "Modo Hoy":
        render_today_mode(df_daily)


if __name__ == '__main__':
    main()

