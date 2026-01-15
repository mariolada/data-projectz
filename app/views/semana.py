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
from ui.styles import inject_main_css
# Import desde src (estos se añaden al path en streamlit_app.py)
from personalization_engine import suggest_weekly_sequence

# Helpers para KPIs y estado

# --- Helpers locales para KPIs y estado ---
def status_from_thresholds(monotony, strain, readiness):
    """Devuelve el estado general de la semana según thresholds NASA."""
    if monotony >= 2.0 or strain >= 1800 or readiness < 55:
        return "RISK"
    elif monotony >= 1.5 or strain >= 1200 or readiness < 70:
        return "WARN"
    else:
        return "OK"

def confidence_from_days(days):
    """Devuelve nivel de confianza según días entrenados en la semana."""
    if days is None:
        return "Insuficiente"
    if days >= 5:
        return "Alta"
    elif days >= 3:
        return "Media"
    elif days >= 1:
        return "Baja"
    else:
        return "Insuficiente"

def format_kpi(value, kind):
    """Formatea el valor de KPI para display bonito."""
    import math
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    if kind in ["volume_week", "Volumen"]:
        return f"{int(value):,}".replace(",", ".") + " kg"
    if kind in ["strain", "Strain"]:
        return f"{int(value):,}".replace(",", ".")
    if kind in ["monotony", "Monotonía"]:
        return f"{value:.2f}"
    if kind in ["readiness_avg", "Readiness"]:
        return f"{value:.0f}/100"
    return str(value)

def inject_nasa_theme(st):
    """Inyecta el tema NASA (gaming-dark, cards, chips, acentos neón)."""
    inject_main_css(st)

def render_chip(text, color):
    """Renderiza un chip/pill de métrica clave."""
    return f"<span class='badge-dynamic badge-{color}'>{text}</span>"

def render_status_chip(status):
    color = {"OK": "green", "WARN": "yellow", "RISK": "red"}.get(status, "muted")
    return render_chip(status, color)

def render_confidence_chip(conf):
    color = {"Alta": "green", "Media": "yellow", "Baja": "red", "Insuficiente": "muted"}.get(conf, "muted")
    return render_chip(f"Confianza {conf}", color)

def render_semana(df_daily: pd.DataFrame, df_weekly: pd.DataFrame):
    """
    Renderiza la vista Semana con tema NASA y estructura dashboard.
    """
    inject_nasa_theme(st)

    # Validación de datos
    if df_weekly is None:
        st.error("❌ weekly.csv no se cargó. Revisa si existe data/processed/weekly.csv")
        st.stop()
    if df_weekly.empty:
        st.warning("⚠️ weekly.csv está vacío")
        st.stop()

    with loading("Analizando datos semanales..."):
        df_weekly['week_start'] = pd.to_datetime(df_weekly['week_start'], errors='coerce')
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
        df_weekly_display_formatted = df_weekly_display.copy()
        df_weekly_display_formatted['Semana (inicio)'] = df_weekly_display['week_start'].dt.strftime('%d/%m/%Y')
        try:
            if 'readiness_score' in df_daily.columns:
                df_daily_copy = df_daily.copy()
                df_daily_copy['date'] = pd.to_datetime(df_daily_copy['date'])
                df_daily_copy['week_start'] = df_daily_copy['date'] - pd.to_timedelta(df_daily_copy['date'].dt.dayofweek, unit='D')
                weekly_readiness = df_daily_copy.groupby('week_start')['readiness_score'].mean().reset_index()
                weekly_readiness.columns = ['week_start', 'readiness_avg']
                df_weekly_display_formatted = df_weekly_display.merge(
                    weekly_readiness,
                    on='week_start',
                    how='left'
                )
            else:
                df_weekly_display_formatted = df_weekly_display.copy()
                df_weekly_display_formatted['readiness_avg'] = None
            # Asegurar que 'Semana (inicio)' existe tras el merge
            df_weekly_display_formatted['Semana (inicio)'] = df_weekly_display_formatted['week_start'].dt.strftime('%d/%m/%Y')
            readiness_error = None
        except Exception as e:
            df_weekly_display_formatted = df_weekly_display.copy()
            df_weekly_display_formatted['readiness_avg'] = None
            df_weekly_display_formatted['Semana (inicio)'] = df_weekly_display_formatted['week_start'].dt.strftime('%d/%m/%Y')
            readiness_error = str(e)
            

        # --- BLOQUE A: Resumen semanal ---
        render_section_title("📊 Resumen semanal", accent="#00D084")
        col_top = st.columns([2, 2, 2, 2, 2])
        # Selector de semana
        week_options = df_weekly_display_formatted['Semana (inicio)'].tolist()
        selected_week = st.selectbox("Semana", week_options, index=0)
        week_row = df_weekly_display_formatted[df_weekly_display_formatted['Semana (inicio)'] == selected_week].iloc[0]
        # KPIs principales
        kpi_keys = ["readiness_avg", "volume_week", "strain", "monotony"]
        kpi_labels = ["Readiness medio", "Volumen", "Strain", "Monotonía"]
        kpi_colors = ["green", "aqua", "yellow", "coral"]
        for i, (key, label, color) in enumerate(zip(kpi_keys, kpi_labels, kpi_colors)):
            val = week_row.get(key, None)
            with col_top[i]:
                st.markdown(render_chip(f"{label}: {format_kpi(val, key)}", color), unsafe_allow_html=True)
        # Estado general
        status = status_from_thresholds(week_row.get('monotony', 0), week_row.get('strain', 0), week_row.get('readiness_avg', 0))
        st.markdown(render_status_chip(f"Semana {status}"), unsafe_allow_html=True)
        # Insights breves
        insights = []
        if week_row.get('monotony', 0) > 1.5 and week_row.get('strain', 0) > 1000:
            insights.append("Monotonía alta + strain alto → riesgo acumulado")
        if week_row.get('readiness_avg', 0) < 55:
            insights.append("Readiness bajo: considera deload")
        if week_row.get('volume_week', 0) > 12000:
            insights.append("Volumen alto: progresión rápida")
        if not insights:
            insights.append("Semana dentro de parámetros normales")
        st.markdown("<div style='margin-top:8px;color:#9CA3AF;font-size:0.98em;'>" + "<br>".join(insights[:3]) + "</div>", unsafe_allow_html=True)

        # --- BLOQUE B: Tabla semanal ---
        render_section_title("📅 Semana macro (tabla)", accent="#4ECDC4")
        # Formatear tabla con chips de estado y confianza
        table = df_weekly_display_formatted.copy()
        # Si no existe la columna 'Días', intentar crearla
        if 'Días' not in table.columns:
            # Si existe 'days', renombrar
            if 'days' in table.columns:
                table = table.rename(columns={'days': 'Días'})
            else:
                # Si no existe, crear con None
                table['Días'] = None
        table['Estado'] = table.apply(lambda r: status_from_thresholds(r.get('monotony', 0), r.get('strain', 0), r.get('readiness_avg', 0)), axis=1)
        table['Estado'] = table['Estado'].apply(render_status_chip)
        table['Confianza'] = table['Días'].apply(lambda d: render_confidence_chip(confidence_from_days(d)),)
        # Explicación de la columna 'Días'
        st.caption("'Días' indica el número de días entrenados esa semana. Sirve para calcular la confianza y saber si los datos son suficientes.")

        # Renderizado manual para chips visuales
        display_cols = ['Semana (inicio)', 'Días', 'Estado', 'Confianza']
        display_cols = [c for c in display_cols if c in table.columns]
        # Construir tabla HTML
        table_html = "<table style='width:100%;border-radius:12px;overflow:hidden;background:rgba(15,22,32,0.92);'>"
        # Header
        table_html += "<tr>" + "".join([f"<th style='padding:8px 10px;color:#E0E0E0;font-size:0.95em;text-align:left;'>{col}</th>" for col in display_cols]) + "</tr>"
        # Filas
        for _, row in table.iterrows():
            table_html += "<tr>"
            for col in display_cols:
                val = row[col]
                # Chips HTML
                if col in ['Estado', 'Confianza']:
                    cell = val if isinstance(val, str) else str(val)
                else:
                    cell = str(val) if val is not None else "—"
                table_html += f"<td style='padding:8px 10px;color:#E0E0E0;font-size:0.97em;border-bottom:1px solid rgba(178,102,255,0.10);'>{cell}</td>"
            table_html += "</tr>"
        table_html += "</table>"
        st.markdown(table_html, unsafe_allow_html=True)

        # --- BLOQUE C: Métricas semanales (gráficas en grid) ---
        render_section_title("📈 Métricas semanales", accent="#FFB81C")
        grid = st.columns(2)
        # Volumen
        with grid[0]:
            vol_data = df_weekly_filtered.set_index('week_start')['volume_week'].dropna()
            if not vol_data.empty:
                fig = create_weekly_volume_chart(vol_data, "Volumen Semanal")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.markdown(render_chip("Confianza baja", "muted"), unsafe_allow_html=True)
            with st.expander("¿Qué significa Volumen?"):
                st.write("Suma total de sets × reps × kg. Progresión gradual = OK. Picos bruscos = riesgo.")
        # Strain
        with grid[1]:
            strain_data = df_weekly_filtered.set_index('week_start')['strain'].dropna()
            if not strain_data.empty:
                fig = create_weekly_strain_chart(strain_data, "Strain Semanal")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.markdown(render_chip("Confianza baja", "muted"), unsafe_allow_html=True)
            with st.expander("¿Qué significa Strain?"):
                st.write("Carga ajustada por variabilidad. Alto + monotonía alta = riesgo.")
        # RPE medio
        with grid[0]:
            effort_data = df_weekly_filtered.set_index('week_start')['effort_week_mean'].dropna()
            if not effort_data.empty:
                fig = go.Figure()
                fig.add_trace(go.Bar(x=effort_data.index, y=effort_data.values, name='RPE', marker=dict(color='#FF6B6B')))
                fig.add_hline(y=8.0, line_dash="dash", line_color="orange", annotation_text="Alto")
                fig.update_layout(title="RPE medio semanal", xaxis_title="Semana", yaxis_title="RPE", template="plotly_dark", height=320)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.markdown(render_chip("Confianza baja", "muted"), unsafe_allow_html=True)
            with st.expander("¿Qué significa RPE medio?"):
                st.write("Esfuerzo percibido. 7-8 ideal, >8.5 riesgo, <6 poco estímulo.")
        # Monotonía
        with grid[1]:
            monotony_data = df_weekly_filtered.set_index('week_start')['monotony'].dropna()
            if not monotony_data.empty:
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=monotony_data.index, y=monotony_data.values, mode='lines+markers', name='Monotonía', line=dict(color='#FFB81C', width=3)))
                fig.add_hline(y=2.0, line_dash="dash", line_color="red", annotation_text="Límite (2.0)")
                fig.add_hline(y=1.5, line_dash="dot", line_color="orange", annotation_text="Advertencia (1.5)")
                fig.update_layout(title="Monotonía semanal", xaxis_title="Semana", yaxis_title="Monotonía", template="plotly_dark", height=320)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.markdown(render_chip("Confianza baja", "muted"), unsafe_allow_html=True)
            with st.expander("¿Qué significa Monotonía?"):
                st.write("Ratio entre carga y variabilidad. >2.0 riesgo, <1.5 ideal.")

        # --- BLOQUE D: Secuencia sugerida (próxima semana) ---
        render_section_title("🗓️ Secuencia sugerida (próxima semana)", accent="#00D084")
        last_week = df_weekly_filtered.sort_values('week_start', ascending=False).iloc[0]
        last_7_strain = [last_week['strain']]
        last_7_monotony = last_week.get('monotony', 0.5)
        last_readiness_mean = df_daily['readiness_score'].dropna().mean() if 'readiness_score' in df_daily.columns else 65
        baselines_weekly = {}
        if 'strain' in df_weekly_filtered.columns:
            strain_series = df_weekly_filtered['strain'].dropna()
            if len(strain_series) >= 4:
                baselines_weekly['_strain_p75'] = float(strain_series.quantile(0.75))
                baselines_weekly['_strain_p50'] = float(strain_series.quantile(0.5))
        weekly_suggestion = suggest_weekly_sequence(last_7_strain, last_7_monotony, last_readiness_mean, baselines=baselines_weekly)
        st.markdown(f"<div style='margin-bottom:8px;color:#9CA3AF;font-size:1.05em;'>Razonamiento: {weekly_suggestion['reasoning']}</div>", unsafe_allow_html=True)
        with st.expander("Detalles de la secuencia"):
            st.write(weekly_suggestion.get('details', ''))
        # Cards por día
        cols = st.columns(7)
        for i, day_plan in enumerate(weekly_suggestion['sequence']):
            color = {
                "PUSH": "green",
                "NORMAL": "aqua",
                "REDUCE": "yellow",
                "DELOAD": "coral",
                "REST": "muted"
            }.get(day_plan['type'].upper(), "muted")
            with cols[i]:
                st.markdown(f"""
                <div style="padding:14px;border-radius:12px;border:2px solid var(--{color});background:rgba(15,22,32,0.92);box-shadow:0 0 18px var(--{color})33;margin-bottom:8px;text-align:center;">
                    <div style='font-size:1.08em;font-weight:800;color:var(--text);margin-bottom:2px;'>{day_plan['day']}</div>
                    <div style='font-size:0.92em;font-weight:700;color:var(--muted);margin-bottom:4px;'>{day_plan['type'].upper()}</div>
                    <div style='font-size:0.85em;color:var(--text);'>{day_plan['description']}</div>
                </div>
                """, unsafe_allow_html=True)
        # UX: Si pocos días, mostrar chip de datos insuficientes
        if week_row.get('Días', 0) < 3:
            st.markdown(render_chip(f"Datos insuficientes (n={week_row.get('Días', 0)})", "muted"), unsafe_allow_html=True)
    # Fin dashboard
