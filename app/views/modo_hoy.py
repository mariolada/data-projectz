"""
Vista Modo Hoy - Cálculo instantáneo de readiness.
"""
import streamlit as st
import pandas as pd
import numpy as np
import datetime

from ui.styles import inject_mode_today_css, inject_mode_today_header
from ui.components import render_section_title
from ui.loader import loading
from ui.helpers import (
    render_badge, render_card, clean_line,
    get_sleep_hours_level, get_sleep_quality_level,
    get_fatigue_level, get_stress_level, get_soreness_level,
    get_energy_level, get_perceived_level,
    render_neural_fatigue_section
)
from data.loaders import load_user_profile, save_mood_to_csv, load_neural_overload_flags
from calculations.readiness import (
    calculate_readiness_from_inputs_v2,
    generate_personalized_insights,
    get_readiness_zone,
    generate_actionable_plan_v2,
    calculate_injury_risk_score_v2
)
from charts.daily_charts import (
    create_readiness_chart,
    create_volume_chart,
    create_sleep_chart,
    create_acwr_chart
)

# Import desde src (estos se añaden al path en streamlit_app.py)
from personalization_engine import (
    calculate_personal_baselines,
    contextualize_readiness,
    detect_fatigue_type,
    calculate_injury_risk_score
)


def render_modo_hoy(df_daily: pd.DataFrame):
    """
    Renderiza la vista Modo Hoy completa.
    
    Args:
        df_daily: DataFrame con datos diarios procesados
    """
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
        with loading("Calculando readiness..."):
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
            
            # === ALERTAS DE SOBRECARGA NEUROMUSCULAR ===
            overload_data = load_neural_overload_flags()
            if overload_data.get('flags') and len(overload_data['flags']) > 0:
                st.markdown("---")
                render_section_title("🧠 Fatiga Neural Detectada", accent="#E07040")
                
                # Renderizar sección completa con nuevo diseño premium
                render_neural_fatigue_section(overload_data)
        
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
