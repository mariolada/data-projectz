"""
Módulo de ciclo menstrual para ajuste de readiness en atletas mujeres.

Basado en evidencia científica sobre variabilidad hormonal y rendimiento deportivo.
La progesterona y estrógeno afectan fatiga, energía y recuperación.
"""
from typing import Dict, Tuple, Any, Optional
import numpy as np


def get_menstrual_cycle_phase(day_of_cycle: int) -> Tuple[str, str]:
    """
    Determina la fase del ciclo menstrual basado en el día (1-28).
    
    Args:
        day_of_cycle: Día del ciclo (1-28)
    
    Returns:
        (phase_name, description)
    """
    day_of_cycle = max(1, min(28, int(day_of_cycle)))
    
    if 1 <= day_of_cycle <= 5:
        return "Menstrual", "Fase menstrual (sangrado)"
    elif 6 <= day_of_cycle <= 14:
        return "Folicular", "Fase folicular (estrógeno alto)"
    elif 15 <= day_of_cycle <= 15:
        return "Ovulación", "Ovulación (pico hormonal)"
    elif 16 <= day_of_cycle <= 21:
        return "Lútea temprana", "Fase lútea temprana"
    else:  # 22-28
        return "Lútea tardía", "Fase lútea tardía (mayor fatiga, recuperación lenta)"


def calculate_menstrual_cycle_adjustment(
    day_of_cycle: int,
    symptoms: Dict[str, int] = None
) -> Dict[str, Any]:
    """
    Calcula ajustes al readiness basados en fase del ciclo y síntomas.
    
    Args:
        day_of_cycle: Día actual del ciclo (1-28)
        symptoms: Dict con 'cramping' (0-5), 'mood' (0-10), 'bloating' (0-5)
    
    Returns:
        Dict con ajustes y notas para el readiness
    """
    if symptoms is None:
        symptoms = {'cramping': 0, 'mood': 5, 'bloating': 0}
    
    phase, phase_desc = get_menstrual_cycle_phase(day_of_cycle)
    
    # Baselines de fase (factores multiplicadores del readiness)
    phase_factors = {
        'Menstrual': {
            'energy_factor': 0.85,      # -15% energía
            'recovery_factor': 0.90,    # -10% recuperación
            'fatigue_sensitivity': 1.25, # +25% sensibilidad a fatiga
            'description': 'Energía reducida, sensibilidad aumentada'
        },
        'Folicular': {
            'energy_factor': 1.10,      # +10% energía
            'recovery_factor': 1.05,    # +5% recuperación
            'fatigue_sensitivity': 0.85, # -15% sensibilidad a fatiga
            'description': 'Mejor energía y tolerancia'
        },
        'Ovulación': {
            'energy_factor': 1.15,      # +15% energía máxima
            'recovery_factor': 1.02,    # +2% recuperación
            'fatigue_sensitivity': 0.80, # -20% sensibilidad a fatiga
            'description': 'Pico de energía, máxima tolerancia'
        },
        'Lútea temprana': {
            'energy_factor': 1.05,      # +5% energía
            'recovery_factor': 1.00,    # Neutral
            'fatigue_sensitivity': 1.00, # Neutral
            'description': 'Energía buena, recuperación estable'
        },
        'Lútea tardía': {
            'energy_factor': 0.90,      # -10% energía
            'recovery_factor': 0.85,    # -15% recuperación
            'fatigue_sensitivity': 1.35, # +35% sensibilidad a fatiga
            'description': 'Fatiga aumentada, recuperación lenta'
        }
    }
    
    base_factors = phase_factors.get(phase, phase_factors['Folicular'])
    
    # SÍNTOMAS: ajustes finos
    symptom_adjustment = {
        'energy_factor': 1.0,
        'recovery_factor': 1.0,
        'fatigue_sensitivity': 1.0
    }
    
    cramping = symptoms.get('cramping', 0)
    bloating = symptoms.get('bloating', 0)
    mood_level = symptoms.get('mood', 5)  # 0=muy deprimida, 10=excelente
    
    # Cólicos afectan energía y tolerancia
    if cramping > 0:
        symptom_adjustment['energy_factor'] *= (1 - (cramping / 5) * 0.15)
        symptom_adjustment['recovery_factor'] *= (1 - (cramping / 5) * 0.10)
    
    # Hinchazón reduce sensación de bienestar pero no física
    if bloating > 0:
        symptom_adjustment['fatigue_sensitivity'] *= (1 + (bloating / 5) * 0.20)
    
    # Humor afecta percepción de readiness
    mood_factor = mood_level / 5  # Normalizar 0-2
    
    # Combinar factores
    final_factors = {
        'energy_factor': base_factors['energy_factor'] * symptom_adjustment['energy_factor'],
        'recovery_factor': base_factors['recovery_factor'] * symptom_adjustment['recovery_factor'],
        'fatigue_sensitivity': base_factors['fatigue_sensitivity'] * symptom_adjustment['fatigue_sensitivity'],
        'mood_factor': mood_factor
    }
    
    # Penalties and recommendations
    recommendations = []
    if phase in ['Menstrual', 'Lútea tardía']:
        if cramping > 2:
            recommendations.append("💊 Considera medicación para cólicos si los necesitas")
        recommendations.append("🔄 Prioriza recuperación activa sobre trabajo duro")
        recommendations.append("💤 Aumenta horas de sueño 30-60 minutos si es posible")
    
    if phase == 'Folicular' or phase == 'Ovulación':
        recommendations.append("💪 Excelente semana para work PRs y volumen")
        recommendations.append("🏋️ Toleras bien la fatiga acumulada")
    
    if bloating > 2:
        recommendations.append("💧 Aumenta hidratación")
        recommendations.append("🧂 Modera sal, especialmente en Lútea tardía")
    
    return {
        'phase': phase,
        'phase_description': phase_desc,
        'day_of_cycle': day_of_cycle,
        'energy_factor': final_factors['energy_factor'],
        'recovery_factor': final_factors['recovery_factor'],
        'fatigue_sensitivity_factor': final_factors['fatigue_sensitivity'],
        'mood_factor': final_factors['mood_factor'],
        'base_description': base_factors['description'],
        'recommendations': recommendations,
        'summary': f"Fase {phase}: {base_factors['description']}"
    }


def adjust_readiness_for_menstrual_cycle(
    readiness_score: int,
    day_of_cycle: int,
    symptoms: Dict[str, int] = None
) -> Dict[str, Any]:
    """
    Ajusta el score de readiness considerando ciclo menstrual.
    
    Args:
        readiness_score: Score original (0-100)
        day_of_cycle: Día del ciclo (1-28)
        symptoms: Dict con síntomas (cramping, mood, bloating)
    
    Returns:
        Dict con score ajustado y explicaciones
    """
    cycle_data = calculate_menstrual_cycle_adjustment(day_of_cycle, symptoms)
    
    # El ajuste no debe cambiar el score más de ±15 puntos
    # Es información COMPLEMENTARIA, no reemplazante
    energy_factor = cycle_data['energy_factor']
    
    # Si hay baja energía, reducir score ligeramente
    # Si hay alta energía, aumentar score ligeramente
    adjustment = (energy_factor - 1.0) * 100  # -15 a +15 puntos aprox
    adjustment = np.clip(adjustment, -15, 15)
    
    adjusted_score = int(readiness_score + adjustment)
    adjusted_score = np.clip(adjusted_score, 0, 100)
    
    return {
        'original_score': readiness_score,
        'menstrual_adjustment': adjustment,
        'adjusted_score': adjusted_score,
        'phase': cycle_data['phase'],
        'phase_description': cycle_data['phase_description'],
        'energy_factor': cycle_data['energy_factor'],
        'recovery_factor': cycle_data['recovery_factor'],
        'mood_factor': cycle_data['mood_factor'],
        'recommendations': cycle_data['recommendations'],
        'explanation': f"Tu readiness se ajusta considerando que estás en fase {cycle_data['phase']}. "
                      f"Energía: {cycle_data['energy_factor']:.0%} | "
                      f"Recuperación: {cycle_data['recovery_factor']:.0%}"
    }


def get_menstrual_questionnaire_fields() -> Dict[str, Any]:
    """Retorna los campos del cuestionario para ciclo menstrual."""
    return {
        'day_of_cycle': {
            'type': 'number',
            'min': 1,
            'max': 28,
            'label': '¿Qué día de tu ciclo estás? (1-28)',
            'help': 'Día 1 = primer día de sangrado. Si no lo sabes, estima.',
            'required': True
        },
        'cramping': {
            'type': 'slider',
            'min': 0,
            'max': 5,
            'label': '¿Intensidad de cólicos? (0=nada, 5=muy fuertes)',
            'required': True
        },
        'bloating': {
            'type': 'slider',
            'min': 0,
            'max': 5,
            'label': '¿Hinchazón abdominal? (0=nada, 5=mucha)',
            'required': True
        },
        'mood': {
            'type': 'slider',
            'min': 0,
            'max': 10,
            'label': '¿Cómo está tu humor? (0=muy bajo, 10=excelente)',
            'required': True
        },
        'flow': {
            'type': 'select',
            'options': ['Menstrual', 'No menstrual'],
            'label': '¿Estás menstruando hoy?',
            'required': True
        }
    }
