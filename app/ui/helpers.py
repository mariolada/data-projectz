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


# =============================================================================
# SISTEMA DE DISEÑO - FATIGA NEURAL (Premium, Clean Gaming)
# =============================================================================

# Paleta de colores por severidad
SEVERITY_COLORS = {
    'critical': {'accent': '#E05555', 'bg': 'rgba(224,85,85,0.08)', 'glow': 'rgba(224,85,85,0.15)'},
    'moderate': {'accent': '#E07040', 'bg': 'rgba(224,112,64,0.06)', 'glow': 'rgba(224,112,64,0.12)'},
    'alert':    {'accent': '#D4A030', 'bg': 'rgba(212,160,48,0.05)', 'glow': 'rgba(212,160,48,0.10)'},
    'low':      {'accent': '#50B080', 'bg': 'rgba(80,176,128,0.05)', 'glow': 'rgba(80,176,128,0.08)'},
}

def _get_severity_level(score: int) -> str:
    """Determina el nivel de severidad basado en el score."""
    if score >= 60: return 'critical'
    if score >= 45: return 'moderate'
    if score >= 30: return 'alert'
    return 'low'

def _get_severity_label(level: str) -> tuple:
    """Retorna (label, emoji) para el nivel de severidad."""
    return {
        'critical': ('CRÍTICO', '🚨'),
        'moderate': ('MODERADO', '⚠️'),
        'alert':    ('ALERTA', '💡'),
        'low':      ('BAJO', '✅'),
    }.get(level, ('DESCONOCIDO', '❓'))


def render_neural_fatigue_summary_bar(total_score: int, primary_cause: str, n_flags: int, 
                                       flags: list, primary_action: str = None):
    """
    Renderiza la Summary Bar premium de fatiga neural.
    """
    level = _get_severity_level(total_score)
    colors = SEVERITY_COLORS[level]
    label, emoji = _get_severity_label(level)
    
    cause_map = {
        'NEURAL_DRIVEN': 'Fatiga Neural',
        'MECHANICAL_DRIVEN': 'Fatiga Mecánica', 
        'MIXED': 'Mixta',
        'UNKNOWN': 'Desconocido'
    }
    cause_label = cause_map.get(primary_cause, primary_cause)
    
    # Extraer chips de factores clave
    chips = _extract_factor_chips(flags)
    chips_html = _render_chips(chips, colors['accent'])
    
    gauge_pct = min(total_score, 100)
    
    # Determinar acción principal
    if not primary_action:
        if level == 'critical':
            primary_action = "Aplicar deload completo hoy"
        elif level == 'moderate':
            primary_action = "Reducir intensidad en ejercicios afectados"
        elif level == 'alert':
            primary_action = "Monitorear y evitar PRs"
        else:
            primary_action = "Continuar con el plan"
    
    readiness_cap = {'critical': 45, 'moderate': 55, 'alert': 65, 'low': None}
    cap = readiness_cap.get(level)
    cap_msg = f" · Readiness limitado a {cap}" if cap else ""
    
    ejercicios_text = f"{n_flags} ejercicio{'s' if n_flags != 1 else ''} afectado{'s' if n_flags != 1 else ''}"
    
    # Construir HTML compacto
    html = (
        f'<div style="background:linear-gradient(135deg,rgba(22,22,28,0.98),rgba(28,26,32,0.95));'
        f'border-radius:16px;padding:24px 28px;margin-bottom:24px;border-left:4px solid {colors["accent"]};'
        f'box-shadow:0 4px 20px rgba(0,0,0,0.4);">'
        
        # Header row
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:20px;">'
        
        # Left side
        f'<div style="flex:1;">'
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">'
        f'<span style="font-size:1.5rem;">{emoji}</span>'
        f'<span style="font-size:1.25rem;font-weight:700;color:#f0f0f0;">FATIGA NEURAL DETECTADA</span>'
        f'<span style="padding:4px 12px;border-radius:6px;background:{colors["bg"]};'
        f'border:1px solid {colors["accent"]}60;color:{colors["accent"]};font-size:0.75rem;'
        f'font-weight:600;text-transform:uppercase;">{label}</span>'
        f'</div>'
        f'<div style="color:#888;font-size:0.85rem;margin-left:42px;">'
        f'{cause_label} · {ejercicios_text}{cap_msg}'
        f'</div>'
        f'</div>'
        
        # Right side - Gauge
        f'<div style="text-align:center;min-width:100px;">'
        f'<div style="position:relative;width:80px;height:80px;margin:0 auto;">'
        f'<svg width="80" height="80" style="transform:rotate(-90deg);">'
        f'<circle cx="40" cy="40" r="32" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="8"/>'
        f'<circle cx="40" cy="40" r="32" fill="none" stroke="{colors["accent"]}" stroke-width="8" '
        f'stroke-dasharray="{gauge_pct * 2.01} 201" stroke-linecap="round"/>'
        f'</svg>'
        f'<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);'
        f'font-size:1.4rem;font-weight:700;color:{colors["accent"]};">{total_score}</div>'
        f'</div>'
        f'<div style="color:#666;font-size:0.7rem;margin-top:4px;text-transform:uppercase;">Severidad</div>'
        f'</div>'
        
        f'</div>'  # End header row
        
        # Chips row
        f'<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;">{chips_html}</div>'
        
        # Primary action
        f'<div style="display:flex;align-items:center;gap:10px;padding:12px 16px;'
        f'background:rgba(255,255,255,0.03);border-radius:10px;border:1px solid rgba(255,255,255,0.06);">'
        f'<span style="color:{colors["accent"]};font-size:1.1rem;">▸</span>'
        f'<span style="color:#c0c0c0;font-size:0.9rem;">'
        f'<strong style="color:#e0e0e0;">Acción principal:</strong> {primary_action}'
        f'</span>'
        f'</div>'
        
        f'</div>'  # End main container
    )
    st.markdown(html, unsafe_allow_html=True)


def _extract_factor_chips(flags: list) -> list:
    """Extrae factores clave de los flags para mostrar como chips."""
    chips = []
    seen = set()
    
    for flag in flags:
        evidence = flag.get('evidence', {})
        
        if 'mean_rir' in evidence and evidence['mean_rir'] <= 1.5:
            if 'rir_bajo' not in seen:
                chips.append({'label': f"RIR {evidence['mean_rir']:.1f}", 'icon': '🎯', 'type': 'warning'})
                seen.add('rir_bajo')
        
        if 'near_failure_proportion' in evidence:
            pct = evidence['near_failure_proportion'] * 100
            if pct >= 50 and 'fallo' not in seen:
                chips.append({'label': f"{pct:.0f}% al fallo", 'icon': '🔥', 'type': 'danger'})
                seen.add('fallo')
        
        if 'baseline_e1rm' in evidence and 'last_e1rm' in evidence:
            delta = evidence['last_e1rm'] - evidence['baseline_e1rm']
            if delta < -5 and 'e1rm' not in seen:
                chips.append({'label': f"e1RM ↓{abs(delta):.0f}kg", 'icon': '📉', 'type': 'danger'})
                seen.add('e1rm')
        
        flag_type = flag.get('flag_type', '')
        if flag_type == 'SUSTAINED_NEAR_FAILURE' and 'sustained' not in seen:
            chips.append({'label': 'Intensidad sostenida', 'icon': '⚡', 'type': 'warning'})
            seen.add('sustained')
        elif flag_type == 'HIGH_VOLATILITY' and 'volatility' not in seen:
            chips.append({'label': 'Alta volatilidad', 'icon': '🎢', 'type': 'info'})
            seen.add('volatility')
    
    return chips[:5]


def _render_chips(chips: list, accent: str) -> str:
    """Renderiza los chips como HTML."""
    chip_colors = {
        'danger':  {'bg': 'rgba(224,85,85,0.12)', 'border': '#E0555560', 'text': '#E08080'},
        'warning': {'bg': 'rgba(224,160,64,0.10)', 'border': '#E0A04060', 'text': '#E0C080'},
        'info':    {'bg': 'rgba(80,160,224,0.10)', 'border': '#50A0E060', 'text': '#80C0E0'},
    }
    
    html = ""
    for chip in chips:
        c = chip_colors.get(chip.get('type', 'info'), chip_colors['info'])
        html += (
            f'<span style="display:inline-flex;align-items:center;gap:6px;padding:6px 12px;'
            f'background:{c["bg"]};border:1px solid {c["border"]};border-radius:20px;'
            f'font-size:0.78rem;color:{c["text"]};font-weight:500;">'
            f'<span>{chip.get("icon", "")}</span>'
            f'<span>{chip.get("label", "")}</span>'
            f'</span>'
        )
    return html


def render_exercise_fatigue_card(flag_type: str, exercise: str, severity: int, 
                                  evidence: dict, recommendations: list):
    """
    Renderiza una card de ejercicio con 3 columnas: Señal, Diagnóstico, Acciones.
    """
    level = _get_severity_level(severity)
    colors = SEVERITY_COLORS[level]
    
    type_config = {
        'SUSTAINED_NEAR_FAILURE': {'icon': '🔥', 'label': 'Intensidad Sostenida'},
        'FIXED_LOAD_DRIFT':       {'icon': '📉', 'label': 'Pérdida de Rendimiento'},
        'HIGH_VOLATILITY':        {'icon': '🎢', 'label': 'Alta Volatilidad'},
        'PLATEAU_EFFORT_RISE':    {'icon': '📈', 'label': 'Meseta con Esfuerzo'},
    }
    config = type_config.get(flag_type, {'icon': '⚠️', 'label': flag_type.replace('_', ' ').title()})
    
    # === Columna 1: Señal (métricas) ===
    metrics_html = ""
    
    if 'baseline_reps' in evidence and 'last_reps' in evidence:
        delta = evidence['last_reps'] - evidence['baseline_reps']
        delta_color = '#E05555' if delta < 0 else '#50B080'
        metrics_html += (
            f'<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:10px;">'
            f'<span style="color:#888;font-size:0.8rem;width:50px;">Reps</span>'
            f'<span style="color:#aaa;font-size:0.95rem;">{evidence["baseline_reps"]:.1f}</span>'
            f'<span style="color:#666;">→</span>'
            f'<span style="color:{delta_color};font-size:0.95rem;font-weight:600;">{evidence["last_reps"]:.0f}</span>'
            f'</div>'
        )
    
    if 'baseline_e1rm' in evidence and 'last_e1rm' in evidence:
        delta = evidence['last_e1rm'] - evidence['baseline_e1rm']
        delta_color = '#E05555' if delta < 0 else '#50B080'
        metrics_html += (
            f'<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:10px;">'
            f'<span style="color:#888;font-size:0.8rem;width:50px;">e1RM</span>'
            f'<span style="color:#aaa;font-size:0.95rem;">{evidence["baseline_e1rm"]:.1f}</span>'
            f'<span style="color:#666;">→</span>'
            f'<span style="color:{delta_color};font-size:0.95rem;font-weight:600;">{evidence["last_e1rm"]:.1f}</span>'
            f'<span style="color:{delta_color};font-size:0.75rem;">({delta:+.1f})</span>'
            f'</div>'
        )
    
    trend_indicator = "↘" if evidence.get('last_e1rm', 0) < evidence.get('baseline_e1rm', 0) else "→"
    trend_color = colors['accent'] if trend_indicator == "↘" else "#666"
    
    # === Columna 2: Diagnóstico ===
    diag_html = ""
    
    if 'mean_rir' in evidence:
        rir_val = evidence['mean_rir']
        rir_status = "⚠️" if rir_val <= 1.5 else "✓"
        diag_html += f'<div style="margin-bottom:8px;color:#b0b0b0;font-size:0.85rem;">{rir_status} RIR promedio: <strong>{rir_val:.1f}</strong></div>'
    
    if 'near_failure_proportion' in evidence:
        pct = evidence['near_failure_proportion'] * 100
        pct_status = "⚠️" if pct >= 50 else "✓"
        diag_html += f'<div style="margin-bottom:8px;color:#b0b0b0;font-size:0.85rem;">{pct_status} Sesiones al fallo: <strong>{pct:.0f}%</strong></div>'
    
    if 'k_sessions' in evidence:
        diag_html += f'<div style="margin-bottom:8px;color:#b0b0b0;font-size:0.85rem;">📊 Ventana: últimas {evidence["k_sessions"]} sesiones</div>'
    
    # === Columna 3: Acciones ===
    actions_html = ""
    for i, rec in enumerate(recommendations[:4]):
        action = str(rec).strip()
        if action.startswith('- ') or action.startswith('• '):
            action = action[2:]
        is_primary = (i == 0)
        checkbox = '◉' if is_primary else '○'
        checkbox_color = colors['accent'] if is_primary else '#555'
        text_color = '#e0e0e0' if is_primary else '#999'
        font_weight = '500' if is_primary else '400'
        actions_html += (
            f'<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:8px;">'
            f'<span style="color:{checkbox_color};font-size:0.9rem;">{checkbox}</span>'
            f'<span style="color:{text_color};font-size:0.85rem;font-weight:{font_weight};">{action}</span>'
            f'</div>'
        )
    
    # === Construir card completa ===
    html = (
        f'<div style="background:linear-gradient(180deg,rgba(26,24,30,0.95),rgba(22,20,26,0.98));'
        f'border-radius:14px;margin-bottom:16px;border-left:3px solid {colors["accent"]};'
        f'overflow:hidden;box-shadow:0 2px 12px rgba(0,0,0,0.3);">'
        
        # Header
        f'<div style="display:flex;justify-content:space-between;align-items:center;'
        f'padding:16px 20px;background:rgba(255,255,255,0.02);border-bottom:1px solid rgba(255,255,255,0.04);">'
        f'<div style="display:flex;align-items:center;gap:12px;">'
        f'<span style="font-size:1.3rem;">{config["icon"]}</span>'
        f'<div>'
        f'<div style="font-size:1rem;font-weight:600;color:#e8e8e8;">{exercise}</div>'
        f'<div style="font-size:0.75rem;color:#777;margin-top:2px;">{config["label"]}</div>'
        f'</div>'
        f'</div>'
        f'<div style="padding:5px 14px;border-radius:8px;background:{colors["bg"]};'
        f'border:1px solid {colors["accent"]}40;font-size:0.8rem;font-weight:600;color:{colors["accent"]};">SEV {severity}</div>'
        f'</div>'
        
        # Body: 3 columns
        f'<div style="display:grid;grid-template-columns:1fr 1fr 1.2fr;gap:1px;background:rgba(255,255,255,0.03);">'
        
        # Col 1: Señal
        f'<div style="background:rgba(22,20,26,0.98);padding:16px 18px;">'
        f'<div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:1.5px;color:#666;margin-bottom:12px;font-weight:600;">Señal</div>'
        f'{metrics_html}'
        f'<div style="display:inline-block;padding:4px 10px;background:rgba(255,255,255,0.03);border-radius:6px;margin-top:6px;">'
        f'<span style="color:{trend_color};font-size:1.1rem;margin-right:4px;">{trend_indicator}</span>'
        f'<span style="color:#666;font-size:0.75rem;">tendencia</span>'
        f'</div>'
        f'</div>'
        
        # Col 2: Diagnóstico
        f'<div style="background:rgba(22,20,26,0.98);padding:16px 18px;">'
        f'<div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:1.5px;color:#666;margin-bottom:12px;font-weight:600;">Diagnóstico</div>'
        f'{diag_html}'
        f'</div>'
        
        # Col 3: Acciones
        f'<div style="background:rgba(22,20,26,0.98);padding:16px 18px;">'
        f'<div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:1.5px;color:#666;margin-bottom:12px;font-weight:600;">Acciones</div>'
        f'{actions_html}'
        f'</div>'
        
        f'</div>'  # End grid
        f'</div>'  # End card
    )
    st.markdown(html, unsafe_allow_html=True)


def render_neural_fatigue_section(overload_data: dict):
    """
    Renderiza la sección completa de Fatiga Neural con el nuevo diseño.
    """
    if not overload_data.get('flags'):
        return
    
    flags = overload_data['flags']
    summary = overload_data.get('summary', {})
    
    total_score = summary.get('total_overload_score', 0)
    primary_cause = summary.get('primary_cause', 'UNKNOWN')
    n_flags = summary.get('n_flags_detected', len(flags))
    
    # 1. Summary Bar
    render_neural_fatigue_summary_bar(
        total_score=total_score,
        primary_cause=primary_cause,
        n_flags=n_flags,
        flags=flags
    )
    
    # 2. Cards por ejercicio (ordenados por severidad)
    sorted_flags = sorted(flags, key=lambda x: x.get('severity', 0), reverse=True)
    
    for flag in sorted_flags:
        render_exercise_fatigue_card(
            flag_type=flag.get('flag_type', ''),
            exercise=flag.get('exercise', ''),
            severity=flag.get('severity', 0),
            evidence=flag.get('evidence', {}),
            recommendations=flag.get('recommendations', [])
        )
    
    # 3. CTA Button
    cta_html = (
        '<div style="text-align:center;margin-top:20px;margin-bottom:10px;">'
        '<div style="display:inline-block;padding:12px 32px;'
        'background:linear-gradient(135deg,rgba(80,176,128,0.15),rgba(80,176,128,0.08));'
        'border:1px solid rgba(80,176,128,0.4);border-radius:10px;'
        'color:#70C090;font-size:0.9rem;font-weight:600;cursor:pointer;">'
        '✓ Aplicar plan de recuperación'
        '</div>'
        '</div>'
    )
    st.markdown(cta_html, unsafe_allow_html=True)


# === FUNCIONES LEGACY (mantener compatibilidad) ===

def render_overload_alert(flag_type: str, exercise: str, severity: int, 
                          evidence: dict, recommendations: list, accent: str = "#FF4500"):
    """LEGACY: Redirige al nuevo componente."""
    render_exercise_fatigue_card(flag_type, exercise, severity, evidence, recommendations)


def render_overload_summary(total_score: int, primary_cause: str, n_flags: int):
    """LEGACY: No-op, el summary ahora se renderiza junto con las cards."""
    pass


def clean_line(s: str) -> str:
    """Limpia una línea de texto de bullets y formato markdown."""
    s = str(s).strip()
    # remove leading markdown bullets
    if s.startswith("- ") or s.startswith("• "):
        s = s[2:].strip()
    # remove bold markers
    s = s.replace("**", "")
    return s
