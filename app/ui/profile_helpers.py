"""
UI helpers para perfil de usuario y cuestionario de ciclo menstrual.
"""
import streamlit as st
from typing import Dict, Any


def render_user_profile_header(display_name: str, email: str, profile_picture: str = None):
    """Renderiza header del perfil con foto y nombre desde Google."""
    col1, col2 = st.columns([1, 3])
    
    with col1:
        if profile_picture:
            st.image(profile_picture, width=120, use_column_width=False)
        else:
            st.markdown(
                '<div style="width:120px; height:120px; background:linear-gradient(135deg, #667eea 0%, #764ba2 100%); '
                'border-radius:50%; display:flex; align-items:center; justify-content:center; ">'
                '<span style="font-size:48px; color:white;">👤</span></div>',
                unsafe_allow_html=True
            )
    
    with col2:
        st.markdown(f"### {display_name}")
        st.markdown(f"**Email:** {email}")
        st.divider()


def render_gender_selection() -> str:
    """Renderiza selector de género con UI amigable."""
    st.subheader("👥 Información Personal")
    st.write("Esta información nos ayuda a personalizar tus métricas de readiness.")
    
    gender = st.radio(
        "¿Cuál es tu género?",
        ["Hombre", "Mujer", "Otro", "Prefiero no decir"],
        horizontal=True,
        help="Esto afecta cómo interpretamos algunos factores de recuperación."
    )
    
    return gender.lower() if gender else None


def render_menstrual_cycle_questionnaire() -> Dict[str, Any]:
    """Renderiza el cuestionario de ciclo menstrual para atletas mujeres."""
    st.subheader("🔄 Ciclo Menstrual")
    st.write("""
    Entender tu ciclo menstrual nos permite ajustar mejor tus métricas de readiness.
    Los cambios hormonales afectan energía, fatiga y recuperación.
    **Toda esta información es privada y confidencial.**
    """)
    
    st.info(
        "📌 **¿Por qué es importante?** El ciclo menstrual puede aumentar o disminuir tu "
        "readiness real en hasta 15 puntos. Queremos que veas datos más precisos según tu ciclo.",
        icon="ℹ️"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        day_of_cycle = st.number_input(
            "¿Qué día de tu ciclo estás? (1-28)",
            min_value=1, max_value=28, value=14,
            help="Día 1 = primer día de sangrado menstrual. Si no lo sabes, estima."
        )
        
        cramping = st.slider(
            "Intensidad de cólicos",
            min_value=0, max_value=5, value=0,
            help="0 = nada | 5 = muy fuertes"
        )
    
    with col2:
        bloating = st.slider(
            "Hinchazón abdominal",
            min_value=0, max_value=5, value=0,
            help="0 = nada | 5 = mucha"
        )
        
        mood = st.slider(
            "¿Cómo está tu humor?",
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
    """Muestra nota basada en el género seleccionado."""
    if gender == "mujer":
        st.success(
            "✅ El algoritmo de readiness ahora incluye factor de ciclo menstrual. "
            "Tus puntuaciones de readiness se ajustarán según tu fase del ciclo.",
            icon="💜"
        )
    elif gender in ["hombre", "otro", "prefiero no decir"]:
        st.info(
            "ℹ️ Tus métricas de readiness se calculan sin ajustes de ciclo menstrual. "
            "Puedes cambiar esto en cualquier momento.",
            icon="ℹ️"
        )
