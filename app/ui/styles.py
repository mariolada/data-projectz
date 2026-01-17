"""
Estilos CSS para la aplicación Streamlit.
Gaming-dark theme con efectos neon.
"""

# CSS principal de la aplicación
MAIN_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
    
    :root {
        --bg: #07090f;
        --panel: #0f1420;
        --panel-2: #111827;
        --purple: #B266FF;
        --green: #00D084;
        --aqua: #4ECDC4;
        --coral: #FF6B6B;
        --amber: #FFB81C;
        --text: #E0E0E0;
        --muted: #9CA3AF;
    }
    
    .main {
        background: radial-gradient(circle at 20% 20%, rgba(178, 102, 255, 0.08), transparent 20%),
                    radial-gradient(circle at 80% 0%, rgba(0, 208, 132, 0.08), transparent 25%),
                    linear-gradient(180deg, #0b0e14 0%, #07090f 80%);
        color: var(--text);
    }
    
    /* Hero */
    .hero {
        background: linear-gradient(135deg, rgba(178, 102, 255, 0.12), rgba(0, 208, 132, 0.08));
        border: 1px solid rgba(178, 102, 255, 0.25);
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 18px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        box-shadow: 0 8px 30px rgba(0,0,0,0.25);
    }
    .hero h1 {
        font-family: 'Orbitron', sans-serif;
        color: var(--text);
        text-shadow: 0 0 16px rgba(178, 102, 255, 0.25);
        margin: 0;
        font-size: 2.1em;
        letter-spacing: 0.04em;
    }
    .hero .eyebrow {
        text-transform: uppercase;
        color: var(--muted);
        letter-spacing: 0.2em;
        font-size: 0.8em;
        margin: 0 0 4px 0;
    }
    .hero .sub {
        color: var(--muted);
        margin: 6px 0 0 0;
    }
    .hero .badge-row {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
    }
    .badge {
        padding: 6px 10px;
        border-radius: 999px;
        font-size: 0.85em;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        color: #0b0e11;
        background: linear-gradient(135deg, var(--green), #00c070);
        box-shadow: 0 0 14px rgba(0, 208, 132, 0.3);
    }
    .badge.purple { background: linear-gradient(135deg, var(--purple), #8f4dff); color: #f8f8ff; box-shadow: 0 0 14px rgba(178, 102, 255, 0.35); }
    .badge.coral { background: linear-gradient(135deg, var(--coral), #ff7f7f); color: #fff; box-shadow: 0 0 14px rgba(255, 107, 107, 0.35); }
    .badge.aqua { background: linear-gradient(135deg, var(--aqua), #27d7c4); color: #0b0e11; box-shadow: 0 0 14px rgba(78, 205, 196, 0.35); }
    
    /* Section titles */
    .section-title {
        display: flex;
        align-items: center;
        gap: 10px;
        font-family: 'Orbitron', sans-serif;
        color: var(--text);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-size: 1.25em;
        margin: 20px 0 12px 0;
    }
    .section-title .section-pill {
        width: 36px;
        height: 6px;
        border-radius: 999px;
        background: linear-gradient(90deg, var(--accent), rgba(255,255,255,0));
        box-shadow: 0 0 16px rgba(178, 102, 255, 0.35);
    }
    .section-title span {
        color: var(--accent);
        text-shadow: 0 0 12px rgba(178, 102, 255, 0.35);
    }
    
    /* Panels */
    [data-testid="stSidebar"] {
        background: #0f1420;
        border-right: 1px solid rgba(178, 102, 255, 0.18);
        color: var(--text);
    }
    .sidebar-title {
        font-family: 'Orbitron', sans-serif;
        color: var(--purple);
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-weight: 700;
        margin-bottom: 10px;
    }
    
    /* Metric styling */
    [data-testid="metric-container"] {
        background: linear-gradient(135deg, #161d2b 0%, #1f1630 100%);
        border: 1px solid rgba(0, 208, 132, 0.2);
        border-radius: 10px;
        padding: 16px;
        box-shadow: 0 6px 20px rgba(0,0,0,0.25);
    }
    
    /* Alert boxes */
    [data-testid="stAlert"] {
        border-left: 4px solid var(--amber);
        border-radius: 8px;
        background: rgba(255, 184, 28, 0.12);
    }
    
    /* Info boxes */
    [data-testid="stInfo"] {
        border-left: 4px solid var(--green);
        border-radius: 8px;
        background: rgba(0, 208, 132, 0.12);
    }
    
    /* Sidebar radio tweaks */
    .stRadio label {
        font-family: 'Orbitron', sans-serif;
        letter-spacing: 0.03em;
    }
    
    /* CTA button styling (Streamlit primary button) */
    div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"],
    button[data-testid="stBaseButton-primary"] {
        width: 100% !important;
        min-height: 56px !important;
        border-radius: 14px !important;
        background: linear-gradient(135deg, #00D084 0%, #00c070 100%) !important;
        color: #0B0E11 !important;
        border: none !important;
        font-weight: 900 !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
        font-size: 1.02rem !important;
        transition: 0.25s ease !important;
    }

    div[data-testid="stButton"] > button[data-testid="stBaseButton-primary"]:hover,
    button[data-testid="stBaseButton-primary"]:hover {
        box-shadow: 0 0 18px rgba(0, 208, 132, 0.55) !important;
        transform: translateY(-1px) !important;
        background: linear-gradient(135deg, #00e094 0%, #00d080 100%) !important;
    }
    
    /* ===== RADIO STYLES (SCOPED) ===== */

    /* Mode toggle (Rápido / Preciso) — scoped by key (BaseWeb radios)
       Your DOM is: label > div(indicator) + input + div(text)
    */

    /* Track */
    .st-key-mode_toggle div[role="radiogroup"] {
        position: relative;
        display: inline-flex;
        gap: 0;
        padding: 6px;
        border-radius: 9999px;
        background: rgba(10,25,41,0.75);
        border: 1px solid rgba(255,255,255,0.12);
        box-shadow: 0 10px 30px rgba(0,0,0,0.25);
    }

    /* Sliding highlight (best-effort; supported in modern Chrome/Edge) */
    .st-key-mode_toggle div[role="radiogroup"]::before {
        content: "";
        position: absolute;
        top: 6px;
        bottom: 6px;
        left: 6px;
        width: calc(50% - 0px);
        border-radius: 9999px;
        background: linear-gradient(135deg, #00D084 0%, #4ECDC4 100%);
        box-shadow: 0 0 0 2px rgba(0,208,132,0.18), 0 10px 26px rgba(0,0,0,0.25);
        transition: transform 0.35s cubic-bezier(0.4, 0, 0.2, 1), background 0.35s ease, box-shadow 0.35s ease;
    }

    .st-key-mode_toggle div[role="radiogroup"]:has(label[data-baseweb="radio"]:nth-child(2) input:checked)::before {
        transform: translateX(100%);
        background: linear-gradient(135deg, #B266FF 0%, #9D4EDD 100%);
        box-shadow: 0 0 0 2px rgba(178,102,255,0.20), 0 10px 26px rgba(0,0,0,0.25);
    }

    .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"] {
        position: relative !important;
        z-index: 1 !important;
        flex: 1 1 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        border: 0 !important;
        background: transparent !important;
        cursor: pointer !important;
    }

    /* Hide BaseWeb indicator block (first div inside label) */
    .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child {
        display: none !important;
    }

    /* Hide the real input but keep checked state */
    .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"] > input {
        position: absolute !important;
        opacity: 0 !important;
        width: 1px !important;
        height: 1px !important;
        pointer-events: none !important;
    }

    /* Surface for label text (kept transparent so the slider is visible)
       Fallback rules below still support per-pill highlight if :has() isn't supported.
    */
    .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"] > input + div,
    .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"] input + div {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 12px 26px !important;
        border-radius: 9999px !important;
        border: 2px solid transparent !important;
        background: transparent !important;
        font-weight: 900 !important;
        letter-spacing: 0.04em !important;
        white-space: nowrap !important;
        transition: color 0.25s ease, transform 0.25s ease !important;
    }

    /* Any SVG artifacts inside the labels */
    .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"] svg {
        display: none !important;
    }

    /* Inactive colors by position */
    .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"]:nth-child(1) > input + div {
        color: rgba(111, 231, 255, 0.60) !important;
    }
    .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"]:nth-child(2) > input + div {
        color: rgba(255, 106, 213, 0.60) !important;
    }

    /* Checked text color (works with or without slider) */
    .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"] > input:checked + div,
    .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"] input:checked + div {
        transform: translateY(-1px) !important;
        color: #0a1929 !important;
    }

    /* Fallback: if :has() isn't supported, highlight the checked pill directly */
    .st-key-mode_toggle div[role="radiogroup"]:not(:has(label[data-baseweb="radio"] input)) label[data-baseweb="radio"] > input:checked + div {
        border-color: transparent !important;
    }
    .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"]:nth-child(1) > input:checked + div {
        background: linear-gradient(135deg, #00D084 0%, #4ECDC4 100%) !important;
        box-shadow: 0 0 0 2px rgba(0,208,132,0.18), 0 10px 26px rgba(0,0,0,0.25) !important;
    }
    .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"]:nth-child(2) > input:checked + div {
        background: linear-gradient(135deg, #B266FF 0%, #9D4EDD 100%) !important;
        box-shadow: 0 0 0 2px rgba(178,102,255,0.20), 0 10px 26px rgba(0,0,0,0.25) !important;
    }

    .st-key-mode_toggle div[role="radiogroup"] label[data-baseweb="radio"]:hover > input + div {
        border-color: rgba(255,255,255,0.22) !important;
    }

    /* Sidebar view toggle (Día / Modo Hoy / Semana) — scoped by key */
    .st-key-view_mode div[data-testid="stRadio"] > div {
        display: flex;
        flex-direction: column;
        gap: 10px;
        padding: 10px;
        border-radius: 16px;
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.10);
    }

    .st-key-view_mode div[role="radiogroup"] input { display: none !important; }
    .st-key-view_mode div[role="radio"] svg { display: none !important; }
    .st-key-view_mode div[role="radio"] > div:first-child { display: none !important; }

    .st-key-view_mode div[role="radiogroup"] label {
        cursor: pointer;
        padding: 12px 14px;
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.10);
        background: rgba(10,25,41,0.35);
        transition: all 0.25s ease;
    }

    .st-key-view_mode div[role="radio"][aria-checked="true"] {
        background: linear-gradient(135deg, #00D084 0%, #4ECDC4 100%) !important;
        color: #0a1929 !important;
        border-color: transparent !important;
        box-shadow: 0 0 0 2px rgba(0, 208, 132, 0.25), 0 10px 24px rgba(0,0,0,0.25) !important;
    }

    .st-key-view_mode div[role="radiogroup"] label:hover {
        border-color: rgba(255,255,255,0.22);
        transform: translateY(-1px);
    }
    
    /* Divider */
    hr {
        border: none;
        border-top: 1px solid rgba(178, 102, 255, 0.18);
        margin: 18px 0;
    }
    
    /* Text styling */
    p, label, span {
        color: var(--text);
    }
    
    /* Caption */
    .caption {
        color: var(--muted);
        font-size: 0.85em;
    }
    
    /* DataFrames and Tables - Gaming Style */
    [data-testid="stDataFrame"] {
        border: 1px solid rgba(178, 102, 255, 0.25) !important;
        border-radius: 8px !important;
        overflow: hidden !important;
        box-shadow: 0 0 20px rgba(178, 102, 255, 0.15) !important;
        background: linear-gradient(135deg, #0f1420 0%, #1a1530 100%) !important;
    }
    
    /* Table header styling */
    [data-testid="stDataFrame"] thead {
        background: linear-gradient(90deg, rgba(178, 102, 255, 0.3), rgba(0, 208, 132, 0.1)) !important;
        border-bottom: 2px solid rgba(178, 102, 255, 0.4) !important;
    }
    
    [data-testid="stDataFrame"] thead th {
        color: #E0E0E0 !important;
        font-weight: 700 !important;
        font-family: 'Orbitron', sans-serif !important;
        letter-spacing: 0.05em !important;
        padding: 14px 10px !important;
        text-transform: uppercase !important;
        font-size: 0.85em !important;
        border-right: 1px solid rgba(178, 102, 255, 0.2) !important;
        text-shadow: 0 0 8px rgba(178, 102, 255, 0.25) !important;
        background: linear-gradient(180deg, rgba(178, 102, 255, 0.25), rgba(178, 102, 255, 0.1)) !important;
    }
    
    [data-testid="stDataFrame"] thead th:last-child {
        border-right: none !important;
    }
    
    /* Table rows styling */
    [data-testid="stDataFrame"] tbody tr {
        border-bottom: 1px solid rgba(178, 102, 255, 0.12) !important;
        transition: all 0.2s ease !important;
    }
    
    [data-testid="stDataFrame"] tbody tr:nth-child(odd) {
        background-color: rgba(15, 20, 32, 0.5) !important;
    }
    
    [data-testid="stDataFrame"] tbody tr:nth-child(even) {
        background-color: rgba(26, 21, 48, 0.3) !important;
    }
    
    [data-testid="stDataFrame"] tbody tr:hover {
        background-color: rgba(178, 102, 255, 0.12) !important;
        box-shadow: inset 0 0 15px rgba(178, 102, 255, 0.1) !important;
    }
    
    /* Table cells styling */
    [data-testid="stDataFrame"] td {
        color: var(--text) !important;
        padding: 12px 10px !important;
        font-size: 0.9em !important;
        border-right: 1px solid rgba(178, 102, 255, 0.08) !important;
    }
    
    [data-testid="stDataFrame"] td:last-child {
        border-right: none !important;
    }
    
    /* Colored cells (readiness_score) */
    [data-testid="stDataFrame"] td[style*="background-color: #00D084"] {
        background-color: rgba(0, 208, 132, 0.25) !important;
        color: #00D084 !important;
        font-weight: 700 !important;
        text-shadow: 0 0 8px rgba(0, 208, 132, 0.4) !important;
        box-shadow: inset 0 0 12px rgba(0, 208, 132, 0.1) !important;
    }
    
    [data-testid="stDataFrame"] td[style*="background-color: #FFB81C"] {
        background-color: rgba(255, 184, 28, 0.2) !important;
        color: #FFB81C !important;
        font-weight: 700 !important;
        text-shadow: 0 0 8px rgba(255, 184, 28, 0.4) !important;
        box-shadow: inset 0 0 12px rgba(255, 184, 28, 0.08) !important;
    }
    
    [data-testid="stDataFrame"] td[style*="background-color: #FF4444"] {
        background-color: rgba(255, 68, 68, 0.2) !important;
        color: #FF6B6B !important;
        font-weight: 700 !important;
        text-shadow: 0 0 8px rgba(255, 107, 107, 0.4) !important;
        box-shadow: inset 0 0 12px rgba(255, 107, 107, 0.08) !important;
    }
    
    /* Scrollbar styling */
    [data-testid="stDataFrame"] ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    
    [data-testid="stDataFrame"] ::-webkit-scrollbar-track {
        background: rgba(178, 102, 255, 0.05);
        border-radius: 10px;
    }
    
    [data-testid="stDataFrame"] ::-webkit-scrollbar-thumb {
        background: linear-gradient(180deg, #B266FF, #00D084);
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(178, 102, 255, 0.3);
    }
    
    [data-testid="stDataFrame"] ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(180deg, #00D084, #B266FF);
        box-shadow: 0 0 15px rgba(0, 208, 132, 0.4);
    }
    
    /* === CUSTOM CARD ANIMATIONS === */
    @keyframes neonPulse {
        0%, 100% { box-shadow: 0 0 20px var(--card-accent)40, 0 0 40px var(--card-accent)20, inset 0 0 60px rgba(0,0,0,0.3); }
        50% { box-shadow: 0 0 30px var(--card-accent)60, 0 0 60px var(--card-accent)30, inset 0 0 60px rgba(0,0,0,0.3); }
    }
    
    @keyframes cardSlideIn {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    /* Card hover effect via CSS */
    div[style*="border: 2px solid"] {
        animation: cardSlideIn 0.4s ease-out;
    }
    
    /* Input sections styling */
    .input-section {
        background: linear-gradient(135deg, rgba(20,20,30,0.6) 0%, rgba(30,30,45,0.4) 100%);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 16px;
        border-left: 3px solid var(--purple);
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    .section-sleep {
        border-left-color: var(--aqua);
    }
    
    .section-state {
        border-left-color: var(--amber);
    }
    
    .section-flags {
        border-left-color: var(--coral);
    }
    
    .section-header {
        font-family: 'Orbitron', sans-serif;
        font-weight: 900;
        font-size: 1.15rem;
        color: var(--text);
        letter-spacing: 0.08em;
        margin-bottom: 12px;
        text-transform: uppercase;
        text-shadow: 0 0 10px rgba(178, 102, 255, 0.3);
    }
</style>
"""

# CSS adicional para el Modo Hoy
MODE_TODAY_CSS = """
<style>
/* =====================================================
   MODO HOY — Base negra minimalista
   (sobrescribe el MAIN_CSS para esta vista)
   ===================================================== */

:root {
    --mh-bg0: #07090f;
    --mh-bg1: #0b0e14;
    --mh-panel: rgba(22, 22, 28, 0.92);
    --mh-panel2: rgba(28, 26, 32, 0.88);
    --mh-border: rgba(255, 255, 255, 0.06);
    --mh-text: #e6e6e6;
    --mh-muted: #9ca3af;
    --mh-aqua: #4ECDC4;
    --mh-green: #00D084;
    --mh-amber: #E0A040;
    --mh-red: #E05555;
    --primary-color: #4ECDC4;
}

html, body {
    background: var(--mh-bg0) !important;
    color: var(--mh-text) !important;
}

/* Streamlit containers (force the black base everywhere) */
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main,
.main {
    background:
        radial-gradient(circle at 12% 10%, rgba(78, 205, 196, 0.06), transparent 28%),
        radial-gradient(circle at 85% 0%, rgba(178, 102, 255, 0.05), transparent 30%),
        linear-gradient(180deg, var(--mh-bg1) 0%, var(--mh-bg0) 78%)
        !important;
    color: var(--mh-text) !important;
}

/* Reduce default top padding feel */
[data-testid="stAppViewContainer"] .main .block-container {
    padding-top: 1.25rem;
}

/* =====================================================
   Contenedores con borde (st.container(border=True))
   ===================================================== */

div[data-testid="stVerticalBlockBorderWrapper"] {
    background: linear-gradient(135deg, var(--mh-panel), var(--mh-panel2)) !important;
    border: 1px solid var(--mh-border) !important;
    border-radius: 14px !important;
    padding: 10px 14px !important;
    box-shadow: 0 2px 14px rgba(0,0,0,0.32) !important;
    margin: 6px 0 !important;
}

/* =====================================================
   Questionnaire wrapper styles are injected inline
   in modo_hoy.py for precise targeting.
   ===================================================== */

/* Make inner border (if present) subtle */
div[data-testid="stVerticalBlockBorderWrapper"] > div {
    border-radius: 12px !important;
}

/* =====================================================
   Tipografía/contraste (labels/captions)
   ===================================================== */

/* Widget labels */
div[data-testid="stWidgetLabel"] > label,
div[data-testid="stWidgetLabel"] p,
div[data-testid="stWidgetLabel"] span {
    color: rgba(230,230,230,0.92) !important;
    font-weight: 600 !important;
}

/* Captions */
div[data-testid="stCaptionContainer"],
.stCaption {
    color: rgba(190,190,190,0.75) !important;
}

/* Markdown inside blocks */
div[data-testid="stMarkdownContainer"] p,
div[data-testid="stMarkdownContainer"] span,
div[data-testid="stMarkdownContainer"] div {
    color: var(--mh-text);
}

/* =====================================================
   MODO HOY — CUESTIONARIO (estética "Consejos")
   Negro limpio + acentos, sin brillos agresivos
   ===================================================== */

/* Chips (badges discretos) */
.mh-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 8px;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 650;
    letter-spacing: 0.01em;
    border: 1px solid rgba(255,255,255,0.08);
    background: rgba(255,255,255,0.03);
    color: rgba(230,230,230,0.92);
    margin: 2px 0;
}
.mh-chip strong { font-weight: 800; }
.mh-chip-green { border-color: rgba(0,208,132,0.30); color: #00D084; background: rgba(0,208,132,0.08); }
.mh-chip-amber { border-color: rgba(224,160,64,0.30); color: #E0A040; background: rgba(224,160,64,0.08); }
.mh-chip-red   { border-color: rgba(224,85,85,0.30); color: #E05555; background: rgba(224,85,85,0.08); }

/* Slider scale labels (meaning row) */
.mh-scale {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    font-size: 0.70rem;
    color: rgba(156,163,175,0.85);
    margin-top: -8px;
    padding: 0 2px 2px 2px;
    user-select: none;
    line-height: 1.2;
}
.mh-scale span:nth-child(2) { opacity: 0.85; }
.mh-scale span:last-child { text-align: right; }

/* Cards base (para wrappers HTML del cuestionario) */
.mh-card {
    background: linear-gradient(135deg, rgba(22,22,28,0.95), rgba(28,26,32,0.90));
    border-radius: 12px;
    padding: 12px 16px;
    border: 1px solid rgba(255,255,255,0.05);
    box-shadow: 0 2px 12px rgba(0,0,0,0.30);
    margin: 4px 0;
}
.mh-card-left {
    border-left: 3px solid rgba(255,255,255,0.12);
}
.mh-card-left.mh-green { border-left-color: #50C878; }
.mh-card-left.mh-aqua  { border-left-color: #4ECDC4; }
.mh-card-left.mh-amber { border-left-color: #E0A040; }
.mh-card-left.mh-red   { border-left-color: #E05555; }
.mh-muted { color: #A0A0A0; }

/* Widgets: inputs/selector/textarea */
div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input,
div[data-testid="stTextArea"] textarea,
div[data-testid="stDateInput"] input {
    background: rgba(255,255,255,0.035) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 10px !important;
    color: var(--mh-text) !important;
}

/* NumberInput +/- buttons */
div[data-testid="stNumberInput"] button {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid rgba(255,255,255,0.08) !important;
    color: var(--mh-text) !important;
    border-radius: 10px !important;
}

/* BaseWeb selectbox surface */
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    background: rgba(255,255,255,0.035) !important;
    border: 1px solid rgba(255,255,255,0.09) !important;
    border-radius: 10px !important;
}
div[data-testid="stSelectbox"] * { color: var(--mh-text) !important; }

/* Checkbox / radio subtle */
div[data-testid="stCheckbox"] label,
div[data-testid="stRadio"] label {
    color: rgba(230,230,230,0.9) !important;
}

/* Slider surface + handle */
div[data-testid="stSlider"] div[data-baseweb="slider"] {
    padding: 6px 2px !important;
    margin: 2px 0 !important;
}
div[data-testid="stSlider"] div[data-baseweb="slider"] div[role="slider"] {
    box-shadow: 0 0 0 2px rgba(255,255,255,0.15) !important;
}

/* Slider track (remove the aggressive magenta look; keep subtle aqua) */
div[data-testid="stSlider"] div[data-baseweb="slider"] div[role="presentation"] {
    background: rgba(255,255,255,0.12) !important;
}
div[data-testid="stSlider"] div[data-baseweb="slider"] div[role="presentation"] > div {
    background: linear-gradient(90deg, rgba(78,205,196,0.95), rgba(0,208,132,0.90)) !important;
}

/* Make widget labels less shouty (more premium) */
label, .stMarkdown, p {
    letter-spacing: 0.01em;
}

/* Mode Toggle */
.mode-toggle-container {
    background: rgba(178, 102, 255, 0.08);
    border-radius: 16px;
    padding: 8px;
    margin: 20px 0;
    border: 2px solid rgba(178, 102, 255, 0.3);
    box-shadow: 0 0 20px rgba(178, 102, 255, 0.15);
}

/* Section cards */
.input-section {
    background: rgba(255, 255, 255, 0.03);
    border-radius: 12px;
    padding: 20px;
    margin: 16px 0;
    border-left: 4px solid;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    transition: all 0.3s ease;
}
.input-section:hover {
    box-shadow: 0 6px 30px rgba(0, 0, 0, 0.4);
    transform: translateY(-2px);
}
.section-recovery { border-left-color: #00D084; }
.section-state { border-left-color: #B266FF; }
.section-flags { border-left-color: #FF6B6B; }

/* Section titles */
.section-header {
    font-size: 1.3rem;
    font-weight: 700;
    margin-bottom: 12px;
    letter-spacing: 0.5px;
}
.section-recovery .section-header { color: #00D084; }
.section-state .section-header { color: #B266FF; }
.section-flags .section-header { color: #FF6B6B; }

/* Live feedback panel */
.live-feedback {
    position: sticky;
    top: 20px;
    background: linear-gradient(135deg, rgba(0, 208, 132, 0.1) 0%, rgba(78, 205, 196, 0.1) 100%);
    border: 2px solid rgba(0, 208, 132, 0.3);
    border-radius: 16px;
    padding: 20px;
    margin: 20px 0;
    box-shadow: 0 8px 32px rgba(0, 208, 132, 0.2);
}

/* Readiness circle */
.readiness-circle {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin: 0 auto 16px;
    font-size: 2.5rem;
    font-weight: 800;
    background: conic-gradient(from 0deg, #00D084 var(--progress), rgba(0, 208, 132, 0.1) var(--progress));
    box-shadow: 0 0 30px rgba(0, 208, 132, 0.4);
    animation: pulse-glow 2s ease-in-out infinite;
}
@keyframes pulse-glow {
    0%, 100% { box-shadow: 0 0 30px rgba(0, 208, 132, 0.4); }
    50% { box-shadow: 0 0 50px rgba(0, 208, 132, 0.6); }
}

/* Action button */
.action-button {
    background: linear-gradient(90deg, #00D084 0%, #4ECDC4 100%);
    color: #0b0b0b;
    font-weight: 800;
    font-size: 1.2rem;
    padding: 18px 32px;
    border-radius: 12px;
    border: none;
    width: 100%;
    cursor: pointer;
    box-shadow: 0 6px 20px rgba(0, 208, 132, 0.4);
    transition: all 0.3s ease;
    text-transform: uppercase;
    letter-spacing: 1px;
}
.action-button:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 30px rgba(0, 208, 132, 0.6);
}

/* Expander surface (flags, etc.) */
div[data-testid="stExpander"] {
    background: rgba(255,255,255,0.02) !important;
    border: 1px solid rgba(255,255,255,0.06) !important;
    border-radius: 12px !important;
}
div[data-testid="stExpander"] summary {
    color: rgba(230,230,230,0.92) !important;
}

/* Remove the old rainbow slider rule (kept intentionally empty) */

/* Compact output card */
.compact-card {
    background: linear-gradient(135deg, rgba(178, 102, 255, 0.1) 0%, rgba(0, 208, 132, 0.1) 100%);
    border: 2px solid rgba(178, 102, 255, 0.3);
    border-radius: 16px;
    padding: 24px;
    margin: 20px 0;
    box-shadow: 0 8px 32px rgba(178, 102, 255, 0.2);
}

/* Badges enhanced */
.badge-dynamic {
    display: inline-block;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: 600;
    margin: 4px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}
.badge-green { background: rgba(0, 208, 132, 0.2); color: #00D084; border: 1px solid #00D084; }
.badge-yellow { background: rgba(255, 184, 28, 0.2); color: #FFB81C; border: 1px solid #FFB81C; }
.badge-red { background: rgba(255, 107, 107, 0.2); color: #FF6B6B; border: 1px solid #FF6B6B; }
</style>
"""

# Hero HTML
HERO_HTML = """
<div class="hero">
    <div>
        <p class="eyebrow">Adventure Mode</p>
        <h1>Trainer — Readiness</h1>
        <p class="sub">Decide tu plan del día con las mismas vibes que las gráficas.</p>
    </div>
    <div class="badge-row">
        <span class="badge purple">Readiness</span>
        <span class="badge">Volumen</span>
        <span class="badge aqua">Sueño</span>
        <span class="badge coral">ACWR</span>
    </div>
</div>
"""

# Header para Modo Hoy
MODE_TODAY_HEADER = """
<div style='text-align:center;margin:20px 0 40px'>
    <h1 style='font-size:2.5rem;font-weight:800;background:linear-gradient(90deg,#00D084,#4ECDC4);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px'>
        Ready Check
    </h1>
    <p style='color:#B266FF;font-size:1.1rem;font-weight:600'>
        Tu puntuación y plan personalizado en segundos
    </p>
</div>
"""


def inject_main_css(st):
    """Inyecta el CSS principal en la aplicación."""
    st.markdown(MAIN_CSS, unsafe_allow_html=True)


def inject_hero(st):
    """Inyecta el hero en la aplicación."""
    st.markdown(HERO_HTML, unsafe_allow_html=True)


def inject_mode_today_css(st):
    """Inyecta CSS adicional para el Modo Hoy."""
    st.markdown(MODE_TODAY_CSS, unsafe_allow_html=True)


def inject_mode_today_header(st):
    """Inyecta el header del Modo Hoy."""
    st.markdown(MODE_TODAY_HEADER, unsafe_allow_html=True)
