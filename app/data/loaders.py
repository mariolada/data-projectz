"""
Data loaders: Funciones para cargar CSVs, JSON y guardar datos.
"""
import streamlit as st
import pandas as pd
import json
from pathlib import Path

from database.connection import get_db
from database.repositories import MoodRepository, UserProfileRepository


def _current_user_id() -> str:
    return (
        st.session_state.get("user_sub")
        or st.session_state.get("user_email")
        or "default_user"
    )


@st.cache_data
def load_csv(path: str):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No existe: {path}")
    df = pd.read_csv(p)
    # normalize date column to Timestamp
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    return df


@st.cache_data(ttl=60)  # Cache expira cada 60 segundos para reflejar cambios
def load_user_profile(profile_path: str = "data/processed/user_profile.json"):
    """Carga el perfil del usuario. Preferir DB; fallback a JSON si existe y DB vacío."""
    # Primero intentar cargar desde DB
    db = next(get_db())
    user_id = _current_user_id()
    try:
        profile_db = UserProfileRepository.get(db, user_id=user_id)
        # Si el perfil en DB parece vacío y existe JSON, usar JSON (migración implícita)
        # Heurística: si archetype es 'unknown' y existe el archivo JSON, leerlo
        p = Path(profile_path)
        if profile_db.get('archetype', {}).get('archetype') == 'unknown' and p.exists():
            try:
                with p.open('r', encoding='utf-8') as f:
                    data_file = json.load(f)
                # Guardar en DB para futuras lecturas
                UserProfileRepository.create_or_update(db, data_file, user_id=user_id)
                return data_file
            except Exception:
                return profile_db
        return profile_db
    finally:
        db.close()


def load_daily_exercise_for_date(path, selected_date):
    """Carga ejercicios del día seleccionado desde daily_exercise.csv."""
    try:
        df = load_csv(path)
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df[df['date'] == selected_date].sort_values('volume', ascending=False)
    except:
        return pd.DataFrame()


def save_mood_to_csv(date, sleep_hours, sleep_quality, fatigue, soreness, stress, motivation, pain_flag, pain_location, readiness):
    """Guarda los datos del "Modo Hoy" en la base de datos."""
    db = next(get_db())
    try:
        user_id = _current_user_id()
        mood_data = {
            'date': date,
            'sleep_hours': float(sleep_hours) if sleep_hours is not None else None,
            'sleep_quality': int(sleep_quality) if sleep_quality is not None else None,
            'fatigue': int(fatigue) if fatigue is not None else None,
            'soreness': int(soreness) if soreness is not None else None,
            'stress': int(stress) if stress is not None else None,
            'motivation': int(motivation) if motivation is not None else None,
            'pain_flag': int(pain_flag) if pain_flag is not None else 0,
            'pain_location': str(pain_location) if pain_location else '',
            'readiness': float(readiness) if readiness is not None else None
        }
        
        MoodRepository.create_or_update(db, mood_data, user_id=user_id)
        return True
    except Exception as e:
        print(f"Error guardando mood: {e}")
        return False
    finally:
        db.close()


def load_mood_by_date(date):
    """Carga el mood de una fecha específica desde la base de datos."""
    db = next(get_db())
    try:
        return MoodRepository.get_by_date(db, date, user_id=_current_user_id())
    finally:
        db.close()


def load_all_mood():
    """Carga todos los registros de mood desde la base de datos."""
    db = next(get_db())
    try:
        return MoodRepository.get_all(db, user_id=_current_user_id())
    finally:
        db.close()


@st.cache_data(ttl=60)
def load_neural_overload_flags(flags_path: str = "data/processed/neural_overload_flags.json"):
    """
    Carga los flags de sobrecarga neuromuscular/SNC desde JSON.
    Retorna estructura con 'summary', 'flags', y 'advanced_lifts'.
    """
    p = Path(flags_path)
    default = {
        'summary': {
            'n_key_lifts_analyzed': 0,
            'n_flags_detected': 0,
            'total_overload_score': 0,
            'primary_cause': None,
            'flags_by_type': {},
            'affected_exercises': []
        },
        'flags': [],
        'advanced_lifts': {}
    }
    
    if not p.exists():
        return default
    
    try:
        with p.open('r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception:
        return default
