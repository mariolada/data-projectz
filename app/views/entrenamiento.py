"""
Vista Entrenamiento - Entrada de ejercicios estilo Excel (modo A: filas con st.columns)
- UI coherente (negro + acento verde)
- Tabla tipo Excel: header sticky, zebra, hover suave, inputs compactos
- Añadir ejercicio "on the fly" (persistente en base de datos)
- Guardado con nombre de sesión + reemplazo por fecha
- Panel lateral: resumen + guardar + recientes (cargar una sesión)
"""

from __future__ import annotations

import datetime

import pandas as pd
import streamlit as st

from ui.loader import loading
from database.connection import get_db, init_db
from database.repositories import TrainingRepository, ExerciseRepository


def _current_user_id() -> str:
    return (
        st.session_state.get("user_sub")
        or st.session_state.get("user_email")
        or "default_user"
    )

# Inicializar base de datos al importar el módulo
init_db()

EJERCICIOS_BASE = [
    "Press Banca", "Press Inclinado", "Press Militar",
    "Sentadilla", "Peso Muerto", "Peso Muerto Rumano",
    "Dominadas", "Remo con Barra", "Remo con Mancuerna",
    "Curl Bíceps", "Extensión Tríceps", "Press Francés",
    "Hip Thrust", "Zancadas", "Prensa de Piernas",
    "Elevaciones Laterales", "Face Pull", "Fondos"
]


# ----------------------------
# Data helpers
# ----------------------------
def get_empty_row(date: datetime.date) -> dict:
    return {
        "date": date,
        "exercise": "",
        "sets": 3,
        "reps": 8,
        "weight": 0.0,
        "rpe": 7,
        "rir": 2
    }


def validate_exercises(df: pd.DataFrame) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if df.empty:
        return False, ["No hay ejercicios para guardar"]

    for idx, row in df.iterrows():
        row_num = idx + 1
        ex = str(row.get("exercise", "")).strip()
        if ex == "":
            errors.append(f"Fila {row_num}: Falta nombre del ejercicio")
        if pd.isna(row.get("sets")) or int(row.get("sets", 0)) <= 0:
            errors.append(f"Fila {row_num}: Series debe ser > 0")
        if pd.isna(row.get("reps")) or int(row.get("reps", 0)) <= 0:
            errors.append(f"Fila {row_num}: Reps debe ser > 0")

    return len(errors) == 0, errors


def load_existing_training() -> pd.DataFrame:
    """Carga entrenamientos desde la base de datos"""
    db = next(get_db())
    try:
        return TrainingRepository.get_all(db, user_id=_current_user_id())
    finally:
        db.close()


def _normalize_ex_name(name: str) -> str:
    # Limpieza suave para evitar duplicados tontos
    return " ".join(str(name).strip().split())


def load_exercises_bank() -> list[str]:
    """Lee ejercicios desde la base de datos"""
    db = next(get_db())
    try:
        return ExerciseRepository.get_all(db, user_id=_current_user_id())
    finally:
        db.close()


def save_exercises_bank(exercises: set[str]) -> None:
    """Guarda ejercicios en la base de datos"""
    db = next(get_db())
    try:
        clean = sorted({_normalize_ex_name(x) for x in exercises if str(x).strip()})
        for exercise_name in clean:
            ExerciseRepository.add(db, exercise_name, user_id=_current_user_id())
    finally:
        db.close()


def add_exercise_to_bank(name: str) -> None:
    """Añade un ejercicio al banco persistido + memoria de sesión."""
    name = _normalize_ex_name(name)
    if not name:
        return

    # sesión
    if "custom_exercises" not in st.session_state:
        st.session_state.custom_exercises = set()
    st.session_state.custom_exercises.add(name)

    # persistente
    existing = set(load_exercises_bank())
    existing.add(name)
    save_exercises_bank(existing)


def get_all_exercises() -> list[str]:
    ejercicios = set(EJERCICIOS_BASE)

    # Persistidos
    ejercicios.update(load_exercises_bank())

    # Historial
    df_hist = load_existing_training()
    if not df_hist.empty and "exercise" in df_hist.columns:
        ejercicios.update({_normalize_ex_name(x) for x in df_hist["exercise"].dropna().astype(str).tolist() if str(x).strip()})

    # Nuevos de sesión
    if "custom_exercises" in st.session_state and st.session_state.custom_exercises:
        ejercicios.update({_normalize_ex_name(x) for x in st.session_state.custom_exercises})

    return sorted([e for e in ejercicios if str(e).strip()])


def save_training(df: pd.DataFrame, date: datetime.date) -> bool:
    """Guarda entrenamientos en la base de datos"""
    db = next(get_db())
    try:
        # Eliminar entrenamientos existentes de esa fecha
        TrainingRepository.delete_by_date(db, date, user_id=_current_user_id())
        
        # Guardar nuevos
        for _, row in df.iterrows():
            training_data = {
                'date': date,
                'exercise': row.get('exercise', ''),
                'sets': int(row.get('sets', 3)),
                'reps': int(row.get('reps', 8)),
                'weight': float(row.get('weight', 0.0)),
                'rpe': float(row.get('rpe', 7.0)) if pd.notna(row.get('rpe')) else 7.0,
                'rir': float(row.get('rir', 2.0)) if pd.notna(row.get('rir')) else 2.0,
                'session_name': str(row.get('session_name', ''))
            }
            TrainingRepository.create(db, training_data, user_id=_current_user_id())
        
        return True
    except Exception as e:
        st.error(f"Error guardando: {e}")
        return False
    finally:
        db.close()


def _session_rows(df_hist: pd.DataFrame, date: datetime.date) -> pd.DataFrame:
    df_day = df_hist[df_hist["date"] == date].copy() if (not df_hist.empty and "date" in df_hist.columns) else pd.DataFrame()
    if df_day.empty:
        return pd.DataFrame([get_empty_row(date)])

    keep_cols = ["date", "exercise", "sets", "reps", "weight", "rpe", "rir"]
    for c in keep_cols:
        if c not in df_day.columns:
            df_day[c] = None
    return df_day[keep_cols].reset_index(drop=True)


def _recent_sessions_summary(df_hist: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    if df_hist.empty or "date" not in df_hist.columns:
        return pd.DataFrame()

    if "session_name" not in df_hist.columns:
        df_hist = df_hist.copy()
        df_hist["session_name"] = ""

    df_hist["session_name"] = df_hist["session_name"].fillna("").astype(str)

    grouped = (
        df_hist.groupby(["date", "session_name"], dropna=False)
        .apply(lambda g: pd.Series({
            "n_ex": int((g["exercise"].astype(str).str.strip() != "").sum()) if "exercise" in g.columns else 0,
            "sets_sum": float(pd.to_numeric(g["sets"], errors="coerce").fillna(0).sum()) if "sets" in g.columns else 0.0,
            "vol": float(
                (pd.to_numeric(g["sets"], errors="coerce").fillna(0)
                 * pd.to_numeric(g["reps"], errors="coerce").fillna(0)
                 * pd.to_numeric(g["weight"], errors="coerce").fillna(0)).sum()
            ) if {"sets", "reps", "weight"}.issubset(g.columns) else 0.0,
            "rpe_mean": float(pd.to_numeric(g["rpe"], errors="coerce").mean()) if "rpe" in g.columns else float("nan"),
        }), include_groups=False)
        .reset_index()
        .sort_values("date", ascending=False)
        .head(limit)
    )
    return grouped


# ----------------------------
# Callbacks (NO st.rerun aquí)
# ----------------------------
def _save_new_exercise_from_row(row_idx: int) -> None:
    """
    Importante:
    - NO llamar a st.rerun() dentro de callbacks (Streamlit lo ignora y avisa).
    - Basta con actualizar session_state; Streamlit ya rerunea por el cambio del widget.
    """
    key_new = f"ex_new_{row_idx}"
    name = _normalize_ex_name(st.session_state.get(key_new, ""))
    if not name:
        return

    add_exercise_to_bank(name)

    # Cambia el selectbox de esa fila al nuevo ejercicio (UX)
    st.session_state[f"ex_select_{row_idx}"] = name

    # Limpia el input
    st.session_state[key_new] = ""

    # Actualiza df de sesión (por consistencia)
    if "training_data" in st.session_state and row_idx < len(st.session_state.training_data):
        st.session_state.training_data.at[row_idx, "exercise"] = name


# ----------------------------
# UI
# ----------------------------
def render_entrenamiento() -> None:
    # ---------- State init ----------
    if "training_date" not in st.session_state:
        st.session_state.training_date = datetime.date.today()

    if "training_data" not in st.session_state:
        st.session_state.training_data = pd.DataFrame(columns=["date", "exercise", "sets", "reps", "weight", "rpe", "rir"])

    if "num_rows" not in st.session_state:
        st.session_state.num_rows = max(0, len(st.session_state.training_data))

    if "custom_exercises" not in st.session_state:
        st.session_state.custom_exercises = set()

    # Hard sync
    if len(st.session_state.training_data) != st.session_state.num_rows:
        st.session_state.num_rows = max(1, len(st.session_state.training_data))

    # ---------- THEME ----------
    st.markdown(
        """
        <style>
        :root {
            --bg: #0B0F14;
            --surface: rgba(15,22,32,0.95);
            --surface-alt: rgba(20,28,40,0.85);
            --border: rgba(255,255,255,0.06);
            --border-light: rgba(255,255,255,0.08);
            --text: rgba(235,235,235,0.95);
            --text-secondary: rgba(200,200,200,0.8);
            --muted: rgba(150,150,150,0.65);
            --good: #00FFB0;
            --good-soft: rgba(0,255,176,0.2);
            --warn: #FFB81C;
            --warn-soft: rgba(255,184,28,0.15);
            --risk: #FF6B5E;
            --risk-soft: rgba(255,107,94,0.15);
        }

        body, .stApp { background: var(--bg) !important; }

        /* FORZAR COLORES OSCUROS GLOBALMENTE */
        * {
            scrollbar-width: thin;
            scrollbar-color: rgba(60,60,65,0.5) transparent;
        }
        
        /* Eliminar TODOS los fondos morados/azules de Streamlit */
        [data-baseweb="select"],
        [data-baseweb="input"],
        [data-baseweb="base-input"],
        .stSelectbox,
        .stNumberInput,
        .stTextInput,
        .stDateInput {
            background-color: transparent !important;
        }

        /* HEADER */
        .training-title {
            color: var(--text);
            font-size: 2.2rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            margin-bottom: 8px;
        }

        .training-subtitle {
            color: var(--muted);
            font-size: 0.95rem;
            line-height: 1.5;
            margin-bottom: 20px;
        }

        /* CARDS */
        .training-card {
            background: rgba(11,14,17,0.65);
            border: 1px solid rgba(255,255,255,0.04);
            border-radius: 16px;
            padding: 28px;
            margin-bottom: 28px;
            box-shadow: 0 8px 24px rgba(0,0,0,0.25);
        }

        .training-card.card-primary {
            border-top: 2px solid rgba(0,255,176,0.5);
            border-left: 1px solid rgba(0,255,176,0.1);
            border-right: 1px solid rgba(0,255,176,0.1);
        }

        .training-card.card-sticky {
            position: sticky;
            top: 1.2rem;
        }

        .card-label {
            color: var(--muted);
            font-size: 0.75rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            margin-bottom: 16px;
            display: block;
        }

        /* CHIPS */
        .training-chip {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 6px 12px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
            border: 1px solid var(--border-light);
            color: var(--text-secondary);
            background: rgba(255,255,255,0.02);
            margin-bottom: 8px;
            margin-right: 8px;
        }

        .training-chip.good {
            border-color: rgba(0,255,176,0.4);
            color: var(--good);
            background: var(--good-soft);
        }

        .training-chip.warn {
            border-color: rgba(255,184,28,0.4);
            color: var(--warn);
            background: var(--warn-soft);
        }

        .training-chip.muted {
            border-color: var(--border);
            color: var(--muted);
            background: rgba(255,255,255,0.01);
        }

        /* GRID HEADER */
        .training-grid-header {
            display: grid;
            grid-template-columns: 0.35fr 3.2fr 1fr 1fr 1.25fr 0.95fr 0.95fr 0.52fr;
            gap: 10px;
            padding: 14px 16px;
            background: transparent;
            border: none;
            border-bottom: 1px solid rgba(60,60,65,0.4);
            border-radius: 0;
            margin-top: 24px;
            margin-bottom: 12px;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: rgba(120,120,125,0.75);
        }

        .training-grid-header > div {
            display: flex;
            align-items: center;
            justify-content: flex-start;
        }

        /* ROWS */
        .training-row {
            display: grid;
            grid-template-columns: 0.35fr 3.2fr 1fr 1fr 1.25fr 0.95fr 0.95fr 0.52fr;
            gap: 10px;
            padding: 14px 16px;
            border: 1px solid transparent;
            background: transparent;
            border-radius: 10px;
            margin-bottom: 6px;
            align-items: center;
            transition: all 0.15s ease;
        }

        .training-row:nth-child(even) {
            background: rgba(255,255,255,0.015);
        }

        .training-row:hover {
            border-color: rgba(0,255,176,0.18);
            background: rgba(0,255,176,0.035);
            box-shadow: 0 2px 8px rgba(0,255,176,0.08);
        }

        /* SUMMARY STATS */
        .summary-stat {
            background: rgba(15,20,25,0.75);
            border: 1px solid rgba(0,255,176,0.08);
            border-left: 2px solid rgba(0,255,176,0.25);
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 12px;
        }

        .summary-stat-label {
            color: var(--muted);
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 6px;
            display: block;
        }

        .summary-stat-value {
            color: var(--text);
            font-size: 1.5rem;
            font-weight: 800;
            line-height: 1.1;
        }

        .summary-stat-hint {
            color: var(--muted);
            font-size: 0.7rem;
            margin-top: 3px;
            opacity: 0.75;
        }

        /* BUTTONS */
        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, rgba(0,200,140,0.85), rgba(0,160,120,0.85)) !important;
            color: rgba(10,15,20,0.95) !important;
            border: 1px solid rgba(0,255,176,0.25) !important;
            border-radius: 10px !important;
            font-weight: 700 !important;
            letter-spacing: 0.02em;
            box-shadow: 0 4px 12px rgba(0,255,176,0.08) !important;
        }

        .stButton > button[kind="primary"]:hover {
            background: linear-gradient(135deg, rgba(0,220,155,0.9), rgba(0,180,135,0.9)) !important;
            box-shadow: 0 6px 16px rgba(0,255,176,0.12) !important;
        }

        .stButton > button:not([kind="primary"] ) {
            background: rgba(30,30,35,0.5) !important;
            color: rgba(200,200,200,0.85) !important;
            border: 1px solid rgba(60,60,65,0.5) !important;
            border-radius: 8px !important;
        }

        .stButton > button:not([kind="primary"]):hover {
            background: rgba(40,40,45,0.7) !important;
            border-color: rgba(80,80,85,0.7) !important;
        }

        /* INPUT STYLING - Forzar negro/gris, eliminar morados */
        div[data-testid="stSelectbox"] > div > div,
        div[data-testid="stNumberInput"] > div > div > input,
        div[data-testid="stTextInput"] > div > div > input,
        div[data-testid="stDateInput"] > div > div > input,
        input[type="number"],
        input[type="text"],
        input[type="date"] {
            background-color: rgba(15,15,18,0.95) !important;
            background: rgba(15,15,18,0.95) !important;
            color: rgba(220,220,220,0.95) !important;
            border: 1px solid rgba(60,60,65,0.5) !important;
            border-radius: 6px !important;
        }

        div[data-testid="stSelectbox"] > div,
        div[data-testid="stNumberInput"] > div,
        div[data-testid="stTextInput"] > div,
        div[data-testid="stDateInput"] > div {
            background: transparent !important;
        }

        div[data-testid="stSelectbox"] > div > div:hover,
        div[data-testid="stNumberInput"] > div > div:hover,
        div[data-testid="stTextInput"] > div > div:hover,
        input:hover {
            border-color: rgba(80,80,85,0.7) !important;
            background: rgba(20,20,23,0.95) !important;
        }

        div[data-testid="stSelectbox"] > div > div:focus-within,
        div[data-testid="stNumberInput"] > div > div:focus-within,
        div[data-testid="stTextInput"] > div > div:focus-within,
        input:focus {
            border-color: rgba(0,255,176,0.3) !important;
            background: rgba(20,20,23,0.98) !important;
            box-shadow: 0 0 0 1px rgba(0,255,176,0.12) !important;
            outline: none !important;
        }

        /* Eliminar fondos morados de los selectbox */
        [role="listbox"],
        [role="option"] {
            background: rgba(15,15,18,0.98) !important;
            color: rgba(220,220,220,0.95) !important;
        }

        [role="option"]:hover {
            background: rgba(30,30,35,0.98) !important;
        }

        /* Eliminar warnings llamativos de Streamlit */
        .element-container:has(.stAlert) .stAlert,
        div[data-testid="stNotification"] {
            background: rgba(30,30,35,0.5) !important;
            border: 1px solid rgba(60,60,65,0.5) !important;
            color: rgba(180,180,185,0.85) !important;
        }

        /* SEPARATOR */
        .training-sep {
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(60,60,65,0.25), transparent);
            margin: 20px 0;
        }

        /* TABS */
        .stTabs [data-baseweb="tab-list"] {
            background: rgba(0,0,0,0.1);
            border-bottom: 1px solid var(--border);
            border-radius: 12px 12px 0 0;
            padding: 0.25rem;
            gap: 4px;
        }

        .stTabs [data-baseweb="tab"] {
            border-radius: 10px;
            color: var(--muted);
        }

        .stTabs [aria-selected="true"] {
            background: rgba(0,255,176,0.15) !important;
            color: var(--good) !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # ---------- Header ----------
    st.markdown('<div class="training-title">Entrenamiento</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="training-subtitle">Registro limpio de tu sesión — mantén el foco, sin ruido visual.</div>',
        unsafe_allow_html=True
    )
    st.markdown('<div style="height:18px"></div>', unsafe_allow_html=True)

    col_main, col_side = st.columns([7, 3], gap="large")

    # ---------- Main ----------
    with col_main:
        # Fecha + nombre sesión (fuera de la card)
        c1, c2 = st.columns([1.15, 2.45], gap="medium")
        with c1:
            def _on_date_change():
                """Callback para sincronizar fecha cuando el usuario la cambia."""
                st.session_state.training_date = st.session_state.training_date_widget
            
            selected_date = st.date_input(
                "Fecha",
                key="training_date_widget",
                value=st.session_state.training_date,
                max_value=datetime.date.today(),
                format="DD/MM/YYYY",
                on_change=_on_date_change
            )

        with c2:
            session_name = st.text_input(
                "Nombre del entrenamiento (opcional)",
                key="session_name",
                value=st.session_state.get("session_name", ""),
                placeholder="Ej: Upper fuerza / Pierna volumen / Push A",
                help="Si lo dejas vacío, se autogenerará al guardar."
            )

        st.markdown('<div style="height:16px"></div>', unsafe_allow_html=True)

        # ABRE LA CARD PRINCIPAL - abarcar el contenido del entrenamiento
        st.markdown('<div class="training-card card-primary">', unsafe_allow_html=True)

        with st.expander("📖 Guía RPE y RIR", expanded=False):
            a, b = st.columns(2)
            with a:
                st.markdown(
                    "**RPE (Percepción del Esfuerzo)**\n"
                    "- **10**: Máximo esfuerzo\n"
                    "- **9**: Muy alto\n"
                    "- **8**: Alto\n"
                    "- **7**: Moderado-alto\n"
                    "- **6**: Moderado"
                )
            with b:
                st.markdown(
                    "**RIR (Reps en recámara)**\n"
                    "- **0**: Fallo\n"
                    "- **1**: 1 rep más\n"
                    "- **2**: 2 reps más\n"
                    "- **3**: 3+ reps más"
                )

        st.markdown('<div class="training-sep"></div>', unsafe_allow_html=True)

        # Inicializar rows_data desde training_data
        if st.session_state.training_data.empty:
            rows_data: list[dict] = []
            rows_to_delete: list[int] = []
        else:
            rows_data: list[dict] = st.session_state.training_data.to_dict('records')
            rows_to_delete: list[int] = []
            all_ex = get_all_exercises()

            # Header "Excel" - Grid horizontal
            header_html = '''
            <div class="training-grid-header">
                <div>#</div>
                <div>Ejercicio</div>
                <div>Series</div>
                <div>Reps</div>
                <div>Peso (kg)</div>
                <div>RPE</div>
                <div>RIR</div>
                <div></div>
            </div>
            '''
            st.markdown(header_html, unsafe_allow_html=True)

            # Render rows
            for i in range(len(rows_data)):
                row = rows_data[i]

                st.markdown(f'<div class="training-row">', unsafe_allow_html=True)

                cols = st.columns([0.35, 3.2, 1.0, 1.0, 1.25, 0.95, 0.95, 0.52], gap="small")

                with cols[0]:
                    st.markdown(f"<div style='color:var(--muted);text-align:center;font-weight:700'>{i+1}</div>", unsafe_allow_html=True)

                with cols[1]:
                    opciones = [""] + all_ex + ["➕ Nuevo ejercicio..."]
                    current_ex = _normalize_ex_name(row.get("exercise", ""))
                    if current_ex and current_ex not in all_ex:
                        opciones = ["", current_ex] + all_ex + ["➕ Nuevo ejercicio..."]
                        default_idx = 1
                    else:
                        default_idx = opciones.index(current_ex) if current_ex in opciones else 0

                    selected = st.selectbox(
                        "Ejercicio",
                        options=opciones,
                        index=default_idx,
                        key=f"ex_select_{i}",
                        label_visibility="collapsed",
                    )

                    if selected == "➕ Nuevo ejercicio...":
                        st.text_input(
                            "Nombre ejercicio",
                            key=f"ex_new_{i}",
                            label_visibility="collapsed",
                            placeholder="Escribe el nombre y Enter…",
                            on_change=lambda idx=i: _save_new_exercise_from_row(idx),
                        )
                        exercise = ""
                    else:
                        exercise = _normalize_ex_name(selected)
                        rows_data[i]["exercise"] = exercise

                with cols[2]:
                    sets = st.number_input(
                        "Series", min_value=1, max_value=30,
                        value=int(row.get("sets", 3)), step=1,
                        key=f"sets_{i}", label_visibility="collapsed"
                    )
                    rows_data[i]["sets"] = int(sets)

                with cols[3]:
                    reps = st.number_input(
                        "Reps", min_value=1, max_value=80,
                        value=int(row.get("reps", 8)), step=1,
                        key=f"reps_{i}", label_visibility="collapsed"
                    )
                    rows_data[i]["reps"] = int(reps)

                with cols[4]:
                    weight = st.number_input(
                        "Peso", min_value=0.0, max_value=600.0,
                        value=float(row.get("weight", 0.0)),
                        step=2.5, format="%.1f",
                        key=f"weight_{i}", label_visibility="collapsed"
                    )
                    rows_data[i]["weight"] = float(weight)

                with cols[5]:
                    rpe = st.number_input(
                        "RPE", min_value=1, max_value=10,
                        value=int(row.get("rpe", 7)), step=1,
                        key=f"rpe_{i}", label_visibility="collapsed"
                    )
                    rows_data[i]["rpe"] = int(rpe)

                with cols[6]:
                    rir = st.number_input(
                        "RIR", min_value=0, max_value=6,
                        value=int(row.get("rir", 2)), step=1,
                        key=f"rir_{i}", label_visibility="collapsed"
                    )
                    rows_data[i]["rir"] = int(rir)

                with cols[7]:
                    if st.button("🗑️", key=f"del_{i}", help="Eliminar fila"):
                        rows_to_delete.append(i)

                st.markdown("</div>", unsafe_allow_html=True)

            # delete handling
            if rows_to_delete:
                rows_data = [r for idx, r in enumerate(rows_data) if idx not in rows_to_delete]

        # Sync con session_state
        st.session_state.training_data = pd.DataFrame(rows_data)
        st.session_state.num_rows = len(rows_data)

        # Add row button (siempre visible)
        st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
        add_cols = st.columns([1.8, 6.2], gap="small")
        with add_cols[0]:
            if st.button("＋ Añadir fila", key="add_row", width="stretch"):
                new_row = {
                    "date": selected_date,
                    "exercise": "",
                    "sets": 3,
                    "reps": 8,
                    "weight": 0.0,
                    "rpe": 7,
                    "rir": 2
                }
                rows_data.append(new_row)
                st.session_state.training_data = pd.DataFrame(rows_data)
                st.session_state.num_rows = len(rows_data)
                st.rerun()
        with add_cols[1]:
            st.caption("💡 Tip: usa Tab para moverte entre celdas")

        # CIERRA LA CARD PRINCIPAL
        st.markdown("</div>", unsafe_allow_html=True)

    # ---------- Sidebar ----------
    with col_side:
        st.markdown('<div class="training-card card-sticky">', unsafe_allow_html=True)
        st.markdown('<span class="card-label">Resumen de Sesión</span>', unsafe_allow_html=True)

        df_to_save = st.session_state.training_data.copy()
        
        # Verificar que el DataFrame no esté vacío y tenga la columna 'exercise'
        if not df_to_save.empty and "exercise" in df_to_save.columns:
            df_to_save["date"] = selected_date

            # Filtrar filas "válidas"
            df_to_save = df_to_save[
                df_to_save["exercise"].notna()
                & (df_to_save["exercise"].astype(str).str.strip() != "")
                & (df_to_save["exercise"].astype(str).str.strip() != "➕ Nuevo ejercicio...")
            ].copy()
        else:
            df_to_save = pd.DataFrame(columns=["date", "exercise", "sets", "reps", "weight", "rpe", "rir"])

        if not df_to_save.empty and "sets" in df_to_save.columns:
            vol = float((df_to_save["sets"] * df_to_save["reps"] * df_to_save["weight"]).sum())
            st.markdown(f'<div class="summary-stat"><span class="summary-stat-label">Ejercicios</span><div class="summary-stat-value">{len(df_to_save)}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="summary-stat"><span class="summary-stat-label">Series Totales</span><div class="summary-stat-value">{int(df_to_save["sets"].sum())}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="summary-stat"><span class="summary-stat-label">Volumen</span><div class="summary-stat-value">{vol:,.0f}</div><div class="summary-stat-hint">kg</div></div>', unsafe_allow_html=True)
            try:
                e1rm_top = float((df_to_save["weight"] * (1 + df_to_save["reps"] / 30.0)).max())
                st.markdown(f'<div class="summary-stat"><span class="summary-stat-label">e1RM Máx</span><div class="summary-stat-value">{e1rm_top:.1f}</div><div class="summary-stat-hint">kg</div></div>', unsafe_allow_html=True)
            except Exception:
                pass

            if "rpe" in df_to_save.columns and df_to_save["rpe"].notna().any():
                st.markdown(
                    f'<div class="summary-stat"><span class="summary-stat-label">RPE Promedio</span><div class="summary-stat-value">{df_to_save["rpe"].mean():.1f}</div><div class="summary-stat-hint">/10</div></div>',
                    unsafe_allow_html=True
                )
            if "rir" in df_to_save.columns and df_to_save["rir"].notna().any():
                st.markdown(
                    f'<div class="summary-stat"><span class="summary-stat-label">RIR Promedio</span><div class="summary-stat-value">{df_to_save["rir"].mean():.1f}</div><div class="summary-stat-hint">reps</div></div>',
                    unsafe_allow_html=True
                )
        else:
            st.info("Añade al menos un ejercicio para ver el resumen.")
        
        st.markdown('<div class="training-sep"></div>', unsafe_allow_html=True)
        
        # Guardar
        save_clicked = st.button(
            "💾 GUARDAR ENTRENAMIENTO",
            type="primary",
            width="stretch",
            key="save_training_primary"
        )
        st.caption("Se guardará con fecha y nombre de sesión (opcional).")

        if save_clicked:
            # Filtrar filas con ejercicio
            df_valid = st.session_state.training_data.copy()
            if "exercise" in df_valid.columns:
                df_valid = df_valid[
                    df_valid["exercise"].notna()
                    & (df_valid["exercise"].astype(str).str.strip() != "")
                    & (df_valid["exercise"].astype(str).str.strip() != "➕ Nuevo ejercicio...")
                ].copy()
            
            if df_valid.empty:
                st.warning("Añade al menos un ejercicio.")
            else:
                is_valid, errors = validate_exercises(df_valid)
                if not is_valid:
                    for e in errors:
                        st.error(e)
                else:
                    name_to_save = str(session_name).strip() or f"Entrenamiento - {selected_date.strftime('%d/%m/%Y')}"
                    with loading("Guardando..."):
                        df_out = df_valid.copy()
                        df_out["date"] = selected_date
                        df_out["session_name"] = name_to_save

                        # Persistimos ejercicios por si acaso
                        for ex in df_out["exercise"].dropna().astype(str).tolist():
                            add_exercise_to_bank(ex)

                        ok = save_training(df_out, selected_date)

                    if ok:
                        st.success(f"✅ Guardado: {name_to_save}")
                        st.balloons()

        st.markdown('<div class="training-sep"></div>', unsafe_allow_html=True)

        # Sesiones recientes
        st.markdown('<span class="card-label">Sesiones Recientes</span>', unsafe_allow_html=True)
        df_hist = load_existing_training()
        recent = _recent_sessions_summary(df_hist, limit=10)

        if recent.empty:
            st.markdown(f"<div style='color:var(--muted);text-align:center;padding:12px;font-size:0.9rem;'>Sin sesiones recientes.</div>", unsafe_allow_html=True)
        else:
            for idx, r in recent.iterrows():
                d = r["date"]
                name = str(r.get("session_name", "")).strip()
                title = name if name else f"Sesión {d.strftime('%d/%m/%Y')}"
                vol = r.get("vol", 0.0)
                rpe_mean = r.get("rpe_mean", float("nan"))

                row = st.columns([3.2, 1.2], gap="small")
                with row[0]:
                    st.markdown(
                        f"**{d.strftime('%d/%m/%Y')} — {title}**  \n"
                        f"<span style='color:rgba(232,255,243,.66)'>Vol: {vol:,.0f} kg"
                        + (f" | RPE: {rpe_mean:.1f}" if pd.notna(rpe_mean) else "")
                        + "</span>",
                        unsafe_allow_html=True
                    )
                with row[1]:
                    if st.button("Cargar", width="stretch", key=f"load_{idx}_{d}"):
                        # Solo actualiza la variable lógica, no la del widget
                        st.session_state.training_date = d
                        st.session_state.training_data = _session_rows(df_hist, d)
                        st.session_state.num_rows = max(1, len(st.session_state.training_data))

                        # Sync banco ejercicios con esa sesión
                        for ex in st.session_state.training_data["exercise"].dropna().astype(str).tolist():
                            add_exercise_to_bank(ex)

                        st.rerun()


        st.markdown("</div>", unsafe_allow_html=True)
