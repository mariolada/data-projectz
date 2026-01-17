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
    gap: 24px;
    padding: 40px 60px;
    background: rgba(20, 20, 28, 0.95);
    border-radius: 20px;
    border: 1px solid rgba(78, 205, 196, 0.25);
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.5),
                0 0 80px rgba(78, 205, 196, 0.12),
                inset 0 0 20px rgba(78, 205, 196, 0.05);
    backdrop-filter: blur(8px);
}

/* SVG circular loader animado */
.loader-svg-circle {
    width: 80px;
    height: 80px;
    filter: drop-shadow(0 0 20px rgba(78, 205, 196, 0.4));
}

.loader-svg-circle svg {
    width: 100%;
    height: 100%;
}

/* Círculo de progreso - rotación */
.spinner-circle {
    animation: spin 2.5s linear infinite;
    transform-origin: center;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* Círculo interior - pulso suave */
.spinner-inner {
    animation: pulse-inner 2s ease-in-out infinite;
}

@keyframes pulse-inner {
    0%, 100% {
        opacity: 0.4;
        r: 28px;
    }
    50% {
        opacity: 0.9;
        r: 32px;
    }
}

/* Puntos decorativos */
.spinner-dot {
    animation: pulse-dot 1.5s ease-in-out infinite;
}

.spinner-dot:nth-child(1) { animation-delay: 0s; }
.spinner-dot:nth-child(2) { animation-delay: 0.5s; }
.spinner-dot:nth-child(3) { animation-delay: 1s; }

@keyframes pulse-dot {
    0%, 100% {
        r: 3px;
        opacity: 0.3;
    }
    50% {
        r: 5px;
        opacity: 0.9;
    }
}

/* Texto del loader */
.loader-text {
    color: #E6E6E6;
    font-size: 16px;
    font-weight: 500;
    letter-spacing: 0.5px;
    text-align: center;
    line-height: 1.4;
}

.loader-text .loader-label {
    display: block;
    color: #4ECDC4;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 1.2px;
    margin-bottom: 6px;
    font-weight: 600;
}

/* Barra de progreso animada mejorada */
.loader-bar {
    width: 140px;
    height: 2px;
    background: rgba(78, 205, 196, 0.15);
    border-radius: 2px;
    overflow: hidden;
    position: relative;
    box-shadow: 0 0 12px rgba(78, 205, 196, 0.2);
}

.loader-bar::after {
    content: '';
    position: absolute;
    top: 0;
    left: -60%;
    width: 40%;
    height: 100%;
    background: linear-gradient(90deg, 
        transparent, 
        #4ECDC4, 
        #00D084,
        transparent);
    box-shadow: 0 0 10px rgba(78, 205, 196, 0.6);
    animation: slide 1.8s ease-in-out infinite;
}

@keyframes slide {
    0% { left: -60%; }
    100% { left: 100%; }
}

/* Variante compacta para operaciones rápidas */
.loader-compact {
    padding: 20px 40px;
    gap: 16px;
}

.loader-compact .loader-svg-circle {
    width: 60px;
    height: 60px;
}

.loader-compact .loader-text {
    font-size: 14px;
}

.loader-compact .loader-bar {
    width: 100px;
}

/* Variante sin barra (más limpio) */
.loader-no-bar .loader-bar {
    display: none;
}

/* Responsive */
@media (max-width: 768px) {
    .loader-container {
        padding: 30px 40px;
        gap: 18px;
    }
    
    .loader-svg-circle {
        width: 70px;
        height: 70px;
    }
    
    .loader-text {
        font-size: 15px;
    }
    
    .loader-bar {
        width: 120px;
    }
}
</style>
"""

# SVG para el spinner circular
def _get_spinner_svg() -> str:
    """Genera el SVG del spinner circular animado."""
    return """
    <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" class="spinner-circle">
        <!-- Círculo externo gradiente -->
        <defs>
            <linearGradient id="spinnerGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#4ECDC4;stop-opacity:0.8" />
                <stop offset="100%" style="stop-color:#00D084;stop-opacity:0.3" />
            </linearGradient>
        </defs>
        
        <!-- Círculo trasero sutil -->
        <circle cx="50" cy="50" r="38" fill="none" stroke="rgba(78,205,196,0.1)" stroke-width="2"/>
        
        <!-- Círculo principal con gradiente -->
        <circle cx="50" cy="50" r="38" fill="none" stroke="url(#spinnerGradient)" 
                stroke-width="3.5" stroke-linecap="round" 
                stroke-dasharray="120 238" stroke-dashoffset="0"/>
        
        <!-- Círculo interior que pulsa -->
        <circle class="spinner-inner" cx="50" cy="50" r="28" fill="none" 
                stroke="rgba(78,205,196,0.4)" stroke-width="1"/>
        
        <!-- Puntos decorativos que pulsean -->
        <circle class="spinner-dot" cx="50" cy="12" r="3" fill="#4ECDC4"/>
        <circle class="spinner-dot" cx="88" cy="50" r="3" fill="#00D084"/>
        <circle class="spinner-dot" cx="50" cy="88" r="3" fill="#4ECDC4"/>
    </svg>
    """

# HTML del loader
def _get_loader_html(message: str = "Cargando...", compact: bool = False, show_bar: bool = True) -> str:
    """Genera el HTML del loader overlay con SVG."""
    container_class = "loader-container loader-compact" if compact else "loader-container"
    if not show_bar:
        container_class += " loader-no-bar"
    
    bar_html = '<div class="loader-bar"></div>' if show_bar else ''
    
    return f"""
    <div class="loader-overlay" id="custom-loader">
        <div class="{container_class}">
            <div class="loader-svg-circle">
                {_get_spinner_svg()}
            </div>
            <div class="loader-text">
                <span class="loader-label">Procesando</span>
                {message}
            </div>
            {bar_html}
        </div>
    </div>
    """

def inject_loader_css():
    """Inyecta el CSS del loader (llamar una vez al inicio de la app)."""
    st.markdown(LOADER_CSS, unsafe_allow_html=True)

def show_loader(message: str = "Cargando...", compact: bool = False, show_bar: bool = True):
    """
    Muestra el loader overlay.
    
    Args:
        message: Texto a mostrar (ej: "Procesando métricas...")
        compact: Si True, usa versión más pequeña
        show_bar: Si True, muestra la barra de progreso
    """
    return st.markdown(_get_loader_html(message, compact, show_bar), unsafe_allow_html=True)

def hide_loader():
    """Oculta el loader (reemplaza con elemento vacío)."""
    st.markdown("<style>.loader-overlay { display: none !important; }</style>", unsafe_allow_html=True)

@contextmanager
def loading(message: str = "Cargando...", compact: bool = False, show_bar: bool = True):
    """
    Context manager para mostrar loader durante una operación.
    
    Uso:
        with loading("Procesando datos..."):
            # operación lenta
            df = pd.read_csv(...)
            
    Args:
        message: Texto a mostrar
        compact: Si True, usa versión compacta
        show_bar: Si True, muestra barra de progreso
    """
    placeholder = st.empty()
    try:
        with placeholder.container():
            st.markdown(LOADER_CSS + _get_loader_html(message, compact, show_bar), unsafe_allow_html=True)
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
    'readiness': "Procesando tu readiness...",
    'weekly': "Analizando datos semanales...",
    'profile': "Cargando tu perfil...",
    'recommendations': "Generando recomendaciones personalizadas...",
    'login': "Iniciando sesión...",
    'auth': "Autenticando cuenta...",
    'neural': "Analizando sobrecarga neuromuscular...",
    'training': "Procesando entrenamiento...",
    'cycle': "Calculando ajuste de ciclo...",
    'insights': "Generando insights...",
    'save': "Guardando cambios...",
    'export': "Exportando datos...",
    'sync': "Sincronizando datos...",
}

def get_loading_message(operation: str) -> str:
    """Obtiene mensaje predefinido para una operación."""
    return LOADING_MESSAGES.get(operation, "Procesando...")
