"""
Vista Semana - Análisis semanal y macro.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from ui.components import render_section_title
from ui.loader import loading
from charts.weekly_charts import create_weekly_volume_chart, create_weekly_strain_chart
from charts.daily_charts import create_performance_chart

# Import desde src (estos se añaden al path en streamlit_app.py)
from personalization_engine import suggest_weekly_sequence


def render_semana(df_daily: pd.DataFrame, df_weekly: pd.DataFrame):
    """
    Renderiza la vista Semana completa.
    
    Args:
        df_daily: DataFrame con datos diarios procesados
        df_weekly: DataFrame con datos semanales procesados
    """
    render_section_title("Semana — Macro", accent="#4ECDC4")
    
    # Check if weekly data exists and is valid
    if df_weekly is None:
        st.error("❌ weekly.csv no se cargó. Revisa si existe data/processed/weekly.csv")
        st.stop()
    
    if df_weekly.empty:
        st.warning("⚠️ weekly.csv está vacío")
        st.stop()
    
    if df_weekly is not None and not df_weekly.empty:
        with loading("Analizando datos semanales..."):
            # Mantener week_start como datetime para gráficos
            df_weekly['week_start'] = pd.to_datetime(df_weekly['week_start'], errors='coerce')
            # Use last 12 weeks for weekly view instead of daily 7-day filter
            max_week = df_weekly['week_start'].max()
            start_week = max_week - pd.Timedelta(weeks=12)
            df_weekly_filtered = df_weekly[df_weekly['week_start'] >= start_week].copy()
            
            if df_weekly_filtered.empty:
                df_weekly_filtered = df_weekly.copy()
                show_all_weeks_warning = True
            else:
                show_all_weeks_warning = False
            
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
                readiness_error = None
            except Exception as e:
                df_weekly_display_formatted = df_weekly_display.copy()
                df_weekly_display_formatted['readiness_avg'] = None
                readiness_error = str(e)
            
            # Formatear para display
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
        
        # Mostrar warnings después del loading
        if show_all_weeks_warning:
            st.warning(f"Sin datos en el rango (últimas 12 semanas desde {max_week.strftime('%d/%m/%Y')}). Mostrando todas las semanas disponibles:")
        if readiness_error:
            st.warning(f"Error al calcular readiness semanal: {readiness_error}")
        
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
