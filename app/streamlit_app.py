import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import datetime
import sys
import secrets

# Añadir paths para imports
APP_DIR = Path(__file__).parent
SRC_DIR = APP_DIR.parent / 'src'
sys.path.insert(0, str(APP_DIR))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Imports desde módulos locales
from data.loaders import load_csv, load_daily_exercise_for_date
from calculations.readiness import (
    get_readiness_zone,
    get_days_until_acwr,
    format_acwr_display,
    get_confidence_level,
    get_anti_fatigue_flag,
    format_reason_codes,
    get_lift_recommendations
)
from charts.daily_charts import (
    create_readiness_chart,
    create_volume_chart,
    create_performance_chart
)
from ui.components import render_section_title
from ui.styles import inject_main_css, inject_hero
from ui.loader import loading, inject_loader_css
from ui.sidebar_premium import inject_sidebar_premium_css, render_sidebar_header
from views import render_modo_hoy, render_semana, render_perfil, render_entrenamiento, render_login
from auth.google_oauth import build_authorization_url, exchange_code_for_token, fetch_userinfo
from auth.session_manager import (
    generate_state_and_verifier,
    create_persistent_session,
    restore_session,
    drop_session,
    save_pkce_pair,
    get_code_verifier,
    delete_pkce_state,
    save_menstrual_cycle_data,
    save_gender,
)
from database.connection import init_db  # Inicializar BD


def _current_user_id() -> str:
    return (
        st.session_state.get("user_sub")
        or st.session_state.get("user_email")
        or "default_user"
    )


def _restore_session_from_query():
    """Restaura la sesión desde el query param 'session' si existe y es válido."""
    params = dict(st.query_params)
    session_token = params.get("session")
    
    if session_token and not st.session_state.get("authenticated"):
        rec = restore_session(session_token)
        if rec:
            st.session_state.authenticated = True
            st.session_state.user_email = rec.email or rec.user_id
            st.session_state.user_sub = rec.user_id
            st.session_state.auth_provider = rec.provider
            st.session_state.session_token = session_token
            st.session_state.display_name = rec.display_name
            st.session_state.profile_picture_url = rec.profile_picture_url  # Restaurar foto
            st.session_state.user_gender = rec.gender  # Restaurar género
            
            # Restaurar datos del ciclo menstrual si existen
            if rec.menstrual_cycle_data:
                import json
                try:
                    st.session_state.menstrual_cycle_data = json.loads(rec.menstrual_cycle_data)
                except:
                    st.session_state.menstrual_cycle_data = None
            
            return True
        else:
            # Limpiar query params si la sesión es inválida
            st.query_params.clear()
            return False
    
    return False


def _handle_oauth_callback(params):
    code = params.get("code")
    state = params.get("state")
    
    if not code:
        return False
    
    # Primero intentar recuperar del estado de sesión (si aún está en memoria)
    code_verifier = None
    
    if state and state == st.session_state.get("oauth_state"):
        # El state coincide: usar el verifier de session_state
        code_verifier = st.session_state.get("oauth_code_verifier")
    else:
        # Intentar recuperar desde la BD
        code_verifier = get_code_verifier(state) if state else None
    
    if not code_verifier:
        st.error(f"❌ Code verifier no encontrado. State recibido: {state[:20] if state else 'None'}...")
        st.error("Esto puede ocurrir si:")
        st.error("• Tu sesión expiró (espera 5 minutos e intenta de nuevo)")
        st.error("• El navegador eliminó las cookies")
        st.error("• Hay un problema con la base de datos")
        st.session_state.authenticated = False
        return False

    try:
        token = exchange_code_for_token(code, code_verifier)
        userinfo = fetch_userinfo(token.get("access_token"))
    except Exception as e:
        st.error(f"❌ Error intercambiando el código: {str(e)}")
        st.session_state.authenticated = False
        return False

    user_email = userinfo.get("email") or "usuario@google.com"
    user_sub = userinfo.get("sub") or user_email
    display_name = userinfo.get("name", "Usuario")
    profile_picture = userinfo.get("picture", None)  # URL de foto de perfil de Google

    try:
        session_token = create_persistent_session(
            provider="google",
            user_id=user_sub,
            email=user_email,
            display_name=display_name,
            access_token=token.get("access_token"),
            refresh_token=token.get("refresh_token"),
            id_token=token.get("id_token"),
            expires_at=None,
            profile_picture_url=profile_picture,

        )
    except Exception as e:
        st.error(f"❌ Error guardando sesión: {str(e)}")
        return False

    st.session_state.authenticated = True
    st.session_state.user_email = user_email
    st.session_state.user_sub = user_sub
    st.session_state.auth_provider = "google"
    st.session_state.session_token = session_token
    st.session_state.display_name = display_name
    st.session_state.profile_picture_url = profile_picture  # Guardar foto de perfil

    # SOLO eliminar el PKCE state después de éxito completo
    if state:
        delete_pkce_state(state)

    return True


def main():
    st.set_page_config(page_title="Trainer Readiness Dashboard", layout="wide")
    
    # Inicializar base de datos (crea tablas si no existen)
    init_db()
    
    # Inicializar session_state para autenticación
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    # Obtener query params (puede tener code/state del callback OAuth o session del restore)
    current_params = dict(st.query_params)
    
    # Si tenemos un session token válido, restaurarlo PRIMERO (antes de procesar callback)
    if "session" in current_params and not st.session_state.authenticated:
        if _restore_session_from_query():
            st.success("✅ Sesión restaurada")
    
    # Procesar callback OAuth SOLO si NO tenemos sesión válida y SÍ tenemos código
    if not st.session_state.authenticated and "code" in current_params:
        if _handle_oauth_callback(current_params):
            # Si el callback fue exitoso, guardar session en query params
            session_token = st.session_state.get("session_token")
            if session_token:
                st.query_params["session"] = session_token
                st.rerun()
        else:
            # Si falló, mostrar login de nuevo
            st.stop()
    
    # Rehidratar sesión desde query params si aún no está autenticada
    if not st.session_state.authenticated:
        _restore_session_from_query()
    
    # Login gate: si no hay usuario autenticado, mostrar pantalla de login y detener
    if not st.session_state.authenticated:
        if "oauth_state" not in st.session_state or "oauth_code_verifier" not in st.session_state:
            state, verifier = generate_state_and_verifier()
            st.session_state.oauth_state = state
            st.session_state.oauth_code_verifier = verifier
            # Guardar inmediatamente en BD para mayor fiabilidad
            try:
                save_pkce_pair(state, verifier)
            except Exception as e:
                st.warning(f"⚠️ Aviso: No se pudo guardar estado PKCE. {str(e)}")
                # Continuar de todas formas - usaremos session_state como fallback
        
        auth_url = build_authorization_url(
            st.session_state.oauth_state,
            st.session_state.oauth_code_verifier,
        )
        render_login(providers=("google",), auth_url=auth_url)
        st.stop()
    
    # Inyectar CSS principal, Hero y Loader
    inject_main_css(st)
    inject_loader_css()
    inject_hero(st)
    inject_sidebar_premium_css()  # Nuevo: estilos premium del sidebar
    
    # Inyectar CSS de Lottie loaders
    from ui.lottie_loader import inject_lottie_loader_css, lottie_loading
    inject_lottie_loader_css()

    daily_path = Path("data/processed/daily.csv")
    reco_path = Path("data/processed/recommendations_daily.csv")
    daily_ex_path = Path("data/processed/daily_exercise.csv")
    weekly_path = Path("data/processed/weekly.csv")

    # Load main data files
    df_metrics = None
    df_recommendations = None
    df_exercises = None
    df_weekly = None
    
    with lottie_loading("Cargando datos del sistema...", animation_type='load'):
        try:
            df_metrics = load_csv(daily_path)
        except FileNotFoundError:
            st.warning("❌ Falta daily.csv. Ejecuta el `pipeline` primero.")
            st.stop()
        
        try:
            df_recommendations = load_csv(reco_path)
        except FileNotFoundError:
            st.warning("❌ Falta recommendations_daily.csv. Ejecuta `decision_engine` primero.")
            st.stop()
        
        # Intentar cargar datos opcionales
        try:
            df_exercises = load_csv(daily_ex_path)
        except FileNotFoundError:
            df_exercises = None
        
        try:
            df_weekly = load_csv(weekly_path)
        except FileNotFoundError:
            df_weekly = None

    # Preparar fechas
    df_metrics['date'] = pd.to_datetime(df_metrics['date']).dt.date
    df_recommendations['date'] = pd.to_datetime(df_recommendations['date']).dt.date
    
    if df_exercises is not None and 'date' in df_exercises.columns:
        df_exercises['date'] = pd.to_datetime(df_exercises['date']).dt.date
    
    if df_weekly is not None:
        # weekly.csv usa 'week_start' en lugar de 'date'
        if 'week_start' in df_weekly.columns:
            df_weekly['week_start'] = pd.to_datetime(df_weekly['week_start']).dt.date
        elif 'date' in df_weekly.columns:
            df_weekly['date'] = pd.to_datetime(df_weekly['date']).dt.date

    # Eliminar columnas duplicadas
    cols_to_drop = [c for c in ['readiness_score', 'recommendation', 'reason', 'action_intensity', 'reason_codes']
                    if c in df_recommendations.columns and c in df_metrics.columns]
    if cols_to_drop:
        df_metrics = df_metrics.drop(columns=cols_to_drop)
    
    # Merge
    merge_cols = ['date'] + [c for c in ['readiness_score', 'recommendation', 'reason', 'action_intensity', 'reason_codes']
                             if c in df_recommendations.columns]
    df_daily = df_metrics.merge(df_recommendations[merge_cols], on='date', how='left')
    
    # Asegurar columnas necesarias
    for col in ['action_intensity', 'reason_codes']:
        if col not in df_daily.columns:
            df_daily[col] = '' if col == 'reason_codes' else 'Normal'

    # Sidebar: header premium
    with st.sidebar:
        render_sidebar_header("Readiness Tracker", "Dashboard")
    
    # Sidebar: view selector (day/week/today)
    st.sidebar.markdown("<div class='sidebar-title'>Navegación</div>", unsafe_allow_html=True)
    
    # Usar select_slider o radio con labels mejorados + help text
    view_mode = st.sidebar.radio(
        "Vista",
        ["Día", "Modo Hoy", "Semana", "Entrenamiento", "Perfil Personal"],
        key="view_mode",
        help="Selecciona la vista que deseas ver"
    )
    
    # Mostrar descripción discreta de la sección activa
    descriptions = {
        "Día": "Vista detallada de un día concreto",
        "Modo Hoy": "Cálculo de readiness y estado actual",
        "Semana": "Resumen y análisis semanal",
        "Entrenamiento": "Registro de entrenamientos",
        "Perfil Personal": "Datos y preferencias personales"
    }
    
    if view_mode in descriptions:
        st.sidebar.markdown(
            f"<div class='sidebar-item-description'>{descriptions[view_mode]}</div>",
            unsafe_allow_html=True
        )

    # Sidebar: date range filter - Solo mostrar en modo Día
    dates = sorted(df_daily['date'].unique())
    if dates:
        max_date = dates[-1]
        min_date = max(max_date - datetime.timedelta(days=6), dates[0])
    else:
        max_date = datetime.date.today()
        min_date = max_date - datetime.timedelta(days=6)

    if view_mode == "Día":
        st.sidebar.markdown("<div class='sidebar-separator'></div>", unsafe_allow_html=True)
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
                
                # Profile Picture in sidebar (left column)
                if st.session_state.get('profile_picture_url'):
                    st.sidebar.markdown("---")
                    st.sidebar.markdown("<div style='text-align: center;'><strong>Perfil</strong></div>", unsafe_allow_html=True)
                    st.sidebar.image(st.session_state.profile_picture_url, width=120, use_container_width=False)
                    if st.session_state.get('display_name'):
                        st.sidebar.caption(f"<div style='text-align: center;'>{st.session_state.display_name}</div>", unsafe_allow_html=True)
                
                # ALERTS
                alerts = []
                if get_anti_fatigue_flag(df_daily, selected_date):
                    alerts.append("Consecutivos de alta exigencia: considera descanso parcial hoy")
                if pd.notna(r.get('sleep_hours', None)) and r['sleep_hours'] < 6.5:
                    alerts.append("Sueño bajo: reduce volumen hoy")
                if pd.notna(r.get('acwr_7_28', None)) and r['acwr_7_28'] > 1.5:
                    alerts.append("Carga aguda muy alta: evita máximos hoy")
                
                if alerts:
                    st.markdown("### Alertas")
                    for alert in alerts:
                        st.warning(alert)
                
                # READINESS WITH ZONE - Mejorado con cards
                st.markdown("### Métricas Clave")
                col1, col2, col3, col4 = st.columns([1.2, 1, 1, 1])
                
                with col1:
                    readiness_text = f"{emoji} {int(readiness) if pd.notna(readiness) else 'N/D'}/100"
                    st.markdown(f"""
<div style='
    background: linear-gradient(135deg, rgba(178, 102, 255, 0.15), rgba(0, 208, 132, 0.05));
    border: 1px solid rgba(178, 102, 255, 0.3);
    border-radius: 8px;
    padding: 14px;
    text-align: center;
'>
    <div style='font-size: 1.8em; font-weight: bold; color: #B266FF;'>{readiness_text}</div>
    <div style='font-size: 0.85em; color: #9CA3AF; margin-top: 4px;'>{zone}</div>
</div>
""", unsafe_allow_html=True)
                
                perf = r.get('performance_index', None)
                acwr = r.get('acwr_7_28', None)
                sleep_h = r.get('sleep_hours', None)
                
                with col2:
                    st.metric("Rendimiento", f"{round(perf, 2)}" if pd.notna(perf) else "—")
                with col3:
                    days_avail = get_days_until_acwr(df_daily, selected_date)
                    acwr_display = format_acwr_display(acwr, days_avail)
                    st.metric("ACWR", acwr_display)
                with col4:
                    st.metric("Sueño", f"{round(sleep_h, 1)}h" if pd.notna(sleep_h) else "—")
                
                # CONFIDENCE PANEL
                conf_text, conf_emoji = get_confidence_level(df_daily, selected_date)
                st.info(f"{conf_emoji} **Confianza del modelo:** {conf_text}")
                
                # RECOMMENDATION - Mejorado
                render_section_title("Recomendación", accent="#FFB81C")
                reco = r.get('recommendation', 'N/D')
                action = r.get('action_intensity', 'N/D')
                
                st.markdown(f"""
<div style='
    background: linear-gradient(135deg, rgba(255, 184, 28, 0.1), rgba(255, 184, 28, 0.05));
    border-left: 4px solid #FFB81C;
    border-radius: 4px;
    padding: 12px;
    margin-bottom: 16px;
'>
    <div style='font-size: 1.3em; font-weight: bold; color: #FFB81C;'>{reco}</div>
    <div style='color: #E0E0E0; margin-top: 4px;'>Intensidad: <strong>{action}</strong></div>
</div>
""", unsafe_allow_html=True)
                
                # REASON CODES AS BULLETS
                reason_codes = r.get('reason_codes', '')
                reasons = format_reason_codes(reason_codes)
                if reasons:
                    st.write("**Razones:**")
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
        
        st.dataframe(styled, width="stretch")
        
        # ============== CHARTS ==============
        render_section_title("Gráficas", accent="#FF6B6B")
        col1, col2 = st.columns(2)

        with col1:
            if 'readiness_score' in df_filtered.columns:
                rts = df_filtered.set_index('date')['readiness_score'].sort_index()
                fig = create_readiness_chart(rts, "Readiness")
                st.plotly_chart(fig)
                
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
                    st.plotly_chart(fig)
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
                        st.plotly_chart(fig)
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
            st.plotly_chart(fig)
            
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
    
    # ============== MODE TODAY (INSTANT) ==============
    elif view_mode == "Modo Hoy":
        render_modo_hoy(df_daily)

    # ============== WEEK VIEW ==============
    elif view_mode == "Semana":
        render_semana(df_daily, df_weekly)
    
    # ============== ENTRENAMIENTO VIEW ==============
    elif view_mode == "Entrenamiento":
        render_entrenamiento()
    
    # ============== PERFIL PERSONAL VIEW ==============
    elif view_mode == "Perfil Personal":
        render_perfil(df_daily, session_token=st.session_state.get('session_token'))


if __name__ == '__main__':
    main()
