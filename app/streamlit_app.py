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

# Añadir paths para imports
APP_DIR = Path(__file__).parent
SRC_DIR = APP_DIR.parent / 'src'
sys.path.insert(0, str(APP_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Imports desde módulos locales
from data.loaders import load_csv, load_user_profile, load_daily_exercise_for_date, save_mood_to_csv
from calculations.readiness import (
    calculate_readiness_from_inputs,
    calculate_readiness_from_inputs_v2,
    generate_personalized_insights,
    get_readiness_zone,
    get_days_until_acwr,
    format_acwr_display,
    generate_actionable_plan,
    generate_actionable_plan_v2,
    calculate_injury_risk_score_v2,
    get_confidence_level,
    get_anti_fatigue_flag,
    format_reason_codes,
    get_lift_recommendations
)
from charts.daily_charts import (
    create_readiness_chart,
    create_volume_chart,
    create_sleep_chart,
    create_acwr_chart,
    create_performance_chart,
    create_strain_chart
)
from charts.weekly_charts import create_weekly_volume_chart, create_weekly_strain_chart
from ui.components import render_section_title
from ui.styles import inject_main_css, inject_hero, inject_mode_today_css, inject_mode_today_header
from ui.helpers import (
    render_badge, render_card, clean_line,
    get_sleep_hours_level, get_sleep_quality_level,
    get_fatigue_level, get_stress_level, get_soreness_level,
    get_energy_level, get_perceived_level
)

# Imports desde src
from personalization_engine import (
    calculate_personal_baselines,
    contextualize_readiness,
    detect_fatigue_type,
    calculate_injury_risk_score,
    suggest_weekly_sequence
)


def main():
    st.set_page_config(page_title="Trainer Readiness Dashboard", layout="wide")
    
    # Inyectar CSS principal y Hero
    inject_main_css(st)
    inject_hero(st)

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
                    alerts.append(" **Sueño bajo**: reduce volumen hoy")
                if pd.notna(r.get('acwr_7_28', None)) and r['acwr_7_28'] > 1.5:
                    alerts.append(" **Carga aguda muy alta**: evita máximos hoy")
                
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
        # Inyectar CSS y Header del Modo Hoy
        inject_mode_today_css(st)
        inject_mode_today_header(st)
        
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
                        # Mostrar nivel basado en strength del análisis
                        strength = sleep_resp.get('strength', 'unknown')
                        strength_labels = {
                            'none': 'Bajo',
                            'weak': 'Débil', 
                            'moderate': 'Moderado',
                            'strong': 'Alto',
                            'unknown': 'Desconocido'
                        }
                        st.markdown(f"**Impacto del sueño:** {strength_labels.get(strength, 'Desconocido')}")
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
                    
                    # Expander explicativo
                    with st.expander("¿Qué significan estos factores?"):
                        st.markdown("""
**Sleep Weight** (Peso del sueño)
- Valor por defecto: 0.25
- Cuánto influye el sueño en tu cálculo de readiness
- Si es **mayor** que 0.25: el sueño te afecta más que a la media, priorízalo
- Si es **menor** que 0.25: el sueño no es tu factor clave, otros aspectos te impactan más

**Performance Weight** (Peso del rendimiento)
- Valor por defecto: 0.25  
- Cuánto pesa tu tendencia de rendimiento reciente (subiendo/bajando)
- Si es **mayor**: tu progresión es muy predecible, aprovecha rachas buenas
- Si es **menor**: tu rendimiento fluctúa por otros factores

**Fatigue Sensitivity** (Sensibilidad a la fatiga)
- Valor por defecto: 1.0x
- Cómo te afecta la fatiga acumulada (RIR bajo, esfuerzo alto)
- Si es **mayor que 1.0x**: eres muy sensible, respeta los deloads
- Si es **menor que 1.0x**: toleras bien la fatiga, puedes sostener cargas altas
                        """)
        
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
            txt, lvl = get_sleep_hours_level(sleep_h)
            render_badge(txt, lvl)
        
        with col_rec2:
            sleep_q = st.slider("Calidad del sueño", 1, 5, st.session_state.get('mood_sleep_q', 4), 
                               help="1=Muy malo (despertares constantes), 5=Perfecto", key="input_sleep_q")
            quality_labels = {1: "Horrible", 2: "Malo", 3: "Regular", 4: "Bueno", 5: "Perfecto"}
            st.caption("Fatiga alta puede reducir tu readiness")
            txt, lvl = get_sleep_quality_level(sleep_q)
            render_badge(txt, lvl)
            
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
        txt, lvl = get_perceived_level(perceived_readiness)
        render_badge(txt, lvl)
        st.write("")
        
        col_st1, col_st2, col_st3, col_st4 = st.columns(4)
        
        with col_st1:
            fatigue = st.slider("Fatiga/Cansancio", 0, 10, st.session_state.get('mood_fatigue', 3), 
                               help="0=Fresco, 5=Normal, >=7 afecta rendimiento", key="input_fatigue")
            txt, lvl = get_fatigue_level(fatigue)
            render_badge(txt, lvl)
        
        with col_st2:
            stress = st.slider("Estrés mental", 0, 10, st.session_state.get('mood_stress', 3), 
                              help="0=Relajado, >=7 suele bajar rendimiento en básicos", key="input_stress")
            txt, lvl = get_stress_level(stress)
            render_badge(txt, lvl)
        
        with col_st3:
            if not quick_mode:
                soreness = st.slider("Agujetas/DOMS", 0, 10, st.session_state.get('mood_soreness', 2), 
                                    help="Dolor muscular general post-entreno", key="input_soreness")
                txt, lvl = get_soreness_level(soreness)
                render_badge(txt, lvl)
            else:
                soreness = 2  # Valor por defecto en modo rápido
        
        with col_st4:
            if not quick_mode:
                energy = st.slider("Energía general", 0, 10, st.session_state.get('mood_energy', 7), 
                                  help="Sensación de vitalidad (a veces 'fatiga' no captura todo)", key="input_energy")
                txt, lvl = get_energy_level(energy)
                render_badge(txt, lvl)
            else:
                energy = 10 - fatigue  # Derivar del fatigue
            
        # Fila 2 de Estado (solo modo completo)
        if not quick_mode:
            col_st5, col_st6, col_st7, col_st8 = st.columns(4)
            
            with col_st5:
                motivation = st.slider("Motivación/Ganas", 0, 10, st.session_state.get('mood_motivation', 7), 
                                      help="0=Ninguna, 10=Máxima", key="input_motivation")
                st.caption(f" {motivation}/10")
            
            with col_st6:
                stiffness = st.slider("Rigidez articular", 0, 10, st.session_state.get('mood_stiffness', 2), 
                                     help="Movilidad limitada, calentar costará más", key="input_stiffness")
                st.caption(f" {stiffness}/10")
            
            with col_st7:
                caffeine = st.selectbox("Cafeína (últimas 6h)", [0, 1, 2, 3], 
                                       index=st.session_state.get('mood_caffeine', 0),
                                       help="Cafés/energéticos consumidos", key="input_caffeine")
                st.caption(f" {caffeine} dosis")
            
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
            st.write("** Enfermo/Resfriado**")
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
            " CALCULAR READINESS & PLAN",
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
                        label = " Sueño"
                    elif key == 'state':
                        label = " Estado (Fatiga/Estrés)"
                    elif key == 'motivation':
                        label = " Motivación"
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
                                label = " Dolor"
                            elif key == 'sick_penalty':
                                label = " Enfermedad"
                            elif key == 'caffeine_mask':
                                label = " Cafeína"
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
                    st.info(" **ERES SENSIBLE AL SUEÑO**\nPrioriza dormir bien para optimizar readiness", icon="💤")
                else:
                    st.success(" **NO ERES TAN SENSIBLE AL SUEÑO**\nTienes flexibilidad con horas, pero calidad importa", icon="🎯")
                
                # Baseline comparison
                if baselines.get('readiness', {}).get('p50'):
                    p50 = baselines['readiness']['p50']
                    delta = readiness_instant - p50
                    if delta > 5:
                        st.success(f" Hoy +{delta:.0f} vs tu media ({p50:.0f})", icon="✅")
                    elif delta > -5:
                        st.info(f" Hoy ~igual a media ({p50:.0f})", icon="ℹ️")
                    else:
                        st.warning(f" Hoy {delta:.0f} vs media ({p50:.0f})", icon="⚠️")
            
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
                    plan_clean = [s for s in (clean_line(p) for p in plan) if s]
                    render_card("Plan accionable", plan_clean, accent="#FFB81C")

                rules_clean = [s for s in (clean_line(r) for r in rules) if s]
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
            render_section_title(" Métricas Semanales", accent="#00D084")
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
            render_section_title(" Readiness & Performance", accent="#B266FF")
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
            render_section_title(" Esfuerzo & Monotonía", accent="#FF6B6B")
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
            render_section_title(" Sueño & Fatiga", accent="#4ECDC4")
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
    # Solo mostrar esta sección si NO estamos en Modo Hoy (para evitar duplicación
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
                        st.warning(" Performance Index sin datos disponibles. Verifica que daily.csv tenga la columna 'performance_index' con valores numéricos o ejecuta el pipeline que lo calcule.")
            else:
                st.warning(" Performance Index no existe en los datos (falta la columna performance_index).")
                
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
