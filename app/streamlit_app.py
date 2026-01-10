import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import matplotlib.pyplot as plt
from pathlib import Path
import datetime


@st.cache_data
def load_csv(path: str):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No existe: {path}")
    df = pd.read_csv(p)
    # normalize date column to Timestamp
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    return df


def get_readiness_zone(readiness):
    """Retorna (zona, emoji, color) basado en readiness score."""
    if pd.isna(readiness):
        return ("N/D", "❓", "#999999")
    if readiness >= 75:
        return ("Alta", "🟢", "#00D084")
    elif readiness >= 55:
        return ("Media", "🟡", "#FFB81C")
    else:
        return ("Muy baja", "🔴", "#FF4444")


def get_days_until_acwr(df_daily, selected_date):
    """Calcula cuántos días de histórico hay hasta la fecha seleccionada."""
    filtered = df_daily[df_daily['date'] <= selected_date]
    return len(filtered)


def format_acwr_display(acwr, days_available):
    """Formatea ACWR: muestra valor o 'Pendiente (x/28 días)'."""
    if pd.isna(acwr) or acwr == '—':
        return f"Pendiente ({days_available}/28 días)"
    return f"{round(float(acwr), 3)}"


def get_confidence_level(df_daily, selected_date):
    """Retorna nivel de confianza basado en días de histórico."""
    filtered = df_daily[df_daily['date'] <= selected_date].copy()
    days_available = len(filtered)
    
    if days_available < 7:
        return "Baja (pocos datos)", "⚠️"
    elif days_available < 28:
        return f"Media ({days_available} días)", "ℹ️"
    else:
        return "Alta (>28 días)", "✅"
    """Retorna nivel de confianza basado en días de histórico."""
    filtered = df_daily[df_daily['date'] <= selected_date].copy()
    days_available = len(filtered)
    
    if days_available < 7:
        return "Baja (pocos datos)", "⚠️"
    elif days_available < 28:
        return f"Media ({days_available} días)", "ℹ️"
    else:
        return "Alta (>28 días)", "✅"


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


def format_reason_codes(reason_codes_str):
    """Convierte string de reason codes a lista legible."""
    if pd.isna(reason_codes_str) or reason_codes_str == '':
        return []
    codes = str(reason_codes_str).split('|')
    
    code_map = {
        'LOW_SLEEP': '😴 Sueño insuficiente',
        'HIGH_ACWR': '📈 Carga aguda muy alta',
        'PERF_DROP': '📉 Rendimiento en caída',
        'HIGH_EFFORT': '💪 Esfuerzo muy alto',
        'FATIGA': '⚠️ Fatiga detectada'
    }
    
    return [code_map.get(c.strip(), c.strip()) for c in codes if c.strip()]


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


def calculate_readiness_from_inputs(sleep_hours, sleep_quality, fatigue, soreness, stress, motivation, pain_flag):
    """Calcula readiness instantáneamente desde inputs del usuario."""
    
    # Normalizar inputs a 0-1
    sleep_hours_score = np.clip((sleep_hours - 6.0) / (7.5 - 6.0), 0, 1)
    sleep_quality_score = (sleep_quality - 1) / 4
    
    # Fatiga: 0 (sin cansancio) → 1, 10 (muy cansado) → 0
    fatigue_score = 1 - (fatigue / 10)
    
    # Soreness: 0 (sin dolor) → 1, 10 (mucho dolor) → 0
    soreness_score = 1 - (soreness / 10)
    
    # Stress: 0 (sin estrés) → 1, 10 (mucho estrés) → 0
    stress_score = 1 - (stress / 10)
    
    # Motivation: 0–10 mapear a 0–1
    motivation_score = motivation / 10
    
    # Pain flag penaliza
    pain_penalty = 0.3 if pain_flag else 0
    
    # Fórmula ponderada
    readiness_0_1 = (
        0.25 * sleep_hours_score +
        0.15 * sleep_quality_score +
        0.15 * fatigue_score +
        0.15 * soreness_score +
        0.15 * stress_score +
        0.15 * motivation_score
    ) - pain_penalty
    
    readiness_0_1 = np.clip(readiness_0_1, 0, 1)
    readiness_score = int(round(readiness_0_1 * 100))
    
    return readiness_score


def generate_actionable_plan(readiness, pain_flag, pain_location, fatigue, soreness, session_goal="fuerza"):
    """Genera un plan accionable basado en readiness y condiciones."""
    
    plan = []
    rules = []
    
    if readiness >= 80:
        zone = "Alta"
        emoji = "🟢"
        reco = "Push day"
        intensity_rir = "RIR 1–2 (máximo 1–2 reps de reserva)"
        volume_adjust = "+10% sets en lifts clave"
    elif readiness >= 55:
        zone = "Media"
        emoji = "🟡"
        reco = "Normal"
        intensity_rir = "RIR 2–3 (técnica impecable)"
        volume_adjust = "Mantén volumen, prioriza técnica"
    else:
        zone = "Muy baja"
        emoji = "🔴"
        reco = "Reduce / Deload"
        intensity_rir = "RIR 3–5 (conservador)"
        volume_adjust = "-20% sets, accesorio ligero"
    
    plan.append(f"**Recomendación:** {reco}")
    plan.append(f"**Intensidad:** {intensity_rir}")
    plan.append(f"**Volumen:** {volume_adjust}")
    
    # Reglas concretas
    if readiness >= 80:
        rules.append("✅ Busca PRs o máximos hoy")
        rules.append("✅ Siente libertad de empujar en los 3 últimos sets")
    elif readiness >= 55:
        rules.append("⚖️ Mantén intensidad, cuida forma")
        rules.append("⚖️ Si algo duele, sustituye el ejercicio")
    else:
        rules.append("⛔ Evita RIR≤1 hoy")
        rules.append("⛔ Recorta 1–2 series por ejercicio")
    
    # Pain management
    if pain_flag and pain_location:
        rules.append(f"🩹 Dolor en {pain_location}: evita movimientos bruscos, sustituye si es necesario")
    
    # Fatiga management
    if fatigue >= 7:
        rules.append("😴 Fatiga alta: reduce volumen en 20%, alarga descansos")
    
    # Soreness management
    if soreness >= 7:
        rules.append("🤕 Agujetas: calentamiento largo, movimiento ligero, accesorios >12 reps")
    
    return f"{emoji} {zone}", plan, rules


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


def main():
    st.set_page_config(page_title="Trainer Readiness Dashboard", layout="wide")
    
    # Custom CSS for clean gaming aesthetic
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
        
        /* Main styling */
        .main {
            background-color: #0B0E11;
        }
        
        /* H1 - Main title with purple accent */
        h1 {
            font-family: 'Orbitron', sans-serif;
            color: #B266FF;
            text-shadow: 0 0 10px rgba(178, 102, 255, 0.2);
            font-size: 2.2em;
            text-align: center;
            border-bottom: 1px solid rgba(178, 102, 255, 0.3);
            padding-bottom: 15px;
            margin-bottom: 10px;
            margin-top: 30px;
        }
        
        /* H2 - Section headers with purple */
        h2 {
            font-family: 'Orbitron', sans-serif;
            color: #B266FF;
            text-shadow: 0 0 8px rgba(178, 102, 255, 0.15);
            font-size: 1.6em;
            border-left: 3px solid #B266FF;
            padding-left: 12px;
            margin-top: 25px;
            margin-bottom: 15px;
            font-weight: 700;
        }
        
        /* H3 - Subsection headers */
        h3 {
            font-family: 'Orbitron', sans-serif;
            color: #FFFFFF;
            font-size: 1.3em;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        
        /* Adventure Mode banner */
        .adventure-banner {
            background: linear-gradient(135deg, #230646 0%, #1A1F2E 100%);
            border-left: 4px solid #B266FF;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
            color: #E0E0E0;
        }
        
        .adventure-banner h1 {
            margin: 0;
            font-size: 1.8em;
            text-align: left;
            border: none;
            padding: 0;
        }
        
        /* Metric styling */
        [data-testid="metric-container"] {
            background: linear-gradient(135deg, #1A1F2E 0%, #230646 100%);
            border-left: 3px solid #00D084;
            border-radius: 8px;
            padding: 15px;
        }
        
        /* Alert boxes */
        [data-testid="stAlert"] {
            border-left: 4px solid #FFB81C;
            border-radius: 6px;
            background: rgba(255, 184, 28, 0.1);
        }
        
        /* Info boxes */
        [data-testid="stInfo"] {
            border-left: 4px solid #00D084;
            border-radius: 6px;
            background: rgba(0, 208, 132, 0.1);
        }
        
        /* Sidebar */
        [data-testid="stSidebar"] {
            background-color: #1A1F2E;
            border-right: 1px solid rgba(178, 102, 255, 0.2);
        }
        
        /* Button styling */
        button {
            border-radius: 6px;
            background: linear-gradient(135deg, #00D084 0%, #00C070 100%);
            color: #0B0E11;
            border: none;
            font-weight: bold;
            transition: 0.3s;
        }
        
        button:hover {
            box-shadow: 0 0 15px rgba(0, 208, 132, 0.5);
        }
        
        /* Divider */
        hr {
            border: none;
            border-top: 1px solid rgba(178, 102, 255, 0.2);
        }
        
        /* Text styling */
        p {
            color: #E0E0E0;
        }
        
        /* Caption */
        .caption {
            color: #999999;
            font-size: 0.85em;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("⚔️ TRAINER — READINESS")
    
    st.markdown("""
    <div class="adventure-banner">
        <h1>🎮 ADVENTURE MODE</h1>
    </div>
    """, unsafe_allow_html=True)

    reco_path = Path("data/processed/recommendations_daily.csv")
    flags_path = Path("data/processed/flags_daily.csv")
    daily_ex_path = Path("data/processed/daily_exercise.csv")
    weekly_path = Path("data/processed/weekly.csv")

    # Load files
    recommendations = None
    try:
        recommendations = load_csv(reco_path)
    except FileNotFoundError:
        st.warning("❌ Faltan archivos. Ejecuta `decision_engine` primero.")
        st.stop()

    df_daily = recommendations.copy()
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
    st.sidebar.header("⚙️ Configuración")
    view_mode = st.sidebar.radio("Vista", ["📅 Día", "🎯 Modo Hoy", "📊 Semana"])

    # Sidebar: date range filter
    dates = sorted(df_daily['date'].unique())
    if dates:
        min_date, max_date = dates[0], dates[-1]
    else:
        min_date = max_date = datetime.date.today()

    date_range = st.sidebar.date_input("Rango de fechas", value=(min_date, max_date))
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range

    df_filtered = df_daily[(df_daily['date'] >= start_date) & (df_daily['date'] <= end_date)].copy()

    # Date selector
    dates_filtered = sorted(df_filtered['date'].unique(), reverse=True)
    today = datetime.date.today()
    default_date = today if today in dates_filtered else (dates_filtered[0] if dates_filtered else None)
    selected_date = st.sidebar.selectbox("Selecciona fecha", options=dates_filtered, 
                                        index=dates_filtered.index(default_date) if default_date in dates_filtered else 0) if dates_filtered else None

    # ============== DAY VIEW ==============
    if view_mode == "📅 Día":
        st.header(f"🎯 {selected_date}")
        
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
                    alerts.append("😴 **Sueño bajo**: reduce volumen hoy")
                if pd.notna(r.get('acwr_7_28', None)) and r['acwr_7_28'] > 1.5:
                    alerts.append("📈 **Carga aguda muy alta**: evita máximos hoy")
                
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
                st.subheader("📌 Recomendación")
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
                        st.subheader("🏋️ QUÉ HACER HOY")
                        st.write("**Lifts clave - plan accionable:**")
                        lift_recs = get_lift_recommendations(df_lifts, readiness, zone)
                        for rec in lift_recs:
                            st.markdown(rec)
                        
                        # Expander con explicación
                        with st.expander("💡 Cómo interpretar estas recomendaciones"):
                            st.write("""
- **Intensidad**: porcentaje de carga o reps en reserva (RIR)
- **Volumen**: sets totales en el lift principal
- **RIR**: repeticiones que podrías hacer más (RIR2 = 2 reps más hasta fallo)

**Zona Alta (Readiness ≥75)**: tu cuerpo está listo, busca progreso
**Zona Media (55–74)**: mantén técnica impecable, evita máximos
**Zona Muy Baja (<55)**: técnica y movimiento, descarga obligatoria
                            """)


    # ============== MODE TODAY (INSTANT) ==============
    elif view_mode == "🎯 Modo Hoy":
        st.header("🎯 MODO HOY")
        st.write("Introduce cómo te sientes **ahora mismo** y obtén recomendaciones instantáneas.")
        
        with st.form("mood_form"):
            # Basic inputs
            col1, col2, col3 = st.columns(3)
            
            with col1:
                sleep_h = st.number_input("Horas de sueño", min_value=0.0, max_value=12.0, value=7.5, step=0.5)
                sleep_q = st.slider("Calidad del sueño", 1, 5, 4, help="1=Muy malo, 5=Excelente")
            
            with col2:
                fatigue = st.slider("Fatiga/Cansancio", 0, 10, 3, help="0=Fresco, 10=Muy cansado")
                soreness = st.slider("Agujetas/Dolor muscular", 0, 10, 2, help="0=Ninguno, 10=Mucho")
            
            with col3:
                stress = st.slider("Estrés mental", 0, 10, 3, help="0=Relajado, 10=Muy estresado")
                motivation = st.slider("Motivación/Ganas", 0, 10, 7, help="0=Ninguna, 10=Máxima")
            
            # Pain management
            st.write("---")
            st.write("**Lesiones / Dolores localizados:**")
            col_pain1, col_pain2 = st.columns([1, 2])
            with col_pain1:
                pain_flag = st.checkbox("Tengo dolor muscular localizado")
            with col_pain2:
                pain_location = st.text_input("Dónde (ej: hombro izquierdo, rodilla derecha)", disabled=not pain_flag)
            
            # Optional inputs
            st.write("---")
            with st.expander("⚙️ Inputs avanzados (opcional)"):
                col_adv1, col_adv2 = st.columns(2)
                with col_adv1:
                    session_goal = st.selectbox("Objetivo de hoy", ["fuerza", "hipertrofia", "técnica", "cardio", "descanso"])
                    time_available = st.number_input("Minutos disponibles", min_value=0, max_value=180, value=60)
                with col_adv2:
                    last_hard = st.checkbox("Último entrenamiento fue MUY exigente")
            
            submitted = st.form_submit_button("🎯 Calcular Readiness & Plan", use_container_width='stretch')
        
        if submitted:
            # Store in session_state to persist across re-runs
            st.session_state.mood_sleep_h = sleep_h
            st.session_state.mood_sleep_q = sleep_q
            st.session_state.mood_fatigue = fatigue
            st.session_state.mood_soreness = soreness
            st.session_state.mood_stress = stress
            st.session_state.mood_motivation = motivation
            st.session_state.mood_pain_flag = pain_flag
            st.session_state.mood_pain_location = pain_location
            st.session_state.mood_session_goal = session_goal
            st.session_state.mood_calculated = True
        
        # Show results if calculated
        if st.session_state.get('mood_calculated', False):
            # Retrieve from session_state
            sleep_h = st.session_state.mood_sleep_h
            sleep_q = st.session_state.mood_sleep_q
            fatigue = st.session_state.mood_fatigue
            soreness = st.session_state.mood_soreness
            stress = st.session_state.mood_stress
            motivation = st.session_state.mood_motivation
            pain_flag = st.session_state.mood_pain_flag
            pain_location = st.session_state.mood_pain_location
            session_goal = st.session_state.mood_session_goal
            
            # Calculate readiness
            readiness_instant = calculate_readiness_from_inputs(
                sleep_h, sleep_q, fatigue, soreness, stress, motivation, pain_flag
            )
            
            # Get zone
            zone, emoji, _ = get_readiness_zone(readiness_instant)
            
            # Generate plan
            zone_display, plan, rules = generate_actionable_plan(
                readiness_instant, pain_flag, pain_location, fatigue, soreness, session_goal
            )
            
            # Display results
            st.markdown("---")
            st.subheader("📊 Tu Readiness HOY")
            
            col_result1, col_result2 = st.columns([2, 1])
            with col_result1:
                readiness_text = f"{emoji} {readiness_instant}/100"
                st.markdown(f"# {readiness_text}")
            with col_result2:
                st.write("")
                st.write("")
                st.write(zone_display)
            
            # Plan
            st.subheader("📋 Plan Accionable")
            for item in plan:
                st.markdown(item)
            
            # Rules
            st.subheader("⚡ Reglas de Hoy")
            for rule in rules:
                st.markdown(rule)
            
            # Save option
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

    # ============== WEEK VIEW ==============
    else:
        st.header("📊 SEMANA")
        
        if df_weekly is not None:
            df_weekly['week_start'] = pd.to_datetime(df_weekly['week_start']).dt.date
            df_weekly_filtered = df_weekly[(df_weekly['week_start'] >= start_date) & (df_weekly['week_start'] <= end_date)]
            
            if df_weekly_filtered.empty:
                st.info("No hay datos semanales disponibles.")
            else:
                st.dataframe(df_weekly_filtered.sort_values('week_start', ascending=False), use_container_width='stretch')
                
                # Charts
                col1, col2 = st.columns(2)
                with col1:
                    if 'volume_week' in df_weekly_filtered.columns:
                        st.subheader("Volumen Semanal")
                        st.line_chart(df_weekly_filtered.set_index('week_start')['volume_week'].sort_index())
                
                with col2:
                    if 'strain' in df_weekly_filtered.columns:
                        st.subheader("Strain")
                        st.line_chart(df_weekly_filtered.set_index('week_start')['strain'].sort_index())
        else:
            st.info("Archivo weekly.csv no disponible.")

    # ============== HISTORICAL TABLE ==============
    st.header("📈 HISTÓRICO")
    hist_cols = ['date', 'readiness_score', 'recommendation', 'action_intensity', 'reason_codes']
    hist_cols_existing = [c for c in hist_cols if c in df_filtered.columns]
    
    display_df = df_filtered[hist_cols_existing].sort_values('date', ascending=False).reset_index(drop=True)
    display_df = display_df.fillna('—')
    
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
    
    # Apply styling with numeric values
    styled = display_df.style.applymap(color_readiness, subset=['readiness_score']) if 'readiness_score' in display_df.columns else display_df.style
    
    # Format readiness_score without decimals AFTER styling
    if 'readiness_score' in display_df.columns:
        display_df['readiness_score'] = display_df['readiness_score'].apply(
            lambda x: f"{int(float(x))}" if isinstance(x, (int, float)) and x == x else '—'
        )
        # Recreate styled with formatted values
        styled = display_df.style.applymap(color_readiness, subset=['readiness_score'])
    
    st.dataframe(styled, use_container_width='stretch')

    # ============== CHARTS ==============
    st.header("📉 GRÁFICAS")
    col1, col2 = st.columns(2)

    with col1:
        if 'readiness_score' in df_filtered.columns:
            st.subheader("Readiness")
            rts = df_filtered.set_index('date')['readiness_score'].sort_index()
            st.line_chart(rts)
            
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
            st.subheader("Performance Index")
            pi = df_filtered.set_index('date')['performance_index'].sort_index()
            st.line_chart(pi)
            
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

    st.subheader("Volumen")
    if 'volume' in df_filtered.columns:
        vol = df_filtered.set_index('date')['volume'].sort_index()
        st.line_chart(vol)
        
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
    st.caption("🔄 La app muestra datos ya procesados. Ejecuta el pipeline para recalcular.")


if __name__ == '__main__':
    main()
