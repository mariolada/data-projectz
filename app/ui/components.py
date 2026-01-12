"""UI Components - Reusable UI elements."""
import streamlit as st


def render_section_title(text, accent="#B266FF"):
    """Renderiza títulos de sección con el mismo look & feel de las gráficas."""
    st.markdown(f"""
    <div class="section-title" style="--accent: {accent};">
        <div class="section-pill"></div>
        <span>{text}</span>
    </div>
    """, unsafe_allow_html=True)
