import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
import datetime
import sys

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
from views import render_modo_hoy, render_semana, render_perfil, render_entrenamiento


def main():
    st.set_page_config(page_title="Trainer Readiness Dashboard", layout="wide")
    
    # Inyectar CSS principal, Hero y Loader
    inject_main_css(st)
    inject_loader_css()
    inject_hero(st)

    daily_path = Path("data/processed/daily.csv")
    reco_path = Path("data/processed/recommendations_daily.csv")
    daily_ex_path = Path("data/processed/daily_exercise.csv")
    weekly_path = Path("data/processed/weekly.csv")

    # Load main data files
    df_metrics = None
    df_recommendations = None
    
    with loading("Cargando datos..."):
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
    view_mode = st.sidebar.radio("Vista", ["Día", "Modo Hoy", "Semana", "Entrenamiento", "Perfil Personal"], key="view_mode")

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
        render_perfil(df_daily)


if __name__ == '__main__':
    main()
