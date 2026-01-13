"""
Vista Entrenamiento - Entrada de ejercicios estilo Excel con autocompletado.
"""
import streamlit as st
import pandas as pd
import datetime
from pathlib import Path

from ui.components import render_section_title
from ui.loader import loading

TRAINING_CSV_PATH = Path("data/raw/training.csv")

# Ejercicios base predefinidos (se amplían con el historial)
EJERCICIOS_BASE = [
    "Press Banca", "Press Inclinado", "Press Militar",
    "Sentadilla", "Peso Muerto", "Peso Muerto Rumano",
    "Dominadas", "Remo con Barra", "Remo con Mancuerna",
    "Curl Bíceps", "Extensión Tríceps", "Press Francés",
    "Hip Thrust", "Zancadas", "Prensa de Piernas",
    "Elevaciones Laterales", "Face Pull", "Fondos"
]


def get_empty_row(date: datetime.date) -> dict:
    """Retorna una fila vacía con valores por defecto."""
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
    """Valida que los ejercicios tengan datos mínimos."""
    errors = []
    if df.empty:
        return False, ["No hay ejercicios para guardar"]
    
    for idx, row in df.iterrows():
        row_num = idx + 1
        if not row.get('exercise') or str(row.get('exercise', '')).strip() == '':
            errors.append(f"Fila {row_num}: Falta nombre del ejercicio")
        if pd.isna(row.get('sets')) or row.get('sets', 0) <= 0:
            errors.append(f"Fila {row_num}: Series debe ser > 0")
        if pd.isna(row.get('reps')) or row.get('reps', 0) <= 0:
            errors.append(f"Fila {row_num}: Reps debe ser > 0")
    
    return len(errors) == 0, errors


def load_existing_training() -> pd.DataFrame:
    """Carga el CSV de training existente."""
    if TRAINING_CSV_PATH.exists():
        try:
            df = pd.read_csv(TRAINING_CSV_PATH)
            df['date'] = pd.to_datetime(df['date']).dt.date
            return df
        except Exception:
            pass
    return pd.DataFrame(columns=['date', 'exercise', 'sets', 'reps', 'weight', 'rpe', 'rir'])


def get_all_exercises() -> list[str]:
    """Obtiene todos los ejercicios: base + historial del usuario + ejercicios de sesión."""
    ejercicios = set(EJERCICIOS_BASE)
    df_hist = load_existing_training()
    if not df_hist.empty and 'exercise' in df_hist.columns:
        ejercicios.update(df_hist['exercise'].dropna().unique().tolist())
    # Añadir ejercicios nuevos de la sesión actual
    if 'custom_exercises' in st.session_state:
        ejercicios.update(st.session_state.custom_exercises)
    return sorted(ejercicios)


def save_training(df: pd.DataFrame, date: datetime.date) -> bool:
    """Guarda los ejercicios, reemplazando los de la fecha."""
    try:
        TRAINING_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        if TRAINING_CSV_PATH.exists():
            df_existing = pd.read_csv(TRAINING_CSV_PATH)
            df_existing['date'] = pd.to_datetime(df_existing['date']).dt.date
            df_existing = df_existing[df_existing['date'] != date]
            df_final = pd.concat([df_existing, df], ignore_index=True)
        else:
            df_final = df
        
        df_final = df_final.sort_values('date', ascending=False)
        df_final.to_csv(TRAINING_CSV_PATH, index=False)
        return True
    except Exception as e:
        st.error(f"Error: {e}")
        return False


def _save_new_exercise(row_idx: int):
    """Guarda un nuevo ejercicio desde el input de texto."""
    key = f"ex_new_{row_idx}"
    if key in st.session_state:
        exercise_name = st.session_state[key].strip()
        if exercise_name:
            # Añadir a ejercicios personalizados
            if 'custom_exercises' not in st.session_state:
                st.session_state.custom_exercises = set()
            st.session_state.custom_exercises.add(exercise_name)
            
            # Actualizar training_data
            if 'training_data' in st.session_state and row_idx < len(st.session_state.training_data):
                st.session_state.training_data.at[row_idx, 'exercise'] = exercise_name


def render_entrenamiento():
    """Vista principal de entrada de entrenamiento."""
    render_section_title("Entrenamiento", "Registra tus ejercicios")
    
    # Selector de fecha
    col_date, col_info = st.columns([1, 2])
    with col_date:
        selected_date = st.date_input(
            "Fecha",
            value=datetime.date.today(),
            max_value=datetime.date.today(),
            format="DD/MM/YYYY"
        )
    
    # Inicializar datos
    if 'training_data' not in st.session_state:
        st.session_state.training_data = pd.DataFrame([get_empty_row(selected_date)])
        st.session_state.training_date = selected_date
        # Cargar existentes
        df_existing = load_existing_training()
        df_date = df_existing[df_existing['date'] == selected_date]
        if not df_date.empty:
            st.session_state.training_data = df_date.copy()
    
    # Cambio de fecha
    if st.session_state.get('training_date') != selected_date:
        st.session_state.training_date = selected_date
        df_existing = load_existing_training()
        df_date = df_existing[df_existing['date'] == selected_date]
        if not df_date.empty:
            st.session_state.training_data = df_date.copy()
        else:
            st.session_state.training_data = pd.DataFrame([get_empty_row(selected_date)])
    
    # Guía RPE/RIR
    with st.expander("📖 Guía RPE y RIR"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            **RPE (Percepción del Esfuerzo)**
            - **10**: Máximo esfuerzo absoluto
            - **9**: Muchísimo esfuerzo
            - **8**: Esfuerzo alto
            - **7**: Esfuerzo moderado-alto
            - **6**: Esfuerzo moderado
            """)
        with col2:
            st.markdown("""
            **RIR (Reps en Recámara)**
            - **0**: Fallo, no puedes hacer más
            - **1**: Te quedaba 1 rep
            - **2**: Te quedaban 2 reps
            - **3**: Te quedaban 3 reps
            """)
    
    # === TABLA EXCEL CON AUTOCOMPLETADO ===
    st.markdown("### Ejercicios")
    st.caption("Selecciona ejercicios guardados o añade uno nuevo")
    
    # Inicializar ejercicios personalizados en sesión
    if 'custom_exercises' not in st.session_state:
        st.session_state.custom_exercises = set()
    
    # Inicializar filas si no existen
    if 'num_rows' not in st.session_state:
        st.session_state.num_rows = max(1, len(st.session_state.training_data))
    
    # Sincronizar num_rows con training_data
    if len(st.session_state.training_data) != st.session_state.num_rows:
        st.session_state.num_rows = max(1, len(st.session_state.training_data))
    
    # CSS para estilo Excel/Tabla
    st.markdown("""
    <style>
    /* Contenedor principal de la tabla */
    .excel-table-container {
        border: 1px solid rgba(178, 102, 255, 0.3);
        border-radius: 8px;
        overflow: hidden;
        margin: 1rem 0;
    }
    
    /* Header de la tabla estilo Excel */
    .table-header {
        background: linear-gradient(180deg, rgba(178, 102, 255, 0.25) 0%, rgba(178, 102, 255, 0.15) 100%);
        padding: 12px 8px;
        border-bottom: 2px solid rgba(178, 102, 255, 0.4);
        font-weight: 600;
        font-size: 0.85em;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        color: #E0E0E0;
    }
    
    /* Filas de la tabla */
    div[data-testid="column"] {
        padding: 2px 4px !important;
    }
    
    /* Inputs más compactos estilo celda */
    div[data-testid="stNumberInput"] > div,
    div[data-testid="stSelectbox"] > div {
        background: rgba(20, 20, 30, 0.6) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 4px !important;
    }
    
    div[data-testid="stNumberInput"] > div:hover,
    div[data-testid="stSelectbox"] > div:hover {
        border-color: rgba(178, 102, 255, 0.5) !important;
        background: rgba(30, 30, 45, 0.8) !important;
    }
    
    div[data-testid="stNumberInput"] > div:focus-within,
    div[data-testid="stSelectbox"] > div:focus-within {
        border-color: rgba(178, 102, 255, 0.8) !important;
        box-shadow: 0 0 0 2px rgba(178, 102, 255, 0.2) !important;
    }
    
    /* Líneas separadoras entre filas */
    .row-separator {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(178, 102, 255, 0.2), transparent);
        margin: 4px 0;
    }
    
    /* Número de fila estilo Excel */
    .row-number {
        background: rgba(178, 102, 255, 0.15);
        color: rgba(255, 255, 255, 0.6);
        font-size: 0.75em;
        font-weight: 600;
        padding: 8px 12px;
        text-align: center;
        border-right: 1px solid rgba(178, 102, 255, 0.2);
        min-width: 35px;
    }
    
    /* Botón eliminar más discreto */
    button[kind="secondary"] {
        background: transparent !important;
        border: none !important;
        opacity: 0.5;
    }
    button[kind="secondary"]:hover {
        opacity: 1;
        background: rgba(255, 100, 100, 0.2) !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Header de la tabla con estilo Excel
    st.markdown('<div class="table-header">', unsafe_allow_html=True)
    cols_header = st.columns([0.3, 3, 1, 1, 1.2, 1, 1, 0.5])
    headers = ["#", "Ejercicio", "Series", "Reps", "Peso (kg)", "RPE", "RIR", ""]
    for col, header in zip(cols_header, headers):
        col.markdown(f"<span style='font-size: 0.85em; font-weight: 600;'>{header}</span>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Renderizar filas
    rows_data = []
    rows_to_delete = []
    
    for i in range(st.session_state.num_rows):
        # Obtener valores actuales de la fila
        if i < len(st.session_state.training_data):
            row = st.session_state.training_data.iloc[i]
            current_exercise = row.get('exercise', '')
            current_sets = int(row.get('sets', 3))
            current_reps = int(row.get('reps', 8))
            current_weight = float(row.get('weight', 0.0))
            current_rpe = int(row.get('rpe', 7))
            current_rir = int(row.get('rir', 2))
        else:
            current_exercise = ''
            current_sets = 3
            current_reps = 8
            current_weight = 0.0
            current_rpe = 7
            current_rir = 2
        
        cols = st.columns([0.3, 3, 1, 1, 1.2, 1, 1, 0.5])
        
        # Número de fila
        with cols[0]:
            st.markdown(f"<div style='padding: 8px; text-align: center; color: rgba(178, 102, 255, 0.8); font-weight: 600;'>{i+1}</div>", unsafe_allow_html=True)
        
        # Obtener ejercicios actualizados (incluye los añadidos en esta sesión)
        todos_ejercicios = get_all_exercises()
        
        # Columna Ejercicio - Selectbox con opción de escribir nuevo
        with cols[1]:
            # Crear opciones: ejercicios existentes + opción de nuevo
            opciones = [""] + todos_ejercicios + ["➕ Nuevo ejercicio..."]
            
            # Determinar índice actual
            if current_exercise in todos_ejercicios:
                default_idx = todos_ejercicios.index(current_exercise) + 1
            elif current_exercise and current_exercise not in ["", "➕ Nuevo ejercicio..."]:
                # Es un ejercicio personalizado no en la lista
                opciones = [""] + [current_exercise] + todos_ejercicios + ["➕ Nuevo ejercicio..."]
                default_idx = 1
            else:
                default_idx = 0
            
            seleccion = st.selectbox(
                f"Ejercicio {i+1}",
                options=opciones,
                index=default_idx,
                key=f"ex_select_{i}",
                label_visibility="collapsed",
                placeholder="Buscar ejercicio..."
            )
            
            # Si seleccionó "Nuevo ejercicio", mostrar input de texto con botón
            if seleccion == "➕ Nuevo ejercicio...":
                col_input, col_btn = st.columns([5, 1])
                with col_input:
                    new_exercise_name = st.text_input(
                        "Nombre",
                        value="",
                        key=f"ex_new_{i}",
                        label_visibility="collapsed",
                        placeholder="Nombre del ejercicio...",
                        on_change=lambda idx=i: _save_new_exercise(idx)
                    )
                with col_btn:
                    if st.button("✓", key=f"add_ex_{i}", help="Añadir ejercicio", use_container_width=True):
                        _save_new_exercise(i)
                
                exercise = new_exercise_name.strip() if new_exercise_name else ""
            else:
                exercise = seleccion
        
        # Columnas numéricas
        with cols[2]:
            sets = st.number_input("Sets", min_value=1, max_value=20, value=current_sets, 
                                   key=f"sets_{i}", label_visibility="collapsed")
        with cols[3]:
            reps = st.number_input("Reps", min_value=1, max_value=50, value=current_reps, 
                                   key=f"reps_{i}", label_visibility="collapsed")
        with cols[4]:
            weight = st.number_input("Peso", min_value=0.0, max_value=500.0, value=current_weight, 
                                     step=2.5, format="%.1f", key=f"weight_{i}", label_visibility="collapsed")
        with cols[5]:
            rpe = st.number_input("RPE", min_value=1, max_value=10, value=current_rpe, 
                                  step=1, key=f"rpe_{i}", label_visibility="collapsed")
        with cols[6]:
            rir = st.number_input("RIR", min_value=0, max_value=5, value=current_rir, 
                                  step=1, key=f"rir_{i}", label_visibility="collapsed")
        
        # Botón eliminar fila
        with cols[7]:
            if st.button("🗑️", key=f"del_{i}", help="Eliminar fila"):
                rows_to_delete.append(i)
        
        # Guardar datos de la fila
        rows_data.append({
            "date": selected_date,
            "exercise": exercise,
            "sets": sets,
            "reps": reps,
            "weight": weight,
            "rpe": rpe,
            "rir": rir
        })
        
        # Separador entre filas (excepto la última)
        if i < st.session_state.num_rows - 1:
            st.markdown('<div class="row-separator"></div>', unsafe_allow_html=True)
    
    # Procesar eliminaciones
    if rows_to_delete:
        rows_data = [r for idx, r in enumerate(rows_data) if idx not in rows_to_delete]
        st.session_state.training_data = pd.DataFrame(rows_data) if rows_data else pd.DataFrame([get_empty_row(selected_date)])
        st.session_state.num_rows = len(st.session_state.training_data)
        st.rerun()
    
    # Actualizar training_data con los valores actuales
    st.session_state.training_data = pd.DataFrame(rows_data)
    
    # Botón añadir fila
    col_add, col_space = st.columns([1, 4])
    with col_add:
        if st.button("➕ Añadir ejercicio", use_container_width=True):
            st.session_state.num_rows += 1
            new_row = pd.DataFrame([get_empty_row(selected_date)])
            st.session_state.training_data = pd.concat(
                [st.session_state.training_data, new_row], 
                ignore_index=True
            )
            st.rerun()
    
    # === GUARDAR ===
    st.markdown("---")
    
    df_to_save = st.session_state.training_data.copy()
    df_to_save['date'] = selected_date
    df_to_save = df_to_save[df_to_save['exercise'].notna() & (df_to_save['exercise'] != '') & (df_to_save['exercise'] != '➕ Nuevo ejercicio...')]
    
    if not df_to_save.empty:
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            st.metric("Ejercicios", len(df_to_save))
        with col_s2:
            st.metric("Series", int(df_to_save['sets'].sum()))
        with col_s3:
            vol = (df_to_save['sets'] * df_to_save['reps'] * df_to_save['weight']).sum()
            st.metric("Volumen", f"{vol:,.0f} kg")
    
    # Botón guardar siempre visible
    if st.button("💾 Guardar entrenamiento", type="primary", use_container_width=True):
        if df_to_save.empty:
            st.warning("Añade al menos un ejercicio")
        else:
            is_valid, errors = validate_exercises(df_to_save)
            if not is_valid:
                for e in errors:
                    st.error(e)
            else:
                with loading("Guardando..."):
                    success = save_training(df_to_save, selected_date)
                if success:
                    st.success(f"✅ Guardado ({len(df_to_save)} ejercicios)")
                    st.balloons()
    
    # Historial
    st.markdown("---")
    with st.expander("📅 Historial reciente"):
        df_hist = load_existing_training()
        if not df_hist.empty:
            week_ago = datetime.date.today() - datetime.timedelta(days=7)
            df_recent = df_hist[df_hist['date'] >= week_ago].sort_values('date', ascending=False)
            if not df_recent.empty:
                df_show = df_recent.copy()
                df_show['date'] = pd.to_datetime(df_show['date']).dt.strftime('%d/%m')
                df_show.columns = ['Fecha', 'Ejercicio', 'Series', 'Reps', 'Peso', 'RPE', 'RIR']
                st.dataframe(df_show, use_container_width=True, hide_index=True)
            else:
                st.info("Sin entrenamientos esta semana")
        else:
            st.info("Sin historial")
