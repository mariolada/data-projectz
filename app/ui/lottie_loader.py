"""
Lottie Loaders - Sistema de indicadores de carga con animaciones Lottie.
Minimalista, elegante y coherente con el diseño oscuro de la app.
"""
import streamlit as st
from streamlit_lottie import st_lottie
import requests
from contextlib import contextmanager
from typing import Optional
import time


# URLs de animaciones Lottie minimalistas y elegantes
LOTTIE_ANIMATIONS = {
    'default': 'https://lottie.host/b947c53f-4c1e-4c74-9c1e-d5ff6f8e8e0f/YVSNwHCbmr.json',  # Circular spinner minimalista
    'dots': 'https://lottie.host/embed/ca999381-52b7-44d7-b97f-0b8c5e6e9b84/wR0HTZkXPD.json',  # Three dots elegant
    'pulse': 'https://lottie.host/4a8e6f0d-b8c3-4b6e-a5e3-7f3e8e5e6e7e/abc123def.json',  # Pulse circle
    'auth': 'https://lottie.host/b947c53f-4c1e-4c74-9c1e-d5ff6f8e8e0f/YVSNwHCbmr.json',  # Para login/auth
    'calculate': 'https://lottie.host/b947c53f-4c1e-4c74-9c1e-d5ff6f8e8e0f/YVSNwHCbmr.json',  # Para cálculos
    'save': 'https://lottie.host/b947c53f-4c1e-4c74-9c1e-d5ff6f8e8e0f/YVSNwHCbmr.json',  # Para guardado
}


def load_lottie_url(url: str) -> Optional[dict]:
    """Carga una animación Lottie desde una URL."""
    try:
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        return r.json()
    except Exception as e:
        print(f"Error cargando Lottie: {e}")
        return None


# CSS para el contenedor del loader Lottie
LOTTIE_LOADER_CSS = """
<style>
.lottie-loader-overlay {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 999999;
    background: rgba(7, 9, 15, 0.92);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
}

.lottie-loader-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
    padding: 40px 50px;
    background: linear-gradient(135deg, rgba(15, 17, 24, 0.98), rgba(20, 22, 30, 0.95));
    border-radius: 20px;
    border: 1px solid rgba(78, 205, 196, 0.15);
    box-shadow: 
        0 20px 60px rgba(0, 0, 0, 0.6),
        0 0 40px rgba(78, 205, 196, 0.08),
        inset 0 1px 0 rgba(255, 255, 255, 0.05);
    min-width: 280px;
    max-width: 400px;
}

.lottie-loader-animation {
    width: 120px;
    height: 120px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.lottie-loader-text {
    color: #E6E6E6;
    font-size: 15px;
    font-weight: 500;
    letter-spacing: 0.3px;
    text-align: center;
    line-height: 1.5;
    margin: 0;
}

.lottie-loader-label {
    display: block;
    color: #4ECDC4;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    margin-bottom: 8px;
    font-weight: 600;
    opacity: 0.8;
}

/* Barra de progreso sutil */
.lottie-loader-bar {
    width: 100%;
    max-width: 200px;
    height: 2px;
    background: rgba(78, 205, 196, 0.12);
    border-radius: 2px;
    overflow: hidden;
    position: relative;
    margin-top: 8px;
}

.lottie-loader-bar::after {
    content: '';
    position: absolute;
    top: 0;
    left: -50%;
    width: 40%;
    height: 100%;
    background: linear-gradient(90deg, 
        transparent, 
        rgba(78, 205, 196, 0.8), 
        transparent);
    animation: lottie-slide 2s ease-in-out infinite;
}

@keyframes lottie-slide {
    0% { left: -50%; }
    100% { left: 100%; }
}

/* Versión compacta */
.lottie-loader-compact .lottie-loader-container {
    padding: 30px 40px;
    gap: 16px;
}

.lottie-loader-compact .lottie-loader-animation {
    width: 90px;
    height: 90px;
}

.lottie-loader-compact .lottie-loader-text {
    font-size: 14px;
}

/* Versión inline (sin overlay) */
.lottie-loader-inline {
    position: relative;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 20px;
}

.lottie-loader-inline .lottie-loader-animation {
    width: 80px;
    height: 80px;
}

.lottie-loader-inline .lottie-loader-text {
    font-size: 13px;
}

/* Responsive */
@media (max-width: 768px) {
    .lottie-loader-container {
        padding: 30px 35px;
        min-width: 240px;
    }
    
    .lottie-loader-animation {
        width: 100px;
        height: 100px;
    }
}
</style>
"""


def inject_lottie_loader_css():
    """Inyecta el CSS del loader Lottie (llamar una vez al inicio)."""
    st.markdown(LOTTIE_LOADER_CSS, unsafe_allow_html=True)


def show_lottie_loader(
    message: str = "Cargando...",
    animation_type: str = 'default',
    compact: bool = False,
    show_bar: bool = True,
    inline: bool = False
) -> None:
    """
    Muestra un loader Lottie.
    
    Args:
        message: Texto a mostrar
        animation_type: Tipo de animación ('default', 'dots', 'auth', 'calculate', 'save')
        compact: Si True, versión más pequeña
        show_bar: Si True, muestra barra de progreso
        inline: Si True, muestra inline sin overlay (para contenido)
    """
    # Cargar animación
    lottie_url = LOTTIE_ANIMATIONS.get(animation_type, LOTTIE_ANIMATIONS['default'])
    lottie_json = load_lottie_url(lottie_url)
    
    if not lottie_json:
        # Fallback si no se puede cargar la animación
        st.info(f"⏳ {message}")
        return
    
    # Clases CSS
    overlay_class = ''
    if not inline:
        overlay_class = 'lottie-loader-overlay'
    if compact:
        overlay_class += ' lottie-loader-compact'
    if inline:
        overlay_class = 'lottie-loader-inline'
    
    # Renderizar
    container_html = f'<div class="{overlay_class}">' if not inline else ''
    container_close = '</div>' if not inline else ''
    
    bar_html = '<div class="lottie-loader-bar"></div>' if show_bar else ''
    
    # Contenedor principal
    html_start = f"""
    {container_html}
        <div class="lottie-loader-container">
            <div class="lottie-loader-animation">
    """
    
    html_end = f"""
            </div>
            <div class="lottie-loader-text">
                <span class="lottie-loader-label">Procesando</span>
                {message}
            </div>
            {bar_html}
        </div>
    {container_close}
    """
    
    st.markdown(html_start, unsafe_allow_html=True)
    st_lottie(
        lottie_json,
        speed=1,
        reverse=False,
        loop=True,
        quality="high",
        height=120 if not compact else 90,
        width=120 if not compact else 90,
        key=f"lottie_{animation_type}_{time.time()}"
    )
    st.markdown(html_end, unsafe_allow_html=True)


@contextmanager
def lottie_loading(
    message: str = "Cargando...",
    animation_type: str = 'default',
    compact: bool = False,
    show_bar: bool = True,
    min_display_time: float = 0.0
):
    """
    Context manager para mostrar loader Lottie durante una operación.
    
    Uso:
        with lottie_loading("Calculando readiness...", animation_type='calculate'):
            readiness = calculate_readiness(data)
    
    Args:
        message: Texto a mostrar
        animation_type: 'default', 'dots', 'auth', 'calculate', 'save'
        compact: Si True, versión compacta
        show_bar: Si True, muestra barra de progreso
        min_display_time: Tiempo mínimo de visualización en segundos (no se usa)
    """
    placeholder = st.empty()
    
    try:
        with placeholder.container():
            show_lottie_loader(message, animation_type, compact, show_bar, inline=False)
        yield
    finally:
        placeholder.empty()


@contextmanager
def lottie_spinner(message: str = "Procesando...", animation_type: str = 'default'):
    """
    Versión inline del loader para usar dentro de contenido.
    Más ligero que lottie_loading (sin overlay).
    
    Uso:
        with lottie_spinner("Guardando datos...", animation_type='save'):
            save_to_database(data)
    """
    placeholder = st.empty()
    
    try:
        with placeholder.container():
            show_lottie_loader(message, animation_type, compact=True, show_bar=False, inline=True)
        yield
    finally:
        placeholder.empty()


# Mensajes predefinidos según operación
LOTTIE_MESSAGES = {
    'auth': "Autenticando tu cuenta...",
    'login': "Iniciando sesión...",
    'readiness': "Calculando tu readiness personalizado...",
    'calculate': "Procesando datos...",
    'training': "Guardando entrenamiento...",
    'save': "Guardando cambios...",
    'load': "Cargando datos...",
    'weekly': "Analizando métricas semanales...",
    'neural': "Detectando sobrecarga neuromuscular...",
    'insights': "Generando insights personalizados...",
    'export': "Exportando datos...",
    'sync': "Sincronizando...",
}


def get_lottie_message(operation: str) -> str:
    """Obtiene mensaje predefinido para una operación."""
    return LOTTIE_MESSAGES.get(operation, "Procesando...")
