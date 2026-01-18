"""
Vista Perfil Personal - Perfil personalizado del atleta.
Estética minimalista neon-dark con cards y jerarquía clara.
"""
import streamlit as st
import pandas as pd

from ui.components import render_section_title
from ui.loader import loading
from ui.lottie_loader import lottie_loading
from data.loaders import load_user_profile
from calculations.readiness import generate_personalized_insights
from ui.profile_helpers import render_gender_selection, render_gender_note

# Import desde src (estos se añaden al path en streamlit_app.py)
from personalization_engine import calculate_personal_baselines


def inject_profile_css():
    """Inyecta CSS para tema minimalista neon-dark con cards."""
    st.markdown(
        """
        <style>
        :root {
            --bg: #0B0F14;
            --surface: rgba(15,22,32,0.95);
            --surface-alt: rgba(20,28,40,0.85);
            --border: rgba(255,255,255,0.06);
            --border-light: rgba(255,255,255,0.08);
            --text: rgba(235,235,235,0.95);
            --text-secondary: rgba(200,200,200,0.8);
            --muted: rgba(150,150,150,0.65);
            --good: #00FFB0;
            --good-soft: rgba(0,255,176,0.2);
            --warn: #FFB81C;
            --warn-soft: rgba(255,184,28,0.15);
            --risk: #FF6B5E;
            --risk-soft: rgba(255,107,94,0.15);
        }

        .profile-header {
            margin-bottom: 32px;
        }

        .profile-title {
            color: var(--text);
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -0.01em;
            margin-bottom: 6px;
        }

        .profile-subtitle {
            color: var(--muted);
            font-size: 0.95rem;
            line-height: 1.5;
            margin-bottom: 12px;
        }

        .profile-accent-line {
            height: 3px;
            width: 56px;
            background: var(--good);
            border-radius: 999px;
            margin-bottom: 24px;
        }

        /* CARDS - Contenedor base */
        .profile-card {
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.4);
        }

        /* Card con acento verde (primary/good) */
        .profile-card.card-primary {
            border-top: 3px solid var(--good);
        }

        /* Card con acento amarillo (warning) */
        .profile-card.card-warn {
            border-top: 3px solid var(--warn);
            background: linear-gradient(135deg, rgba(255,184,28,0.08) 0%, rgba(15,22,32,0.95) 100%);
        }

        /* Card con acento rojo (risk) */
        .profile-card.card-risk {
            border-top: 3px solid var(--risk);
            background: linear-gradient(135deg, rgba(255,107,94,0.08) 0%, rgba(15,22,32,0.95) 100%);
        }

        /* Card label (título de sección dentro del card) */
        .card-label {
            color: var(--muted);
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            margin-bottom: 16px;
            display: block;
        }

        /* KPI: Bloque valor + etiqueta */
        .kpi {
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .kpi-label {
            color: var(--muted);
            font-size: 0.8rem;
            letter-spacing: 0.02em;
            font-weight: 500;
        }

        .kpi-value {
            color: var(--text);
            font-size: 1.5rem;
            font-weight: 800;
            letter-spacing: -0.01em;
        }

        .kpi-hint {
            color: var(--muted);
            font-size: 0.75rem;
            margin-top: 2px;
        }

        /* CHIPS: Badges inline pequeños */
        .chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 5px 11px;
            border-radius: 999px;
            font-size: 0.7rem;
            font-weight: 600;
            border: 1px solid var(--border-light);
            color: var(--text-secondary);
            background: rgba(255,255,255,0.02);
            white-space: nowrap;
        }

        .chip.good {
            border-color: rgba(0,255,176,0.4);
            color: var(--good);
            background: var(--good-soft);
        }

        .chip.warn {
            border-color: rgba(255,184,28,0.4);
            color: var(--warn);
            background: var(--warn-soft);
        }

        .chip.risk {
            border-color: rgba(255,107,94,0.4);
            color: var(--risk);
            background: var(--risk-soft);
        }

        /* INSIGHT ITEMS: Mini tarjetas en lista */
        .insight-item {
            display: flex;
            gap: 12px;
            align-items: flex-start;
            padding: 12px;
            border-radius: 12px;
            border: 1px solid var(--border);
            background: var(--surface-alt);
            margin-bottom: 8px;
        }

        .insight-icon {
            font-size: 1rem;
            color: var(--good);
            margin-top: 2px;
            flex-shrink: 0;
        }

        .insight-content {
            flex: 1;
        }

        .insight-title {
            color: var(--text);
            font-size: 0.9rem;
            font-weight: 600;
            margin-bottom: 2px;
        }

        .insight-text {
            color: var(--muted);
            font-size: 0.85rem;
            line-height: 1.4;
        }

        /* MINI CARDS: Tarjetas pequeñas en grid */
        .mini-card {
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 14px;
            background: var(--surface-alt);
            text-align: center;
        }

        .mini-card-title {
            color: var(--muted);
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 8px;
            display: block;
        }

        .mini-card-text {
            color: var(--text-secondary);
            font-size: 0.85rem;
            line-height: 1.4;
        }

        /* ESTADO MESSAGE: Mensaje destacado principal */
        .estado-message {
            background: linear-gradient(135deg, rgba(0,255,176,0.15) 0%, rgba(15,22,32,0.95) 100%);
            border: 1px solid rgba(0,255,176,0.3);
            border-left: 3px solid var(--good);
            border-radius: 12px;
            padding: 16px;
            margin-bottom: 12px;
        }

        .estado-message.warn {
            background: linear-gradient(135deg, rgba(255,184,28,0.12) 0%, rgba(15,22,32,0.95) 100%);
            border-color: rgba(255,184,28,0.25);
            border-left-color: var(--warn);
        }

        .estado-message.risk {
            background: linear-gradient(135deg, rgba(255,107,94,0.12) 0%, rgba(15,22,32,0.95) 100%);
            border-color: rgba(255,107,94,0.25);
            border-left-color: var(--risk);
        }

        .estado-text {
            color: var(--text);
            font-size: 0.95rem;
            line-height: 1.5;
        }

        /* RESPONSIVIDAD: Grid layout */
        .kpi-grid-4 {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-top: 8px;
        }

        .kpi-grid-3 {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 16px;
            margin-top: 8px;
        }

        @media (max-width: 1200px) {
            .kpi-grid-4 {
                grid-template-columns: repeat(2, 1fr);
            }
            .kpi-grid-3 {
                grid-template-columns: repeat(2, 1fr);
            }
        }

        @media (max-width: 768px) {
            .kpi-grid-4,
            .kpi-grid-3 {
                grid-template-columns: 1fr;
            }
        }

        /* EXPANDIBLE: Mejorar estilo de expander */
        details {
            margin-top: 12px;
        }

        summary {
            color: var(--good);
            font-weight: 600;
            cursor: pointer;
            user-select: none;
            padding: 8px 0;
        }

        summary:hover {
            color: var(--text);
        }

        .expand-content {
            padding: 12px 0;
            margin-top: 12px;
            border-top: 1px solid var(--border);
            color: var(--text-secondary);
            font-size: 0.9rem;
            line-height: 1.6;
        }

        .expand-bullet {
            margin-bottom: 8px;
            padding-left: 16px;
        }

        .expand-bullet::before {
            content: "→ ";
            color: var(--good);
            font-weight: 600;
            margin-left: -16px;
            margin-right: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_chip(text: str, tone: str = "good"):
    """Renderiza un chip/badge pequeño."""
    st.markdown(
        f"<span class='chip {tone}'>{text}</span>",
        unsafe_allow_html=True,
    )


def render_kpi(label: str, value: str, hint: str | None = None):
    """Renderiza un bloque KPI (label + value + hint opcional)."""
    hint_html = f"<div class='kpi-hint'>{hint}</div>" if hint else ""
    st.markdown(
        f"""
        <div class='kpi'>
            <div class='kpi-label'>{label}</div>
            <div class='kpi-value'>{value}</div>
            {hint_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_mini_card(title: str, content: str):
    """Renderiza una mini-tarjeta compacta."""
    st.markdown(
        f"""
        <div class='mini-card'>
            <span class='mini-card-title'>{title}</span>
            <div class='mini-card-text'>{content}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_perfil(df_daily: pd.DataFrame, session_token: str = None):
    """
    Renderiza Perfil Personal con layout en 7 cards coherentes.
    
    Estructura:
    1. Header (título + línea acento)
    2. Card 1: Resumen ejecutivo (4 KPIs)
    3. Card 2: Estado/Mensaje principal
    4. Card 3: Insights clave (lista mini-cards)
    5. Card 4: Factores de personalización (4 KPIs)
    6. Card 5: Baselines históricas (3 KPIs)
    7. Card 6: Recomendaciones personalizadas
    8. Card 7: Ver más (expandible)
    """
    inject_profile_css()

    st.markdown('<div class="fade-in">', unsafe_allow_html=True)
    
    # ============ HEADER ============
    st.markdown("<div class='profile-header'>", unsafe_allow_html=True)
    st.markdown("<div class='profile-title'>Tu Perfil Personalizado</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='profile-subtitle'>Resumen personalizado basado en tu historial de entrenamientos, sueño y respuestas. Usa esto para optimizar carga, recuperación y decisiones diarias.</div>",
        unsafe_allow_html=True
    )
    st.markdown("<div class='profile-accent-line'></div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # ============ PROFILE INFO + GENDER CONFIG ============
    with st.expander("Configuración de Perfil", expanded=False):
        col_profile = st.columns(1)[0]
        with col_profile:
            # Obtener info del usuario actual
            display_name = st.session_state.get('display_name', 'Usuario')
            user_email = st.session_state.get('user_email', 'no-email@example.com')
            
            st.markdown(f"### {display_name}")
            st.caption(f"Correo: {user_email}")
            
            st.divider()
            
            # Cargar género guardado de la base de datos
            saved_gender = None
            if session_token:
                try:
                    from auth.session_manager import get_gender
                    saved_gender = get_gender(session_token)
                except:
                    pass
            
            st.markdown("**¿Cuál es tu género?**")
            gender = render_gender_selection(saved_gender=saved_gender)
            st.session_state['user_gender'] = gender
            
            render_gender_note(gender)
            
            # Botón de guardar género
            if st.button("Guardar Género", key="save_gender", use_container_width=True):
                if session_token:
                    from auth.session_manager import save_gender
                    try:
                        success = save_gender(session_token, gender)
                        if success:
                            st.success("Género guardado correctamente")
                        else:
                            st.error("Error al guardar género")
                    except Exception as e:
                        st.error(f"Error: {str(e)}")
                else:
                    st.warning("No se pudo guardar (sesión no disponible)")
    
    # Cargar datos
    with lottie_loading("Cargando tu perfil personalizado...", animation_type='profile'):
        baselines = calculate_personal_baselines(df_daily)
        user_profile = load_user_profile()
        adjustment_factors = user_profile.get('adjustment_factors', {})
        data_quality = baselines.get('_data_quality', {})
        total_days = data_quality.get('total_days', 0)
        last_date = data_quality.get('last_date')
    
    # Validación: mínimo 7 días
    if not baselines or total_days < 7:
        st.markdown("<div class='profile-card card-warn'>", unsafe_allow_html=True)
        st.markdown("<span class='card-label'>Datos insuficientes</span>", unsafe_allow_html=True)
        st.markdown(
            f"<div class='estado-message warn'><div class='estado-text'>Necesitas al menos 7 días de datos para generar tu perfil. Actualmente tienes <strong>{total_days} días</strong>. Sigue registrando entrenamientos y datos de sueño.</div></div>",
            unsafe_allow_html=True
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return
    
    # ============ CARD 1: RESUMEN EJECUTIVO ============
    hint1 = f"Último: {pd.to_datetime(last_date).strftime('%d/%m/%Y')}" if last_date else None
    arch = user_profile.get('archetype', {}).get('archetype', '?')
    sleep_resp = user_profile.get('sleep_responsiveness', {}).get('sleep_responsive')
    val_sleep = "Alta" if sleep_resp else ("Baja" if sleep_resp is not None else "N/D")
    confidence = user_profile.get('archetype', {}).get('confidence', 0)
    
    st.markdown(
        f"""
        <div class='profile-card card-primary'>
            <span class='card-label'>Resumen Ejecutivo</span>
            <div class='kpi-grid-4'>
                <div class='kpi'>
                    <div class='kpi-label'>Días con datos</div>
                    <div class='kpi-value'>{total_days}</div>
                    <div class='kpi-hint'>{hint1 or ''}</div>
                </div>
                <div class='kpi'>
                    <div class='kpi-label'>Arquetipo</div>
                    <div class='kpi-value'>{arch.upper() if arch else "—"}</div>
                </div>
                <div class='kpi'>
                    <div class='kpi-label'>Sensibilidad Sueño</div>
                    <div class='kpi-value'>{val_sleep}</div>
                </div>
                <div class='kpi'>
                    <div class='kpi-label'>Confianza</div>
                    <div class='kpi-value'>{confidence:.0%}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # ============ GENERAR INSIGHTS ============
    personalized_insights = generate_personalized_insights(baselines, adjustment_factors, user_profile, df_daily)
    
    # ============ CARD 2: ESTADO / MENSAJE PRINCIPAL ============
    is_stable = baselines.get('readiness', {}).get('std', 0) <= 15
    is_fatigue_sensitive = adjustment_factors.get('fatigue_sensitivity', 1.0) > 1.2
    
    if is_fatigue_sensitive and not is_stable:
        tone_class = "risk"
        main_message = "Eres hipersensible a fatiga y tu readiness es variable. Requiere monitoreo cuidadoso de carga y recuperación."
    elif is_fatigue_sensitive:
        tone_class = "warn"
        main_message = "Eres hipersensible a fatiga. Planifica deloads cada 4-5 semanas para evitar lesiones."
    elif not is_stable:
        tone_class = "warn"
        main_message = "Tu readiness es variable. Monitorea diariamente carga, sueño y estrés para predecir fluctuaciones."
    else:
        tone_class = "good"
        main_message = "Tu readiness es estable. Puedes planificar entrenamientos con confianza."
    
    st.markdown(
        f"""
        <div class='profile-card'>
            <span class='card-label'>Tu Estado Actual</span>
            <div class='estado-message {tone_class}'>
                <div class='estado-text'>{main_message}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # ============ CARD 3: INSIGHTS CLAVE ============
    insights_list = []
    if personalized_insights:
        for key, val in personalized_insights.items():
            if isinstance(val, dict):
                insight = val.get('summary') or val.get('recommendation') or val.get('insight')
            else:
                insight = val
            if insight and isinstance(insight, str) and insight.strip() and insight.strip() != "—":
                insights_list.append((key.replace('_', ' ').title(), insight))
    
    # Construir HTML de insights en una sola cadena
    insights_items_html = ""
    if insights_list:
        for label, insight in insights_list[:3]:
            insights_items_html += f"<div class='insight-item'><div class='insight-icon'>✦</div><div class='insight-content'><div class='insight-title'>{label}</div><div class='insight-text'>{insight}</div></div></div>"
    else:
        insights_items_html = "<div class='insight-item'><div class='insight-icon'>–</div><div class='insight-content'><div class='insight-text'>No hay insights suficientes aún. Sigue registrando datos.</div></div></div>"
    
    st.markdown(
        f"<div class='profile-card'><span class='card-label'>Insights Clave</span>{insights_items_html}</div>",
        unsafe_allow_html=True
    )
    
    # Si hay más insights, mostrar expandible
    if len(insights_list) > 3:
        with st.expander(f"📌 Ver {len(insights_list) - 3} insights más"):
            remaining_html = "<div class='expand-content'>"
            for label, insight in insights_list[3:]:
                remaining_html += f"<div class='expand-bullet'><strong>{label}:</strong> {insight}</div>"
            remaining_html += "</div>"
            st.markdown(remaining_html, unsafe_allow_html=True)
    
    # ============ CARD 4: FACTORES DE PERSONALIZACIÓN ============
    sleep_weight = adjustment_factors.get('sleep_weight', 0.25)
    fatigue_sens = adjustment_factors.get('fatigue_sensitivity', 1.0)
    stress_sens = adjustment_factors.get('stress_sensitivity', 1.0)
    recovery_speed = adjustment_factors.get('recovery_speed', 1.0)
    
    st.markdown(
        f"""
        <div class='profile-card'>
            <span class='card-label'>Factores de Personalización</span>
            <div class='kpi-grid-4'>
                <div class='kpi'>
                    <div class='kpi-label'>Sleep Weight</div>
                    <div class='kpi-value'>{sleep_weight:.2f}</div>
                    <div class='kpi-hint'>Δ {sleep_weight - 0.25:+.2f}</div>
                </div>
                <div class='kpi'>
                    <div class='kpi-label'>Fatiga Sensit.</div>
                    <div class='kpi-value'>{fatigue_sens:.2f}×</div>
                    <div class='kpi-hint'>Δ {fatigue_sens - 1.0:+.2f}</div>
                </div>
                <div class='kpi'>
                    <div class='kpi-label'>Stress Sensit.</div>
                    <div class='kpi-value'>{stress_sens:.2f}×</div>
                    <div class='kpi-hint'>Δ {stress_sens - 1.0:+.2f}</div>
                </div>
                <div class='kpi'>
                    <div class='kpi-label'>Velocidad Recup.</div>
                    <div class='kpi-value'>{recovery_speed:.2f}×</div>
                    <div class='kpi-hint'>Δ {recovery_speed - 1.0:+.2f}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # ============ CARD 5: BASELINES HISTÓRICAS ============
    readiness_p50 = baselines.get('readiness', {}).get('p50', 0)
    readiness_std = baselines.get('readiness', {}).get('std', 0)
    sleep_p50 = baselines.get('sleep', {}).get('p50', 0)
    sleep_p25 = baselines.get('sleep', {}).get('p25', 0)
    volume_p50 = baselines.get('volume', {}).get('p50', 0)
    
    st.markdown(
        f"""
        <div class='profile-card'>
            <span class='card-label'>Tus Baselines Históricas</span>
            <div class='kpi-grid-3'>
                <div class='kpi'>
                    <div class='kpi-label'>Readiness Mediana</div>
                    <div class='kpi-value'>{readiness_p50:.0f}/100</div>
                    <div class='kpi-hint'>Std: {readiness_std:.1f}</div>
                </div>
                <div class='kpi'>
                    <div class='kpi-label'>Sueño Mediano</div>
                    <div class='kpi-value'>{sleep_p50:.1f}h</div>
                    <div class='kpi-hint'>Q1: {sleep_p25:.1f}h</div>
                </div>
                <div class='kpi'>
                    <div class='kpi-label'>Volumen Mediano</div>
                    <div class='kpi-value'>{volume_p50:.0f}</div>
                    <div class='kpi-hint'>Reps acum.</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # ============ CARD 6: RECOMENDACIONES ============
    rec_tone = "card-primary" if is_stable and not is_fatigue_sensitive else "card-warn"
    
    rec_items_html = ""
    rec_items = []
    
    if user_profile.get('sleep_responsiveness', {}).get('sleep_responsive'):
        rec_items.append(
            ("Priorizar Sueño", "Duerme 7.5-8h consistentemente. Cada hora bajo tu media penaliza readiness significativamente.")
        )
    
    if is_fatigue_sensitive:
        rec_items.append(
            ("Deloads Frecuentes", "Eres hipersensible a fatiga. Programa deloads cada 4-5 semanas, no cada 6.")
        )
    
    if not is_stable:
        rec_items.append(
            ("Monitoreo Diario", "Tu readiness es variable. Trackea carga, sueño y estrés para predecir fluctuaciones.")
        )
    else:
        rec_items.append(
            ("Planificación Segura", "Tu readiness es estable. Puedes planificar entrenamientos difíciles con confianza.")
        )
    
    for title, desc in rec_items:
        rec_items_html += f"""
        <div class='insight-item'>
            <div class='insight-icon'>→</div>
            <div class='insight-content'>
                <div class='insight-title'>{title}</div>
                <div class='insight-text'>{desc}</div>
            </div>
        </div>
        """
    
    st.markdown(
        f"""
        <div class='profile-card {rec_tone}'>
            <span class='card-label'>Recomendaciones Personalizadas</span>
            {rec_items_html}
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # ============ CARD 7: VER MÁS (EXPANDIBLE) ============
    archetype = user_profile.get('archetype', {})
    arch_name = archetype.get('archetype', '?')
    arch_conf = archetype.get('confidence', 0)
    arch_reason = archetype.get('reason', 'Sin información')
    
    sleep_resp_data = user_profile.get('sleep_responsiveness', {})
    
    st.markdown(
        f"""
        <div class='profile-card'>
            <span class='card-label'>Detalles Técnicos</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    with st.expander("📊 Información avanzada", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(
                f"""
                <div style='background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 12px; color: rgba(200,200,200,0.8); font-size: 0.9rem;'>
                <strong>Calidad de Datos:</strong><br>
                • Días registrados: {total_days}<br>
                • Mínimo requerido: 7<br>
                • Último registro: {pd.to_datetime(last_date).strftime('%d/%m/%Y') if last_date else 'N/D'}<br>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        with col2:
            st.markdown(
                f"""
                <div style='background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 12px; color: rgba(200,200,200,0.8); font-size: 0.9rem;'>
                <strong>Arquetipo Detectado:</strong><br>
                • Tipo: {arch_name.upper()}<br>
                • Confianza: {arch_conf:.0%}<br>
                • Razón: {arch_reason}<br>
                </div>
                """,
                unsafe_allow_html=True
            )
        
        st.markdown(
            f"""
            <div style='margin-top: 12px; background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 10px; padding: 12px; color: rgba(200,200,200,0.8); font-size: 0.9rem;'>
            <strong>Responsividad al Sueño:</strong><br>
            • Sensible: {sleep_resp_data.get('sleep_responsive', False)}<br>
            • Correlación Sueño-Readiness: {sleep_resp_data.get('correlation', 0):.2f}<br>
            • Fortaleza: {sleep_resp_data.get('strength', 'unknown').upper()}<br>
            • Interpretación: {sleep_resp_data.get('interpretation', 'Sin información')}<br>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.markdown('</div>', unsafe_allow_html=True)
