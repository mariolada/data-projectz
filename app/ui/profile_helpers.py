"""
UI helpers para perfil de usuario y cuestionario de ciclo menstrual.
Estilo minimalista coherente con el tema de la aplicación.
"""
import streamlit as st
from typing import Dict, Any

# Paleta de colores consistente
COLORS = {
    'primary': '#B266FF',      # Purple
    'success': '#00D084',      # Green
    'warning': '#FFB81C',      # Amber
    'danger': '#FF6B6B',       # Coral
    'info': '#4ECDC4',         # Aqua
    'cycle': '#D947EF',        # Magenta para ciclo menstrual
    'text': '#E0E0E0',
    'text_muted': '#9CA3AF',
}


def render_user_profile_header(display_name: str, email: str, profile_picture: str = None):
    """Renderiza header del perfil con foto y nombre desde Google."""
    st.markdown(f"<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 3], gap="medium")
    
    with col1:
        if profile_picture:
            st.image(profile_picture, width=100, use_column_width=False)
        else:
            st.markdown(
                f'<div style="width:100px; height:100px; background:linear-gradient(135deg, {COLORS["primary"]} 0%, {COLORS["cycle"]} 100%); '
                'border-radius:50%; display:flex; align-items:center; justify-content:center; border: 2px solid rgba(217,71,239,0.3);">'
                '<span style="font-size:48px; color:#E0E0E0;">●</span></div>',
                unsafe_allow_html=True
            )
    
    with col2:
        st.markdown(f"# {display_name}")
        st.markdown(f"Correo: {email}")


def render_gender_selection() -> str:
    """Renderiza selector de género con UI amigable."""
    st.markdown(f"### Información Personal")
    st.markdown("Esta información personaliza tus métricas de readiness.")
    st.markdown("")
    
    gender = st.radio(
        "¿Cuál es tu género?",
        ["Hombre", "Mujer"],
        horizontal=True,
        help="Esto afecta cómo interpretamos factores de recuperación y performance."
    )
    
    return gender.lower() if gender else None


def render_menstrual_cycle_questionnaire() -> Dict[str, Any]:
    """Renderiza el cuestionario de ciclo menstrual para atletas mujeres."""
    st.markdown(f"### Ciclo Menstrual")
    st.markdown("""
    Entender tu ciclo nos permite ajustar mejor tus métricas. Los cambios hormonales 
    afectan energía, fatiga y recuperación. **Toda esta información es privada.**
    """)
    
    st.markdown(
        f'<div style="background:rgba(217, 71, 239, 0.1); border-left:4px solid {COLORS["cycle"]}; '
        'border-radius:6px; padding:14px; margin:16px 0;">' 
        '<div style="color:#E0E0E0; font-weight:600; margin-bottom:6px;">Nota importante</div>'
        '<div style="color:#9CA3AF; font-size:0.9rem;">El ciclo menstrual puede cambiar tu readiness real hasta ±15 puntos. '
        'Queremos que veas datos más precisos según tu fase del ciclo.</div></div>',
        unsafe_allow_html=True
    )
    col1, col2 = st.columns(2, gap="medium")
    
    with col1:
        day_of_cycle = st.number_input(
            "¿Qué día de tu ciclo? (1-28)",
            min_value=1, max_value=28, value=14,
            help="Día 1 = sangrado | Si no lo sabes, estima aproximadamente"
        )
        
        cramping = st.slider(
            "Intensidad de cólicos (0-5)",
            min_value=0, max_value=5, value=0,
            help="0 = ninguno | 5 = muy fuertes"
        )
    
    with col2:
        bloating = st.slider(
            "Hinchazón abdominal (0-5)",
            min_value=0, max_value=5, value=0,
            help="0 = ninguna | 5 = mucha"
        )
        
        mood = st.slider(
            "Humor general (0-10)",
            min_value=0, max_value=10, value=5,
            help="0 = muy bajo | 10 = excelente"
        )
    
    return {
        'day_of_cycle': day_of_cycle,
        'cramping': cramping,
        'bloating': bloating,
        'mood': mood
    }


def render_gender_note(gender: str):
    """Muestra nota personalizada según el género seleccionado."""
    if gender == "mujer":
        st.markdown(
            f'<div style="background:rgba(0, 208, 132, 0.1); border-left:4px solid {COLORS["success"]}; '
            'border-radius:6px; padding:14px; margin:16px 0;">' 
            '<div style="color:#E0E0E0; font-weight:600; margin-bottom:6px;">Ciclo menstrual activado</div>'
            '<div style="color:#9CA3AF; font-size:0.9rem;">El algoritmo de readiness incluye factor de ciclo menstrual. '
            'Tus puntuaciones se ajustarán según tu fase.</div></div>',
            unsafe_allow_html=True
        )
    elif gender == "hombre":
        st.markdown(
            f'<div style="background:rgba(78, 205, 196, 0.1); border-left:4px solid {COLORS["info"]}; '
            'border-radius:6px; padding:14px; margin:16px 0;">' 
            '<div style="color:#E0E0E0; font-weight:600; margin-bottom:6px;">Configuración de género</div>'
            '<div style="color:#9CA3AF; font-size:0.9rem;">Tus métricas se calculan sin ajustes de ciclo menstrual. '
            'Puedes cambiar esto en cualquier momento.</div></div>',
            unsafe_allow_html=True
        )
