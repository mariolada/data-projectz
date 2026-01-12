"""
Cálculo de Readiness (Disposición para Entrenar)
Módulo: calculations/readiness_calc.py
"""
import numpy as np


def calculate_readiness_from_inputs_v2(
    sleep_hours, sleep_quality, fatigue, soreness, stress, motivation, pain_flag,
    nap_mins=0, sleep_disruptions=False, energy=7, stiffness=2, 
    caffeine=0, alcohol=False, sick_flag=False, perceived_readiness=None
):
    """
    Versión mejorada: considera nap, energía, rigidez, cafeína, alcohol, enfermo, y PERCEPCIÓN PERSONAL.
    
    Parámetros:
    -----------
    sleep_hours : float
        Horas de sueño la noche anterior (0–12)
    sleep_quality : int
        Calidad del sueño (1=pésimo, 5=excelente)
    fatigue : int
        Fatiga general (0=nada, 10=extrema)
    soreness : int
        Agujetas/dolor muscular (0=nada, 10=insoportable)
    stress : int
        Estrés (0=relajado, 10=estresadísimo)
    motivation : int
        Motivación (0=nada, 10=altísima)
    pain_flag : bool
        ¿Hay dolor localizado?
    nap_mins : int, optional
        Duración de siesta (0, 20, 45, 90 minutos). Default: 0
    sleep_disruptions : bool, optional
        ¿Sueño fragmentado? Default: False
    energy : int, optional
        Nivel de energía (0–10). Default: 7
    stiffness : int, optional
        Rigidez articular (0–10). Default: 2
    caffeine : int, optional
        Consumo de cafeína (0=nada, 1=bajo, 2=moderado, 3=alto). Default: 0
    alcohol : bool, optional
        ¿Consumió alcohol ayer? Default: False
    sick_flag : bool, optional
        ¿Enfermo/resfriado/infección? Default: False
    perceived_readiness : int, optional
        Cómo te sientes SUBJETIVAMENTE (0–10). Sobreescribe métricas si presente. Default: None
    
    Retorna:
    --------
    int : Readiness score (0–100)
        - 80–100: Excelente, push day
        - 55–79: Bueno, sesión normal
        - 35–54: Moderado, reduce volumen
        - 0–34: Muy bajo, deload/descanso
    
    Detalles del Algoritmo:
    ----------------------
    Si perceived_readiness está presente (usuario dijo cómo se siente):
        - Percepción personal = 25% del score (el factor más importante)
        - Otros factores = 75% del score total
    
    Si no hay percepción:
        - Sueño = ~40%
        - Estado físico = ~35%
        - Motivación = ~15%
    
    Penalizaciones graves:
        - Dolor localizado: -25 puntos
        - Enfermedad: -35 puntos
        - Cafeína enmascarando fatiga: -8 puntos
    """
    
    # === PERCEPCIÓN PERSONAL (25% si está presente) ===
    # Este es el factor clave: cómo TE SIENTES realmente, puede sobreescribir métricas objetivas
    if perceived_readiness is not None:
        perceived_score = perceived_readiness / 10
        perceived_component = 0.25 * perceived_score
        # Reducimos el peso de otros componentes proporcionalmente
        base_weight_multiplier = 0.75  # Los demás componentes suman 75%
    else:
        perceived_component = 0
        base_weight_multiplier = 1.0  # Si no hay percepción, pesos originales
    
    # === RECUPERACIÓN (30% del score si hay percepción, 40% si no) ===
    # Sueño base
    sleep_hours_score = np.clip((sleep_hours - 6.0) / (7.5 - 6.0), 0, 1)
    sleep_quality_score = (sleep_quality - 1) / 4
    
    # Bonus siesta (20-90 min suman)
    nap_bonus = 0
    if nap_mins == 20:
        nap_bonus = 0.05
    elif nap_mins == 45:
        nap_bonus = 0.08
    elif nap_mins == 90:
        nap_bonus = 0.10
    
    # Penalización sueño fragmentado
    disruption_penalty = 0.15 if sleep_disruptions else 0
    
    # Penalización alcohol (afecta recuperación)
    alcohol_penalty = 0.20 if alcohol else 0
    
    sleep_component = base_weight_multiplier * (0.25 * sleep_hours_score + 0.15 * sleep_quality_score + nap_bonus 
                      - disruption_penalty - alcohol_penalty)
    
    # === ESTADO (26% del score si hay percepción, 35% si no) ===
    fatigue_score = 1 - (fatigue / 10)
    stress_score = 1 - (stress / 10)
    energy_score = energy / 10
    soreness_score = 1 - (soreness / 10)
    
    # Rigidez penaliza movilidad (importante para sesiones técnicas)
    stiffness_penalty = (stiffness / 10) * 0.10
    
    state_component = base_weight_multiplier * (0.12 * fatigue_score + 0.08 * stress_score + 
                      0.10 * energy_score + 0.05 * soreness_score - stiffness_penalty)
    
    # === MOTIVACIÓN (11% del score si hay percepción, 15% si no) ===
    motivation_score = motivation / 10
    motivation_component = base_weight_multiplier * 0.15 * motivation_score
    
    # === PENALIZACIONES FLAGS ===
    pain_penalty = 0.25 if pain_flag else 0
    sick_penalty = 0.35 if sick_flag else 0  # Enfermo es muy grave
    
    # Cafeína: si es alta, puede estar enmascarando fatiga
    caffeine_mask = 0
    if caffeine >= 2 and fatigue >= 6:
        caffeine_mask = 0.08  # "te sientes bien pero es cafeína"
    
    # === FÓRMULA FINAL ===
    readiness_0_1 = (perceived_component + sleep_component + state_component + motivation_component 
                    - pain_penalty - sick_penalty - caffeine_mask)
    
    readiness_0_1 = np.clip(readiness_0_1, 0, 1)
    readiness_score = int(round(readiness_0_1 * 100))
    
    return readiness_score


def calculate_readiness_from_inputs(
    sleep_hours, sleep_quality, fatigue, soreness, stress, motivation, pain_flag
):
    """
    Versión original (sin nap, sin perceived, etc.).
    Se mantiene por compatibilidad.
    
    Retorna int: Readiness score (0–100)
    """
    # Normalizar inputs a [0, 1]
    sleep_score = np.clip((sleep_hours - 6.0) / (8.0 - 6.0), 0, 1)
    quality_score = (sleep_quality - 1) / 4
    fatigue_score = 1 - (fatigue / 10)
    soreness_score = 1 - (soreness / 10)
    stress_score = 1 - (stress / 10)
    motivation_score = motivation / 10
    pain_score = 0 if pain_flag else 0.2
    
    # Pesos
    readiness = (
        0.25 * sleep_score +
        0.15 * quality_score +
        0.15 * fatigue_score +
        0.10 * soreness_score +
        0.10 * stress_score +
        0.15 * motivation_score +
        0.10 * pain_score
    )
    
    readiness = np.clip(readiness, 0, 1)
    return int(round(readiness * 100))
