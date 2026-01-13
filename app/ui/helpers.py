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


def clean_line(s: str) -> str:
    """Limpia una línea de texto de bullets y formato markdown."""
    s = str(s).strip()
    # remove leading markdown bullets
    if s.startswith("- ") or s.startswith("• "):
        s = s[2:].strip()
    # remove bold markers
    s = s.replace("**", "")
    return s
