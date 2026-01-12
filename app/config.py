"""
Configuración global y constantes de la aplicación.
"""

# ===== PATHS =====
DATA_DIR = "data/processed"
DAILY_PATH = f"{DATA_DIR}/daily.csv"
RECOMMENDATIONS_PATH = f"{DATA_DIR}/recommendations_daily.csv"
EXERCISES_PATH = f"{DATA_DIR}/daily_exercise.csv"
WEEKLY_PATH = f"{DATA_DIR}/weekly.csv"
USER_PROFILE_PATH = f"{DATA_DIR}/user_profile.json"

# ===== COLORS =====
COLORS = {
    "bg": "#07090f",
    "panel": "#0f1420",
    "panel_2": "#111827",
    "purple": "#B266FF",
    "green": "#00D084",
    "aqua": "#4ECDC4",
    "coral": "#FF6B6B",
    "amber": "#FFB81C",
    "text": "#E0E0E0",
    "muted": "#9CA3AF",
}

# ===== READINESS ZONES =====
READINESS_ZONES = {
    "HIGH": {"min": 75, "name": "Alta", "emoji": "🟢", "color": "#00D084"},
    "MEDIUM": {"min": 55, "name": "Media", "emoji": "🟡", "color": "#FFB81C"},
    "LOW": {"min": 0, "name": "Baja", "emoji": "🔴", "color": "#FF4444"},
}

# ===== DEFAULTS =====
DEFAULT_READINESS_WEIGHTS = {
    "sleep": 0.25,
    "performance": 0.25,
    "acwr": 0.15,
    "fatigue": 0.10,
    "perceived": 0.25,
}

# ===== FORM OPTIONS =====
GOALS = ["Fuerza", "Hipertrofia", "Resistencia", "Velocidad/Potencia", "General"]
NAPS = [0, 20, 45, 90]
TIME_AVAILABLE = [30, 45, 60, 75, 90, 120]

# ===== LABELS =====
PAGE_TITLE = "Trainer — Readiness"
SIDEBAR_TITLE = "Adventure Mode"
