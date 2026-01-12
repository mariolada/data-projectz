"""Data formatters and helpers."""
import pandas as pd


def get_readiness_zone(readiness):
    """Retorna (zona, emoji, color) basado en readiness score."""
    if pd.isna(readiness):
        return ("Desconocida", "❓", "#999999")
    readiness = float(readiness)
    if readiness >= 75:
        return ("Alta", "🟢", "#00D084")
    elif readiness >= 55:
        return ("Media", "🟡", "#FFB81C")
    else:
        return ("Muy baja", "🔴", "#FF4444")


def get_days_until_acwr(df_daily, selected_date):
    """Calcula cuántos días de histórico hay hasta la fecha seleccionada."""
    filtered = df_daily[df_daily['date'] <= selected_date]
    return len(filtered)


def get_confidence_level(df_daily, selected_date):
    """Retorna nivel de confianza basado en días de histórico."""
    filtered = df_daily[df_daily['date'] <= selected_date].copy()
    days_available = len(filtered)
    if days_available < 7:
        return "Baja (pocos datos)", "⚠️"
    elif days_available < 28:
        return f"Media ({days_available} días)", "ℹ️"
    else:
        return "Alta (>28 días)", "✅"


def format_acwr_display(acwr, days_available):
    """Formatea ACWR: muestra valor o 'Pendiente (x/28 días)'."""
    if pd.isna(acwr) or acwr == '—':
        return f"Pendiente ({days_available}/28 días)"
    return f"{round(float(acwr), 3)}"


def format_reason_codes(reason_codes_str):
    """Convierte string de reason codes a lista legible."""
    if pd.isna(reason_codes_str) or reason_codes_str == '':
        return []
    codes = str(reason_codes_str).split('|')
    code_map = {
        'LOW_SLEEP': '😴 Sueño insuficiente',
        'HIGH_ACWR': '📈 Carga aguda muy alta',
        'PERF_DROP': '📉 Rendimiento en caída',
        'HIGH_EFFORT': '💪 Esfuerzo muy alto',
        'FATIGA': '⚠️ Fatiga detectada'
    }
    return [code_map.get(c.strip(), c.strip()) for c in codes if c.strip()]
