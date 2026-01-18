import streamlit as st

PRIMARY = "#00FFB0"
SECONDARY = "#FFB81C"
BG_SOLID = "#050607"
CARD_BG = "rgba(12,12,14,0.9)"
BORDER = "rgba(255,255,255,0.08)"
TEXT_MAIN = "rgba(230,230,230,0.94)"
TEXT_SUB = "rgba(200,200,200,0.72)"
TEXT_DIM = "rgba(160,160,160,0.65)"
ERROR_RED = "rgba(255,80,80,0.75)"


def _inject_login_css():
    st.markdown(
        f"""
        <style>
        /* Hide sidebar and header */
        [data-testid="stSidebar"], header {{ display: none !important; }}

        /* Fullscreen centering for the login view */
        div[data-testid="stAppViewContainer"] > .main {{
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            background: radial-gradient(65% 65% at 50% 35%, rgba(0,255,176,0.05), rgba(0,0,0,0.65) 55%, #050607 100%);
            padding: 24px 12px;
        }}

        /* Constrain the block that holds the marker */
        div[data-testid="stVerticalBlock"]:has(#login-shell-marker) {{
            max-width: 480px;
            width: 100%;
            margin: 0 auto;
            background: {CARD_BG};
            border: 1px solid {BORDER};
            border-radius: 14px;
            padding: 28px 26px;
            box-shadow: 0 16px 38px rgba(0,0,0,0.4);
        }}

        /* Tighten global padding */
        .block-container {{
            padding: 0 !important;
            width: 100% !important;
        }}

        /* Buttons scoped to the login block */
        div[data-testid="stVerticalBlock"]:has(#login-shell-marker) button {{
            width: 100% !important;
            height: 46px;
            border-radius: 10px !important;
            border: 1px solid rgba(0,255,176,0.5) !important;
            background: linear-gradient(135deg, rgba(0,255,176,0.12), rgba(0,0,0,0.35)) !important;
            color: {TEXT_MAIN} !important;
            font-weight: 600 !important;
            letter-spacing: 0.2px;
            transition: all 150ms ease;
            box-shadow: none !important;
        }}
        div[data-testid="stVerticalBlock"]:has(#login-shell-marker) button:hover {{
            border-color: {PRIMARY} !important;
            background: rgba(0,255,176,0.18) !important;
        }}
        div[data-testid="stVerticalBlock"]:has(#login-shell-marker) button:active {{
            transform: translateY(1px);
        }}

        .login-google-btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            height: 46px;
            border-radius: 10px;
            border: 1px solid rgba(0,255,176,0.5);
            background: linear-gradient(135deg, rgba(0,255,176,0.12), rgba(0,0,0,0.35));
            color: {TEXT_MAIN};
            font-weight: 700;
            letter-spacing: 0.2px;
            text-decoration: none;
            transition: all 150ms ease;
        }}
        .login-google-btn:hover {{
            border-color: {PRIMARY};
            background: rgba(0,255,176,0.18);
        }}
        .login-google-btn:active {{
            transform: translateY(1px);
        }}

        .login-icon {{
            width: 42px;
            height: 42px;
            border-radius: 50%;
            border: 1px solid rgba(255,255,255,0.08);
            display: grid;
            place-items: center;
            color: {PRIMARY};
            background: linear-gradient(135deg, rgba(0,255,176,0.12), rgba(0,0,0,0.25));
            margin-bottom: 12px;
            font-size: 18px;
        }}
        .login-title {{
            font-size: 30px;
            font-weight: 700;
            letter-spacing: 0.5px;
            color: {TEXT_MAIN};
            margin: 0 0 6px 0;
        }}
        .login-sub {{
            font-size: 15px;
            color: {TEXT_SUB};
            margin: 0 0 18px 0;
        }}
        .login-micro {{
            font-size: 12px;
            color: {TEXT_DIM};
            margin-top: 10px;
        }}
        .login-error {{
            margin-top: 12px;
            padding: 10px 12px;
            border-radius: 10px;
            border: 1px solid {ERROR_RED};
            color: {TEXT_MAIN};
            background: rgba(255,80,80,0.08);
            font-size: 13px;
        }}
        .login-chip {{
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 10px;
            background: rgba(0,255,176,0.08);
            border: 1px solid rgba(0,255,176,0.3);
            border-radius: 999px;
            color: {TEXT_MAIN};
            font-size: 13px;
        }}
        .fade-in {{
            opacity: 0;
            transform: translateY(6px);
            animation: fadeInUp 220ms ease-out both;
            will-change: opacity, transform;
        }}
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(6px); }}
            to   {{ opacity: 1; transform: translateY(0); }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _provider_label(provider: str) -> str:
    label = provider.strip().lower()
    if label == "google":
        return "Google"
    if label == "github":
        return "GitHub"
    return provider.title()


def render_login(providers=("google",), auth_url: str = None):
    """Renderiza la pantalla de login minimalista con OAuth real."""
    _inject_login_css()

    # Inicializar variables de sesión
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    # Marker to scope CSS to this block (for width/centering)
    st.markdown("<div id='login-shell-marker'></div>", unsafe_allow_html=True)
    with st.container():
        st.markdown("<div class='login-card-shell fade-in'>", unsafe_allow_html=True)

        st.markdown("<div class='login-icon'>✦</div>", unsafe_allow_html=True)
        st.markdown("<div class='login-title'>Accede a tu panel</div>", unsafe_allow_html=True)
        st.markdown("<div class='login-sub'>Tus datos, tu progreso. Sin ruido.</div>", unsafe_allow_html=True)

        if st.session_state.authenticated:
            identity = st.session_state.user_email or "Usuario autenticado"
            st.markdown(f"<div class='login-chip'>✅ Conectado como: {identity}</div>", unsafe_allow_html=True)
            if st.button("Entrar", type="primary", key="btn_enter"):
                st.rerun()
        else:
            if not auth_url:
                st.markdown("<div class='login-error'>Falta configurar Google OAuth.</div>", unsafe_allow_html=True)
            else:
                st.markdown(
                    f"<a class='login-google-btn' href='{auth_url}'>Continuar con Google</a>",
                    unsafe_allow_html=True,
                )
        
            if st.session_state.get("login_error"):
                st.markdown(f"<div class='login-error'>{st.session_state['login_error']}</div>", unsafe_allow_html=True)

        st.markdown(
            "<div class='login-micro'>Privacidad: tus datos están aislados por usuario.<br/>Si tienes problemas, prueba otro proveedor.</div>",
            unsafe_allow_html=True,
        )

        st.markdown("</div>", unsafe_allow_html=True)  # shell
