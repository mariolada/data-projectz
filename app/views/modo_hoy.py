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
    render_neural_fatigue_section,
    render_consejos_section,
    render_desglose_section,
    render_readiness_section,
    # Nuevos componentes del cuestionario
    _get_recovery_status, _get_state_status, _count_flags,
    render_live_summary, render_wizard_progress, render_step_header,
    render_micro_badge, render_intuition_slider_label,
    render_section_divider, render_collapsible_flags_header,
    render_quick_mode_section_header,
    render_status_badge, render_slider_scale
)
from data.loaders import load_user_profile, save_mood_to_csv, load_neural_overload_flags
from calculations.readiness import (
    calculate_readiness_from_inputs_v3_compat,  # v3 ahora es el algoritmo principal (NASA)
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
from menstrual_cycle_readiness import adjust_readiness_for_menstrual_cycle


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
    
    # =============================================================
    # QUESTIONNAIRE WRAPPER (single card with green left accent line)
    # =============================================================
    with st.container(border=True):
        # Inject inline style to force the green left border on this container
        st.markdown('''
            <style>
            /* Target ONLY the stVerticalBlock that has the marker as a DIRECT descendant */
            div[data-testid="stVerticalBlock"]:has(> div[data-testid="stElementContainer"] #mh-questionnaire-wrap) {
                border-left: 4px solid #00D084 !important;
                padding-left: 16px !important;
            }
            #mh-questionnaire-wrap { height:0; overflow:hidden; margin:0; padding:0; display:block; }
            </style>
            <div id="mh-questionnaire-wrap"></div>
        ''', unsafe_allow_html=True)

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

        # === INICIALIZAR VALORES POR DEFECTO ===
        # Estos se usarán para el resumen en vivo
        sleep_h = st.session_state.get('mood_sleep_h', 7.5)
        sleep_q = st.session_state.get('mood_sleep_q', 4)
        sleep_disruptions = st.session_state.get('mood_sleep_disruptions', False)
        nap_mins = st.session_state.get('mood_nap_mins', 0)
        perceived_readiness = st.session_state.get('mood_perceived_readiness', 7)
        fatigue = st.session_state.get('mood_fatigue', 3)
        stress = st.session_state.get('mood_stress', 3)
        soreness = st.session_state.get('mood_soreness', 2)
        energy = st.session_state.get('mood_energy', 7)
        motivation = st.session_state.get('mood_motivation', 7)
        stiffness = st.session_state.get('mood_stiffness', 2)
        caffeine = st.session_state.get('mood_caffeine', 0)
        alcohol = st.session_state.get('mood_alcohol', False)
        pain_flag = st.session_state.get('mood_pain_flag', False)
        sick_flag = st.session_state.get('mood_sick_flag', False)
        last_hard = st.session_state.get('mood_last_hard', False)
        # Variables adicionales que pueden no definirse en todos los pasos
        sick_level = st.session_state.get('mood_sick_level', 0)
        session_goal = st.session_state.get('mood_session_goal', 'fuerza')
        time_available = st.session_state.get('mood_time_available', 60)
        pain_zone = st.session_state.get('mood_pain_zone', None)
        pain_side = st.session_state.get('mood_pain_side', None)
        pain_severity = st.session_state.get('mood_pain_severity', 0)
        pain_type = st.session_state.get('mood_pain_type', None)
        pain_location = st.session_state.get('mood_pain_location', '')

        # === WIZARD STATE (solo modo preciso) ===
        if 'wizard_step' not in st.session_state:
            st.session_state.wizard_step = 1

        # =========================================================================
        # MODO RÁPIDO: Vista compacta en 1 pantalla
        # =========================================================================
        if quick_mode:
            st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)

            # --- RECUPERACIÓN (compacto) ---
            render_quick_mode_section_header("Recuperación", "")

            with st.container(border=True):
                col_r1, col_r2, col_r3 = st.columns([1, 1, 1])

                with col_r1:
                    sleep_h = st.number_input(
                        "Horas de sueño",
                        min_value=0.0, max_value=12.0,
                        value=float(st.session_state.get('mood_sleep_h', 7.5)),
                        step=0.5,
                        key="quick_sleep_h",
                        help="Horas totales en las últimas 24h"
                    )
                    txt, lvl = get_sleep_hours_level(sleep_h)
                    render_micro_badge(txt, lvl)

                with col_r2:
                    sleep_q = st.slider(
                        "Calidad (1-5)", 1, 5,
                        st.session_state.get('mood_sleep_q', 4),
                        key="quick_sleep_q",
                        help="1=Muy malo, 5=Perfecto"
                    )
                    render_slider_scale("Mala", "OK", "Perfecta")
                    txt, lvl = get_sleep_quality_level(sleep_q)
                    render_micro_badge(txt, lvl)

                with col_r3:
                    sleep_disruptions = st.checkbox(
                        "Sueño fragmentado",
                        value=st.session_state.get('mood_sleep_disruptions', False),
                        key="quick_disruptions",
                        help="3+ despertares durante la noche"
                    )
                    nap_mins = 0  # En modo rápido no se pregunta siesta

            # --- ESTADO (compacto) ---
            render_quick_mode_section_header("Cómo estás ahora", "")

            with st.container(border=True):
                # Input dominante: Intuición
                with st.container(border=True):
                    st.markdown(
                        '<div style="color:#4ECDC4;font-size:0.8rem;font-weight:650;margin-bottom:8px;">'
                        'TU INTUICIÓN HOY <span style="color:#9CA3AF; font-weight:600;">(input principal)</span>'
                        '</div>',
                        unsafe_allow_html=True
                    )
                    perceived_readiness = st.slider(
                        "¿Cómo te sientes de 0 a 10?", 0, 10,
                        st.session_state.get('mood_perceived_readiness', 7),
                        key="quick_perceived",
                        label_visibility="collapsed"
                    )
                    render_slider_scale("Mal", "Normal", "Genial")
                    render_intuition_slider_label(perceived_readiness)

            # Inputs secundarios en grid 2x2
            col_s1, col_s2 = st.columns(2)

            with col_s1:
                fatigue = st.slider(
                    "Fatiga/Cansancio", 0, 10,
                    st.session_state.get('mood_fatigue', 3),
                    key="quick_fatigue",
                    help="0=Fresco, 10=Agotado"
                )
                render_slider_scale("Fresco", "OK", "Agotado")
                txt, lvl = get_fatigue_level(fatigue)
                render_micro_badge(txt, lvl)

            with col_s2:
                stress = st.slider(
                    "Estrés mental", 0, 10,
                    st.session_state.get('mood_stress', 3),
                    key="quick_stress",
                    help="0=Relajado, 10=Muy estresado"
                )
                render_slider_scale("Calma", "OK", "Alto")
                txt, lvl = get_stress_level(stress)
                render_micro_badge(txt, lvl)

            # Energía en fila completa (agujetas solo en modo preciso)
            energy = st.slider(
                "Energía", 0, 10,
                st.session_state.get('mood_energy', 7),
                key="quick_energy",
                help="Sensación de vitalidad"
            )
            render_slider_scale("Baja", "OK", "Alta")
            txt, lvl = get_energy_level(energy)
            render_micro_badge(txt, lvl)

            # Valores por defecto en modo rápido (optimistas para no penalizar injustamente)
            soreness = 0  # Sin dolor muscular
            motivation = 8  # Motivación buena por defecto
            stiffness = 0  # Sin rigidez

            # --- FLAGS (colapsable) ---
            # Importante: en modo rápido, los widgets usan claves `quick_*`.
            # Para el label del expander usamos session_state para reflejar el estado actual.
            alcohol_ss = st.session_state.get('quick_alcohol', st.session_state.get('mood_alcohol', False))
            caffeine_ss = st.session_state.get('quick_caffeine', st.session_state.get('mood_caffeine', 0))
            sick_ss = st.session_state.get('quick_sick', st.session_state.get('mood_sick_flag', False))
            last_hard_ss = st.session_state.get('quick_lasthard', st.session_state.get('mood_last_hard', False))
            sleep_disruptions_ss = st.session_state.get('quick_disruptions', sleep_disruptions)
            flag_count = sum([alcohol_ss, caffeine_ss >= 2, pain_flag, sick_ss, sleep_disruptions_ss, last_hard_ss])

            # Label simple para el expander (no acepta HTML)
            if flag_count == 0:
                flags_label = "Algo fuera de lo normal? (Sin alertas)"
            elif flag_count == 1:
                flags_label = "Algo fuera de lo normal? (1 alerta)"
            else:
                flags_label = f"Algo fuera de lo normal? ({flag_count} alertas)"

            with st.expander(flags_label, expanded=False):
                col_f1, col_f2 = st.columns(2)

                with col_f1:
                    alcohol = st.checkbox(
                        "Alcohol anoche",
                        value=st.session_state.get('mood_alcohol', False),
                        key="quick_alcohol"
                    )
                    if alcohol:
                        st.caption("Impacto: recuperación -5 a -15")

                    caffeine = st.selectbox(
                        "Cafeína (últimas 6h)",
                        [0, 1, 2, 3],
                        index=st.session_state.get('mood_caffeine', 0),
                        key="quick_caffeine"
                    )
                    if caffeine >= 2:
                        st.caption("Puede enmascarar fatiga real")

                with col_f2:
                    sick_flag = st.checkbox(
                        "Enfermo/resfriado",
                        value=st.session_state.get('mood_sick_flag', False),
                        key="quick_sick"
                    )
                    if sick_flag:
                        st.caption("Impacto: -20 a -40 readiness")

                    last_hard = st.checkbox(
                        "Último entreno muy duro",
                        value=st.session_state.get('mood_last_hard', False),
                        key="quick_lasthard"
                    )
                    if last_hard:
                        st.caption("Posible fatiga residual")

                # En modo rápido, dolor y otros son simplificados
                pain_flag = False
                pain_zone = None
                pain_side = None
                pain_severity = 0
                pain_type = None
                pain_location = ""
                sick_level = 2 if sick_flag else 0
                session_goal = "fuerza"
                time_available = 60

            # CICLO MENSTRUAL (modo rápido)
            user_gender = st.session_state.get('user_gender', None)
            menstrual_cycle_data = None
            
            if user_gender == "mujer":
                st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
                from ui.profile_helpers import render_menstrual_cycle_questionnaire
                
                with st.container(border=True):
                    st.markdown("""
                    <div style='background:rgba(217, 71, 239, 0.08);border:1px solid rgba(217, 71, 239, 0.25);
                    border-radius:12px;padding:16px;margin-bottom:16px;'>
                        <div style='color:#D947EF;font-size:0.9rem;font-weight:600;'>Ciclo Menstrual</div>
                        <div style='color:#9CA3AF;font-size:0.85rem;margin-top:6px;'>
                        Esta información se usará para ajustar tu readiness según tu fase del ciclo.
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    menstrual_cycle_data = render_menstrual_cycle_questionnaire()
                    st.session_state['menstrual_cycle_data'] = menstrual_cycle_data

        # =========================================================================
        # MODO PRECISO: Wizard de 3 pasos
        # =========================================================================
        else:
            st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)

            # Wizard progress bar
            render_wizard_progress(st.session_state.wizard_step)

            # =====================================================================
            # PASO 1: RECUPERACIÓN
            # =====================================================================
            if st.session_state.wizard_step == 1:
                render_step_header(1, "Recuperación", "Cómo dormiste y descansaste")

                col_r1, col_r2 = st.columns(2)

                with col_r1:
                    with st.container(border=True):
                        st.caption("Horas de sueño")
                        sleep_h = st.number_input(
                            "Horas",
                            min_value=0.0, max_value=12.0,
                            value=float(st.session_state.get('mood_sleep_h', 7.5)),
                            step=0.5,
                            key="wiz_sleep_h",
                            label_visibility="collapsed"
                        )
                        txt, lvl = get_sleep_hours_level(sleep_h)
                        render_micro_badge(txt, lvl)

                    with st.container(border=True):
                        st.caption("Calidad del sueño")
                        sleep_q = st.slider(
                            "Calidad", 1, 5,
                            st.session_state.get('mood_sleep_q', 4),
                            key="wiz_sleep_q",
                            label_visibility="collapsed"
                        )
                        render_slider_scale("Mala", "OK", "Perfecta")
                        quality_map = {1: "Muy malo", 2: "Malo", 3: "Regular", 4: "Bueno", 5: "Perfecto"}
                        st.caption(f"{quality_map[sleep_q]}")
                        txt, lvl = get_sleep_quality_level(sleep_q)
                        render_micro_badge(txt, lvl)

                with col_r2:
                    with st.container(border=True):
                        st.caption("Siesta")
                        nap_options = {
                            "Sin siesta": 0,
                            "Power nap (20 min)": 20,
                            "Siesta media (45 min)": 45,
                            "Ciclo completo (90 min)": 90,
                        }
                        current_nap = st.session_state.get('mood_nap_mins', 0)
                        nap_index = list(nap_options.values()).index(current_nap) if current_nap in nap_options.values() else 0
                        nap_selection = st.selectbox(
                            "Siesta",
                            list(nap_options.keys()),
                            index=nap_index,
                            key="wiz_nap",
                            label_visibility="collapsed"
                        )
                        nap_mins = nap_options[nap_selection]

                    with st.container(border=True):
                        st.caption("Sueño fragmentado")
                        sleep_disruptions = st.checkbox(
                            "3+ despertares",
                            value=st.session_state.get('mood_sleep_disruptions', False),
                            key="wiz_disruptions"
                        )
                        if sleep_disruptions:
                            st.caption("Impacto: reduce calidad de recuperación")

                # Feedback de paso
                recovery_status = _get_recovery_status(sleep_h, sleep_q, sleep_disruptions)
                render_status_badge("Recuperación", recovery_status)

                # CICLO MENSTRUAL (solo en modo preciso, en Paso 1)
                user_gender = st.session_state.get('user_gender', None)
                menstrual_cycle_data = None
                
                if user_gender == "mujer":
                    st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)
                    from ui.profile_helpers import render_menstrual_cycle_questionnaire
                    
                    with st.container(border=True):
                        st.markdown("""
                        <div style='background:rgba(217, 71, 239, 0.08);border:1px solid rgba(217, 71, 239, 0.25);
                        border-radius:12px;padding:16px;margin-bottom:16px;'>
                            <div style='color:#D947EF;font-size:0.9rem;font-weight:600;'>Ciclo Menstrual</div>
                            <div style='color:#9CA3AF;font-size:0.85rem;margin-top:6px;'>
                            Esta información se usará para ajustar tu readiness según tu fase del ciclo.
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        menstrual_cycle_data = render_menstrual_cycle_questionnaire()
                        st.session_state['menstrual_cycle_data'] = menstrual_cycle_data

                # Botón siguiente
                st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
                if st.button("Siguiente → Estado", width="stretch", type="primary", key="wiz_next_1"):
                    st.session_state.mood_sleep_h = sleep_h
                    st.session_state.mood_sleep_q = sleep_q
                    st.session_state.mood_nap_mins = nap_mins
                    st.session_state.mood_sleep_disruptions = sleep_disruptions
                    st.session_state.wizard_step = 2
                    st.rerun()

            # =====================================================================
            # PASO 2: ESTADO
            # =====================================================================
            elif st.session_state.wizard_step == 2:
                render_step_header(2, "Estado", "Cómo te sientes ahora mismo")

                # Input dominante: Intuición
                st.markdown(
                    '<div style="background:rgba(78,205,196,0.08);border:1px solid rgba(78,205,196,0.25);'
                    'border-radius:12px;padding:20px;margin-bottom:20px;">'
                    '<div style="color:#4ECDC4;font-size:0.85rem;font-weight:600;margin-bottom:12px;">'
                    'TU INTUICIÓN — El input más importante</div>',
                    unsafe_allow_html=True
                )
                perceived_readiness = st.slider(
                    "¿Cómo te sientes hoy de 0 a 10?", 0, 10,
                    st.session_state.get('mood_perceived_readiness', 7),
                    key="wiz_perceived",
                    label_visibility="collapsed"
                )
                render_slider_scale("Mal", "Normal", "Genial")
                render_intuition_slider_label(perceived_readiness)
                st.markdown('</div>', unsafe_allow_html=True)

                # Inputs secundarios en grid
                st.caption("Detalles adicionales")

                col_e1, col_e2, col_e3 = st.columns(3)

                with col_e1:
                    fatigue = st.slider(
                        "Fatiga/Cansancio", 0, 10,
                        st.session_state.get('mood_fatigue', 3),
                        key="wiz_fatigue",
                        help="0=Fresco, 10=Agotado"
                    )
                    render_slider_scale("Fresco", "OK", "Agotado")
                    txt, lvl = get_fatigue_level(fatigue)
                    render_micro_badge(txt, lvl)

                    energy = st.slider(
                        "Energía", 0, 10,
                        st.session_state.get('mood_energy', 7),
                        key="wiz_energy",
                        help="Sensación de vitalidad"
                    )
                    render_slider_scale("Baja", "OK", "Alta")
                    txt, lvl = get_energy_level(energy)
                    render_micro_badge(txt, lvl)

                with col_e2:
                    stress = st.slider(
                        "Estrés mental", 0, 10,
                        st.session_state.get('mood_stress', 3),
                        key="wiz_stress",
                        help="0=Relajado, 10=Muy estresado"
                    )
                    render_slider_scale("Calma", "OK", "Alto")
                    txt, lvl = get_stress_level(stress)
                    render_micro_badge(txt, lvl)

                    motivation = st.slider(
                        "Motivación", 0, 10,
                        st.session_state.get('mood_motivation', 7),
                        key="wiz_motivation",
                        help="Ganas de entrenar"
                    )
                    render_slider_scale("Baja", "OK", "Alta")
                    render_micro_badge(f"{motivation}/10", "ok" if motivation >= 7 else "mid" if motivation >= 4 else "low")

                with col_e3:
                    soreness = st.slider(
                        "Agujetas/DOMS", 0, 10,
                        st.session_state.get('mood_soreness', 2),
                        key="wiz_soreness",
                        help="Dolor muscular post-entreno"
                    )
                    render_slider_scale("Bajas", "OK", "Altas")
                    txt, lvl = get_soreness_level(soreness)
                    render_micro_badge(txt, lvl)

                    stiffness = st.slider(
                        "Rigidez articular", 0, 10,
                        st.session_state.get('mood_stiffness', 2),
                        key="wiz_stiffness",
                        help="Movilidad limitada"
                    )
                    render_slider_scale("Suelta", "OK", "Alta")
                    render_micro_badge(f"{stiffness}/10", "ok" if stiffness <= 3 else "mid" if stiffness <= 6 else "low")

                # Feedback de paso
                state_status = _get_state_status(perceived_readiness, fatigue, stress, energy)
                render_status_badge("Estado", state_status)

                # Botones navegación
                st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)
                col_nav1, col_nav2 = st.columns(2)
                with col_nav1:
                    if st.button("← Volver", width="stretch", key="wiz_back_2"):
                        st.session_state.wizard_step = 1
                        st.rerun()
                with col_nav2:
                    if st.button("Siguiente → Flags", width="stretch", type="primary", key="wiz_next_2"):
                        st.session_state.mood_perceived_readiness = perceived_readiness
                        st.session_state.mood_fatigue = fatigue
                        st.session_state.mood_stress = stress
                        st.session_state.mood_soreness = soreness
                        st.session_state.mood_energy = energy
                        st.session_state.mood_motivation = motivation
                        st.session_state.mood_stiffness = stiffness
                        st.session_state.wizard_step = 3
                        st.rerun()

            # =====================================================================
            # PASO 3: FLAGS
            # =====================================================================
            elif st.session_state.wizard_step == 3:
                render_step_header(3, "Flags", "Algo fuera de lo normal que debamos saber")

                st.caption("Estas señales pueden afectar tu capacidad de entrenar o aumentar riesgo de lesión.")

                col_fl1, col_fl2 = st.columns(2)

                with col_fl1:
                    # Alcohol
                    with st.container(border=True):
                        alcohol = st.checkbox(
                            "Alcohol anoche",
                            value=st.session_state.get('mood_alcohol', False),
                            key="wiz_alcohol"
                        )
                        if alcohol:
                            st.caption("Impacto: recuperación -5 a -15 pts")

                    # Cafeína
                    with st.container(border=True):
                        caffeine = st.selectbox(
                            "Cafeína (últimas 6h)",
                            [0, 1, 2, 3],
                            index=st.session_state.get('mood_caffeine', 0),
                            key="wiz_caffeine",
                            format_func=lambda x: f"{x} {'dosis' if x != 1 else 'dosis'}"
                        )
                        if caffeine >= 2:
                            st.caption("Puede enmascarar fatiga real")

                    # Enfermedad
                    with st.container(border=True):
                        sick_flag = st.checkbox(
                            "Enfermo/resfriado",
                            value=st.session_state.get('mood_sick_flag', False),
                            key="wiz_sick"
                        )
                        if sick_flag:
                            sick_level = st.slider(
                                "Nivel de malestar", 1, 5,
                                st.session_state.get('mood_sick_level', 2),
                                key="wiz_sick_level"
                            )
                            render_slider_scale("Leve", "Mod.", "Grave")
                            sick_labels = {1: "Leve", 2: "Leve-Moderado", 3: "Moderado", 4: "Moderado-Grave", 5: "Grave"}
                            st.caption(f"Estado: {sick_labels.get(sick_level, 'Sin malestar')}")
                            st.caption("Impacto: -20 a -40 readiness según gravedad")
                        else:
                            sick_level = 0

                with col_fl2:
                    # Último entreno duro
                    with st.container(border=True):
                        last_hard = st.checkbox(
                            "Último entreno muy exigente",
                            value=st.session_state.get('mood_last_hard', False),
                            key="wiz_lasthard",
                            help="Alta intensidad/volumen en últimas 48h"
                        )
                        if last_hard:
                            st.caption("Posible fatiga residual del SNC")

                    # Dolor localizado
                    with st.container(border=True):
                        pain_flag = st.checkbox(
                            "Dolor localizado",
                            value=st.session_state.get('mood_pain_flag', False),
                            key="wiz_pain"
                        )
                        if pain_flag:
                            zones = ["Hombro", "Codo", "Muñeca", "Espalda alta", "Espalda baja", "Cadera", "Rodilla", "Tobillo", "Otra"]
                            pain_zone = st.selectbox("Zona", zones, key="wiz_pain_zone")
                            sides = ["Izquierdo", "Derecho", "Ambos"]
                            pain_side = st.radio("Lado", sides, horizontal=True, key="wiz_pain_side")
                            pain_severity = st.slider("Severidad (0-10)", 0, 10, 5, key="wiz_pain_severity")
                            render_slider_scale("Leve", "Media", "Alta")
                            types = ["Punzante", "Molestia", "Rigidez", "Ardor"]
                            pain_type = st.selectbox("Tipo", types, key="wiz_pain_type")
                            pain_location = f"{pain_zone} {pain_side.lower()} ({pain_type}, {pain_severity}/10)"
                            st.caption("Ajustaremos ejercicios para proteger esta zona")
                        else:
                            pain_zone = None
                            pain_side = None
                            pain_severity = 0
                            pain_type = None
                            pain_location = ""

                    # Objetivo y tiempo
                    with st.container(border=True):
                        st.caption("Objetivo de hoy")
                        goals = ["fuerza", "hipertrofia", "técnica", "cardio", "descanso"]
                        session_goal = st.selectbox(
                            "Objetivo",
                            goals,
                            index=goals.index(st.session_state.get('mood_session_goal', 'fuerza')),
                            key="wiz_goal",
                            label_visibility="collapsed"
                        )
                        time_available = st.number_input(
                            "Minutos disponibles",
                            min_value=0, max_value=180,
                            value=st.session_state.get('mood_time_available', 60),
                            step=5,
                            key="wiz_time"
                        )

                # Feedback de flags
                flags_status = _count_flags(alcohol, caffeine, pain_flag, sick_flag, sleep_disruptions, last_hard)
                render_status_badge("Flags", flags_status)

                # Botones navegación
                st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
                col_nav1, _ = st.columns(2)
                with col_nav1:
                    if st.button("← Volver", width="stretch", key="wiz_back_3"):
                        st.session_state.wizard_step = 2
                        st.rerun()

        # =========================================================================
        # RESUMEN EN VIVO (siempre visible arriba del botón)
        # =========================================================================
        st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)

        # Calcular estados para resumen
        recovery_status = _get_recovery_status(sleep_h, sleep_q, sleep_disruptions)
        state_status = _get_state_status(perceived_readiness, fatigue, stress, energy)
        flags_status = _count_flags(alcohol, caffeine, pain_flag, sick_flag, sleep_disruptions, last_hard)

        # Estimación de readiness más precisa (alineada con cálculo real)
        perceived_component = (perceived_readiness / 10) * 18
        base_multiplier = 0.85

        sleep_hours_score = max(0, min(1, (sleep_h - 5.0) / 2.5))
        sleep_quality_score = (sleep_q - 1) / 4
        sleep_base = (sleep_hours_score * 0.6 + sleep_quality_score * 0.4)
        sleep_component = base_multiplier * 38 * sleep_base

        if sleep_disruptions:
            sleep_component -= 5
        if alcohol:
            sleep_component -= 12

        fatigue_score = (10 - fatigue) / 10
        stress_score = (10 - stress) / 10
        energy_score = energy / 10
        soreness_score = (10 - soreness) / 10
        state_component = base_multiplier * 42 * (
            energy_score * 0.40 +
            fatigue_score * 0.35 +
            stress_score * 0.20 +
            soreness_score * 0.05
        )
        if stiffness > 3:
            state_component -= (stiffness - 3) * 0.3

        motivation_component = base_multiplier * 18 * (motivation / 10)

        pain_penalty = 15 if pain_flag else 0
        sick_penalty = {0: 0, 1: 5, 2: 8, 3: 15, 4: 25, 5: 35}.get(sick_level, 0)
        caffeine_mask = 5 if (caffeine >= 3 and fatigue >= 7) else 0

        estimated_readiness = int(
            perceived_component + sleep_component + state_component + motivation_component
            - pain_penalty - sick_penalty - caffeine_mask
        )
        estimated_readiness = max(20, min(95, estimated_readiness))

        render_live_summary(recovery_status, state_status, flags_status, estimated_readiness)

        # === ACTION BUTTON ===
        st.markdown(
            '<div style="text-align:center;color:rgba(255,255,255,0.5);font-size:0.85rem;margin-bottom:12px;">'
            'Obtén tu puntuación exacta y plan personalizado'
            '</div>',
            unsafe_allow_html=True
        )

        # En modo preciso, solo mostrar botón en paso 3
        show_submit = quick_mode or st.session_state.wizard_step == 3

        if show_submit:
            submitted = st.button(
                "CALCULAR READINESS & PLAN",
                width="stretch",
                key="submit_readiness",
                type="primary",
            )
        else:
            submitted = False


    # Cheat sheet de métricas clave (ayuda rápida)
    with st.expander("¿Qué significa cada métrica?"):
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
                    st.plotly_chart(fig)
            
            with col_hist2:
                if 'volume' in last_7_days.columns:
                    volume_hist = last_7_days.set_index('date')['volume']
                    fig = create_volume_chart(volume_hist, "Volumen")
                    st.plotly_chart(fig)
            
            col_hist3, col_hist4 = st.columns(2)
            
            with col_hist3:
                if 'sleep_hours' in last_7_days.columns:
                    sleep_hist = last_7_days.set_index('date')['sleep_hours']
                    fig = create_sleep_chart(sleep_hist, "Sueño (horas)")
                    st.plotly_chart(fig)
            
            with col_hist4:
                if 'acwr_7_28' in last_7_days.columns:
                    acwr_hist = last_7_days.set_index('date')['acwr_7_28']
                    fig = create_acwr_chart(acwr_hist, "ACWR (Carga)")
                    st.plotly_chart(fig)
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
            # Usar readiness v3 (wrapper compatible)
            readiness_instant, readiness_breakdown = calculate_readiness_from_inputs_v3_compat(
                sleep_h, sleep_q, fatigue, soreness, stress, motivation, pain_flag,
                nap_mins, sleep_disruptions, energy, stiffness, caffeine, alcohol, sick_level,
                perceived_readiness=perceived_readiness,
                baselines=baselines,
                adjustment_factors=adjustment_factors,
                df_daily=df_daily
            )
            
            # DEBUG: Mostrar breakdown detallado
            with st.expander("🔍 DEBUG: Breakdown detallado del cálculo", expanded=False):
                st.write("**Readiness final:**", readiness_instant)
                st.write("**Percepción component:**", f"{readiness_breakdown.get('perceived_component', 0):.1f} pts")
                st.write("**Components:**")
                for key, val in readiness_breakdown.get('components', {}).items():
                    st.write(f"  - {key}: {val:.1f} pts")
                st.write("**Adjustments:**")
                for key, val in readiness_breakdown.get('context_adjustments', {}).items():
                    st.write(f"  - {key}: {val:.1f} pts")
                if readiness_breakdown.get('notes'):
                    st.write("**Notas:**")
                    for note in readiness_breakdown['notes']:
                        st.write(f"  - {note}")
            
            # === AJUSTE POR CICLO MENSTRUAL (si es mujer) ===
            menstrual_adjustment = None
            user_gender = st.session_state.get('user_gender', 'hombre')
            if user_gender == 'mujer':
                cycle_data = st.session_state.get('menstrual_cycle_data', {})
                if cycle_data:
                    menstrual_adjustment = adjust_readiness_for_menstrual_cycle(
                        readiness_instant,
                        cycle_data.get('day_of_cycle', 14),
                        {
                            'cramping': cycle_data.get('cramping', 0),
                            'bloating': cycle_data.get('bloating', 0),
                            'mood': cycle_data.get('mood', 5)
                        }
                    )
                    # Usar readiness ajustado
                    readiness_instant = menstrual_adjustment['adjusted_score']
            
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
        
        # ===== DESGLOSE PERSONALIZADO (nuevo diseño) =====
        render_section_title("Desglose Personalizado de tu Readiness", accent="#FFB81C")
        
        components = readiness_breakdown.get('components', {})
        adjustments = readiness_breakdown.get('context_adjustments', {})
        notes = readiness_breakdown.get('notes', [])
        p50 = baselines.get('readiness', {}).get('p50', 50)
        p75 = baselines.get('readiness', {}).get('p75', 55)
        n_days = baselines.get('readiness', {}).get('n', 0)
        sleep_responsive = adjustment_factors.get('sleep_responsive', False)
        
        render_desglose_section(
            components=components,
            adjustments=adjustments,
            sleep_responsive=sleep_responsive,
            readiness=readiness_instant,
            p50=p50,
            p75=p75,
            n_days=n_days,
            notes=notes
        )
        
        # ===== TU READINESS HOY (nuevo diseño) =====
        st.markdown("---")
        render_section_title("Tu Readiness HOY", accent="#00D084")
        
        render_readiness_section(
            readiness=readiness_instant,
            emoji=emoji,
            baselines=baselines,
            injury_risk=injury_risk,
            adjustment_factors=adjustment_factors
        )
        
        # Advice Cards (nuevo diseño premium)
        st.markdown("---")
        
        # === SECCIÓN DE CICLO MENSTRUAL (si es mujer) ===
        if menstrual_adjustment:
            render_section_title("🔄 Ajuste por Ciclo Menstrual", accent="#D947EF")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Fase", menstrual_adjustment['phase'], delta=None)
            with col2:
                st.metric("Energía", f"{menstrual_adjustment['energy_factor']:.0%}", delta=None)
            with col3:
                st.metric("Ajuste", f"{menstrual_adjustment['menstrual_adjustment']:+.0f} pts", delta=None)
            
            with st.expander("📊 Detalles del Ciclo", expanded=False):
                st.write(menstrual_adjustment['explanation'])
                if menstrual_adjustment['recommendations']:
                    st.write("**Recomendaciones:**")
                    for rec in menstrual_adjustment['recommendations']:
                        st.write(f"• {rec}")
            
            st.markdown("---")
        
        render_section_title("Consejos de hoy", accent="#FFB81C")

        # Nueva sección unificada con Summary Strip + Cards + Checklist
        render_consejos_section(
            fatigue_analysis=fatigue_analysis,
            zone_display=zone_display,
            plan=plan,
            rules=rules,
            sleep_h=sleep_h,
            stress=stress
        )
        
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
                if st.button("💾 Guardar", width="stretch"):
                    today_save = datetime.date.today()
                    save_mood_to_csv(
                        today_save, sleep_h, sleep_q, fatigue, soreness, stress, motivation,
                        pain_flag, pain_location, readiness_instant
                    )
                    st.success(f"Guardado para {today_save}")
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
                st.plotly_chart(fig)
            
            # Volume Chart
            with col_chart2:
                volume_chart = chart_data.set_index('date')['volume']
                fig = create_volume_chart(volume_chart, "Volumen")
                st.plotly_chart(fig)
            
            col_chart3, col_chart4 = st.columns(2)
            
            # Sleep Chart
            with col_chart3:
                sleep_chart = chart_data.set_index('date')['sleep_hours']
                fig = create_sleep_chart(sleep_chart, "Sueño (horas)")
                st.plotly_chart(fig)
            
            # ACWR Chart
            with col_chart4:
                acwr_chart = chart_data.set_index('date')['acwr_7_28']
                fig = create_acwr_chart(acwr_chart, "ACWR (Carga)")
                st.plotly_chart(fig)
