"""
Vista Perfil Personal - Perfil personalizado del atleta.
"""
import streamlit as st
import pandas as pd

from ui.components import render_section_title
from ui.loader import loading
from data.loaders import load_user_profile
from calculations.readiness import generate_personalized_insights

# Import desde src (estos se añaden al path en streamlit_app.py)
from personalization_engine import calculate_personal_baselines


def render_perfil(df_daily: pd.DataFrame):
    """
    Renderiza la vista Perfil Personal completa.
    
    Args:
        df_daily: DataFrame con datos diarios procesados
    """
    st.markdown("<div style='margin-top:32px'></div>", unsafe_allow_html=True)
    render_section_title("Tu Perfil Personalizado", accent="#B266FF")
    
    # Cargar datos necesarios
    with loading("Cargando perfil..."):
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
