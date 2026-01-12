"""
Estilos CSS y tema visual de la aplicación (gaming-dark).
"""

def get_theme_css():
    """Retorna el CSS completo del tema."""
    return """
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
        
        /* CTA button styling */
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
            background: linear-gradient(135deg, #B266FF, #7a3fe5) !important;
            border-color: rgba(178, 102, 255, 0.5);
            box-shadow: 0 4px 16px rgba(178, 102, 255, 0.2);
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
        .live-feedback h4 {
            color: #00D084;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-top: 0;
        }
        .live-feedback .metric-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }
        .live-feedback .metric {
            background: rgba(0, 208, 132, 0.08);
            border: 1px solid rgba(0, 208, 132, 0.2);
            border-radius: 8px;
            padding: 8px;
            font-size: 0.85rem;
        }
        .live-feedback .metric-label {
            color: rgba(0, 208, 132, 0.7);
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.03em;
        }
        .live-feedback .metric-value {
            color: #00D084;
            font-weight: 700;
            font-size: 1rem;
        }

        .stRadio label {
            font-family: 'Orbitron', sans-serif;
            letter-spacing: 0.03em;
        }
    </style>
    """
