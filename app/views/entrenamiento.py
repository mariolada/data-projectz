"""
Vista Entrenamiento - Entrada de ejercicios estilo Excel (modo A: filas con st.columns)
- UI coherente (negro + acento verde)
- Tabla tipo Excel: header sticky, zebra, hover suave, inputs compactos
- Añadir ejercicio "on the fly" (persistente en exercises.csv)
- Guardado con nombre de sesión + reemplazo por fecha
- Panel lateral: resumen + guardar + recientes (cargar una sesión)
"""

from __future__ import annotations

import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from ui.loader import loading

TRAINING_CSV_PATH = Path("data/raw/training.csv")
EXERCISES_CSV_PATH = Path("data/raw/exercises.csv")

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
    if TRAINING_CSV_PATH.exists():
        try:
            df = pd.read_csv(TRAINING_CSV_PATH)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"]).dt.date
            return df
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame(columns=["date", "session_name", "exercise", "sets", "reps", "weight", "rpe", "rir"])


def _normalize_ex_name(name: str) -> str:
    # Limpieza suave para evitar duplicados tontos
    return " ".join(str(name).strip().split())


def load_exercises_bank() -> list[str]:
    """Lee ejercicios persistidos (exercises.csv)."""
    if EXERCISES_CSV_PATH.exists():
        try:
            df = pd.read_csv(EXERCISES_CSV_PATH)
            if "exercise" in df.columns:
                return sorted({_normalize_ex_name(x) for x in df["exercise"].dropna().astype(str).tolist() if str(x).strip()})
        except Exception:
            pass
    return []


def save_exercises_bank(exercises: set[str]) -> None:
    """Guarda ejercicios persistidos (exercises.csv) de forma idempotente."""
    EXERCISES_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    clean = sorted({_normalize_ex_name(x) for x in exercises if str(x).strip()})
    pd.DataFrame({"exercise": clean}).to_csv(EXERCISES_CSV_PATH, index=False)


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
    try:
        TRAINING_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

        if TRAINING_CSV_PATH.exists():
            df_existing = pd.read_csv(TRAINING_CSV_PATH)
            if "date" in df_existing.columns:
                df_existing["date"] = pd.to_datetime(df_existing["date"]).dt.date
            df_existing = df_existing[df_existing["date"] != date]
            df_final = pd.concat([df_existing, df], ignore_index=True)
        else:
            df_final = df

        df_final = df_final.sort_values("date", ascending=False)
        df_final.to_csv(TRAINING_CSV_PATH, index=False)
        return True
    except Exception as e:
        st.error(f"Error guardando: {e}")
        return False


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
        }))
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

    # OJO: el widget NO debe usar la misma key que modificamos a mano.
    if "training_date_widget" not in st.session_state:
        st.session_state.training_date_widget = st.session_state.training_date

    if "training_data" not in st.session_state:
        st.session_state.training_data = pd.DataFrame([get_empty_row(st.session_state.training_date)])

    if "num_rows" not in st.session_state:
        st.session_state.num_rows = max(1, len(st.session_state.training_data))

    if "custom_exercises" not in st.session_state:
        st.session_state.custom_exercises = set()

    # Hard sync
    if len(st.session_state.training_data) != st.session_state.num_rows:
        st.session_state.num_rows = max(1, len(st.session_state.training_data))

    # ---------- THEME ----------
    st.markdown(
        """
        <style>
        :root{
          --bg:#0b0f14;
          --surface:#0f1620;
          --surface2:#0c131c;
          --border:rgba(255,255,255,.10);
          --border2:rgba(255,255,255,.07);
          --text:#e8fff3;
          --muted:rgba(232,255,243,.66);
          --accent:#00ffb0;
          --danger:#ff4b4b;
          --radius:14px;
          --shadow: 0 10px 30px rgba(0,0,0,.33);
        }

        body, .stApp { background: var(--bg) !important; }

        .n-card{
          background: linear-gradient(180deg, rgba(15,22,32,.92), rgba(12,19,28,.92));
          border:1px solid var(--border);
          border-radius: var(--radius);
          box-shadow: var(--shadow);
          padding: 14px 14px;
        }
        .n-title{
          font-size: 2.05rem;
          font-weight: 850;
          letter-spacing: .02em;
          color: var(--text);
          margin: .15rem 0 .15rem 0;
          text-shadow: 0 0 14px rgba(0,255,176,.14);
        }
        .n-sub{
          color: var(--muted);
          font-size: 1.02rem;
          margin: 0 0 .9rem 0;
        }
        .n-sep{
          height: 1px;
          background: linear-gradient(90deg, transparent, rgba(0,255,176,.34), transparent);
          opacity: .35;
          margin: 12px 0;
        }

        /* Chips */
        .n-chip{
          display:inline-flex;
          align-items:center;
          gap:8px;
          padding: 6px 10px;
          border: 1px solid rgba(0,255,176,.26);
          border-radius: 999px;
          color: var(--text);
          background: rgba(0,0,0,.25);
          font-weight: 780;
          font-size: .92rem;
          margin: 4px 6px 4px 0;
          white-space: nowrap;
        }
        .n-chip-muted{
          border-color: var(--border2);
          color: var(--muted);
          font-weight: 650;
        }

        /* Grid header */
        .n-grid-header{
          position: sticky;
          top: 0;
          z-index: 10;
          background: rgba(15,22,32,.98);
          border: 1px solid var(--border);
          border-radius: 12px;
          padding: 7px 10px;
          margin-top: 10px;
        }
        .n-hcell{
          color: rgba(232,255,243,.78);
          font-weight: 900;
          letter-spacing: .08em;
          font-size: .74rem;
          text-transform: uppercase;
        }

        /* Rows */
        .n-row{
          border: 1px solid var(--border2);
          background: rgba(0,0,0,.13);
          border-radius: 12px;
          padding: 7px 10px;
          margin: 7px 0;
          transition: border-color .12s ease, background .12s ease, transform .08s ease;
        }
        .n-row.zebra{ background: rgba(255,255,255,.03); }
        .n-row:hover{
          border-color: rgba(0,255,176,.28);
          background: rgba(0,255,176,.055);
          transform: translateY(-1px);
        }

        /* Make widgets feel like cells */
        div[data-testid="stSelectbox"] > div,
        div[data-testid="stNumberInput"] > div,
        div[data-testid="stTextInput"] > div{
          background: rgba(0,0,0,.18) !important;
          border: 1px solid var(--border2) !important;
          border-radius: 10px !important;
        }
        div[data-testid="stSelectbox"] > div:hover,
        div[data-testid="stNumberInput"] > div:hover,
        div[data-testid="stTextInput"] > div:hover{
          border-color: rgba(0,255,176,.22) !important;
        }
        div[data-testid="stSelectbox"] > div:focus-within,
        div[data-testid="stNumberInput"] > div:focus-within,
        div[data-testid="stTextInput"] > div:focus-within{
          border-color: rgba(0,255,176,.55) !important;
          box-shadow: 0 0 0 2px rgba(0,255,176,.16) !important;
        }

        /* Reduce vertical gaps */
        .stNumberInput, .stSelectbox, .stTextInput { margin-top: -3px; }
        .stButton { margin-top: -2px; }

        /* Primary button */
        .stButton > button[kind="primary"]{
          border-radius: 12px !important;
          font-weight: 900 !important;
          letter-spacing: .02em;
          padding: 0.78rem 1rem !important;
          border: none !important;
          background: linear-gradient(90deg, rgba(0,255,176,1), rgba(0,201,167,1)) !important;
          color: #061018 !important;
          box-shadow: 0 10px 26px rgba(0,255,176,.14) !important;
        }
        .stButton > button[kind="primary"]:hover{
          filter: brightness(1.03);
          box-shadow: 0 12px 30px rgba(0,255,176,.18) !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # ---------- Header ----------
    st.markdown('<div class="n-title">Entrenamiento</div>', unsafe_allow_html=True)
    st.markdown('<div class="n-sub">Registra tu sesión estilo Excel: rápido, claro y coherente con el resto de la app.</div>', unsafe_allow_html=True)

    col_main, col_side = st.columns([7, 3], gap="large")

    # ---------- Main ----------
    with col_main:
        st.markdown('<div class="n-card">', unsafe_allow_html=True)

        # Fecha + nombre sesión
        c1, c2 = st.columns([1.15, 2.45], gap="medium")
        with c1:
            selected_date = st.date_input(
                "Fecha",
                key="training_date_widget",  # <- clave del widget separada
                value=st.session_state.training_date_widget,
                max_value=datetime.date.today(),
                format="DD/MM/YYYY"
            )

        # Sync: si el usuario cambió la fecha en el widget
        if selected_date != st.session_state.training_date:
            st.session_state.training_date = selected_date
            st.session_state.training_date_widget = selected_date

        with c2:
            session_name = st.text_input(
                "Nombre del entrenamiento (opcional)",
                key="session_name",
                value=st.session_state.get("session_name", ""),
                placeholder="Ej: Upper fuerza / Pierna volumen / Push A",
                help="Si lo dejas vacío, se autogenerará al guardar."
            )

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
                    "- **1**: 1 rep\n"
                    "- **2**: 2 reps\n"
                    "- **3**: 3 reps"
                )

        st.markdown('<div class="n-sep"></div>', unsafe_allow_html=True)

        # Header “Excel”
        st.markdown('<div class="n-grid-header">', unsafe_allow_html=True)
        hcols = st.columns([0.35, 3.2, 1.0, 1.0, 1.25, 0.95, 0.95, 0.52], gap="small")
        labels = ["#", "Ejercicio", "Series", "Reps", "Peso (kg)", "RPE", "RIR", ""]
        for col, lab in zip(hcols, labels):
            with col:
                st.markdown(f'<div class="n-hcell">{lab}</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

        # Render rows
        rows_data: list[dict] = []
        rows_to_delete: list[int] = []
        all_ex = get_all_exercises()

        for i in range(st.session_state.num_rows):
            if i < len(st.session_state.training_data):
                row = st.session_state.training_data.iloc[i].to_dict()
            else:
                row = get_empty_row(selected_date)

            zebra = "zebra" if i % 2 == 1 else ""
            st.markdown(f'<div class="n-row {zebra}">', unsafe_allow_html=True)

            cols = st.columns([0.35, 3.2, 1.0, 1.0, 1.25, 0.95, 0.95, 0.52], gap="small")

            with cols[0]:
                st.markdown(f"**{i+1}**")

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
                    # Mientras escribe, no ensuciamos df
                    exercise = ""
                else:
                    exercise = _normalize_ex_name(selected)

            with cols[2]:
                sets = st.number_input(
                    "Series", min_value=1, max_value=30,
                    value=int(row.get("sets", 3)), step=1,
                    key=f"sets_{i}", label_visibility="collapsed"
                )
            with cols[3]:
                reps = st.number_input(
                    "Reps", min_value=1, max_value=80,
                    value=int(row.get("reps", 8)), step=1,
                    key=f"reps_{i}", label_visibility="collapsed"
                )
            with cols[4]:
                weight = st.number_input(
                    "Peso", min_value=0.0, max_value=600.0,
                    value=float(row.get("weight", 0.0)),
                    step=2.5, format="%.1f",
                    key=f"weight_{i}", label_visibility="collapsed"
                )
            with cols[5]:
                rpe = st.number_input(
                    "RPE", min_value=1, max_value=10,
                    value=int(row.get("rpe", 7)), step=1,
                    key=f"rpe_{i}", label_visibility="collapsed"
                )
            with cols[6]:
                rir = st.number_input(
                    "RIR", min_value=0, max_value=6,
                    value=int(row.get("rir", 2)), step=1,
                    key=f"rir_{i}", label_visibility="collapsed"
                )

            with cols[7]:
                if st.button("🗑️", key=f"del_{i}", help="Eliminar fila"):
                    rows_to_delete.append(i)

            st.markdown("</div>", unsafe_allow_html=True)

            rows_data.append({
                "date": selected_date,
                "exercise": exercise,
                "sets": int(sets),
                "reps": int(reps),
                "weight": float(weight),
                "rpe": int(rpe),
                "rir": int(rir),
            })

        # delete handling
        if rows_to_delete:
            rows_data = [r for idx, r in enumerate(rows_data) if idx not in rows_to_delete]
            if not rows_data:
                rows_data = [get_empty_row(selected_date)]
            st.session_state.training_data = pd.DataFrame(rows_data)
            st.session_state.num_rows = len(st.session_state.training_data)
            st.rerun()

        st.session_state.training_data = pd.DataFrame(rows_data)

        # Add row
        add_cols = st.columns([1.5, 6.5], gap="small")
        with add_cols[0]:
            if st.button("＋ Añadir fila", key="add_row", width="stretch"):
                st.session_state.num_rows += 1
                new_row = pd.DataFrame([get_empty_row(selected_date)])
                st.session_state.training_data = pd.concat([st.session_state.training_data, new_row], ignore_index=True)
                st.rerun()
        with add_cols[1]:
            st.markdown(
                '<span class="n-chip n-chip-muted">Tip: usa Tab para moverte rápido por las celdas</span>',
                unsafe_allow_html=True
            )

        st.markdown("</div>", unsafe_allow_html=True)  # end card

    # ---------- Sidebar ----------
    with col_side:
        st.markdown('<div class="n-card" style="position:sticky;top:1.2rem;">', unsafe_allow_html=True)
        st.markdown("### Resumen de sesión")

        df_to_save = st.session_state.training_data.copy()
        df_to_save["date"] = selected_date

        # Filtrar filas “válidas”
        df_to_save = df_to_save[
            df_to_save["exercise"].notna()
            & (df_to_save["exercise"].astype(str).str.strip() != "")
            & (df_to_save["exercise"].astype(str).str.strip() != "➕ Nuevo ejercicio...")
        ].copy()

        if not df_to_save.empty:
            vol = float((df_to_save["sets"] * df_to_save["reps"] * df_to_save["weight"]).sum())
            st.markdown(
                f'<span class="n-chip">Ejercicios: {len(df_to_save)}</span>'
                f'<span class="n-chip">Series: {int(df_to_save["sets"].sum())}</span>'
                f'<span class="n-chip">Volumen: {vol:,.0f} kg</span>',
                unsafe_allow_html=True
            )
            try:
                e1rm_top = float((df_to_save["weight"] * (1 + df_to_save["reps"] / 30.0)).max())
                st.markdown(f'<span class="n-chip">e1RM top: {e1rm_top:.1f} kg</span>', unsafe_allow_html=True)
            except Exception:
                pass

            if "rpe" in df_to_save.columns and df_to_save["rpe"].notna().any():
                st.markdown(
                    f'<span class="n-chip n-chip-muted">RPE medio: {df_to_save["rpe"].mean():.2f}</span>',
                    unsafe_allow_html=True
                )
            if "rir" in df_to_save.columns and df_to_save["rir"].notna().any():
                st.markdown(
                    f'<span class="n-chip n-chip-muted">RIR medio: {df_to_save["rir"].mean():.2f}</span>',
                    unsafe_allow_html=True
                )
        else:
            st.info("Añade al menos un ejercicio para ver el resumen.")

        st.markdown('<div class="n-sep"></div>', unsafe_allow_html=True)

        # Guardar (siempre visible)
        save_clicked = st.button(
            "💾 Guardar entrenamiento",
            type="primary",
            width="stretch",
            key="save_training_primary"
        )
        st.caption("Se guardará con fecha y nombre de sesión (opcional).")

        if save_clicked:
            if df_to_save.empty:
                st.warning("Añade al menos un ejercicio.")
            else:
                is_valid, errors = validate_exercises(df_to_save)
                if not is_valid:
                    for e in errors:
                        st.error(e)
                else:
                    name_to_save = str(session_name).strip() or f"Entrenamiento - {selected_date.strftime('%d/%m/%Y')}"
                    with loading("Guardando..."):
                        df_out = df_to_save.copy()
                        df_out["session_name"] = name_to_save

                        # Persistimos ejercicios por si acaso
                        for ex in df_out["exercise"].dropna().astype(str).tolist():
                            add_exercise_to_bank(ex)

                        ok = save_training(df_out, selected_date)

                    if ok:
                        st.success(f"✅ Guardado: {name_to_save}")
                        st.balloons()

        st.markdown('<div class="n-sep"></div>', unsafe_allow_html=True)

        # Recientes / Plantillas (siempre visibles)
        tabs = st.tabs(["Recientes", "Plantillas"])

        with tabs[0]:
            df_hist = load_existing_training()
            recent = _recent_sessions_summary(df_hist, limit=10)

            if recent.empty:
                st.caption("Sin sesiones recientes.")
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

        with tabs[1]:
            st.caption("Plantillas (próximo paso): guardar una sesión como plantilla reutilizable.")
            st.markdown('<span class="n-chip n-chip-muted">Idea: “Upper A”, “Lower B”, “Full Body”</span>', unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
