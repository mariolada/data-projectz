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


# =============================================================================
# CONSEJOS DE HOY - Nuevo Sistema de Componentes Premium
# =============================================================================

def _get_zone_color(zone: str) -> dict:
    """Retorna colores según la zona de readiness."""
    zone_lower = zone.lower()
    if 'alta' in zone_lower or 'high' in zone_lower or '🟢' in zone:
        return {'accent': '#50C878', 'bg': 'rgba(80,200,120,0.08)', 'label': 'ALTA'}
    elif 'media' in zone_lower or 'medium' in zone_lower or '🟡' in zone:
        return {'accent': '#E0A040', 'bg': 'rgba(224,160,64,0.08)', 'label': 'MEDIA'}
    else:
        return {'accent': '#E05555', 'bg': 'rgba(224,85,85,0.08)', 'label': 'BAJA'}


def _get_fatigue_color(fatigue_type: str) -> dict:
    """Retorna colores según el tipo de fatiga."""
    ftype = fatigue_type.lower()
    if ftype == 'fresh':
        return {'accent': '#50C878', 'bg': 'rgba(80,200,120,0.10)', 'emoji': '✨'}
    elif ftype == 'central':
        return {'accent': '#E07040', 'bg': 'rgba(224,112,64,0.08)', 'emoji': '🧠'}
    elif ftype == 'peripheral':
        return {'accent': '#D4A030', 'bg': 'rgba(212,160,48,0.08)', 'emoji': '💪'}
    elif ftype == 'mixed':
        return {'accent': '#E05555', 'bg': 'rgba(224,85,85,0.08)', 'emoji': '⚠️'}
    elif ftype == 'fatigued':
        return {'accent': '#E07040', 'bg': 'rgba(224,112,64,0.08)', 'emoji': '😴'}
    else:
        return {'accent': '#888888', 'bg': 'rgba(136,136,136,0.08)', 'emoji': '❓'}


def render_consejos_summary_strip(fatigue_type: str, zone_display: str, 
                                   target_split: str, intensity_hint: str,
                                   volume: str, diagnosis_short: str):
    """
    Renderiza la Summary Strip horizontal con badges/chips.
    Es lo primero que ve el usuario - estado en 2 segundos.
    """
    fatigue_colors = _get_fatigue_color(fatigue_type)
    zone_colors = _get_zone_color(zone_display)
    
    # Extraer RIR del intensity_hint (ej: "RIR 2–3" de "Normal: RIR 2–3")
    rir_match = intensity_hint if 'RIR' in intensity_hint else 'RIR 2-3'
    if ':' in rir_match:
        rir_match = rir_match.split(':')[-1].strip()
    
    # Construir chips
    chips = [
        {'label': fatigue_type.upper(), 'color': fatigue_colors['accent'], 'bg': fatigue_colors['bg'], 'primary': True},
        {'label': f"ZONA: {zone_colors['label']}", 'color': zone_colors['accent'], 'bg': zone_colors['bg']},
        {'label': f"SPLIT: {target_split.upper()}", 'color': '#80A0C0', 'bg': 'rgba(128,160,192,0.08)'},
        {'label': rir_match.upper(), 'color': '#A080C0', 'bg': 'rgba(160,128,192,0.08)'},
        {'label': f"VOL: {volume.upper() if len(volume) < 15 else 'ESTÁNDAR'}", 'color': '#80C0A0', 'bg': 'rgba(128,192,160,0.08)'},
    ]
    
    chips_html = ""
    for chip in chips:
        primary_style = "font-weight:700;font-size:0.85rem;" if chip.get('primary') else "font-weight:500;font-size:0.78rem;"
        chips_html += (
            f'<span style="display:inline-flex;align-items:center;padding:6px 14px;'
            f'background:{chip["bg"]};border:1px solid {chip["color"]}50;border-radius:6px;'
            f'color:{chip["color"]};{primary_style}margin-right:8px;margin-bottom:6px;">'
            f'{chip["label"]}'
            f'</span>'
        )
    
    html = (
        f'<div style="background:linear-gradient(135deg,rgba(22,22,28,0.95),rgba(28,26,32,0.90));'
        f'border-radius:12px;padding:16px 20px;margin-bottom:20px;'
        f'border-left:3px solid {fatigue_colors["accent"]};box-shadow:0 2px 12px rgba(0,0,0,0.3);">'
        
        # Chips row
        f'<div style="display:flex;flex-wrap:wrap;align-items:center;margin-bottom:10px;">'
        f'{chips_html}'
        f'</div>'
        
        # Diagnosis line
        f'<div style="color:#a0a0a0;font-size:0.85rem;padding-left:2px;">'
        f'<span style="color:{fatigue_colors["accent"]};margin-right:6px;">—</span>'
        f'{diagnosis_short}'
        f'</div>'
        
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_card_diagnostico(fatigue_type: str, diagnosis: str, recommendations: list, 
                             intensity_hint: str = None):
    """
    Card 1: Diagnóstico - ¿Qué me pasa y por qué?
    Incluye tipo de fatiga, razón y acciones específicas.
    """
    colors = _get_fatigue_color(fatigue_type)
    
    # Limpiar recomendaciones
    clean_recs = []
    for rec in recommendations[:4]:
        r = str(rec).strip()
        if r.startswith('- ') or r.startswith('• '):
            r = r[2:]
        clean_recs.append(r)
    
    # Construir acciones HTML
    actions_html = ""
    for i, action in enumerate(clean_recs):
        is_primary = (i == 0)
        bullet = '▸' if is_primary else '·'
        text_color = '#e0e0e0' if is_primary else '#b0b0b0'
        actions_html += (
            f'<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:8px;">'
            f'<span style="color:{colors["accent"]};font-size:0.9rem;">{bullet}</span>'
            f'<span style="color:{text_color};font-size:0.85rem;line-height:1.5;">{action}</span>'
            f'</div>'
        )
    
    # Hint de intensidad si existe
    intensity_html = ""
    if intensity_hint:
        intensity_html = (
            f'<div style="margin-top:12px;padding:8px 12px;background:rgba(255,255,255,0.03);'
            f'border-radius:6px;border-left:2px solid {colors["accent"]}50;">'
            f'<span style="color:#888;font-size:0.75rem;text-transform:uppercase;letter-spacing:1px;">Intensidad sugerida</span>'
            f'<div style="color:#c0c0c0;font-size:0.85rem;margin-top:4px;">{intensity_hint}</div>'
            f'</div>'
        )
    
    html = (
        f'<div style="background:linear-gradient(180deg,rgba(26,24,30,0.95),rgba(22,20,26,0.98));'
        f'border-radius:12px;border-left:3px solid {colors["accent"]};overflow:hidden;'
        f'box-shadow:0 2px 10px rgba(0,0,0,0.25);height:100%;">'
        
        # Header
        f'<div style="padding:16px 18px;background:rgba(255,255,255,0.02);'
        f'border-bottom:1px solid rgba(255,255,255,0.04);">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<span style="font-size:1.2rem;">{colors["emoji"]}</span>'
        f'<span style="font-size:0.95rem;font-weight:600;color:#e0e0e0;">Diagnóstico</span>'
        f'</div>'
        f'<span style="padding:4px 10px;border-radius:5px;background:{colors["bg"]};'
        f'border:1px solid {colors["accent"]}40;color:{colors["accent"]};'
        f'font-size:0.75rem;font-weight:600;">{fatigue_type.upper()}</span>'
        f'</div>'
        f'</div>'
        
        # Body
        f'<div style="padding:16px 18px;">'
        
        # Diagnosis text
        f'<div style="color:#909090;font-size:0.8rem;margin-bottom:14px;line-height:1.5;">{diagnosis}</div>'
        
        # Actions section
        f'<div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:1.5px;'
        f'color:#666;margin-bottom:10px;font-weight:600;">Acciones específicas</div>'
        f'{actions_html}'
        
        f'{intensity_html}'
        
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_card_plan_ejecucion(zone_display: str, reco_base: str, intensity: str, 
                                volume: str, target_split: str, extras: list = None):
    """
    Card 2: Plan de Ejecución - ¿Qué hago exactamente?
    Formato de bloques en 2 columnas: Qué (zona/split) | Cómo (intensidad/volumen).
    """
    zone_colors = _get_zone_color(zone_display)
    
    # Limpiar zona display (quitar emoji si ya está)
    zone_label = zone_colors['label']
    
    # Extras (pain, stiffness, etc)
    extras_html = ""
    if extras:
        for extra in extras[:3]:
            extras_html += (
                f'<div style="display:flex;align-items:flex-start;gap:8px;margin-bottom:6px;'
                f'padding:6px 10px;background:rgba(255,255,255,0.02);border-radius:6px;">'
                f'<span style="color:#c0c0c0;font-size:0.82rem;line-height:1.4;">{extra}</span>'
                f'</div>'
            )
    
    html = (
        f'<div style="background:linear-gradient(180deg,rgba(26,24,30,0.95),rgba(22,20,26,0.98));'
        f'border-radius:12px;border-left:3px solid {zone_colors["accent"]};overflow:hidden;'
        f'box-shadow:0 2px 10px rgba(0,0,0,0.25);height:100%;">'
        
        # Header
        f'<div style="padding:16px 18px;background:rgba(255,255,255,0.02);'
        f'border-bottom:1px solid rgba(255,255,255,0.04);">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<span style="font-size:1.2rem;">📋</span>'
        f'<span style="font-size:0.95rem;font-weight:600;color:#e0e0e0;">Plan de Ejecución</span>'
        f'</div>'
        f'</div>'
        
        # Body - 2 columns grid
        f'<div style="padding:16px 18px;">'
        
        f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:14px;">'
        
        # Column 1: QUÉ
        f'<div>'
        f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:1.5px;'
        f'color:#555;margin-bottom:10px;font-weight:600;">Qué</div>'
        
        # Zona
        f'<div style="margin-bottom:12px;">'
        f'<div style="color:#777;font-size:0.75rem;margin-bottom:4px;">Zona</div>'
        f'<span style="display:inline-block;padding:5px 12px;border-radius:6px;'
        f'background:{zone_colors["bg"]};border:1px solid {zone_colors["accent"]}50;'
        f'color:{zone_colors["accent"]};font-size:0.85rem;font-weight:600;">{zone_label}</span>'
        f'</div>'
        
        # Split
        f'<div>'
        f'<div style="color:#777;font-size:0.75rem;margin-bottom:4px;">Split</div>'
        f'<span style="display:inline-block;padding:5px 12px;border-radius:6px;'
        f'background:rgba(128,160,192,0.08);border:1px solid rgba(128,160,192,0.4);'
        f'color:#80A0C0;font-size:0.85rem;font-weight:600;">{target_split.upper()}</span>'
        f'</div>'
        
        f'</div>'
        
        # Column 2: CÓMO
        f'<div>'
        f'<div style="font-size:0.65rem;text-transform:uppercase;letter-spacing:1.5px;'
        f'color:#555;margin-bottom:10px;font-weight:600;">Cómo</div>'
        
        # Intensidad
        f'<div style="margin-bottom:12px;">'
        f'<div style="color:#777;font-size:0.75rem;margin-bottom:4px;">Intensidad</div>'
        f'<span style="color:#c0c0c0;font-size:0.85rem;">{intensity}</span>'
        f'</div>'
        
        # Volumen
        f'<div>'
        f'<div style="color:#777;font-size:0.75rem;margin-bottom:4px;">Volumen</div>'
        f'<span style="color:#c0c0c0;font-size:0.85rem;">{volume}</span>'
        f'</div>'
        
        f'</div>'
        
        f'</div>'  # End grid
        
        # Recomendación base
        f'<div style="padding:10px 12px;background:rgba(255,255,255,0.02);border-radius:8px;'
        f'border-left:2px solid {zone_colors["accent"]}60;margin-bottom:12px;">'
        f'<span style="color:#a0a0a0;font-size:0.82rem;">{reco_base}</span>'
        f'</div>'
        
        # Extras (pain, stiffness, etc)
        f'{extras_html}'
        
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_reglas_checklist(rules: list, title: str = "Reglas de hoy"):
    """
    Renderiza las reglas como checklist operativo compacto.
    Formato de checks antes de entrenar.
    """
    # Categorizar reglas por tipo
    obligatorias = []
    recomendadas = []
    advertencias = []
    
    for rule in rules:
        r = str(rule).strip()
        if r.startswith('❌') or 'NO ' in r.upper() or 'STOP' in r.upper():
            obligatorias.append(r)
        elif r.startswith('⚠️'):
            advertencias.append(r)
        else:
            recomendadas.append(r)
    
    # Limpiar emojis iniciales para uniformidad
    def clean_rule(r):
        for prefix in ['✅ ', '❌ ', '⚠️ ', '🧊 ', '🔥 ']:
            if r.startswith(prefix):
                return r[len(prefix):]
        return r
    
    def render_rule_item(rule, icon, color):
        cleaned = clean_rule(rule)
        return (
            f'<div style="display:flex;align-items:flex-start;gap:10px;margin-bottom:8px;'
            f'padding:8px 12px;background:rgba(255,255,255,0.02);border-radius:8px;'
            f'border:1px solid rgba(255,255,255,0.03);">'
            f'<span style="color:{color};font-size:1rem;flex-shrink:0;">{icon}</span>'
            f'<span style="color:#c0c0c0;font-size:0.85rem;line-height:1.5;">{cleaned}</span>'
            f'</div>'
        )
    
    rules_html = ""
    
    # Obligatorias primero (rojas)
    for rule in obligatorias:
        rules_html += render_rule_item(rule, '⛔', '#E05555')
    
    # Advertencias
    for rule in advertencias:
        rules_html += render_rule_item(rule, '⚠️', '#E0A040')
    
    # Recomendadas
    for rule in recomendadas:
        rules_html += render_rule_item(rule, '✓', '#50C878')
    
    n_rules = len(rules)
    
    html = (
        f'<div style="background:linear-gradient(180deg,rgba(26,24,30,0.95),rgba(22,20,26,0.98));'
        f'border-radius:12px;overflow:hidden;box-shadow:0 2px 10px rgba(0,0,0,0.25);'
        f'border:1px solid rgba(255,255,255,0.04);">'
        
        # Header
        f'<div style="padding:14px 18px;background:rgba(255,255,255,0.02);'
        f'border-bottom:1px solid rgba(255,255,255,0.04);'
        f'display:flex;justify-content:space-between;align-items:center;">'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<span style="font-size:1.1rem;">📝</span>'
        f'<span style="font-size:0.95rem;font-weight:600;color:#e0e0e0;">{title}</span>'
        f'</div>'
        f'<span style="color:#666;font-size:0.75rem;">{n_rules} checks antes de entrenar</span>'
        f'</div>'
        
        # Body
        f'<div style="padding:14px 16px;">'
        f'{rules_html}'
        f'</div>'
        
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_consejos_section(fatigue_analysis: dict, zone_display: str, plan: list, rules: list,
                            sleep_h: float = 0, stress: int = 0):
    """
    Función principal que orquesta toda la sección "Consejos de hoy".
    Reemplaza el bloque antiguo con el nuevo diseño.
    
    Args:
        fatigue_analysis: Dict del motor de personalización
        zone_display: Zona de readiness (ej: "🟡 MEDIA")
        plan: Lista de líneas del plan accionable
        rules: Lista de reglas de hoy
        sleep_h: Horas de sueño (para diagnosis short)
        stress: Nivel de estrés (para diagnosis short)
    """
    # Extraer datos del fatigue_analysis
    fatigue_type = fatigue_analysis.get('type', 'unknown')
    diagnosis = fatigue_analysis.get('reason', '')
    target_split = fatigue_analysis.get('target_split', 'full')
    intensity_hint = fatigue_analysis.get('intensity_hint', 'RIR 2-3')
    recommendations = fatigue_analysis.get('recommendations', [])
    
    # Parsear plan para extraer zona, intensidad, volumen
    reco_base = "Mantén técnica impecable"
    volume = "Estándar"
    intensity = "RIR 2-3"
    extras = []
    
    for line in plan:
        line_clean = clean_line(line)
        if 'Recomendación base' in line_clean:
            reco_base = line_clean.replace('Recomendación base:', '').strip()
        elif 'Volumen' in line_clean:
            volume = line_clean.replace('Volumen:', '').strip()
        elif 'Intensidad' in line_clean and 'RIR' in line_clean:
            intensity = line_clean.replace('Intensidad:', '').strip()
        elif 'Dolor detectado' in line_clean or 'Evita hoy' in line_clean or 'Puedes hacer' in line_clean:
            extras.append(line_clean)
        elif 'Rigidez' in line_clean:
            extras.append(line_clean)
    
    # Construir diagnosis short
    diagnosis_short = f"Bien descansado ({sleep_h}h, estrés {stress}/10)" if fatigue_type == 'fresh' else diagnosis
    if len(diagnosis_short) > 80:
        diagnosis_short = diagnosis_short[:77] + "..."
    
    # 1. Summary Strip
    render_consejos_summary_strip(
        fatigue_type=fatigue_type,
        zone_display=zone_display,
        target_split=target_split,
        intensity_hint=intensity_hint,
        volume=volume,
        diagnosis_short=diagnosis_short
    )
    
    # 2. Two cards side by side
    col1, col2 = st.columns(2)
    
    with col1:
        render_card_diagnostico(
            fatigue_type=fatigue_type,
            diagnosis=diagnosis,
            recommendations=recommendations,
            intensity_hint=intensity_hint
        )
    
    with col2:
        render_card_plan_ejecucion(
            zone_display=zone_display,
            reco_base=reco_base,
            intensity=intensity,
            volume=volume,
            target_split=target_split,
            extras=extras if extras else None
        )
    
    # 3. Reglas checklist (full width, más compacto)
    st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)
    render_reglas_checklist(rules)


# =============================================================================
# DESGLOSE PERSONALIZADO + READINESS HOY - Componentes Premium
# =============================================================================

def _get_readiness_color(readiness: int) -> dict:
    """Retorna colores según el valor de readiness."""
    if readiness >= 75:
        return {'accent': '#50C878', 'bg': 'rgba(80,200,120,0.08)', 'label': 'ALTA', 'glow': 'rgba(80,200,120,0.25)'}
    elif readiness >= 55:
        return {'accent': '#E0A040', 'bg': 'rgba(224,160,64,0.08)', 'label': 'MEDIA', 'glow': 'rgba(224,160,64,0.20)'}
    else:
        return {'accent': '#E05555', 'bg': 'rgba(224,85,85,0.08)', 'label': 'BAJA', 'glow': 'rgba(224,85,85,0.20)'}


def _get_risk_color(risk_level: str) -> dict:
    """Retorna colores según nivel de riesgo."""
    level = risk_level.lower()
    if level == 'low':
        return {'accent': '#50C878', 'bg': 'rgba(80,200,120,0.08)', 'emoji': '✅'}
    elif level == 'medium':
        return {'accent': '#E0A040', 'bg': 'rgba(224,160,64,0.08)', 'emoji': '⚠️'}
    else:
        return {'accent': '#E05555', 'bg': 'rgba(224,85,85,0.08)', 'emoji': '🚨'}


def render_component_rows(components: dict, adjustments: dict = None):
    """
    Renderiza los componentes del readiness como card-rows con barras.
    Reemplaza la tabla tradicional.
    """
    # Iconos por componente
    component_icons = {
        'sleep': '🌙',
        'state': '🧠',
        'motivation': '🔥',
    }
    component_labels = {
        'sleep': 'Sueño',
        'state': 'Estado (Fatiga/Estrés)',
        'motivation': 'Motivación',
    }
    
    rows_html = ""
    max_val = max(components.values()) if components else 30
    
    for key, val in components.items():
        icon = component_icons.get(key, '📊')
        label = component_labels.get(key, key.capitalize())
        bar_width = min(100, (val / max_val) * 100) if max_val > 0 else 0
        
        rows_html += (
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'padding:12px 14px;margin-bottom:8px;background:rgba(255,255,255,0.02);'
            f'border-radius:10px;border:1px solid rgba(255,255,255,0.04);">'
            
            # Left: icon + label
            f'<div style="display:flex;align-items:center;gap:10px;flex:1;">'
            f'<span style="font-size:1.1rem;opacity:0.7;">{icon}</span>'
            f'<span style="color:#b0b0b0;font-size:0.85rem;">{label}</span>'
            f'</div>'
            
            # Right: percentage + bar
            f'<div style="text-align:right;min-width:100px;">'
            f'<div style="font-size:1.1rem;font-weight:700;color:#e0e0e0;margin-bottom:4px;">{val:.1f}%</div>'
            f'<div style="height:4px;background:rgba(255,255,255,0.08);border-radius:2px;overflow:hidden;">'
            f'<div style="height:100%;width:{bar_width}%;background:linear-gradient(90deg,#50C878,#80D0A0);'
            f'border-radius:2px;"></div>'
            f'</div>'
            f'</div>'
            
            f'</div>'
        )
    
    # Penalizaciones si existen
    if adjustments:
        adj_icons = {'pain_penalty': '🩹', 'sick_penalty': '🤒', 'caffeine_mask': '☕'}
        adj_labels = {'pain_penalty': 'Dolor', 'sick_penalty': 'Enfermedad', 'caffeine_mask': 'Cafeína'}
        
        for key, val in adjustments.items():
            if val != 0:
                icon = adj_icons.get(key, '⚡')
                label = adj_labels.get(key, key)
                color = '#E05555' if val < 0 else '#E0A040'
                
                rows_html += (
                    f'<div style="display:flex;align-items:center;justify-content:space-between;'
                    f'padding:10px 14px;margin-bottom:6px;background:rgba(224,85,85,0.05);'
                    f'border-radius:8px;border-left:2px solid {color};">'
                    f'<div style="display:flex;align-items:center;gap:10px;">'
                    f'<span style="font-size:0.95rem;">{icon}</span>'
                    f'<span style="color:#a0a0a0;font-size:0.82rem;">{label}</span>'
                    f'</div>'
                    f'<span style="color:{color};font-size:0.95rem;font-weight:600;">{val:+.1f}%</span>'
                    f'</div>'
                )
    
    html = (
        f'<div style="margin-bottom:16px;">'
        f'<div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:1.5px;'
        f'color:#666;margin-bottom:12px;font-weight:600;">Componentes del cálculo</div>'
        f'{rows_html}'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_insights_stack(sleep_responsive: bool, readiness: int, p50: float, p75: float, n_days: int = 0):
    """
    Renderiza el stack de insights personalizados.
    """
    delta = readiness - p50 if p50 else 0
    
    # Insight principal (sensibilidad al sueño)
    if sleep_responsive:
        main_icon = "💤"
        main_title = "ERES SENSIBLE AL SUEÑO"
        main_subtitle = "Prioriza dormir bien para optimizar readiness"
        main_color = "#80A0E0"
    else:
        main_icon = "🎯"
        main_title = "NO ERES TAN SENSIBLE AL SUEÑO"
        main_subtitle = "Flexibilidad con horas, pero calidad importa"
        main_color = "#50C878"
    
    # Insight secundario (delta vs media)
    if delta > 5:
        delta_icon = "✅"
        delta_color = "#50C878"
        delta_text = f"Hoy +{delta:.0f} vs tu media ({p50:.0f})"
    elif delta >= -5:
        delta_icon = "ℹ️"
        delta_color = "#80A0C0"
        delta_text = f"Hoy ~igual a media ({p50:.0f})"
    else:
        delta_icon = "⚠️"
        delta_color = "#E0A040"
        delta_text = f"Hoy {delta:.0f} vs media ({p50:.0f})"
    
    # P75 display
    p75_display = f"p75≈{p75:.0f}" if p75 and abs(p75 - p50) < 3 else f"p75: {p75:.0f}" if p75 else ""
    if n_days < 14 and n_days > 0:
        p75_display += f" (histórico corto: {n_days}d)"
    
    html = (
        f'<div style="display:flex;flex-direction:column;gap:12px;">'
        
        # Main insight
        f'<div style="padding:16px;background:linear-gradient(135deg,rgba(26,24,30,0.95),rgba(22,20,26,0.98));'
        f'border-radius:12px;border-left:3px solid {main_color};box-shadow:0 2px 10px rgba(0,0,0,0.2);">'
        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="font-size:1.1rem;">{main_icon}</span>'
        f'<span style="font-size:0.9rem;font-weight:600;color:#e0e0e0;">{main_title}</span>'
        f'</div>'
        f'<span style="padding:3px 8px;border-radius:4px;background:rgba(128,160,192,0.15);'
        f'color:#80A0C0;font-size:0.65rem;font-weight:600;">PERSONALIZADO</span>'
        f'</div>'
        f'<div style="color:#909090;font-size:0.82rem;padding-left:28px;">{main_subtitle}</div>'
        f'</div>'
        
        # Delta insight
        f'<div style="padding:14px;background:rgba(255,255,255,0.02);'
        f'border-radius:10px;border-left:3px solid {delta_color};">'
        f'<div style="display:flex;justify-content:space-between;align-items:center;">'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="font-size:1rem;">{delta_icon}</span>'
        f'<span style="font-size:0.88rem;font-weight:500;color:#c0c0c0;">{delta_text}</span>'
        f'</div>'
        f'<span style="padding:3px 8px;border-radius:4px;background:rgba(224,160,64,0.12);'
        f'color:#E0A040;font-size:0.65rem;font-weight:600;">TENDENCIA</span>'
        f'</div>'
        f'</div>'
        
        # P75 note if relevant
        + (f'<div style="color:#666;font-size:0.75rem;padding-left:4px;">{p75_display}</div>' if p75_display else '')
        +
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_notes_compact(notes: list):
    """
    Renderiza notas del análisis de forma compacta.
    Primera nota visible, resto en expander.
    """
    if not notes:
        return
    
    # Primera nota siempre visible
    first_note = notes[0] if notes else ""
    remaining = notes[1:] if len(notes) > 1 else []
    
    html = (
        f'<div style="margin-top:12px;padding:10px 14px;background:rgba(80,200,120,0.06);'
        f'border-radius:8px;border-left:2px solid #50C87880;">'
        f'<div style="display:flex;align-items:flex-start;gap:8px;">'
        f'<span style="color:#50C878;font-size:0.9rem;">✓</span>'
        f'<span style="color:#a0a0a0;font-size:0.82rem;line-height:1.5;">{first_note}</span>'
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    
    # Resto en expander si hay más
    if remaining:
        with st.expander(f"Ver {len(remaining)} nota(s) más"):
            for note in remaining:
                st.caption(f"• {note}")


def render_readiness_hero(readiness: int, zone_label: str, confidence: str = "medium"):
    """
    Renderiza el bloque hero del readiness con gauge circular y badges.
    Columna 1 del nuevo layout.
    """
    colors = _get_readiness_color(readiness)
    
    # Calcular ángulo para el gauge (0-100 -> 0-360)
    gauge_pct = min(readiness, 100)
    
    # Microtexto según zona
    zone_microtexts = {
        'ALTA': 'Listo para push / PRs',
        'MEDIA': 'Listo para entrenar normal',
        'BAJA': 'Considera deload o descanso',
    }
    microtext = zone_microtexts.get(colors['label'], 'Evalúa según sensaciones')
    
    # Confidence chip
    conf_colors = {
        'high': {'bg': 'rgba(80,200,120,0.12)', 'text': '#50C878'},
        'medium': {'bg': 'rgba(224,160,64,0.12)', 'text': '#E0A040'},
        'low': {'bg': 'rgba(224,85,85,0.12)', 'text': '#E05555'},
    }
    conf = conf_colors.get(confidence.lower(), conf_colors['medium'])
    
    html = (
        f'<div style="background:linear-gradient(135deg,rgba(22,22,28,0.98),rgba(28,26,32,0.95));'
        f'border-radius:16px;padding:24px;border-left:4px solid {colors["accent"]};'
        f'box-shadow:0 4px 20px rgba(0,0,0,0.3),0 0 30px {colors["glow"]};text-align:center;">'
        
        # Gauge circular
        f'<div style="position:relative;width:120px;height:120px;margin:0 auto 16px;">'
        f'<svg width="120" height="120" style="transform:rotate(-90deg);">'
        f'<circle cx="60" cy="60" r="50" fill="none" stroke="rgba(255,255,255,0.06)" stroke-width="10"/>'
        f'<circle cx="60" cy="60" r="50" fill="none" stroke="{colors["accent"]}" stroke-width="10" '
        f'stroke-dasharray="{gauge_pct * 3.14} 314" stroke-linecap="round"/>'
        f'</svg>'
        f'<div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);text-align:center;">'
        f'<div style="font-size:2.2rem;font-weight:800;color:{colors["accent"]};line-height:1;">{readiness}</div>'
        f'<div style="font-size:0.7rem;color:#666;margin-top:2px;">/100</div>'
        f'</div>'
        f'</div>'
        
        # Chips row
        f'<div style="display:flex;justify-content:center;gap:8px;margin-bottom:10px;">'
        
        # Zona chip
        f'<span style="padding:5px 12px;border-radius:6px;background:{colors["bg"]};'
        f'border:1px solid {colors["accent"]}50;color:{colors["accent"]};'
        f'font-size:0.75rem;font-weight:600;">ZONA: {colors["label"]}</span>'
        
        # Confidence chip
        f'<span style="padding:5px 10px;border-radius:6px;background:{conf["bg"]};'
        f'color:{conf["text"]};font-size:0.7rem;font-weight:500;">CONF: {confidence.upper()}</span>'
        
        f'</div>'
        
        # Microtext
        f'<div style="color:#808080;font-size:0.8rem;">{microtext}</div>'
        
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_baseline_comparison(readiness: int, p50: float, p75: float, n_days: int = 0):
    """
    Renderiza la comparación con baseline personal.
    Columna 2 del nuevo layout - barra con 3 marcadores.
    """
    delta = readiness - p50 if p50 else 0
    delta_color = '#50C878' if delta >= 0 else '#E05555'
    
    # Posiciones en la barra (0-100 scale)
    # Normalizar todo a un rango visual razonable
    min_val = min(p50 - 20, readiness - 10) if p50 else 30
    max_val = max(p75 + 10, readiness + 10) if p75 else 90
    range_val = max_val - min_val if max_val > min_val else 60
    
    def to_pct(val):
        return max(5, min(95, ((val - min_val) / range_val) * 100))
    
    p50_pos = to_pct(p50) if p50 else 40
    p75_pos = to_pct(p75) if p75 else 60
    today_pos = to_pct(readiness)
    
    # P75 display text
    if p75 and abs(p75 - p50) < 3:
        p75_text = f"p75≈{p75:.0f}"
    else:
        p75_text = f"p75: {p75:.0f}" if p75 else ""
    
    # History note
    history_note = f"Basado en {n_days} días" if n_days > 0 and n_days < 30 else ""
    
    # Pre-compute formatted values
    p50_display = f"{p50:.0f}" if p50 else "—"
    p75_display = f"{p75:.0f}" if p75 else "—"
    delta_display = f"{delta:+.0f}"
    p75_label = p75_text.split(":")[0] if p75_text else "p75"
    
    html = (
        f'<div style="background:linear-gradient(135deg,rgba(26,24,30,0.95),rgba(22,20,26,0.98));'
        f'border-radius:14px;padding:20px;border:1px solid rgba(255,255,255,0.04);height:100%;">'
        
        f'<div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:1.5px;'
        f'color:#666;margin-bottom:16px;font-weight:600;">Contexto Personal</div>'
        
        # Stats row
        f'<div style="display:flex;justify-content:space-between;margin-bottom:16px;">'
        f'<div>'
        f'<div style="color:#777;font-size:0.72rem;">Tu media</div>'
        f'<div style="color:#b0b0b0;font-size:1.1rem;font-weight:600;">{p50_display}</div>'
        f'</div>'
        f'<div style="text-align:center;">'
        f'<div style="color:#777;font-size:0.72rem;">{p75_label}</div>'
        f'<div style="color:#b0b0b0;font-size:1.1rem;font-weight:600;">{p75_display}</div>'
        f'</div>'
        f'<div style="text-align:right;">'
        f'<div style="color:#777;font-size:0.72rem;">Hoy</div>'
        f'<div style="color:{delta_color};font-size:1.1rem;font-weight:700;">{delta_display}</div>'
        f'</div>'
        f'</div>'
        
        # Visual bar with markers
        f'<div style="position:relative;height:24px;margin-bottom:12px;">'
        
        # Background bar
        f'<div style="position:absolute;top:10px;left:0;right:0;height:4px;'
        f'background:rgba(255,255,255,0.08);border-radius:2px;"></div>'
        
        # P50 marker
        f'<div style="position:absolute;top:6px;left:{p50_pos}%;transform:translateX(-50%);">'
        f'<div style="width:2px;height:12px;background:#808080;border-radius:1px;"></div>'
        f'<div style="font-size:0.6rem;color:#666;margin-top:2px;white-space:nowrap;">p50</div>'
        f'</div>'
    )
    
    # P75 marker (conditional)
    if p75 and abs(p75_pos - p50_pos) > 8:
        html += (
            f'<div style="position:absolute;top:6px;left:{p75_pos}%;transform:translateX(-50%);">'
            f'<div style="width:2px;height:12px;background:#A0A0A0;border-radius:1px;"></div>'
            f'<div style="font-size:0.6rem;color:#888;margin-top:2px;">p75</div>'
            f'</div>'
        )
    
    # Today marker (highlighted)
    today_shadow = delta_color + "60"
    html += (
        f'<div style="position:absolute;top:4px;left:{today_pos}%;transform:translateX(-50%);">'
        f'<div style="width:8px;height:16px;background:{delta_color};border-radius:4px;'
        f'box-shadow:0 0 8px {today_shadow};"></div>'
        f'<div style="font-size:0.65rem;color:{delta_color};margin-top:2px;font-weight:600;">HOY</div>'
        f'</div>'
        f'</div>'
    )
    
    # History note
    if history_note:
        html += f'<div style="color:#555;font-size:0.7rem;text-align:center;">{history_note}</div>'
    
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_injury_risk_card(risk_level: str, score: float, confidence: str, 
                            action: str = None, factors: list = None):
    """
    Renderiza el bloque de riesgo de lesión.
    Columna 3 del nuevo layout.
    """
    colors = _get_risk_color(risk_level)
    
    # Si score es 0 y risk es low, mostrar versión minimal
    is_minimal = (score == 0 or score < 5) and risk_level.lower() == 'low'
    
    # Confidence chip
    conf_map = {'high': '#50C878', 'medium': '#E0A040', 'low': '#E05555'}
    conf_color = conf_map.get(confidence.lower(), '#808080')
    
    html = (
        f'<div style="background:linear-gradient(135deg,rgba(26,24,30,0.95),rgba(22,20,26,0.98));'
        f'border-radius:14px;padding:18px;border:1px solid rgba(255,255,255,0.04);'
        f'{"opacity:0.85;" if is_minimal else ""}height:100%;">'
        
        f'<div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:1.5px;'
        f'color:#666;margin-bottom:14px;font-weight:600;">Riesgo de Lesión</div>'
        
        # Badge grande
        f'<div style="display:flex;align-items:center;justify-content:center;gap:10px;margin-bottom:12px;">'
        f'<span style="font-size:1.5rem;">{colors["emoji"]}</span>'
        f'<span style="padding:6px 16px;border-radius:8px;background:{colors["bg"]};'
        f'border:1px solid {colors["accent"]}60;color:{colors["accent"]};'
        f'font-size:1rem;font-weight:700;">{risk_level.upper()}</span>'
        f'</div>'
        
        # Score y confidence
        f'<div style="display:flex;justify-content:center;gap:16px;margin-bottom:8px;">'
        f'<div style="text-align:center;">'
        f'<div style="color:#777;font-size:0.7rem;">Score</div>'
        f'<div style="color:#b0b0b0;font-size:1rem;font-weight:600;">{score:.0f}/100</div>'
        f'</div>'
        f'<div style="text-align:center;">'
        f'<div style="color:#777;font-size:0.7rem;">Confianza</div>'
        f'<span style="padding:3px 8px;border-radius:4px;background:rgba(255,255,255,0.05);'
        f'color:{conf_color};font-size:0.75rem;font-weight:500;">{confidence.upper()}</span>'
        f'</div>'
        f'</div>'
        
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)
    
    # Action y factors fuera del HTML (usando streamlit nativo)
    if action and risk_level.lower() != 'low':
        st.warning(f"⚠️ **{action}**")
        if factors:
            with st.expander("Factores de riesgo"):
                for factor in factors:
                    st.caption(f"• {factor}")


def render_desglose_section(components: dict, adjustments: dict, 
                            sleep_responsive: bool, readiness: int,
                            p50: float, p75: float, n_days: int, notes: list):
    """
    Función principal que renderiza toda la sección "Desglose Personalizado".
    """
    col1, col2 = st.columns([1.3, 1])
    
    with col1:
        render_component_rows(components, adjustments)
    
    with col2:
        render_insights_stack(sleep_responsive, readiness, p50, p75, n_days)
    
    # Notas compactas
    if notes:
        render_notes_compact(notes)


def render_readiness_section(readiness: int, emoji: str, baselines: dict, 
                             injury_risk: dict, adjustment_factors: dict):
    """
    Función principal que renderiza toda la sección "Tu Readiness Hoy".
    Layout de 3 columnas: Hero | Contexto | Riesgo
    """
    p50 = baselines.get('readiness', {}).get('p50', 50)
    p75 = baselines.get('readiness', {}).get('p75', 55)
    n_days = baselines.get('readiness', {}).get('n', 0)
    
    # Determinar confidence basado en n_days
    if n_days >= 21:
        confidence = "high"
    elif n_days >= 7:
        confidence = "medium"
    else:
        confidence = "low"
    
    col1, col2, col3 = st.columns([1.2, 1.3, 1])
    
    with col1:
        colors = _get_readiness_color(readiness)
        render_readiness_hero(readiness, colors['label'], confidence)
    
    with col2:
        if p50:
            render_baseline_comparison(readiness, p50, p75, n_days)
        else:
            st.info("⏳ Necesita más historia (mínimo 7 días)")
    
    with col3:
        render_injury_risk_card(
            risk_level=injury_risk.get('risk_level', 'low'),
            score=injury_risk.get('score', 0),
            confidence=injury_risk.get('confidence', 'medium'),
            action=injury_risk.get('action'),
            factors=injury_risk.get('factors', [])
        )


# =============================================================================
# CUESTIONARIO REDISEÑADO - Wizard + Live Summary
# =============================================================================

def _get_recovery_status(sleep_h: float, sleep_q: int, disruptions: bool = False) -> dict:
    """Calcula el estado de recuperación basado en sueño."""
    score = 0
    # Horas (0-40 pts)
    if sleep_h >= 7.5:
        score += 40
    elif sleep_h >= 6.5:
        score += 25
    elif sleep_h >= 5.5:
        score += 15
    else:
        score += 5
    
    # Calidad (0-40 pts)
    score += (sleep_q - 1) * 10
    
    # Disruptions penalty
    if disruptions:
        score -= 15
    
    score = max(0, min(100, score))
    
    if score >= 65:
        return {'label': 'Buena', 'level': 'ok', 'emoji': '✅', 'score': score}
    elif score >= 40:
        return {'label': 'Media', 'level': 'mid', 'emoji': '🟡', 'score': score}
    else:
        return {'label': 'Mala', 'level': 'low', 'emoji': '🔴', 'score': score}


def _get_state_status(perceived: int, fatigue: int, stress: int, energy: int = None) -> dict:
    """Calcula el estado general basado en sensaciones."""
    # Perceived es el input dominante (40%)
    # Fatigue/stress/energy son secundarios
    if energy is None:
        energy = 10 - fatigue
    
    # Perceived: 0-10 -> 0-40 pts
    score = perceived * 4
    
    # Energy: 0-10 -> 0-20 pts
    score += energy * 2
    
    # Fatigue penalty: 0-10 -> 0-20 pts penalty
    score -= fatigue * 2
    
    # Stress penalty: 0-10 -> 0-20 pts penalty  
    score -= stress * 2
    
    score = max(0, min(100, score + 40))  # Offset para centrar
    
    if score >= 65:
        return {'label': 'Fresco', 'level': 'ok', 'emoji': '💪', 'score': score}
    elif score >= 40:
        return {'label': 'Normal', 'level': 'mid', 'emoji': '🟡', 'score': score}
    else:
        return {'label': 'Tocado', 'level': 'low', 'emoji': '⚠️', 'score': score}


def _count_flags(alcohol: bool, caffeine: int, pain: bool, sick: bool, 
                 disruptions: bool = False, last_hard: bool = False) -> dict:
    """Cuenta las banderas activas."""
    count = 0
    active = []
    
    if alcohol:
        count += 1
        active.append('alcohol')
    if caffeine >= 2:
        count += 1
        active.append('caffeine')
    if pain:
        count += 1
        active.append('pain')
    if sick:
        count += 1
        active.append('sick')
    if disruptions:
        count += 1
        active.append('disruptions')
    if last_hard:
        count += 1
        active.append('last_hard')
    
    if count == 0:
        return {'label': '0', 'level': 'ok', 'emoji': '✅', 'count': count, 'active': active}
    elif count == 1:
        return {'label': '1', 'level': 'mid', 'emoji': '⚠️', 'count': count, 'active': active}
    else:
        return {'label': f'{count}+', 'level': 'low', 'emoji': '🔴', 'count': count, 'active': active}


def render_live_summary(recovery: dict, state: dict, flags: dict, 
                        estimated_readiness: int = None):
    """
    Renderiza el resumen en vivo sticky del cuestionario.
    Muestra: Recuperación, Estado, Flags y Readiness estimado.
    """
    level_colors = {
        'ok': '#50C878',
        'mid': '#E0A040', 
        'low': '#E05555'
    }
    
    rec_color = level_colors.get(recovery['level'], '#808080')
    state_color = level_colors.get(state['level'], '#808080')
    flags_color = level_colors.get(flags['level'], '#808080')
    
    # Readiness color
    if estimated_readiness:
        if estimated_readiness >= 75:
            ready_color = '#50C878'
        elif estimated_readiness >= 55:
            ready_color = '#E0A040'
        else:
            ready_color = '#E05555'
    else:
        ready_color = '#808080'
    
    ready_display = f"{estimated_readiness}" if estimated_readiness else "—"
    
    html = (
        f'<div style="background:linear-gradient(135deg,rgba(20,18,24,0.98),rgba(26,24,30,0.95));'
        f'border-radius:16px;padding:16px 20px;margin-bottom:20px;'
        f'border:1px solid rgba(255,255,255,0.08);'
        f'box-shadow:0 4px 20px rgba(0,0,0,0.3);">'
        
        f'<div style="font-size:0.7rem;text-transform:uppercase;letter-spacing:1.5px;'
        f'color:#666;margin-bottom:12px;font-weight:600;">📊 Resumen en vivo</div>'
        
        f'<div style="display:flex;justify-content:space-between;align-items:center;gap:12px;">'
        
        # Recuperación
        f'<div style="text-align:center;flex:1;">'
        f'<div style="font-size:0.7rem;color:#888;margin-bottom:4px;">Recuperación</div>'
        f'<div style="display:flex;align-items:center;justify-content:center;gap:6px;">'
        f'<span style="font-size:1.1rem;">{recovery["emoji"]}</span>'
        f'<span style="color:{rec_color};font-weight:600;font-size:0.9rem;">{recovery["label"]}</span>'
        f'</div>'
        f'</div>'
        
        # Divider
        f'<div style="width:1px;height:32px;background:rgba(255,255,255,0.1);"></div>'
        
        # Estado
        f'<div style="text-align:center;flex:1;">'
        f'<div style="font-size:0.7rem;color:#888;margin-bottom:4px;">Estado</div>'
        f'<div style="display:flex;align-items:center;justify-content:center;gap:6px;">'
        f'<span style="font-size:1.1rem;">{state["emoji"]}</span>'
        f'<span style="color:{state_color};font-weight:600;font-size:0.9rem;">{state["label"]}</span>'
        f'</div>'
        f'</div>'
        
        # Divider
        f'<div style="width:1px;height:32px;background:rgba(255,255,255,0.1);"></div>'
        
        # Flags
        f'<div style="text-align:center;flex:1;">'
        f'<div style="font-size:0.7rem;color:#888;margin-bottom:4px;">Flags</div>'
        f'<div style="display:flex;align-items:center;justify-content:center;gap:6px;">'
        f'<span style="font-size:1.1rem;">{flags["emoji"]}</span>'
        f'<span style="color:{flags_color};font-weight:600;font-size:0.9rem;">{flags["label"]}</span>'
        f'</div>'
        f'</div>'
        
        # Divider
        f'<div style="width:1px;height:32px;background:rgba(255,255,255,0.1);"></div>'
        
        # Readiness estimado
        f'<div style="text-align:center;flex:1.2;">'
        f'<div style="font-size:0.7rem;color:#888;margin-bottom:4px;">Readiness est.</div>'
        f'<div style="color:{ready_color};font-weight:700;font-size:1.3rem;">{ready_display}</div>'
        f'</div>'
        
        f'</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_wizard_progress(current_step: int, total_steps: int = 3):
    """Renderiza la barra de progreso del wizard."""
    steps = ['Recuperación', 'Estado', 'Flags']
    
    html = (
        f'<div style="display:flex;justify-content:center;align-items:center;gap:8px;margin-bottom:24px;">'
    )
    
    for i, step_name in enumerate(steps):
        step_num = i + 1
        if step_num < current_step:
            # Completed
            bg = '#50C878'
            border = '#50C878'
            text_color = '#fff'
            label_color = '#50C878'
        elif step_num == current_step:
            # Current
            bg = 'linear-gradient(135deg,#4ECDC4,#44A08D)'
            border = '#4ECDC4'
            text_color = '#fff'
            label_color = '#4ECDC4'
        else:
            # Pending
            bg = 'rgba(255,255,255,0.05)'
            border = 'rgba(255,255,255,0.2)'
            text_color = '#666'
            label_color = '#666'
        
        html += (
            f'<div style="text-align:center;">'
            f'<div style="width:32px;height:32px;border-radius:50%;'
            f'background:{bg};border:2px solid {border};'
            f'display:flex;align-items:center;justify-content:center;'
            f'color:{text_color};font-weight:600;font-size:0.9rem;margin:0 auto 4px;">{step_num}</div>'
            f'<div style="font-size:0.7rem;color:{label_color};white-space:nowrap;">{step_name}</div>'
            f'</div>'
        )
        
        # Connector line (except last)
        if i < len(steps) - 1:
            line_color = '#50C878' if step_num < current_step else 'rgba(255,255,255,0.15)'
            html += (
                f'<div style="flex:1;max-width:60px;height:2px;background:{line_color};'
                f'margin:0 4px;margin-bottom:20px;"></div>'
            )
    
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_step_header(step_num: int, title: str, subtitle: str):
    """Renderiza el header de un paso del wizard."""
    html = (
        f'<div style="margin-bottom:20px;">'
        f'<div style="display:flex;align-items:center;gap:12px;margin-bottom:8px;">'
        f'<span style="background:linear-gradient(135deg,#4ECDC4,#44A08D);'
        f'color:#fff;font-weight:700;font-size:0.85rem;padding:4px 10px;'
        f'border-radius:6px;">PASO {step_num}</span>'
        f'<span style="color:#e0e0e0;font-size:1.1rem;font-weight:600;">{title}</span>'
        f'</div>'
        f'<div style="color:#888;font-size:0.85rem;padding-left:2px;">{subtitle}</div>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_input_card(label: str, badge_text: str = None, badge_level: str = None, 
                      help_text: str = None, is_primary: bool = False):
    """
    Renderiza el wrapper de una tarjeta de input.
    Retorna el estilo para usar con st.container.
    """
    level_colors = {
        'ok': '#50C878',
        'mid': '#E0A040',
        'low': '#E05555'
    }
    
    badge_html = ""
    if badge_text and badge_level:
        color = level_colors.get(badge_level, '#808080')
        badge_html = (
            f'<span style="background:{color}20;color:{color};'
            f'font-size:0.7rem;font-weight:600;padding:2px 8px;'
            f'border-radius:4px;margin-left:8px;">{badge_text}</span>'
        )
    
    border_color = 'rgba(78,205,196,0.3)' if is_primary else 'rgba(255,255,255,0.06)'
    bg = 'rgba(78,205,196,0.05)' if is_primary else 'rgba(26,24,30,0.6)'
    
    html = (
        f'<div style="background:{bg};border-radius:12px;padding:16px;'
        f'border:1px solid {border_color};margin-bottom:12px;">'
        f'<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;">'
        f'<span style="color:#c0c0c0;font-size:0.85rem;font-weight:500;">{label}</span>'
        f'{badge_html}'
        f'</div>'
    )
    return html


def render_micro_badge(text: str, level: str):
    """Renderiza un micro-badge inline alineado a la derecha."""
    level_colors = {
        'ok': '#50C878',
        'mid': '#E0A040',
        'low': '#E05555'
    }
    color = level_colors.get(level, '#808080')
    
    html = (
        f'<div style="display:flex;justify-content:flex-end;margin-top:4px;">'
        f'<span style="background:{color}15;color:{color};'
        f'font-size:0.7rem;font-weight:600;padding:2px 8px;'
        f'border-radius:4px;">{text}</span>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_intuition_slider_label(value: int):
    """Renderiza la etiqueta dinámica del slider de intuición."""
    labels = {
        0: ("Fatal, no debería entrenar", "#E05555"),
        1: ("Muy mal", "#E05555"),
        2: ("Bastante mal", "#E05555"),
        3: ("Mal", "#E07040"),
        4: ("Regular tirando a mal", "#E0A040"),
        5: ("Normal, ni bien ni mal", "#C0C0C0"),
        6: ("Bien", "#90C870"),
        7: ("Bastante bien", "#50C878"),
        8: ("Muy bien", "#50C878"),
        9: ("Genial", "#40D090"),
        10: ("Increíble, día perfecto", "#40D090")
    }
    
    text, color = labels.get(value, ("Normal", "#C0C0C0"))
    
    html = (
        f'<div style="display:flex;align-items:center;justify-content:space-between;'
        f'margin-top:8px;padding:8px 12px;background:rgba(255,255,255,0.03);'
        f'border-radius:8px;">'
        f'<span style="color:{color};font-size:1rem;font-weight:600;">'
        f'{value}/10 — {text}</span>'
        f'<span style="color:#666;font-size:0.75rem;">Peso: ~25% en cálculo</span>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_flag_toggle(label: str, emoji: str, impact: str = None, 
                       is_active: bool = False):
    """Renderiza un toggle de flag con su impacto."""
    if is_active and impact:
        impact_html = (
            f'<div style="color:#E07040;font-size:0.75rem;margin-top:4px;'
            f'padding-left:28px;">{impact}</div>'
        )
    else:
        impact_html = ""
    
    active_style = 'border-color:#E07040;background:rgba(224,112,64,0.08);' if is_active else ''
    
    html = (
        f'<div style="background:rgba(26,24,30,0.6);border-radius:10px;padding:12px;'
        f'border:1px solid rgba(255,255,255,0.06);margin-bottom:8px;{active_style}">'
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="font-size:1.1rem;">{emoji}</span>'
        f'<span style="color:#b0b0b0;font-size:0.9rem;">{label}</span>'
        f'</div>'
        f'{impact_html}'
        f'</div>'
    )
    return html


def render_section_divider(text: str = None):
    """Renderiza un divisor de sección opcional."""
    if text:
        html = (
            f'<div style="display:flex;align-items:center;gap:12px;margin:20px 0;">'
            f'<div style="flex:1;height:1px;background:rgba(255,255,255,0.08);"></div>'
            f'<span style="color:#666;font-size:0.75rem;text-transform:uppercase;'
            f'letter-spacing:1px;">{text}</span>'
            f'<div style="flex:1;height:1px;background:rgba(255,255,255,0.08);"></div>'
            f'</div>'
        )
    else:
        html = '<div style="height:1px;background:rgba(255,255,255,0.08);margin:20px 0;"></div>'
    st.markdown(html, unsafe_allow_html=True)


def render_collapsible_flags_header(flag_count: int):
    """Renderiza el header del panel colapsable de flags."""
    if flag_count == 0:
        color = '#50C878'
        text = 'Sin alertas'
        emoji = '✅'
    elif flag_count == 1:
        color = '#E0A040'
        text = '1 alerta'
        emoji = '⚠️'
    else:
        color = '#E05555'
        text = f'{flag_count} alertas'
        emoji = '🔴'
    
    html = (
        f'<div style="display:flex;align-items:center;gap:8px;">'
        f'<span style="color:#b0b0b0;">¿Algo fuera de lo normal?</span>'
        f'<span style="background:{color}20;color:{color};'
        f'font-size:0.75rem;font-weight:600;padding:2px 8px;'
        f'border-radius:4px;">{emoji} {text}</span>'
        f'</div>'
    )
    return html


def render_quick_mode_section_header(title: str, emoji: str = ""):
    """Header compacto para secciones en modo rápido."""
    html = (
        f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;margin-top:20px;">'
        f'<span style="font-size:1.1rem;">{emoji}</span>'
        f'<span style="color:#e0e0e0;font-size:0.95rem;font-weight:600;">{title}</span>'
        f'</div>'
    )
    st.markdown(html, unsafe_allow_html=True)

