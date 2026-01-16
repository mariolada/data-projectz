"""
Estilos premium para el sidebar de navegación.
Minimalismo negro/gris con acentos sutiles por sección.
"""

SIDEBAR_PREMIUM_CSS = """
<style>
    /* ============================================
       SIDEBAR PREMIUM - Minimalista Black/Grey
       ============================================ */
    
    :root {
        --sidebar-bg: #0A0E14;
        --sidebar-surface: #0F1419;
        --sidebar-card: #13171F;
        --sidebar-card-hover: #181D26;
        --sidebar-border: rgba(255, 255, 255, 0.06);
        --sidebar-text: #E0E5EB;
        --sidebar-text-muted: #7B8496;
        
        /* Acentos por sección */
        --accent-day: #06B6D4;          /* Cian frío - Día */
        --accent-today: #10B981;        /* Verde - Modo Hoy */
        --accent-week: #0891B2;         /* Azul cian - Semana */
        --accent-training: #A78BFA;     /* Morado suave - Entrenamiento */
        --accent-profile: #64748B;      /* Gris plata - Perfil */
        
        --sidebar-shadow: rgba(0, 0, 0, 0.3);
    }
    
    /* ============================================
       CONTENEDOR SIDEBAR
       ============================================ */
    [data-testid="stSidebar"] {
        background: var(--sidebar-bg) !important;
        border-right: 1px solid var(--sidebar-border) !important;
    }
    
    [data-testid="stSidebar"] > div:first-child {
        background: var(--sidebar-bg) !important;
        padding-top: 2rem !important;
    }
    
    /* ============================================
       HEADER DEL SIDEBAR
       ============================================ */
    .sidebar-header {
        padding: 1.25rem 1rem 1.75rem 1rem;
        border-bottom: 1px solid var(--sidebar-border);
        margin-bottom: 1.5rem;
    }
    
    .sidebar-header-title {
        font-size: 1.1rem;
        font-weight: 700;
        letter-spacing: -0.02em;
        color: var(--sidebar-text);
        margin: 0;
        padding: 0;
        line-height: 1.2;
    }
    
    .sidebar-header-subtitle {
        font-size: 0.75rem;
        font-weight: 500;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        color: var(--sidebar-text-muted);
        margin-top: 0.25rem;
    }
    
    .sidebar-header-dot {
        display: inline-block;
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #2DD4BF;  /* Turquesa sutil */
        margin-right: 0.5rem;
        box-shadow: 0 0 8px rgba(45, 212, 191, 0.6);
    }
    
    /* ============================================
       TÍTULO DE SECCIÓN
       ============================================ */
    .sidebar-title {
        font-size: 0.7rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
        color: var(--sidebar-text-muted) !important;
        margin: 1.5rem 1rem 0.75rem 1rem !important;
        padding: 0 !important;
        line-height: 1 !important;
    }
    
    /* ============================================
       NAVEGACIÓN - RADIO GROUP
       ============================================ */
    
    /* Contenedor del radio (Vista) */
    .st-key-view_mode div[data-testid="stRadio"] > div {
        display: flex !important;
        flex-direction: column !important;
        gap: 0.375rem !important;
        padding: 0.5rem 0.75rem !important;
        border-radius: 0 !important;
        background: transparent !important;
        border: none !important;
        width: 100% !important;
        box-sizing: border-box !important;
    }
    
    /* Esconder el label "Vista" */
    .st-key-view_mode div[data-testid="stRadio"] > label {
        display: none !important;
    }
    
    /* Cada opción del menú (pill-card) */
    .st-key-view_mode div[role="radiogroup"] label[data-baseweb="radio"] {
        position: relative !important;
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
        background: transparent !important;
        cursor: pointer !important;
        display: block !important;
    }
    
    /* Label base */
    .st-key-view_mode div[role="radiogroup"] label[data-baseweb="radio"] {
        display: block !important;
        width: 100% !important;
    }
    
    /* Esconder el indicador nativo de Streamlit (primer div dentro de label) */
    .st-key-view_mode div[role="radiogroup"] label[data-baseweb="radio"] > div:first-of-type {
        display: none !important;
    }
    
    /* Input real (escondido pero funcional) */
    .st-key-view_mode div[role="radiogroup"] label[data-baseweb="radio"] > input {
        position: absolute !important;
        opacity: 0 !important;
        width: 1px !important;
        height: 1px !important;
        pointer-events: none !important;
    }
    
    /* Card de cada opción - Apuntar al último div (contenedor de texto) */
    .st-key-view_mode div[role="radiogroup"] label[data-baseweb="radio"] > div:last-of-type {
        position: relative !important;
        display: flex !important;
        align-items: center !important;
        gap: 0.75rem !important;
        padding: 0.875rem 1rem !important;
        border-radius: 10px !important;
        background: var(--sidebar-card) !important;
        width: 100% !important;
        box-sizing: border-box !important;
        border: 1px solid var(--sidebar-border) !important;
        color: var(--sidebar-text-muted) !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        letter-spacing: -0.01em !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
        box-shadow: 0 1px 3px var(--sidebar-shadow) !important;
    }
    
    /* Indicador lateral (barra fina izquierda) */
    .st-key-view_mode div[role="radiogroup"] label[data-baseweb="radio"] > div:last-of-type::before {
        content: '' !important;
        position: absolute !important;
        left: 0 !important;
        top: 0 !important;
        bottom: 0 !important;
        width: 3px !important;
        background: transparent !important;
        border-radius: 10px 0 0 10px !important;
        transition: background 0.2s ease, box-shadow 0.2s ease !important;
    }
    
    /* ESTADO: HOVER (inactivo) */
    .st-key-view_mode div[role="radiogroup"] label[data-baseweb="radio"]:hover > input:not(:checked) ~ div:last-of-type {
        background: var(--sidebar-card-hover) !important;
        border-color: rgba(255, 255, 255, 0.08) !important;
        color: var(--sidebar-text) !important;
    }
    
    /* ESTADO: ACTIVO (checked) - Default */
    .st-key-view_mode div[role="radiogroup"] label[data-baseweb="radio"] > input:checked ~ div:last-of-type {
        background: var(--sidebar-surface) !important;
        border-color: var(--accent-day) !important;
        color: var(--sidebar-text) !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 8px rgba(6, 182, 212, 0.12), 0 1px 3px var(--sidebar-shadow) !important;
    }
    
    /* Barra lateral activa - Día (opción 1) */
    .st-key-view_mode div[role="radiogroup"] label[data-baseweb="radio"]:nth-child(1) > input:checked ~ div:last-of-type::before {
        background: var(--accent-day) !important;
        box-shadow: 0 0 6px var(--accent-day) !important;
    }
    
    /* Barra lateral activa - Modo Hoy (opción 2) */
    .st-key-view_mode div[role="radiogroup"] label[data-baseweb="radio"]:nth-child(2) > input:checked ~ div:last-of-type::before {
        background: var(--accent-today) !important;
        box-shadow: 0 0 6px var(--accent-today) !important;
    }
    
    /* Barra lateral activa - Semana (opción 3) */
    .st-key-view_mode div[role="radiogroup"] label[data-baseweb="radio"]:nth-child(3) > input:checked ~ div:last-of-type::before {
        background: var(--accent-week) !important;
        box-shadow: 0 0 6px var(--accent-week) !important;
    }
    
    /* Barra lateral activa - Entrenamiento (opción 4) */
    .st-key-view_mode div[role="radiogroup"] label[data-baseweb="radio"]:nth-child(4) > input:checked ~ div:last-of-type::before {
        background: var(--accent-training) !important;
        box-shadow: 0 0 6px var(--accent-training) !important;
    }
    
    /* Barra lateral activa - Perfil (opción 5) */
    .st-key-view_mode div[role="radiogroup"] label[data-baseweb="radio"]:nth-child(5) > input:checked ~ div:last-of-type::before {
        background: var(--accent-profile) !important;
        box-shadow: 0 0 6px var(--accent-profile) !important;
    }
    
    /* Borde activo según sección */
    .st-key-view_mode div[role="radiogroup"] label[data-baseweb="radio"]:nth-child(1) > input:checked ~ div:last-of-type {
        border-color: var(--accent-day) !important;
        box-shadow: 0 2px 8px rgba(6, 182, 212, 0.12), 0 1px 3px var(--sidebar-shadow) !important;
    }
    
    .st-key-view_mode div[role="radiogroup"] label[data-baseweb="radio"]:nth-child(2) > input:checked ~ div:last-of-type {
        border-color: var(--accent-today) !important;
        box-shadow: 0 2px 8px rgba(16, 185, 129, 0.12), 0 1px 3px var(--sidebar-shadow) !important;
    }
    
    .st-key-view_mode div[role="radiogroup"] label[data-baseweb="radio"]:nth-child(3) > input:checked ~ div:last-of-type {
        border-color: var(--accent-week) !important;
        box-shadow: 0 2px 8px rgba(8, 145, 178, 0.12), 0 1px 3px var(--sidebar-shadow) !important;
    }
    
    .st-key-view_mode div[role="radiogroup"] label[data-baseweb="radio"]:nth-child(4) > input:checked ~ div:last-of-type {
        border-color: var(--accent-training) !important;
        box-shadow: 0 2px 8px rgba(167, 139, 250, 0.12), 0 1px 3px var(--sidebar-shadow) !important;
    }
    
    .st-key-view_mode div[role="radiogroup"] label[data-baseweb="radio"]:nth-child(5) > input:checked ~ div:last-of-type {
        border-color: var(--accent-profile) !important;
        box-shadow: 0 2px 8px rgba(100, 116, 139, 0.12), 0 1px 3px var(--sidebar-shadow) !important;
    }
    
    /* Esconder SVGs */
    .st-key-view_mode div[role="radiogroup"] label[data-baseweb="radio"] svg {
        display: none !important;
    }
    
    /* ============================================
       SUBTÍTULOS/DESCRIPCIONES DE SECCIONES
       ============================================ */
    
    .sidebar-item-description {
        font-size: 0.7rem;
        font-weight: 400;
        letter-spacing: -0.01em;
        color: var(--sidebar-text-muted);
        margin-top: 0.25rem;
        line-height: 1.2;
        opacity: 0.8;
    }
    
    /* ============================================
       FILTROS Y OTROS CONTROLES
       ============================================ */
    
    /* Título de secciones secundarias */
    [data-testid="stSidebar"] h3 {
        font-size: 0.7rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
        color: var(--sidebar-text-muted) !important;
        margin: 1.5rem 0 0.75rem 0 !important;
        padding: 0 1rem !important;
    }
    
    /* Date inputs */
    [data-testid="stSidebar"] [data-testid="stDateInput"] > div {
        background: var(--sidebar-card) !important;
        border: 1px solid var(--sidebar-border) !important;
        border-radius: 8px !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stDateInput"] input {
        color: var(--sidebar-text) !important;
        font-size: 0.85rem !important;
    }
    
    /* Selectbox */
    [data-testid="stSidebar"] [data-testid="stSelectbox"] > div {
        background: var(--sidebar-card) !important;
        border: 1px solid var(--sidebar-border) !important;
        border-radius: 8px !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stSelectbox"] input {
        color: var(--sidebar-text) !important;
        font-size: 0.85rem !important;
    }
    
    /* ============================================
       SEPARADOR FINO
       ============================================ */
    .sidebar-separator {
        height: 1px;
        background: var(--sidebar-border);
        margin: 1.5rem 1rem;
    }
    
</style>
"""


def inject_sidebar_premium_css():
    """Inyecta los estilos premium del sidebar."""
    import streamlit as st
    st.markdown(SIDEBAR_PREMIUM_CSS, unsafe_allow_html=True)


def render_sidebar_header(title: str = "Readiness Tracker", subtitle: str = "Dashboard"):
    """
    Renderiza un header premium para el sidebar.
    
    Args:
        title: Título principal de la app
        subtitle: Subtítulo o tagline
    """
    import streamlit as st
    
    st.markdown(
        f"""
        <div class='sidebar-header'>
            <div class='sidebar-header-title'>{title}</div>
            <div class='sidebar-header-subtitle'>
                <span class='sidebar-header-dot'></span>{subtitle}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_sidebar_navigation_items():
    """
    Renderiza los items de navegación con sus descripciones discretas.
    Nota: Esta función es informativa; los items reales se controlan por st.sidebar.radio().
    """
    # Esta información se proporciona para referencia; los labels reales están en streamlit_app.py
    items = [
        ("Día", "Vista detallada de un día concreto"),
        ("Modo Hoy", "Cálculo de readiness y estado actual"),
        ("Semana", "Resumen y análisis semanal"),
        ("Entrenamiento", "Registro de entrenamientos"),
        ("Perfil Personal", "Datos y preferencias personales"),
    ]
    return items
