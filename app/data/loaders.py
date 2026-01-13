"""
Data loaders: Funciones para cargar CSVs, JSON y guardar datos.
"""
import streamlit as st
import pandas as pd
import json
from pathlib import Path


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
    """Carga el perfil personalizado del usuario desde JSON."""
    p = Path(profile_path)
    default_profile = {
        'archetype': {'archetype': 'unknown', 'confidence': 0, 'reason': ''},
        'adjustment_factors': {
            'sleep_weight': 0.25,
            'performance_weight': 0.25,
            'fatigue_sensitivity': 1.0,
            'stress_sensitivity': 1.0,
            'recovery_speed': 1.0,
            'sleep_responsive': True,
        },
        'sleep_responsiveness': {},
        'insights': [],
        'data_quality': {},
    }

    if not p.exists():
        return default_profile
    try:
        with p.open('r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception:
        return default_profile


def load_daily_exercise_for_date(path, selected_date):
    """Carga ejercicios del día seleccionado desde daily_exercise.csv."""
    try:
        df = load_csv(path)
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df[df['date'] == selected_date].sort_values('volume', ascending=False)
    except:
        return pd.DataFrame()


def save_mood_to_csv(date, sleep_hours, sleep_quality, fatigue, soreness, stress, motivation, pain_flag, pain_location, readiness):
    """Guarda los datos del "Modo Hoy" a un CSV de histórico (para persistencia manual)."""
    mood_data = {
        'date': [date],
        'sleep_hours': [sleep_hours],
        'sleep_quality': [sleep_quality],
        'fatigue': [fatigue],
        'soreness': [soreness],
        'stress': [stress],
        'motivation': [motivation],
        'pain_flag': [pain_flag],
        'pain_location': [pain_location if pain_location else '—'],
        'readiness_instant': [readiness]
    }
    
    df_mood = pd.DataFrame(mood_data)
    mood_path = Path("data/processed/mood_daily.csv")
    
    # Si existe, append; si no, crea
    if mood_path.exists():
        df_existing = pd.read_csv(mood_path)
        df_mood = pd.concat([df_existing, df_mood], ignore_index=True)
    
    df_mood.to_csv(mood_path, index=False)
    return True


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
