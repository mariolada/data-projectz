"""
Vista Entrenamiento - Entrada de ejercicios estilo Excel.
"""
import streamlit as st
import pandas as pd
import datetime
from pathlib import Path

from ui.components import render_section_title
from ui.loader import loading

TRAINING_CSV_PATH = Path("data/raw/training.csv")


def get_empty_row(date: datetime.date) -> dict:
    """Retorna una fila vacía con valores por defecto."""
    return {
        "date": date,
        "exercise": "",
        "sets": 3,
        "reps": 8,
        "weight": 0.0,
        "rpe": 7.0,
        "rir": 2.0
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
    
    # === TABLA EXCEL ===
    st.markdown("### Ejercicios")
    
    # Obtener ejercicios guardados
    df_hist = load_existing_training()
    ejercicios_guardados = []
    if not df_hist.empty and 'exercise' in df_hist.columns:
        ejercicios_guardados = sorted(df_hist['exercise'].dropna().unique().tolist())
    
    # Añadir rápido desde historial
    if ejercicios_guardados:
        col_add, col_btn = st.columns([4, 1])
        with col_add:
            ejercicio_rapido = st.selectbox(
                "Añadir ejercicio guardado",
                options=[""] + ejercicios_guardados,
                key="ejercicio_rapido",
                label_visibility="collapsed",
                placeholder="⚡ Añadir ejercicio guardado..."
            )
        with col_btn:
            if st.button("➕", key="btn_add_rapido", help="Añadir a la tabla"):
                if ejercicio_rapido:
                    new_row = pd.DataFrame([get_empty_row(selected_date)])
                    new_row['exercise'] = ejercicio_rapido
                    st.session_state.training_data = pd.concat(
                        [st.session_state.training_data, new_row], 
                        ignore_index=True
                    )
                    st.rerun()
    
    st.caption("O escribe directamente en la tabla (puedes añadir ejercicios nuevos)")
    
    column_config = {
        "date": None,
        "exercise": st.column_config.TextColumn(
            "Ejercicio",
            help="Escribe cualquier nombre de ejercicio",
            required=True,
            width="large"
        ),
        "sets": st.column_config.NumberColumn(
            "Series", min_value=1, max_value=20, step=1, default=3
        ),
        "reps": st.column_config.NumberColumn(
            "Reps", min_value=1, max_value=50, step=1, default=8
        ),
        "weight": st.column_config.NumberColumn(
            "Peso (kg)", min_value=0.0, max_value=500.0, step=2.5, format="%.1f"
        ),
        "rpe": st.column_config.NumberColumn(
            "RPE", min_value=1.0, max_value=10.0, step=0.5, default=7.0
        ),
        "rir": st.column_config.NumberColumn(
            "RIR", min_value=0.0, max_value=5.0, step=0.5, default=2.0
        )
    }
    
    edited_df = st.data_editor(
        st.session_state.training_data,
        column_config=column_config,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        key="training_editor"
    )
    
    st.session_state.training_data = edited_df
    
    # === GUARDAR ===
    st.markdown("---")
    
    df_to_save = edited_df.copy()
    df_to_save['date'] = selected_date
    df_to_save = df_to_save[df_to_save['exercise'].notna() & (df_to_save['exercise'] != '')]
    
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
