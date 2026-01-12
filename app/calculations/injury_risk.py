"""
Cálculo de Riesgo de Lesión
Módulo: calculations/injury_risk.py
"""
# Importar la función base desde src
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from src.personalization_engine import calculate_injury_risk_score
except ImportError:
    # Fallback si src no está disponible: definir versión mínima
    def calculate_injury_risk_score(readiness_score, acwr, sleep_hours, performance_index, effort_level,
                                    pain_flag=False, baselines=None, days_high_strain=0):
        score = 0
        factors = []
        if readiness_score < 55:
            score += 15
        if acwr > 1.5:
            score += 20
        if sleep_hours < 6:
            score += 12
        if pain_flag:
            score += 15
        return {
            'score': min(score, 100),
            'factors': factors or ['Métricas dentro de rango'],
            'confidence': 0.85
        }


def calculate_injury_risk_score_v2(
    readiness_score, acwr, sleep_hours, performance_index, effort_level,
    pain_flag=False, pain_severity=0, stiffness=0, sick_flag=False, 
    last_hard=False, baselines=None, days_high_strain=0
):
    """
    Versión mejorada con factores adicionales: pain_severity, stiffness, sick_flag.
    
    Parámetros:
    -----------
    readiness_score : int
        Score de readiness (0–100)
    acwr : float
        Acute-to-Chronic Workload Ratio
    sleep_hours : float
        Horas de sueño
    performance_index : float
        Índice de performance
    effort_level : int
        Esfuerzo último entreno (1–10)
    pain_flag : bool
        ¿Hay dolor? Default: False
    pain_severity : int
        Severidad del dolor (0–10). Default: 0
    stiffness : int
        Rigidez articular (0–10). Default: 0
    sick_flag : bool
        ¿Enfermo? Default: False
    last_hard : bool
        ¿Último entreno muy exigente hace <48h? Default: False
    baselines : dict, optional
        Baseline metrics
    days_high_strain : int
        Días con alta carga. Default: 0
    
    Retorna:
    --------
    dict con keys:
        - 'risk_level': str ('high', 'medium', 'low')
        - 'score': int (0–100)
        - 'emoji': str ('🔴', '🟡', '🟢')
        - 'factors': list[str]
        - 'confidence': float
        - 'action': str (recomendación accionable)
    """
    
    # Usar función base
    base_risk = calculate_injury_risk_score(
        readiness_score, acwr, sleep_hours, performance_index, effort_level,
        pain_flag, baselines, days_high_strain
    )
    
    # Añadir factores nuevos
    extra_score = 0
    extra_factors = []
    
    # Pain severity (más severo = más riesgo)
    if pain_severity >= 7:
        extra_score += 15
        extra_factors.append(f'Dolor severo ({pain_severity}/10)')
    elif pain_severity >= 5:
        extra_score += 8
        extra_factors.append(f'Dolor moderado ({pain_severity}/10)')
    
    # Stiffness (rigidez alta = movilidad limitada)
    if stiffness >= 7:
        extra_score += 10
        extra_factors.append(f'Rigidez articular alta ({stiffness}/10)')
    
    # Sick flag (enfermo = riesgo altísimo)
    if sick_flag:
        extra_score += 25
        extra_factors.append('⚠️ Estado de enfermedad detectado')
    
    # Last hard session (fatiga acumulada)
    if last_hard:
        extra_score += 8
        extra_factors.append('Último entreno muy exigente (48h)')
    
    # Combinar
    new_score = min(base_risk['score'] + extra_score, 100)
    
    # Re-clasificar
    if new_score >= 60:
        level = 'high'
        emoji = '🔴'
        action = 'DELOAD OBLIGATORIO. Reduce volumen -30%, evita máximos.'
    elif new_score >= 35:
        level = 'medium'
        emoji = '🟡'
        action = 'Precaución. Entrena pero sin buscar máximos. Foco en técnica.'
    else:
        level = 'low'
        emoji = '🟢'
        action = 'Bajo riesgo. Puedes entrenar normal.'
    
    return {
        'risk_level': level,
        'score': new_score,
        'emoji': emoji,
        'factors': base_risk['factors'] + extra_factors,
        'confidence': base_risk['confidence'],
        'action': action
    }
