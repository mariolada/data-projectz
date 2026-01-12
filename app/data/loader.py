"""Data loading and caching."""
import json
import pandas as pd
from pathlib import Path


@staticmethod
def load_csv(path: str):
    """Carga CSV y normaliza fecha a Timestamp."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"No existe: {path}")
    df = pd.read_csv(p)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    return df


def load_user_profile(profile_path: str = "data/processed/user_profile.json"):
    """Carga el perfil personalizado del usuario desde JSON."""
    p = Path(profile_path)
    if not p.exists():
        return {
            'archetype': {'archetype': 'unknown', 'confidence': 0},
            'adjustment_factors': {
                'sleep_weight': 0.25,
                'performance_weight': 0.25,
                'acwr_weight': 0.15,
                'fatigue_sensitivity': 1.0,
                'recovery_speed': 1.0
            },
            'sleep_responsiveness': {'sleep_responsive': None},
            'insights': ['No hay datos suficientes aún para personalización'],
            'data_quality': {'total_days': 0}
        }
    try:
        with open(p, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}
