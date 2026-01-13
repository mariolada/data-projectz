"""
Helpers de UI para el Modo Hoy.
Funciones para badges dinámicos y clasificación de niveles.
"""
import streamlit as st


def render_badge(text: str, level: str):
    """Renderiza un badge con color según nivel (ok, mid, low)."""
    cls = {"ok": "badge-green", "mid": "badge-yellow", "low": "badge-red"}.get(level, "badge-yellow")
    st.markdown(f"<span class='badge-dynamic {cls}'>{text}</span>", unsafe_allow_html=True)


def get_sleep_hours_level(hours: float) -> tuple:
    """Clasifica las horas de sueño y retorna (texto, nivel)."""
    if hours >= 7.5:
        return ("Excelente", "ok")
    if hours >= 6.5:
        return ("Moderado", "mid")
    return ("Crítico", "low")


def get_sleep_quality_level(quality: int) -> tuple:
    """Clasifica la calidad de sueño (1-5) y retorna (texto, nivel)."""
    mapping = {
        1: ("Muy malo", "low"),
        2: ("Malo", "mid"),
        3: ("Regular", "mid"),
        4: ("Bueno", "ok"),
        5: ("Perfecto", "ok")
    }
    return mapping.get(quality, ("Regular", "mid"))


def get_fatigue_level(fatigue: int) -> tuple:
    """Clasifica el nivel de fatiga (0-10) y retorna (texto, nivel)."""
    if fatigue <= 3:
        return ("Baja", "ok")
    if fatigue <= 6:
        return ("Media", "mid")
    return ("Alta", "low")


def get_stress_level(stress: int) -> tuple:
    """Clasifica el nivel de estrés (0-10) y retorna (texto, nivel)."""
    if stress <= 3:
        return ("Bajo", "ok")
    if stress <= 6:
        return ("Medio", "mid")
    return ("Alto", "low")


def get_soreness_level(soreness: int) -> tuple:
    """Clasifica el nivel de agujetas (0-10) y retorna (texto, nivel)."""
    if soreness <= 2:
        return ("Ligera", "ok")
    if soreness <= 5:
        return ("Moderada", "mid")
    return ("Alta", "low")


def get_energy_level(energy: int) -> tuple:
    """Clasifica el nivel de energía (0-10) y retorna (texto, nivel)."""
    if energy >= 7:
        return ("Alta", "ok")
    if energy >= 4:
        return ("Media", "mid")
    return ("Baja", "low")


def get_perceived_level(perceived: int) -> tuple:
    """Clasifica la percepción personal (0-10) y retorna (texto, nivel)."""
    if perceived >= 8:
        return ("Me siento genial", "ok")
    elif perceived >= 6:
        return ("Me siento bien", "mid")
    elif perceived >= 4:
        return ("Regular", "mid")
    else:
        return ("Me siento mal", "low")


def render_card(title: str, lines: list, accent: str = "#4ECDC4", icon: str = ""):
    """
    Renderiza una tarjeta con estilo gaming.
    
    Args:
        title: Título de la tarjeta
        lines: Lista de líneas de contenido
        accent: Color del acento
        icon: Emoji/icono opcional
    """
    card_style = (
        "position: relative; "
        "border-radius: 16px; "
        "padding: 24px; "
        "margin-bottom: 20px; "
        "background: linear-gradient(135deg, rgba(20,20,30,0.95) 0%, rgba(30,30,45,0.85) 100%); "
        f"border: 2px solid {accent}; "
        f"box-shadow: 0 0 20px {accent}40, "
        f"0 0 40px {accent}20, "
        "inset 0 0 60px rgba(0,0,0,0.3); "
        "transition: all 0.3s ease; "
        "backdrop-filter: blur(10px);"
    )
    title_style = (
        "display: flex; "
        "align-items: center; "
        "gap: 12px; "
        "font-weight: 800; "
        "font-size: 1.1rem; "
        "text-transform: uppercase; "
        "letter-spacing: 1.5px; "
        f"color: {accent}; "
        "margin-bottom: 16px; "
        f"text-shadow: 0 0 10px {accent}80, 0 0 20px {accent}40; "
        "font-family: 'Courier New', monospace;"
    )
    # filter out empty/whitespace lines to avoid blank bullets
    safe_lines = [str(l).strip() for l in lines if str(l).strip()]
    bullet_html = "".join([
        f"<div style='margin-bottom:8px; padding-left:8px; border-left:2px solid {accent}50; padding-top:4px; padding-bottom:4px;'>"
        f"<span style='color:{accent}; margin-right:8px; font-weight:bold;'>▸</span>"
        f"<span style='color:#e0e0e0;'>{l}</span></div>" 
        for l in safe_lines
    ])
    icon_html = f"<span style='font-size:1.3rem; filter: drop-shadow(0 0 8px {accent});'>{icon}</span>" if icon else f"<span style='width:6px; height:6px; background:{accent}; display:inline-block; border-radius:50%; box-shadow: 0 0 8px {accent};'></span>"
    st.markdown(
        f"<div style='{card_style}'>"
        f"<div style='{title_style}'>{icon_html}{title}</div>"
        f"<div style='font-size:0.95rem; line-height:1.6;'>" + bullet_html + "</div>"
        + "</div>",
        unsafe_allow_html=True,
    )


def render_overload_alert(flag_type: str, exercise: str, severity: int, 
                          evidence: dict, recommendations: list, accent: str = "#FF4500"):
    """
    Renderiza una alerta de sobrecarga neuromuscular con estilo gaming neon.
    
    Args:
        flag_type: Tipo de flag (SUSTAINED_NEAR_FAILURE, FIXED_LOAD_DRIFT, etc.)
        exercise: Nombre del ejercicio
        severity: Severidad (0-100)
        evidence: Dict con evidencia
        recommendations: Lista de recomendaciones
        accent: Color del acento
    """
    # Iconos según tipo
    type_icons = {
        'SUSTAINED_NEAR_FAILURE': '🔥',
        'FIXED_LOAD_DRIFT': '📉',
        'HIGH_VOLATILITY': '🎢',
        'PLATEAU_EFFORT_RISE': '📈'
    }
    type_labels = {
        'SUSTAINED_NEAR_FAILURE': 'INTENSIDAD SOSTENIDA',
        'FIXED_LOAD_DRIFT': 'PÉRDIDA DE RENDIMIENTO',
        'HIGH_VOLATILITY': 'ALTA VOLATILIDAD',
        'PLATEAU_EFFORT_RISE': 'MESETA CON ESFUERZO'
    }
    icon = type_icons.get(flag_type, '⚠️')
    label = type_labels.get(flag_type, flag_type.replace('_', ' '))
    
    # Determinar color según severidad
    if severity >= 30:
        accent = "#FF0000"  # Rojo intenso
        glow_intensity = "60"
    elif severity >= 20:
        accent = "#FF4500"  # Naranja-rojo
        glow_intensity = "50"
    else:
        accent = "#FFB81C"  # Amarillo-naranja
        glow_intensity = "40"
    
    card_style = (
        "position: relative; "
        "border-radius: 16px; "
        "padding: 20px; "
        "margin-bottom: 16px; "
        "background: linear-gradient(135deg, rgba(40,10,10,0.95) 0%, rgba(50,20,20,0.85) 100%); "
        f"border: 2px solid {accent}; "
        f"box-shadow: 0 0 25px {accent}{glow_intensity}, "
        f"0 0 50px {accent}30, "
        "inset 0 0 60px rgba(0,0,0,0.4); "
        "backdrop-filter: blur(10px);"
    )
    
    header_style = (
        "display: flex; "
        "justify-content: space-between; "
        "align-items: center; "
        "margin-bottom: 16px; "
        "padding-bottom: 12px; "
        f"border-bottom: 1px solid {accent}40;"
    )
    
    title_style = (
        "font-weight: 800; "
        "font-size: 1.1rem; "
        "text-transform: uppercase; "
        "letter-spacing: 2px; "
        f"color: {accent}; "
        f"text-shadow: 0 0 15px {accent}, 0 0 30px {accent}80; "
        "font-family: 'Courier New', monospace;"
    )
    
    severity_style = (
        "padding: 4px 12px; "
        "border-radius: 20px; "
        f"background: {accent}30; "
        f"border: 1px solid {accent}; "
        f"color: {accent}; "
        "font-weight: bold; "
        "font-size: 0.85rem; "
        f"box-shadow: 0 0 10px {accent}50;"
    )
    
    # Construir evidencia HTML
    evidence_items = []
    if 'mean_rir' in evidence:
        evidence_items.append(f"RIR promedio: <strong>{evidence['mean_rir']:.1f}</strong>")
    if 'near_failure_proportion' in evidence:
        pct = evidence['near_failure_proportion'] * 100
        evidence_items.append(f"Sesiones al fallo: <strong>{pct:.0f}%</strong>")
    if 'baseline_reps' in evidence and 'last_reps' in evidence:
        evidence_items.append(f"Reps: {evidence['baseline_reps']:.1f} → <strong>{evidence['last_reps']:.0f}</strong>")
    if 'baseline_e1rm' in evidence and 'last_e1rm' in evidence:
        delta = evidence['last_e1rm'] - evidence['baseline_e1rm']
        color = "#FF4500" if delta < 0 else "#00FF00"
        evidence_items.append(f"e1RM: {evidence['baseline_e1rm']:.1f} → <span style='color:{color}'><strong>{evidence['last_e1rm']:.1f}</strong></span>")
    if 'k_sessions' in evidence:
        evidence_items.append(f"Últimas <strong>{evidence['k_sessions']}</strong> sesiones analizadas")
    
    evidence_html = "".join([
        f"<div style='margin-bottom:6px; color:#ccc;'>▸ {item}</div>" 
        for item in evidence_items
    ])
    
    # Construir recomendaciones HTML
    reco_html = "".join([
        f"<div style='margin-bottom:8px; padding-left:10px; border-left:3px solid {accent}; padding-top:4px; padding-bottom:4px;'>"
        f"<span style='color:#e0e0e0;'>{rec}</span></div>" 
        for rec in recommendations[:3]
    ])
    
    html = f"""
    <div style='{card_style}'>
        <div style='{header_style}'>
            <div style='{title_style}'>
                <span style='font-size:1.4rem; margin-right:10px; filter: drop-shadow(0 0 10px {accent});'>{icon}</span>
                {exercise.upper()}
            </div>
            <div style='{severity_style}'>SEV: {severity}</div>
        </div>
        <div style='display:grid; grid-template-columns:1fr 1fr; gap:20px;'>
            <div>
                <div style='color:{accent}; font-weight:bold; margin-bottom:8px; font-size:0.85rem; letter-spacing:1px;'>
                    📊 {label}
                </div>
                <div style='font-size:0.9rem;'>{evidence_html}</div>
            </div>
            <div>
                <div style='color:{accent}; font-weight:bold; margin-bottom:8px; font-size:0.85rem; letter-spacing:1px;'>
                    💡 ACCIONES
                </div>
                <div style='font-size:0.9rem;'>{reco_html}</div>
            </div>
        </div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def render_overload_summary(total_score: int, primary_cause: str, n_flags: int):
    """
    Renderiza el resumen de sobrecarga con estilo neon.
    """
    # Determinar nivel y colores
    if total_score >= 60:
        level = "CRÍTICO"
        accent = "#FF0000"
        emoji = "🚨"
        msg = "Sistema nervioso sobrecargado. Readiness limitado a 45 máx."
    elif total_score >= 45:
        level = "MODERADO"
        accent = "#FF4500"
        emoji = "⚠️"
        msg = "Acumulación de fatiga neural. Readiness limitado a 55 máx."
    elif total_score >= 30:
        level = "ALERTA"
        accent = "#FFB81C"
        emoji = "💡"
        msg = "Señales tempranas de fatiga. Readiness limitado a 65 máx."
    else:
        level = "BAJO"
        accent = "#00FF00"
        emoji = "✅"
        msg = "Sin señales significativas de sobrecarga."
    
    summary_style = (
        "border-radius: 12px; "
        "padding: 16px 24px; "
        "margin-bottom: 20px; "
        "background: linear-gradient(90deg, rgba(20,20,30,0.9) 0%, rgba(40,20,20,0.8) 100%); "
        f"border-left: 4px solid {accent}; "
        f"box-shadow: 0 0 20px {accent}40; "
        "display: flex; "
        "justify-content: space-between; "
        "align-items: center;"
    )
    
    score_style = (
        "font-size: 2rem; "
        "font-weight: 900; "
        f"color: {accent}; "
        f"text-shadow: 0 0 20px {accent}, 0 0 40px {accent}80; "
        "font-family: 'Courier New', monospace;"
    )
    
    cause_map = {
        'NEURAL_DRIVEN': 'Fatiga Neural',
        'MECHANICAL_DRIVEN': 'Fatiga Mecánica',
        'MIXED': 'Mixta',
        'UNKNOWN': 'Desconocido'
    }
    cause_label = cause_map.get(primary_cause, primary_cause)
    
    html = f"""
    <div style='{summary_style}'>
        <div>
            <div style='font-size:1.2rem; font-weight:bold; color:{accent}; margin-bottom:4px;'>
                {emoji} SOBRECARGA {level}
            </div>
            <div style='color:#aaa; font-size:0.9rem;'>{msg}</div>
            <div style='color:#888; font-size:0.8rem; margin-top:4px;'>
                Causa: {cause_label} | {n_flags} ejercicio(s) afectado(s)
            </div>
        </div>
        <div style='{score_style}'>{total_score}</div>
    </div>
    """
    st.markdown(html, unsafe_allow_html=True)


def clean_line(s: str) -> str:
    """Limpia una línea de texto de bullets y formato markdown."""
    s = str(s).strip()
    # remove leading markdown bullets
    if s.startswith("- ") or s.startswith("• "):
        s = s[2:].strip()
    # remove bold markers
    s = s.replace("**", "")
    return s
