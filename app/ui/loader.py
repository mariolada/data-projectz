"""
Loader overlay personalizado para la app.
Proporciona un indicador de carga centrado con estilo oscuro y acento morado.
"""
import streamlit as st
from contextlib import contextmanager
import time

# CSS para el loader overlay
LOADER_CSS = """
<style>
/* Overlay container - centrado real en pantalla */
.loader-overlay {
    position: fixed;
    inset: 0;
    display: grid;
    place-items: center;
    z-index: 999999;
    background: rgba(10, 10, 15, 0.85);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
}

/* Contenedor del loader */
.loader-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
    padding: 40px 60px;
    background: rgba(30, 30, 40, 0.95);
    border-radius: 16px;
    border: 1px solid rgba(178, 102, 255, 0.3);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4),
                0 0 60px rgba(178, 102, 255, 0.15);
}

/* Icono de fuego animado */
.loader-icon {
    font-size: 48px;
    animation: pulse-glow 1.5s ease-in-out infinite;
    filter: drop-shadow(0 0 12px rgba(178, 102, 255, 0.6));
}

/* Animación pulse/glow suave */
@keyframes pulse-glow {
    0%, 100% {
        opacity: 0.7;
        transform: scale(1);
        filter: drop-shadow(0 0 8px rgba(178, 102, 255, 0.4));
    }
    50% {
        opacity: 1;
        transform: scale(1.08);
        filter: drop-shadow(0 0 20px rgba(178, 102, 255, 0.8));
    }
}

/* Texto del loader */
.loader-text {
    color: #E0E0E0;
    font-size: 16px;
    font-weight: 500;
    letter-spacing: 0.5px;
    text-align: center;
}

/* Barra de progreso animada */
.loader-bar {
    width: 120px;
    height: 3px;
    background: rgba(178, 102, 255, 0.2);
    border-radius: 2px;
    overflow: hidden;
    position: relative;
}

.loader-bar::after {
    content: '';
    position: absolute;
    top: 0;
    left: -50%;
    width: 50%;
    height: 100%;
    background: linear-gradient(90deg, transparent, #B266FF, transparent);
    animation: slide 1.2s ease-in-out infinite;
}

@keyframes slide {
    0% { left: -50%; }
    100% { left: 100%; }
}

/* Variante compacta para operaciones rápidas */
.loader-compact {
    padding: 24px 40px;
}

.loader-compact .loader-icon {
    font-size: 32px;
}

.loader-compact .loader-text {
    font-size: 14px;
}
</style>
"""

# HTML del loader
def _get_loader_html(message: str = "Cargando...", compact: bool = False) -> str:
    """Genera el HTML del loader overlay."""
    container_class = "loader-container loader-compact" if compact else "loader-container"
    return f"""
    <div class="loader-overlay" id="custom-loader">
        <div class="{container_class}">
            <div class="loader-icon">🔥</div>
            <div class="loader-text">{message}</div>
            <div class="loader-bar"></div>
        </div>
    </div>
    """

def inject_loader_css():
    """Inyecta el CSS del loader (llamar una vez al inicio de la app)."""
    st.markdown(LOADER_CSS, unsafe_allow_html=True)

def show_loader(message: str = "Cargando...", compact: bool = False):
    """
    Muestra el loader overlay.
    
    Args:
        message: Texto a mostrar (ej: "Procesando métricas...")
        compact: Si True, usa versión más pequeña
    """
    return st.markdown(_get_loader_html(message, compact), unsafe_allow_html=True)

def hide_loader():
    """Oculta el loader (reemplaza con elemento vacío)."""
    st.markdown("<style>.loader-overlay { display: none !important; }</style>", unsafe_allow_html=True)

@contextmanager
def loading(message: str = "Cargando...", compact: bool = False):
    """
    Context manager para mostrar loader durante una operación.
    
    Uso:
        with loading("Procesando datos..."):
            # operación lenta
            df = pd.read_csv(...)
            
    Args:
        message: Texto a mostrar
        compact: Si True, usa versión compacta
    """
    placeholder = st.empty()
    try:
        with placeholder.container():
            st.markdown(LOADER_CSS + _get_loader_html(message, compact), unsafe_allow_html=True)
        yield
    finally:
        placeholder.empty()

@contextmanager  
def loading_status(message: str = "Cargando..."):
    """
    Versión alternativa usando st.status nativo de Streamlit.
    Menos intrusivo pero mantiene feedback visual.
    
    Uso:
        with loading_status("Cargando datos..."):
            df = load_csv(path)
    """
    with st.status(message, expanded=False) as status:
        yield status
        status.update(label="Completado", state="complete", expanded=False)

# Mensajes predefinidos para diferentes operaciones
LOADING_MESSAGES = {
    'csv': "Cargando datos...",
    'merge': "Combinando datasets...",
    'calculate': "Calculando métricas...",
    'charts': "Generando gráficos...",
    'readiness': "Procesando readiness...",
    'weekly': "Analizando datos semanales...",
    'profile': "Cargando perfil...",
    'recommendations': "Generando recomendaciones...",
}

def get_loading_message(operation: str) -> str:
    """Obtiene mensaje predefinido para una operación."""
    return LOADING_MESSAGES.get(operation, "Procesando...")
