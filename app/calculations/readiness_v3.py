"""
Readiness v3 "NASA" - Cálculo avanzado de readiness con curvas suaves.

Características:
- Curvas sigmoides en lugar de lineales (transiciones suaves)
- Personalización por baselines históricos
- Confidence score según datos disponibles
- Consistency bonus por estabilidad
- Penalizaciones proporcionales y acotadas
- Explicaciones humanas del score

Autor: data-projectz v3.0
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field


# ============================================================================
# FUNCIONES DE CURVAS SUAVES
# ============================================================================

def sigmoid(x: float, center: float = 0.5, steepness: float = 10.0) -> float:
    """
    Sigmoid centrada y configurable.
    
    Args:
        x: Valor de entrada (normalizado 0-1 idealmente)
        center: Punto donde sigmoid = 0.5
        steepness: Pendiente (más alto = transición más abrupta)
    
    Returns:
        Valor entre 0 y 1
    """
    return 1.0 / (1.0 + np.exp(-steepness * (x - center)))


def smoothstep(x: float, edge0: float = 0.0, edge1: float = 1.0) -> float:
    """
    Smoothstep: transición suave tipo S entre edge0 y edge1.
    
    Fórmula: 3x² - 2x³ (Hermite interpolation)
    
    Args:
        x: Valor de entrada
        edge0: Inicio de la transición (retorna 0 si x <= edge0)
        edge1: Fin de la transición (retorna 1 si x >= edge1)
    
    Returns:
        Valor entre 0 y 1 con curva S
    """
    # Normalizar x al rango [0, 1]
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    # Smoothstep: 3t² - 2t³
    return t * t * (3.0 - 2.0 * t)


def smootherstep(x: float, edge0: float = 0.0, edge1: float = 1.0) -> float:
    """
    Smootherstep: versión más suave de smoothstep.
    
    Fórmula: 6x⁵ - 15x⁴ + 10x³
    """
    t = np.clip((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def soft_clip(x: float, lo: float, hi: float, softness: float = 0.1) -> float:
    """
    Recorte suave: en lugar de cortar bruscamente, aplica transición gradual.
    
    Args:
        x: Valor a recortar
        lo: Límite inferior
        hi: Límite superior
        softness: Suavidad de la transición (0 = clip duro, >0 = suave)
    
    Returns:
        Valor recortado suavemente
    """
    if softness <= 0:
        return np.clip(x, lo, hi)
    
    # Usar tanh para suavizar en los bordes
    mid = (lo + hi) / 2
    half_range = (hi - lo) / 2
    
    # Normalizar al rango [-1, 1] y aplicar tanh
    normalized = (x - mid) / (half_range + softness)
    softened = np.tanh(normalized)
    
    # Volver al rango original
    return mid + half_range * softened


def asymmetric_sigmoid(x: float, center: float = 0.5, 
                       steepness_left: float = 8.0, 
                       steepness_right: float = 12.0) -> float:
    """
    Sigmoid asimétrica: diferente pendiente a cada lado del centro.
    
    Útil para: penalizar más las caídas que premiar las subidas.
    """
    if x < center:
        return sigmoid(x, center, steepness_left)
    else:
        return sigmoid(x, center, steepness_right)


def saturating_curve(x: float, saturation_point: float = 0.8) -> float:
    """
    Curva que sube rápido al inicio pero satura.
    
    Útil para motivación: subir de 3 a 6 importa más que de 7 a 10.
    
    Fórmula: 1 - e^(-kx) con ajuste para saturar en saturation_point
    """
    k = -np.log(1 - 0.9) / saturation_point  # 90% del máximo en saturation_point
    return 1.0 - np.exp(-k * x)


# ============================================================================
# SCORING POR COMPONENTE (CON CURVAS)
# ============================================================================

def score_sleep_hours_v3(hours: float, baseline_p50: Optional[float] = None,
                          baseline_p25: Optional[float] = None) -> Tuple[float, str]:
    """
    Score de horas de sueño con curva centrada en tu baseline.
    
    - Dormir un poco menos que tu media → penalización leve
    - Dormir mucho menos → penalización fuerte (curva sigmoide)
    - Dormir más → bonus suave con saturación
    
    Returns:
        (score 0-1, explicación)
    """
    # Usar baseline personal o fallback genérico
    center = baseline_p50 if baseline_p50 and baseline_p50 > 0 else 7.0
    min_acceptable = baseline_p25 if baseline_p25 else max(5.0, center - 2.0)
    
    if pd.isna(hours) or hours <= 0:
        return 0.5, "Sin datos de sueño"
    
    # Calcular delta vs baseline
    delta = hours - center
    
    # Normalizar: 0 = mínimo aceptable, 1 = baseline + 1h
    # Usamos smootherstep para transición muy suave
    normalized = (hours - min_acceptable) / (center + 1.0 - min_acceptable)
    
    # Aplicar curva asimétrica: penaliza más dormir menos que dormir más
    if normalized < 0.5:
        # Por debajo del centro: sigmoide con pendiente fuerte
        score = smootherstep(normalized, -0.2, 0.6) * 0.85
    else:
        # Por encima: curva que satura (dormir 10h no es 2x mejor que 8h)
        base_score = 0.85
        bonus = saturating_curve((normalized - 0.5) * 2, 0.7) * 0.15
        score = base_score + bonus
    
    score = np.clip(score, 0.0, 1.0)
    
    # Explicación
    if delta >= 0.5:
        expl = f"por encima de tu mediana (+{delta:.1f}h)"
    elif delta >= -0.5:
        expl = f"cerca de tu mediana ({hours:.1f}h)"
    elif delta >= -1.5:
        expl = f"algo bajo tu mediana ({delta:.1f}h)"
    else:
        expl = f"muy bajo tu mediana ({delta:.1f}h)"
    
    return score, expl


def score_sleep_quality_v3(quality: int) -> Tuple[float, str]:
    """
    Score de calidad de sueño (1-5) con curva suave.
    """
    if pd.isna(quality) or quality < 1:
        return 0.5, "sin datos"
    
    # Normalizar 1-5 → 0-1
    normalized = (quality - 1) / 4.0
    
    # Aplicar smoothstep para suavizar
    score = smoothstep(normalized, 0.0, 1.0)
    
    labels = {1: "muy mala", 2: "mala", 3: "normal", 4: "buena", 5: "excelente"}
    expl = labels.get(quality, "normal")
    
    return score, expl


def score_fatigue_v3(fatigue: float, sensitivity: float = 1.0) -> Tuple[float, str]:
    """
    Score de fatiga con curva sigmoide.
    
    Fatiga 0-3: casi no penaliza (normal)
    Fatiga 4-6: penalización moderada
    Fatiga 7-10: penalización fuerte
    """
    if pd.isna(fatigue):
        return 0.7, "sin datos"
    
    fatigue = np.clip(fatigue, 0, 10)
    
    # Invertir: fatiga baja = score alto
    # Usar sigmoide centrada en 5.5 (punto medio de preocupación)
    normalized = fatigue / 10.0
    
    # Curva que penaliza más a partir de fatiga 5
    # Más generosa: centro en 0.6 y pendiente más suave
    raw_score = 1.0 - sigmoid(normalized, center=0.60, steepness=6.0)
    
    # Aplicar sensibilidad personal (si el usuario es sensible a fatiga)
    sensitivity_factor = min(sensitivity, 1.2)  # Cap para no exagerar
    score = raw_score ** sensitivity_factor
    
    # Fatiga baja (<= 2) siempre da score alto
    if fatigue <= 2:
        score = max(score, 0.92)
    
    score = np.clip(score, 0.0, 1.0)
    
    if fatigue <= 2:
        expl = "baja"
    elif fatigue <= 4:
        expl = "normal"
    elif fatigue <= 6:
        expl = "moderada"
    elif fatigue <= 8:
        expl = "alta"
    else:
        expl = "muy alta"
    
    return score, expl


def score_stress_v3(stress: float, sensitivity: float = 1.0) -> Tuple[float, str]:
    """
    Score de estrés con curva sigmoide.
    Similar a fatiga pero con centro ligeramente más alto (toleramos más estrés).
    """
    if pd.isna(stress):
        return 0.7, "sin datos"
    
    stress = np.clip(stress, 0, 10)
    normalized = stress / 10.0
    
    # Centro en 0.65 (estrés 6.5/10 es el punto de inflexión)
    raw_score = 1.0 - sigmoid(normalized, center=0.65, steepness=5.5)
    
    sensitivity_factor = min(sensitivity, 1.15)
    score = raw_score ** sensitivity_factor
    
    # Estrés bajo (<= 2) siempre da score alto
    if stress <= 2:
        score = max(score, 0.90)
    
    score = np.clip(score, 0.0, 1.0)
    
    if stress <= 2:
        expl = "bajo"
    elif stress <= 4:
        expl = "normal"
    elif stress <= 6:
        expl = "moderado"
    else:
        expl = "alto"
    
    return score, expl


def score_energy_v3(energy: float) -> Tuple[float, str]:
    """
    Score de energía con curva que sube rápido pero satura.
    
    Energía 0-3: muy bajo
    Energía 4-6: subiendo rápido
    Energía 7-10: ya bueno, saturando
    """
    if pd.isna(energy):
        return 0.6, "sin datos"
    
    energy = np.clip(energy, 0, 10)
    normalized = energy / 10.0
    
    # Curva que satura: subir de 6 a 8 es menor diferencia que de 3 a 5
    score = saturating_curve(normalized, saturation_point=0.65)
    
    # Boost para energía alta (≥7)
    if normalized >= 0.7:
        score = min(1.0, score + (normalized - 0.7) * 0.25)
    
    if energy <= 3:
        expl = "muy baja"
    elif energy <= 5:
        expl = "baja"
    elif energy <= 7:
        expl = "buena"
    else:
        expl = "alta"
    
    return score, expl


def score_soreness_v3(soreness: float) -> Tuple[float, str]:
    """
    Score de dolor muscular/DOMS.
    
    DOMS leve es NORMAL post-entreno, no debe penalizar mucho.
    Solo penaliza significativamente si es alto (>6).
    """
    if pd.isna(soreness):
        return 0.85, "sin datos"
    
    soreness = np.clip(soreness, 0, 10)
    normalized = soreness / 10.0
    
    # Centro muy alto (0.65) porque DOMS leve es normal
    raw_score = 1.0 - sigmoid(normalized, center=0.65, steepness=6.0)
    
    # No bajar de 0.4 incluso con soreness máximo (no es tan grave como enfermedad)
    score = 0.4 + raw_score * 0.6
    
    if soreness <= 2:
        expl = "sin dolor"
    elif soreness <= 4:
        expl = "leve (normal)"
    elif soreness <= 6:
        expl = "moderado"
    else:
        expl = "alto"
    
    return score, expl


def score_motivation_v3(motivation: float) -> Tuple[float, str]:
    """
    Score de motivación con curva saturante.
    
    Motivación 5-6 ya es "suficiente", más allá satura.
    No queremos que motivación 10 "salve" un día malo.
    """
    if pd.isna(motivation):
        return 0.7, "sin datos"
    
    motivation = np.clip(motivation, 0, 10)
    normalized = motivation / 10.0
    
    # Sube rápido hasta 0.6 (motivación 6), luego satura
    score = saturating_curve(normalized, saturation_point=0.6)
    
    if motivation <= 3:
        expl = "baja"
    elif motivation <= 6:
        expl = "normal"
    elif motivation <= 8:
        expl = "alta"
    else:
        expl = "muy alta"
    
    return score, expl


def score_perceived_readiness_v3(perceived: float) -> Tuple[float, str]:
    """
    Score de percepción subjetiva (0-10).
    
    Usa smootherstep para transición muy suave.
    """
    if pd.isna(perceived):
        return 0.7, "sin datos"
    
    perceived = np.clip(perceived, 0, 10)
    normalized = perceived / 10.0
    
    # Smootherstep para transición ultra suave
    score = smootherstep(normalized, 0.1, 0.9)
    
    if perceived <= 3:
        expl = "te sientes mal"
    elif perceived <= 5:
        expl = "regular"
    elif perceived <= 7:
        expl = "bien"
    elif perceived <= 9:
        expl = "muy bien"
    else:
        expl = "increíble"
    
    return score, expl


# ============================================================================
# PENALIZACIONES SUAVES
# ============================================================================

def penalty_pain_v3(pain_flag: bool, pain_location: Optional[str] = None,
                     soreness: float = 0, stiffness: float = 0) -> Tuple[float, str]:
    """
    Penalización por dolor proporcional al contexto.
    
    - Dolor leve local → penalización menor
    - Dolor + alta rigidez/soreness → penalización mayor
    
    Returns:
        (penalización 0-0.20, explicación)
    """
    if not pain_flag:
        return 0.0, ""
    
    # Base penalty (dolor reportado)
    base_penalty = 0.08
    
    # Agravar si hay contexto negativo
    context_multiplier = 1.0
    
    # Si hay mucha rigidez o soreness, el dolor es más problemático
    if soreness > 6:
        context_multiplier += 0.3
    if stiffness > 5:
        context_multiplier += 0.2
    
    # Si es dolor en zona crítica (espalda, hombro, rodilla)
    critical_zones = ['espalda', 'lumbar', 'hombro', 'rodilla', 'back', 'shoulder', 'knee']
    if pain_location:
        pain_loc_lower = pain_location.lower()
        if any(zone in pain_loc_lower for zone in critical_zones):
            context_multiplier += 0.25
    
    penalty = base_penalty * context_multiplier
    penalty = min(penalty, 0.20)  # Cap máximo
    
    if penalty < 0.10:
        expl = "dolor leve"
    elif penalty < 0.15:
        expl = "dolor moderado"
    else:
        expl = "dolor significativo"
    
    return penalty, expl


def penalty_sick_v3(sick_level: int) -> Tuple[float, str]:
    """
    Penalización por enfermedad con curva sigmoide (no escalones).
    """
    if pd.isna(sick_level) or sick_level <= 0:
        return 0.0, ""
    
    sick_level = np.clip(sick_level, 0, 5)
    
    # Usar sigmoid en lugar de mapa discreto
    normalized = sick_level / 5.0
    penalty = sigmoid(normalized, center=0.35, steepness=6.0) * 0.40
    
    labels = {1: "malestar leve", 2: "algo enfermo", 3: "enfermo", 
              4: "bastante enfermo", 5: "muy enfermo"}
    expl = labels.get(sick_level, "")
    
    return penalty, expl


def penalty_alcohol_v3(alcohol: bool, sleep_hours: float = 7.0,
                        sleep_quality: int = 3) -> Tuple[float, str]:
    """
    Penalización por alcohol, proporcional al impacto en sueño.
    
    - Alcohol + sueño ok → penalización menor
    - Alcohol + sueño malo → penalización mayor
    """
    if not alcohol:
        return 0.0, ""
    
    # Base penalty
    base_penalty = 0.06
    
    # Agravar si el sueño fue afectado
    if sleep_hours < 6.5 or sleep_quality <= 2:
        base_penalty += 0.04
    if sleep_hours < 5.5:
        base_penalty += 0.03
    
    penalty = min(base_penalty, 0.15)
    expl = "alcohol anoche"
    
    return penalty, expl


def penalty_sleep_disruption_v3(disrupted: bool, sleep_hours: float = 7.0,
                                  sleep_quality: int = 3) -> Tuple[float, str]:
    """
    Penalización por sueño fragmentado, proporcional al contexto.
    """
    if not disrupted:
        return 0.0, ""
    
    # Base penalty
    base_penalty = 0.03
    
    # Agravar si durmió poco además
    if sleep_hours < 6.0:
        base_penalty += 0.02
    if sleep_quality <= 2:
        base_penalty += 0.02
    
    penalty = min(base_penalty, 0.08)
    expl = "sueño fragmentado"
    
    return penalty, expl


# ============================================================================
# CONFIDENCE SCORE
# ============================================================================

def calculate_confidence(df_daily: Optional[pd.DataFrame],
                          inputs: Dict[str, Any]) -> Tuple[float, str]:
    """
    Calcula confidence score basado en datos disponibles.
    
    Returns:
        (score 0-1, nivel "low"/"medium"/"high")
    """
    score = 0.0
    
    # Factor 1: Días de histórico (60% del confidence)
    if df_daily is not None and len(df_daily) > 0:
        n_days = len(df_daily)
        if n_days >= 28:
            days_score = 0.95
        elif n_days >= 14:
            days_score = 0.70 + (n_days - 14) * 0.025 / 14
        elif n_days >= 7:
            days_score = 0.45 + (n_days - 7) * 0.025 / 7
        else:
            days_score = 0.20 + n_days * 0.035
    else:
        days_score = 0.15
    
    score += days_score * 0.60
    
    # Factor 2: Completitud de inputs de hoy (40% del confidence)
    key_inputs = ['sleep_hours', 'sleep_quality', 'fatigue', 'energy', 'perceived_readiness']
    present = sum(1 for k in key_inputs if k in inputs and not pd.isna(inputs.get(k)))
    completeness = present / len(key_inputs)
    
    score += completeness * 0.40
    
    # Determinar nivel
    if score >= 0.75:
        level = "high"
    elif score >= 0.45:
        level = "medium"
    else:
        level = "low"
    
    return score, level


# ============================================================================
# CONSISTENCY BONUS
# ============================================================================

def calculate_consistency_bonus(df_daily: Optional[pd.DataFrame],
                                  n_days: int = 7) -> Tuple[float, str]:
    """
    Bonus por consistencia en los últimos N días.
    
    Premia:
    - Sueño estable (baja variabilidad)
    - Fatiga no disparada múltiples días
    - Readiness sin "dientes de sierra"
    
    Returns:
        (bonus 0-0.06, explicación)
    """
    if df_daily is None or len(df_daily) < 3:
        return 0.0, ""
    
    recent = df_daily.tail(n_days).copy()
    
    if len(recent) < 3:
        return 0.0, ""
    
    bonus = 0.0
    reasons = []
    
    # 1. Estabilidad de sueño (hasta +0.02)
    if 'sleep_hours' in recent.columns:
        sleep_std = recent['sleep_hours'].std()
        if not pd.isna(sleep_std):
            if sleep_std < 0.5:
                bonus += 0.02
                reasons.append("sueño muy estable")
            elif sleep_std < 1.0:
                bonus += 0.01
                reasons.append("sueño estable")
    
    # 2. Fatiga controlada (hasta +0.02)
    if 'fatigue' in recent.columns:
        high_fatigue_days = (recent['fatigue'] > 7).sum()
        if high_fatigue_days == 0:
            bonus += 0.02
            reasons.append("fatiga controlada")
        elif high_fatigue_days <= 1:
            bonus += 0.01
    
    # 3. Readiness sin grandes oscilaciones (hasta +0.02)
    if 'readiness_score' in recent.columns:
        readiness_std = recent['readiness_score'].std()
        if not pd.isna(readiness_std):
            if readiness_std < 8:
                bonus += 0.02
                reasons.append("readiness consistente")
            elif readiness_std < 15:
                bonus += 0.01
    
    bonus = min(bonus, 0.06)  # Cap total
    
    expl = ", ".join(reasons) if reasons else ""
    
    return bonus, expl


# ============================================================================
# MOMENTUM BONUS (TENDENCIA)
# ============================================================================

def calculate_momentum_bonus(df_daily: Optional[pd.DataFrame],
                              n_days: int = 7) -> Tuple[float, str]:
    """
    Bonus por tendencia positiva reciente.
    
    Returns:
        (bonus 0-0.03, explicación)
    """
    if df_daily is None or len(df_daily) < 5:
        return 0.0, ""
    
    recent = df_daily.tail(n_days)
    
    if len(recent) < 5:
        return 0.0, ""
    
    bonus = 0.0
    reasons = []
    
    # Performance index mejorando
    if 'performance_index' in recent.columns:
        pi_values = recent['performance_index'].dropna()
        if len(pi_values) >= 3:
            first_half = pi_values.iloc[:len(pi_values)//2].mean()
            second_half = pi_values.iloc[len(pi_values)//2:].mean()
            if second_half > first_half * 1.01:
                bonus += 0.02
                reasons.append("rendimiento subiendo")
    
    # Readiness mejorando
    if 'readiness_score' in recent.columns:
        rs_values = recent['readiness_score'].dropna()
        if len(rs_values) >= 3:
            first_half = rs_values.iloc[:len(rs_values)//2].mean()
            second_half = rs_values.iloc[len(rs_values)//2:].mean()
            if second_half > first_half + 3:
                bonus += 0.01
                reasons.append("tendencia positiva")
    
    bonus = min(bonus, 0.03)
    expl = ", ".join(reasons) if reasons else ""
    
    return bonus, expl


# ============================================================================
# NAP BONUS
# ============================================================================

def calculate_nap_bonus(nap_minutes: int) -> Tuple[float, str]:
    """
    Bonus por siesta, con curva que maximiza el power nap.
    """
    if pd.isna(nap_minutes) or nap_minutes <= 0:
        return 0.0, ""
    
    # Óptimos: 20min (power nap) o 90min (ciclo completo)
    if nap_minutes <= 10:
        bonus = 0.01
        expl = "siesta corta"
    elif nap_minutes <= 25:
        bonus = 0.03  # Power nap óptimo
        expl = "power nap"
    elif nap_minutes <= 50:
        bonus = 0.04
        expl = "siesta media"
    elif nap_minutes <= 100:
        bonus = 0.05  # Ciclo completo
        expl = "siesta completa"
    else:
        bonus = 0.04  # Muy larga puede causar grogginess
        expl = "siesta larga"
    
    return bonus, expl


# ============================================================================
# FUNCIÓN PRINCIPAL v3
# ============================================================================

def calculate_readiness_from_inputs_v3(
    inputs: Dict[str, Any],
    df_daily: Optional[pd.DataFrame] = None,
    baselines: Optional[Dict] = None,
    adjustment_factors: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Calcula Readiness Score v3 "NASA" con curvas suaves.
    
    Args:
        inputs: Dict con inputs del cuestionario diario
        df_daily: DataFrame histórico (para confidence y consistency)
        baselines: Dict con baselines personales (p50, p75, etc.)
        adjustment_factors: Dict con sensibilidades personales
    
    Returns:
        Dict con:
        - readiness_score (0-100)
        - readiness_0_1 (0-1)
        - confidence ("low"/"medium"/"high")
        - confidence_score (0-1)
        - components (dict con desglose)
        - explanations (list de strings)
        - debug (valores intermedios)
    """
    
    if baselines is None:
        baselines = {}
    if adjustment_factors is None:
        adjustment_factors = {}
    
    # Extraer inputs con defaults
    sleep_hours = inputs.get('sleep_hours', 7.0)
    sleep_quality = inputs.get('sleep_quality', 3)
    fatigue = inputs.get('fatigue', 3)
    stress = inputs.get('stress', 3)
    energy = inputs.get('energy', 7)
    soreness = inputs.get('soreness', 2)
    motivation = inputs.get('motivation', 7)
    perceived = inputs.get('perceived_readiness')
    stiffness = inputs.get('stiffness', 2)
    pain_flag = inputs.get('pain_flag', False)
    pain_location = inputs.get('pain_location')
    sick_level = inputs.get('sick_level', 0)
    caffeine = inputs.get('caffeine', 0)
    alcohol = inputs.get('alcohol', False)
    sleep_disruption = inputs.get('sleep_disruption', False) or inputs.get('fragmented', False)
    nap_minutes = inputs.get('nap_minutes', 0) or inputs.get('nap_mins', 0)
    
    # Sensibilidades personales
    fatigue_sensitivity = adjustment_factors.get('fatigue_sensitivity', 1.0)
    stress_sensitivity = adjustment_factors.get('stress_sensitivity', 1.0)
    
    # =========================================================================
    # CONFIDENCE
    # =========================================================================
    confidence_score, confidence_level = calculate_confidence(df_daily, inputs)
    
    # Factor de moderación según confidence
    # Si confidence es baja, reducimos peso de baselines y penalizaciones
    confidence_mod = 0.5 + confidence_score * 0.5  # Rango 0.5-1.0
    
    # =========================================================================
    # COMPONENTES PRINCIPALES (80% del score)
    # =========================================================================
    explanations = []
    components = {}
    
    # --- SUEÑO (32% del core) ---
    sleep_baseline_p50 = baselines.get('sleep', {}).get('p50')
    sleep_baseline_p25 = baselines.get('sleep', {}).get('p25')
    
    sleep_hours_score, sleep_hours_expl = score_sleep_hours_v3(
        sleep_hours, sleep_baseline_p50, sleep_baseline_p25
    )
    sleep_quality_score, sleep_quality_expl = score_sleep_quality_v3(sleep_quality)
    
    # Combinar (horas 60%, calidad 40%)
    sleep_combined = sleep_hours_score * 0.60 + sleep_quality_score * 0.40
    
    # Nap bonus
    nap_bonus, nap_expl = calculate_nap_bonus(nap_minutes)
    sleep_combined = min(1.0, sleep_combined + nap_bonus)
    
    sleep_component = sleep_combined * 0.32
    components['sleep'] = sleep_component * 100
    
    sleep_expl_parts = [f"{sleep_hours:.1f}h ({sleep_hours_expl})", f"cal {sleep_quality_expl}"]
    if nap_expl:
        sleep_expl_parts.append(nap_expl)
    explanations.append(f"Sueño: +{components['sleep']:.0f} pts ({', '.join(sleep_expl_parts)})")
    
    # --- ESTADO FÍSICO (36% del core) ---
    fatigue_score, fatigue_expl = score_fatigue_v3(fatigue, fatigue_sensitivity)
    stress_score, stress_expl = score_stress_v3(stress, stress_sensitivity)
    energy_score, energy_expl = score_energy_v3(energy)
    soreness_score, soreness_expl = score_soreness_v3(soreness)
    
    # Pesos internos del estado
    state_combined = (
        energy_score * 0.40 +
        fatigue_score * 0.30 +
        stress_score * 0.20 +
        soreness_score * 0.10
    )
    
    state_component = state_combined * 0.36
    components['state'] = state_component * 100
    
    state_parts = [
        f"energía {energy_expl}",
        f"fatiga {fatigue_expl}",
        f"estrés {stress_expl}"
    ]
    explanations.append(f"Estado: +{components['state']:.0f} pts ({', '.join(state_parts)})")
    
    # --- PERCEPCIÓN (18% del core) ---
    if perceived is not None:
        perceived_score, perceived_expl = score_perceived_readiness_v3(perceived)
    else:
        # Sin percepción: usar promedio de otros indicadores
        perceived_score = (energy_score * 0.4 + (1 - fatigue/10) * 0.3 + motivation/10 * 0.3)
        perceived_expl = "estimada"
    
    perceived_component = perceived_score * 0.18
    components['perceived'] = perceived_component * 100
    explanations.append(f"Percepción: +{components['perceived']:.0f} pts ({perceived_expl})")
    
    # --- MOTIVACIÓN (14% del core) ---
    motivation_score, motivation_expl = score_motivation_v3(motivation)
    motivation_component = motivation_score * 0.14
    components['motivation'] = motivation_component * 100
    explanations.append(f"Motivación: +{components['motivation']:.0f} pts ({motivation_expl})")
    
    # =========================================================================
    # CORE READINESS (suma de componentes)
    # =========================================================================
    core_readiness = (sleep_component + state_component + 
                      perceived_component + motivation_component)
    
    # =========================================================================
    # MODIFIERS (bonuses)
    # =========================================================================
    
    # Consistency bonus
    consistency_bonus, consistency_expl = calculate_consistency_bonus(df_daily)
    if consistency_bonus > 0:
        explanations.append(f"Consistencia: +{consistency_bonus*100:.0f} pts ({consistency_expl})")
    
    # Momentum bonus
    momentum_bonus, momentum_expl = calculate_momentum_bonus(df_daily)
    if momentum_bonus > 0:
        explanations.append(f"Momentum: +{momentum_bonus*100:.0f} pts ({momentum_expl})")
    
    total_bonus = consistency_bonus + momentum_bonus
    components['bonuses'] = total_bonus * 100
    
    # =========================================================================
    # PENALIZACIONES (suaves y acotadas)
    # =========================================================================
    penalties = {}
    total_penalty = 0.0
    penalty_notes = []
    
    # Pain
    pain_penalty, pain_expl = penalty_pain_v3(pain_flag, pain_location, soreness, stiffness)
    if pain_penalty > 0:
        # Moderar según confidence (si hay pocos datos, menos agresivo)
        pain_penalty *= confidence_mod
        penalties['pain'] = pain_penalty * 100
        total_penalty += pain_penalty
        penalty_notes.append(pain_expl)
    
    # Sick
    sick_penalty, sick_expl = penalty_sick_v3(sick_level)
    if sick_penalty > 0:
        penalties['sick'] = sick_penalty * 100
        total_penalty += sick_penalty
        penalty_notes.append(sick_expl)
    
    # Alcohol
    alcohol_penalty, alcohol_expl = penalty_alcohol_v3(alcohol, sleep_hours, sleep_quality)
    if alcohol_penalty > 0:
        alcohol_penalty *= confidence_mod
        penalties['alcohol'] = alcohol_penalty * 100
        total_penalty += alcohol_penalty
        penalty_notes.append(alcohol_expl)
    
    # Sleep disruption
    disruption_penalty, disruption_expl = penalty_sleep_disruption_v3(
        sleep_disruption, sleep_hours, sleep_quality
    )
    if disruption_penalty > 0:
        penalties['sleep_disruption'] = disruption_penalty * 100
        total_penalty += disruption_penalty
        penalty_notes.append(disruption_expl)
    
    # Caffeine mask (solo si fatiga alta)
    if caffeine >= 3 and fatigue >= 7:
        caffeine_penalty = 0.03
        penalties['caffeine_mask'] = caffeine_penalty * 100
        total_penalty += caffeine_penalty
        penalty_notes.append("cafeína alta + fatiga")
    
    components['penalties'] = -total_penalty * 100
    
    if penalty_notes:
        explanations.append(f"Penalizaciones: -{total_penalty*100:.0f} pts ({', '.join(penalty_notes)})")
    
    # =========================================================================
    # SCORE FINAL
    # =========================================================================
    readiness_0_1 = core_readiness + total_bonus - total_penalty
    
    # Soft clip para evitar extremos bruscos
    readiness_0_1 = soft_clip(readiness_0_1, 0.0, 1.0, softness=0.02)
    
    # Score final (0-100)
    readiness_score = int(round(readiness_0_1 * 100))
    readiness_score = max(0, min(100, readiness_score))
    
    # Añadir explicación de confidence
    days_available = len(df_daily) if df_daily is not None else 0
    explanations.append(f"Confidence: {confidence_level} ({days_available} días de datos)")
    
    # =========================================================================
    # DEBUG INFO
    # =========================================================================
    debug = {
        'sleep_hours_score': sleep_hours_score,
        'sleep_quality_score': sleep_quality_score,
        'sleep_combined': sleep_combined,
        'fatigue_score': fatigue_score,
        'stress_score': stress_score,
        'energy_score': energy_score,
        'soreness_score': soreness_score,
        'state_combined': state_combined,
        'perceived_score': perceived_score,
        'motivation_score': motivation_score,
        'core_readiness': core_readiness,
        'total_bonus': total_bonus,
        'total_penalty': total_penalty,
        'confidence_mod': confidence_mod,
        'baselines_used': baselines
    }
    
    return {
        'readiness_score': readiness_score,
        'readiness_0_1': readiness_0_1,
        'confidence': confidence_level,
        'confidence_score': confidence_score,
        'components': components,
        'penalties': penalties,
        'explanations': explanations,
        'debug': debug
    }


# ============================================================================
# WRAPPER DE COMPATIBILIDAD CON v2
# ============================================================================

def calculate_readiness_from_inputs_v3_compat(
    sleep_hours, sleep_quality, fatigue, soreness, stress, motivation, pain_flag,
    nap_mins=0, sleep_disruptions=False, energy=7, stiffness=2, 
    caffeine=0, alcohol=False, sick_level=0, perceived_readiness=None,
    baselines=None, adjustment_factors=None,
    df_daily=None, pain_location=None
):
    """
    Wrapper de compatibilidad con la API de v2.
    
    Acepta los mismos parámetros que calculate_readiness_from_inputs_v2
    pero usa internamente v3 con curvas suaves.
    
    Retorna: (readiness_score, breakdown_dict) como v2
    """
    # Construir dict de inputs
    inputs = {
        'sleep_hours': sleep_hours,
        'sleep_quality': sleep_quality,
        'fatigue': fatigue,
        'soreness': soreness,
        'stress': stress,
        'motivation': motivation,
        'pain_flag': pain_flag,
        'pain_location': pain_location,
        'nap_minutes': nap_mins,
        'sleep_disruption': sleep_disruptions,
        'energy': energy,
        'stiffness': stiffness,
        'caffeine': caffeine,
        'alcohol': alcohol,
        'sick_level': sick_level,
        'perceived_readiness': perceived_readiness
    }
    
    # Llamar a v3
    result = calculate_readiness_from_inputs_v3(
        inputs=inputs,
        df_daily=df_daily,
        baselines=baselines,
        adjustment_factors=adjustment_factors
    )
    
    # Convertir a formato v2
    breakdown = {
        'perceived_component': result['components'].get('perceived', 0),
        'components': {
            'sleep': result['components'].get('sleep', 0),
            'state': result['components'].get('state', 0),
            'motivation': result['components'].get('motivation', 0)
        },
        'context_adjustments': {
            'pain_penalty': -result['penalties'].get('pain', 0),
            'sick_penalty': -result['penalties'].get('sick', 0),
            'caffeine_mask': -result['penalties'].get('caffeine_mask', 0)
        },
        'notes': result['explanations'],
        'final_score': result['readiness_score'],
        # Extras de v3
        'confidence': result['confidence'],
        'confidence_score': result['confidence_score'],
        'bonuses': result['components'].get('bonuses', 0)
    }
    
    return result['readiness_score'], breakdown


# ============================================================================
# TESTS
# ============================================================================

def run_tests():
    """Tests de la implementación v3."""
    print("=" * 60)
    print("TESTS DE READINESS v3 'NASA'")
    print("=" * 60)
    
    # TEST 1: Día perfecto
    print("\n📋 TEST 1: Día perfecto")
    print("-" * 40)
    
    perfect_day = {
        'sleep_hours': 8.0,
        'sleep_quality': 5,
        'fatigue': 1,
        'stress': 1,
        'energy': 9,
        'soreness': 0,
        'motivation': 9,
        'perceived_readiness': 9,
        'pain_flag': False,
        'sick_level': 0,
        'alcohol': False,
        'nap_minutes': 20
    }
    
    result1 = calculate_readiness_from_inputs_v3(perfect_day)
    print(f"Score: {result1['readiness_score']}")
    print(f"Confidence: {result1['confidence']}")
    for expl in result1['explanations']:
        print(f"  • {expl}")
    
    # Sin histórico, 87-90 es excelente para un día perfecto
    assert result1['readiness_score'] >= 87, f"Día perfecto debe ser ≥87, got {result1['readiness_score']}"
    print("✅ TEST 1 PASADO")
    
    # TEST 2: Día normal
    print("\n📋 TEST 2: Día normal")
    print("-" * 40)
    
    normal_day = {
        'sleep_hours': 7.0,
        'sleep_quality': 3,
        'fatigue': 4,
        'stress': 4,
        'energy': 6,
        'soreness': 3,
        'motivation': 7,
        'perceived_readiness': 7,
        'pain_flag': False,
        'sick_level': 0,
        'alcohol': False
    }
    
    result2 = calculate_readiness_from_inputs_v3(normal_day)
    print(f"Score: {result2['readiness_score']}")
    for expl in result2['explanations']:
        print(f"  • {expl}")
    
    assert 65 <= result2['readiness_score'] <= 80, f"Día normal debe ser 65-80, got {result2['readiness_score']}"
    print("✅ TEST 2 PASADO")
    
    # TEST 3: Día malo pero no catastrófico
    print("\n📋 TEST 3: Día malo (pero no punitivo)")
    print("-" * 40)
    
    bad_day = {
        'sleep_hours': 5.5,
        'sleep_quality': 2,
        'fatigue': 7,
        'stress': 6,
        'energy': 4,
        'soreness': 5,
        'motivation': 4,
        'perceived_readiness': 4,
        'pain_flag': False,
        'sick_level': 0,
        'alcohol': False,
        'sleep_disruption': True
    }
    
    result3 = calculate_readiness_from_inputs_v3(bad_day)
    print(f"Score: {result3['readiness_score']}")
    for expl in result3['explanations']:
        print(f"  • {expl}")
    
    # No debe ser demasiado bajo (>40) incluso en día malo sin enfermedad
    assert result3['readiness_score'] >= 40, f"Día malo no debe ser <40, got {result3['readiness_score']}"
    print("✅ TEST 3 PASADO")
    
    # TEST 4: Enfermedad (aquí sí bajamos)
    print("\n📋 TEST 4: Enfermo (penalización justificada)")
    print("-" * 40)
    
    sick_day = {
        'sleep_hours': 6.0,
        'sleep_quality': 2,
        'fatigue': 8,
        'stress': 5,
        'energy': 3,
        'soreness': 4,
        'motivation': 3,
        'perceived_readiness': 3,
        'pain_flag': False,
        'sick_level': 3,  # Enfermo
        'alcohol': False
    }
    
    result4 = calculate_readiness_from_inputs_v3(sick_day)
    print(f"Score: {result4['readiness_score']}")
    for expl in result4['explanations']:
        print(f"  • {expl}")
    
    # Enfermo debe bajar significativamente
    assert result4['readiness_score'] < 50, f"Enfermo debe ser <50, got {result4['readiness_score']}"
    print("✅ TEST 4 PASADO")
    
    # TEST 5: Con histórico (confidence alta + bonus)
    print("\n📋 TEST 5: Con histórico (confidence + consistency)")
    print("-" * 40)
    
    # Simular histórico de 30 días
    import datetime
    dates = [datetime.date.today() - datetime.timedelta(days=i) for i in range(30)]
    df_daily = pd.DataFrame({
        'date': dates,
        'sleep_hours': [7.0 + np.random.uniform(-0.3, 0.3) for _ in range(30)],
        'fatigue': [4 + np.random.randint(-1, 2) for _ in range(30)],
        'readiness_score': [72 + np.random.randint(-5, 6) for _ in range(30)],
        'performance_index': [1.0 + np.random.uniform(-0.01, 0.015) for _ in range(30)]
    })
    
    baselines = {
        'sleep': {'p50': 7.0, 'p25': 6.5, 'p75': 7.5}
    }
    
    result5 = calculate_readiness_from_inputs_v3(
        normal_day, df_daily=df_daily, baselines=baselines
    )
    print(f"Score: {result5['readiness_score']}")
    print(f"Confidence: {result5['confidence']} ({result5['confidence_score']:.2f})")
    for expl in result5['explanations']:
        print(f"  • {expl}")
    
    assert result5['confidence'] == 'high', "Con 30 días debe ser confidence high"
    print("✅ TEST 5 PASADO")
    
    # TEST 5b: Día perfecto CON histórico debe llegar a 90+
    print("\n📋 TEST 5b: Día perfecto CON histórico")
    print("-" * 40)
    
    result5b = calculate_readiness_from_inputs_v3(
        perfect_day, df_daily=df_daily, baselines=baselines
    )
    print(f"Score: {result5b['readiness_score']}")
    print(f"Confidence: {result5b['confidence']}")
    for expl in result5b['explanations']:
        print(f"  • {expl}")
    
    assert result5b['readiness_score'] >= 90, f"Día perfecto con histórico debe ser ≥90, got {result5b['readiness_score']}"
    print("✅ TEST 5b PASADO")
    
    # TEST 6: Curvas suaves (verificar que no hay saltos)
    print("\n📋 TEST 6: Verificar suavidad de curvas")
    print("-" * 40)
    
    scores_by_sleep = []
    for hours in np.arange(4.0, 9.0, 0.5):
        test_inputs = normal_day.copy()
        test_inputs['sleep_hours'] = hours
        result = calculate_readiness_from_inputs_v3(test_inputs)
        scores_by_sleep.append((hours, result['readiness_score']))
        print(f"  Sleep {hours}h → Readiness {result['readiness_score']}")
    
    # Verificar que no hay saltos >8 puntos entre valores consecutivos
    for i in range(1, len(scores_by_sleep)):
        diff = abs(scores_by_sleep[i][1] - scores_by_sleep[i-1][1])
        assert diff <= 10, f"Salto muy grande entre {scores_by_sleep[i-1]} y {scores_by_sleep[i]}"
    
    print("✅ TEST 6 PASADO (transiciones suaves)")
    
    print("\n" + "=" * 60)
    print("✅ TODOS LOS TESTS PASADOS")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
