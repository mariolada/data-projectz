"""
Neural Overload Detector - Detección de sobrecarga neuromuscular/SNC

Este módulo detecta patrones de fatiga del sistema nervioso central en atletas,
especialmente optimizado para atletas avanzados donde:
- El progreso en carga es más lento (mantener carga puede ser normal)
- Hay mayor sensibilidad a fatiga neural
- Las señales "finas" son más relevantes (drift de rendimiento, volatilidad)

Signals detectados:
1. SUSTAINED_NEAR_FAILURE - Intensidad alta sostenida (RIR≤1 repetido)
2. FIXED_LOAD_DRIFT - Degradación de rendimiento a carga igual
3. HIGH_VOLATILITY - Oscilaciones grandes en rendimiento
4. PLATEAU_EFFORT_RISE - Estancamiento con esfuerzo creciente

Autor: Decision Engine v2.0
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


# ============================================================================
# CONFIGURACIÓN Y CONSTANTES
# ============================================================================

class AthleteLevel(Enum):
    """Nivel del atleta basado en experiencia y características del lift."""
    NOVICE = "novice"           # <6 sesiones del lift
    INTERMEDIATE = "intermediate"  # 6-12 sesiones
    ADVANCED = "advanced"        # 12+ sesiones con progreso lento

@dataclass
class OverloadConfig:
    """Configuración de umbrales para detección de sobrecarga."""
    # Ventanas de análisis
    window_sessions: int = 6           # Últimas N sesiones para comparaciones
    min_sessions_analysis: int = 4     # Mínimo de sesiones para analizar
    
    # Tolerancias
    load_tolerance_kg: float = 2.5     # ±kg para considerar "misma carga"
    
    # Umbrales SUSTAINED_NEAR_FAILURE
    near_failure_rir_threshold: float = 1.0
    near_failure_rpe_threshold: float = 9.0
    near_failure_proportion: float = 0.66  # 2/3 de sesiones
    near_failure_k_sessions: int = 3       # Ventana para este check
    
    # Umbrales FIXED_LOAD_DRIFT
    drift_rep_drop: int = 1             # Caída de reps para disparar
    drift_rir_drop: float = 1.0         # Caída de RIR para disparar
    drift_e1rm_drop_pct: float = 0.03   # 3% caída en e1RM
    
    # Umbrales HIGH_VOLATILITY
    volatility_rep_range: int = 2       # max-min reps en misma carga
    volatility_e1rm_cv: float = 0.04    # Coeficiente de variación
    
    # Umbrales PLATEAU_EFFORT_RISE
    plateau_rir_slope: float = -0.2     # Pendiente negativa por sesión
    plateau_rir_diff: float = 0.7       # Diferencia entre mitades
    
    # Pesos para overload_score
    weight_sustained_failure: int = 25
    weight_fixed_load_drift: int = 20
    weight_plateau_effort: int = 15
    weight_high_volatility: int = 10
    
    # Caps de readiness por overload_score
    cap_score_30: int = 65
    cap_score_45: int = 55
    cap_score_60: int = 45

@dataclass
class AdvancedConfig(OverloadConfig):
    """Configuración más sensible para atletas avanzados."""
    near_failure_k_sessions: int = 2       # Más sensible
    near_failure_proportion: float = 0.5   # 1/2 de sesiones
    drift_e1rm_drop_pct: float = 0.015     # 1.5% (más estricto)
    drift_rep_drop: int = 1
    weight_sustained_failure: int = 30     # Mayor peso
    weight_fixed_load_drift: int = 25


# Ejercicios clave para monitorear (normalizados)
KEY_LIFTS = [
    "press militar", "press banca", "sentadilla", "peso muerto",
    "ohp", "overhead press", "bench press", "squat", "deadlift",
    "press inclinado", "remo"
]


# ============================================================================
# FUNCIONES DE CÁLCULO BASE
# ============================================================================

def estimate_e1rm(load_kg: float, reps: float, rir: float = 0) -> float:
    """
    Estima 1RM usando fórmula Epley modificada.
    Ajusta reps efectivas si hay RIR > 0.
    
    e1RM = load × (1 + reps_efectivas / 30)
    """
    if pd.isna(load_kg) or pd.isna(reps) or load_kg <= 0:
        return np.nan
    
    rir_adj = rir if not pd.isna(rir) else 0
    reps_effective = reps + max(rir_adj, 0) * 0.5
    return float(load_kg * (1.0 + reps_effective / 30.0))


def normalize_exercise_name(name: str) -> str:
    """Normaliza nombre de ejercicio para comparaciones."""
    if pd.isna(name):
        return ""
    return str(name).lower().strip()


def is_key_lift(exercise: str) -> bool:
    """Determina si un ejercicio es un lift clave para monitoreo."""
    normalized = normalize_exercise_name(exercise)
    return any(key in normalized for key in KEY_LIFTS)


# ============================================================================
# EXTRACCIÓN DE TOP SETS
# ============================================================================

def extract_top_sets(df_exercise: pd.DataFrame) -> pd.DataFrame:
    """
    Extrae el top set por ejercicio y día.
    
    El top set se define como el set con mayor e1RM estimado.
    
    Input esperado (df_exercise):
        date, exercise, volume, e1rm_max, effort_mean, rir_w
        O si es set-level:
        date, exercise, load_kg, reps, rir (o rpe)
    
    Output:
        date, exercise, top_load, top_reps, top_rir, top_rpe, top_e1rm
    """
    df = df_exercise.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["exercise_norm"] = df["exercise"].apply(normalize_exercise_name)
    
    # Detectar formato de datos
    has_set_level = all(c in df.columns for c in ["load_kg", "reps"])
    
    if has_set_level:
        # Formato set-level: calcular e1RM por set
        rir_col = "rir" if "rir" in df.columns else None
        rpe_col = "rpe" if "rpe" in df.columns else None
        
        if rir_col:
            df["_rir"] = df[rir_col].fillna(2)
        elif rpe_col:
            df["_rir"] = 10 - df[rpe_col].fillna(7)  # Conversión RPE->RIR
        else:
            df["_rir"] = 2  # Default
        
        df["_e1rm"] = df.apply(
            lambda r: estimate_e1rm(r["load_kg"], r["reps"], r.get("_rir", 2)),
            axis=1
        )
        
        # Obtener top set por día y ejercicio
        idx = df.groupby(["date", "exercise_norm"])["_e1rm"].idxmax()
        top_sets = df.loc[idx].copy()
        
        top_sets = top_sets.rename(columns={
            "load_kg": "top_load",
            "reps": "top_reps",
            "_rir": "top_rir",
            "_e1rm": "top_e1rm"
        })
        
        if rpe_col:
            top_sets["top_rpe"] = top_sets[rpe_col]
        else:
            top_sets["top_rpe"] = 10 - top_sets["top_rir"]
            
    else:
        # Formato agregado: usar e1rm_max y derivar
        # Este formato tiene menos granularidad pero funciona
        # Buscar columnas con diferentes nombres posibles
        e1rm_col = None
        for col in ["e1rm_max", "e1rm", "e1RM"]:
            if col in df.columns:
                e1rm_col = col
                break
        
        rir_col = None
        for col in ["rir_w", "rir_weighted", "rir", "RIR"]:
            if col in df.columns:
                rir_col = col
                break
        
        rpe_col = None
        for col in ["effort_mean", "rpe", "RPE", "effort"]:
            if col in df.columns:
                rpe_col = col
                break
        
        if e1rm_col:
            df["_e1rm"] = df[e1rm_col]
        else:
            # Fallback: estimar desde volume si existe
            if "volume" in df.columns:
                # Aproximación muy gruesa: e1RM ≈ volume^0.33 * factor
                df["_e1rm"] = (df["volume"] ** 0.33) * 10
            else:
                df["_e1rm"] = 100  # Default
        
        if rir_col:
            df["_rir"] = df[rir_col].fillna(2)
        elif rpe_col:
            df["_rir"] = 10 - df[rpe_col].fillna(7)
        else:
            df["_rir"] = 2
        
        if rpe_col:
            df["_rpe"] = df[rpe_col].fillna(7)
        elif rir_col:
            df["_rpe"] = 10 - df[rir_col].fillna(2)
        else:
            df["_rpe"] = 7
        
        df["top_e1rm"] = df["_e1rm"]
        df["top_rir"] = df["_rir"]
        df["top_rpe"] = df["_rpe"]
        # Aproximar load: load ≈ e1RM / 1.17 (asumiendo 5 reps)
        df["top_load"] = df["_e1rm"] / 1.17
        df["top_reps"] = 5  # Asunción por defecto
        
        top_sets = df.copy()
    
    # Seleccionar columnas finales
    cols_out = ["date", "exercise", "exercise_norm", "top_load", "top_reps", 
                "top_rir", "top_rpe", "top_e1rm"]
    cols_exist = [c for c in cols_out if c in top_sets.columns]
    
    result = top_sets[cols_exist].copy()
    result = result.sort_values(["exercise_norm", "date"]).reset_index(drop=True)
    
    return result


# ============================================================================
# CLASIFICACIÓN DE ATLETA AVANZADO
# ============================================================================

def classify_advanced_lifts(df_top: pd.DataFrame, 
                            min_sessions: int = 12,
                            cv_threshold: float = 0.05) -> Dict[str, bool]:
    """
    Clasifica cada lift como "avanzado" o no.
    
    Criterios para lift avanzado:
    1. >= min_sessions sesiones del ejercicio
    2. Coeficiente de variación de carga bajo (CV < cv_threshold)
       → Indica plateau / progreso lento
    3. Opcional: percentil alto de carga personal
    
    Returns:
        Dict[exercise_norm] = True/False
    """
    result = {}
    
    for exercise in df_top["exercise_norm"].unique():
        df_ex = df_top[df_top["exercise_norm"] == exercise]
        
        n_sessions = len(df_ex)
        
        if n_sessions < 6:
            result[exercise] = False  # Novice
            continue
        
        if n_sessions < min_sessions:
            result[exercise] = False  # Intermediate
            continue
        
        # Calcular CV de carga
        load_mean = df_ex["top_load"].mean()
        load_std = df_ex["top_load"].std()
        cv_load = load_std / load_mean if load_mean > 0 else 0
        
        # Es avanzado si tiene muchas sesiones Y la carga es estable (plateau)
        result[exercise] = cv_load < cv_threshold
    
    return result


def get_athlete_level(exercise: str, 
                      advanced_map: Dict[str, bool],
                      n_sessions: int) -> AthleteLevel:
    """Determina el nivel del atleta para un ejercicio específico."""
    if n_sessions < 6:
        return AthleteLevel.NOVICE
    if n_sessions < 12:
        return AthleteLevel.INTERMEDIATE
    if advanced_map.get(exercise, False):
        return AthleteLevel.ADVANCED
    return AthleteLevel.INTERMEDIATE


# ============================================================================
# DETECCIÓN DE SEÑALES POR LIFT
# ============================================================================

@dataclass
class LiftFlag:
    """Representa un flag/señal detectada para un ejercicio."""
    flag_type: str              # Tipo de señal (ej: "SUSTAINED_NEAR_FAILURE")
    exercise: str               # Ejercicio afectado
    severity: int               # Severidad (0-100)
    evidence: Dict              # Datos de evidencia
    recommendations: List[str]  # Recomendaciones específicas
    date_detected: str = ""     # Fecha de detección


def detect_sustained_near_failure(
    df_ex: pd.DataFrame,
    config: OverloadConfig,
    is_advanced: bool
) -> Optional[LiftFlag]:
    """
    Detecta SUSTAINED_NEAR_FAILURE: intensidad alta sostenida.
    
    Condición:
    - En las últimas K sesiones:
      - proportion(RIR ≤ 1 OR RPE ≥ 9) >= threshold
      - media RIR <= 1.0
    """
    k = config.near_failure_k_sessions
    if is_advanced:
        k = max(2, k - 1)  # Más sensible para avanzados
    
    if len(df_ex) < k:
        return None
    
    recent = df_ex.tail(k)
    
    # Calcular flags de intensidad
    intensity_flag = (
        (recent["top_rir"] <= config.near_failure_rir_threshold) |
        (recent["top_rpe"] >= config.near_failure_rpe_threshold)
    )
    
    proportion = intensity_flag.mean()
    mean_rir = recent["top_rir"].mean()
    
    threshold = config.near_failure_proportion
    if is_advanced:
        threshold = 0.5  # Más sensible
    
    if proportion >= threshold and mean_rir <= 1.0:
        exercise = df_ex["exercise"].iloc[-1]
        severity = config.weight_sustained_failure
        if is_advanced:
            severity = int(severity * 1.2)  # +20% para avanzados
        
        return LiftFlag(
            flag_type="SUSTAINED_NEAR_FAILURE",
            exercise=exercise,
            severity=severity,
            evidence={
                "k_sessions": k,
                "near_failure_proportion": round(proportion, 2),
                "mean_rir": round(mean_rir, 2),
                "sessions_at_rir0_1": int(intensity_flag.sum()),
                "is_advanced": is_advanced
            },
            recommendations=[
                f"Evita RIR0 en {exercise} durante 7 días",
                f"Top set a RIR2 + 2 backoff sets en {exercise}",
                f"Reduce sets de {exercise} -20%"
            ]
        )
    
    return None


def detect_fixed_load_drift(
    df_ex: pd.DataFrame,
    config: OverloadConfig,
    is_advanced: bool
) -> Optional[LiftFlag]:
    """
    Detecta FIXED_LOAD_DRIFT: degradación de rendimiento a carga igual.
    
    Condición:
    - Comparar sesiones con misma carga (±tolerance)
    - Detectar: menos reps, RIR más bajo, o e1RM más bajo
    """
    if len(df_ex) < config.min_sessions_analysis:
        return None
    
    recent = df_ex.tail(config.window_sessions)
    last = recent.iloc[-1]
    last_load = last["top_load"]
    
    # Filtrar sesiones comparables (misma carga ± tolerancia)
    tol = config.load_tolerance_kg
    comparable = recent[
        (recent["top_load"] >= last_load - tol) &
        (recent["top_load"] <= last_load + tol) &
        (recent.index != recent.index[-1])  # Excluir la última
    ]
    
    if len(comparable) < 2:
        return None
    
    # Calcular métricas baseline
    baseline_reps = comparable["top_reps"].median()
    baseline_rir = comparable["top_rir"].median()
    baseline_e1rm = comparable["top_e1rm"].median()
    
    # Detectar drift
    rep_drop = last["top_reps"] <= baseline_reps - config.drift_rep_drop
    rir_drop = last["top_rir"] <= baseline_rir - config.drift_rir_drop
    
    e1rm_threshold = config.drift_e1rm_drop_pct
    if is_advanced:
        e1rm_threshold = 0.015  # 1.5% para avanzados
    
    e1rm_drop = last["top_e1rm"] < baseline_e1rm * (1 - e1rm_threshold)
    
    if rep_drop or rir_drop or e1rm_drop:
        exercise = df_ex["exercise"].iloc[-1]
        severity = config.weight_fixed_load_drift
        if is_advanced:
            severity = int(severity * 1.25)
        
        drift_type = []
        if rep_drop:
            drift_type.append("reps")
        if rir_drop:
            drift_type.append("rir")
        if e1rm_drop:
            drift_type.append("e1rm")
        
        return LiftFlag(
            flag_type="FIXED_LOAD_DRIFT",
            exercise=exercise,
            severity=severity,
            evidence={
                "last_load": round(last_load, 1),
                "last_reps": int(last["top_reps"]),
                "baseline_reps": round(baseline_reps, 1),
                "last_rir": round(last["top_rir"], 1),
                "baseline_rir": round(baseline_rir, 1),
                "last_e1rm": round(last["top_e1rm"], 1),
                "baseline_e1rm": round(baseline_e1rm, 1),
                "drift_type": drift_type,
                "is_advanced": is_advanced
            },
            recommendations=[
                f"Micro-deload de {exercise}: -5% load o +2 RIR por 1 semana",
                f"Cambia estímulo en {exercise}: pausas/tempo, rep ranges 6-8",
                f"No busques PR en {exercise} esta semana"
            ]
        )
    
    return None


def detect_high_volatility(
    df_ex: pd.DataFrame,
    config: OverloadConfig,
    is_advanced: bool
) -> Optional[LiftFlag]:
    """
    Detecta HIGH_VOLATILITY: oscilaciones grandes en rendimiento.
    
    Condición:
    - En sesiones con misma carga:
      - Rango de reps >= threshold
      - O CV de e1RM > threshold
    """
    if len(df_ex) < config.min_sessions_analysis:
        return None
    
    recent = df_ex.tail(config.window_sessions)
    last_load = recent.iloc[-1]["top_load"]
    tol = config.load_tolerance_kg
    
    # Filtrar sesiones con carga similar
    comparable = recent[
        (recent["top_load"] >= last_load - tol) &
        (recent["top_load"] <= last_load + tol)
    ]
    
    if len(comparable) < 3:
        return None
    
    # Calcular volatilidad
    rep_range = comparable["top_reps"].max() - comparable["top_reps"].min()
    rep_std = comparable["top_reps"].std()
    
    e1rm_mean = comparable["top_e1rm"].mean()
    e1rm_std = comparable["top_e1rm"].std()
    e1rm_cv = e1rm_std / e1rm_mean if e1rm_mean > 0 else 0
    
    # Proporción de sesiones a RIR bajo
    low_rir_share = (comparable["top_rir"] <= 1).mean()
    
    is_volatile = (
        (rep_range >= config.volatility_rep_range) or
        (e1rm_cv > config.volatility_e1rm_cv)
    ) and (low_rir_share >= 0.5)
    
    if is_volatile:
        exercise = df_ex["exercise"].iloc[-1]
        severity = config.weight_high_volatility
        if is_advanced:
            severity = int(severity * 1.3)
        
        return LiftFlag(
            flag_type="HIGH_VOLATILITY",
            exercise=exercise,
            severity=severity,
            evidence={
                "load": round(last_load, 1),
                "rep_range": int(rep_range),
                "rep_std": round(rep_std, 2) if pd.notna(rep_std) else 0,
                "e1rm_cv": round(e1rm_cv, 3),
                "low_rir_share": round(low_rir_share, 2),
                "n_comparable_sessions": len(comparable),
                "is_advanced": is_advanced
            },
            recommendations=[
                f"Aumenta consistencia en {exercise}: misma estructura y descanso",
                f"Controla fatiga: máx 1 top set pesado por sesión en {exercise}",
                f"Máx 1 set @RIR0/semana en {exercise}; usa top set @RIR1 + backoffs"
            ]
        )
    
    return None


def detect_plateau_effort_rise(
    df_ex: pd.DataFrame,
    config: OverloadConfig,
    is_advanced: bool
) -> Optional[LiftFlag]:
    """
    Detecta PLATEAU_EFFORT_RISE: estancamiento con esfuerzo creciente.
    
    Condición:
    - Carga no sube (Δload ≈ 0)
    - Pero RPE sube o RIR baja (tendencia)
    """
    if len(df_ex) < config.window_sessions:
        return None
    
    recent = df_ex.tail(config.window_sessions)
    
    # Verificar plateau de carga
    load_first = recent.iloc[:len(recent)//2]["top_load"].median()
    load_last = recent.iloc[len(recent)//2:]["top_load"].median()
    load_change_pct = abs(load_last - load_first) / load_first if load_first > 0 else 0
    
    is_plateau = load_change_pct < 0.03  # <3% cambio = plateau
    
    if not is_plateau:
        return None
    
    # Verificar tendencia de esfuerzo
    half = len(recent) // 2
    rir_first_half = recent.iloc[:half]["top_rir"].mean()
    rir_second_half = recent.iloc[half:]["top_rir"].mean()
    rir_diff = rir_second_half - rir_first_half  # Negativo = más esfuerzo
    
    # También calcular pendiente de RIR
    x = np.arange(len(recent))
    y = recent["top_rir"].values
    if len(x) >= 3:
        slope = np.polyfit(x, y, 1)[0]
    else:
        slope = 0
    
    effort_rising = (rir_diff < -config.plateau_rir_diff) or (slope < config.plateau_rir_slope)
    
    if effort_rising:
        exercise = df_ex["exercise"].iloc[-1]
        severity = config.weight_plateau_effort
        if is_advanced:
            severity = int(severity * 1.2)
        
        return LiftFlag(
            flag_type="PLATEAU_EFFORT_RISE",
            exercise=exercise,
            severity=severity,
            evidence={
                "load_first_half": round(load_first, 1),
                "load_second_half": round(load_last, 1),
                "load_change_pct": round(load_change_pct * 100, 1),
                "rir_first_half": round(rir_first_half, 2),
                "rir_second_half": round(rir_second_half, 2),
                "rir_diff": round(rir_diff, 2),
                "rir_slope": round(slope, 3),
                "is_advanced": is_advanced
            },
            recommendations=[
                f"Micro-deload de {exercise}: -5% load o +2 RIR por 1 semana",
                f"Cambia estímulo: back-off sets, tempo, pausas",
                f"Considera deload si hay 2+ señales de fatiga"
            ]
        )
    
    return None


def detect_lift_flags(
    df_top: pd.DataFrame,
    exercise: str,
    advanced_map: Dict[str, bool],
    config: OverloadConfig = None
) -> List[LiftFlag]:
    """
    Ejecuta todas las detecciones para un ejercicio específico.
    
    Returns:
        Lista de LiftFlag detectados
    """
    if config is None:
        config = OverloadConfig()
    
    # Filtrar datos del ejercicio
    exercise_norm = normalize_exercise_name(exercise)
    df_ex = df_top[df_top["exercise_norm"] == exercise_norm].copy()
    
    if len(df_ex) < config.min_sessions_analysis:
        return []
    
    # Determinar si es avanzado
    is_advanced = advanced_map.get(exercise_norm, False)
    
    # Usar configuración para avanzados si aplica
    if is_advanced:
        config = AdvancedConfig()
    
    flags = []
    
    # Ejecutar cada detector
    detectors = [
        detect_sustained_near_failure,
        detect_fixed_load_drift,
        detect_high_volatility,
        detect_plateau_effort_rise
    ]
    
    for detector in detectors:
        flag = detector(df_ex, config, is_advanced)
        if flag:
            flag.date_detected = str(df_ex["date"].max().date())
            flags.append(flag)
    
    return flags


# ============================================================================
# CÁLCULO DE OVERLOAD SCORE DIARIO
# ============================================================================

def compute_daily_overload(
    df_top: pd.DataFrame,
    key_lifts: List[str] = None,
    advanced_map: Dict[str, bool] = None,
    config: OverloadConfig = None
) -> pd.DataFrame:
    """
    Calcula el overload_score diario basado en flags de ejercicios clave.
    
    Returns:
        DataFrame con columnas:
        - date
        - overload_score (0-100)
        - overload_flags (string separado por |)
        - exercise_specific_recos (string separado por |)
        - advanced_lifts (string)
    """
    if config is None:
        config = OverloadConfig()
    
    if advanced_map is None:
        advanced_map = classify_advanced_lifts(df_top)
    
    # Determinar lifts clave a analizar
    if key_lifts is None:
        key_lifts = [ex for ex in df_top["exercise_norm"].unique() if is_key_lift(ex)]
    
    # Detectar flags para cada lift
    all_flags = []
    for exercise in key_lifts:
        flags = detect_lift_flags(df_top, exercise, advanced_map, config)
        all_flags.extend(flags)
    
    # Agrupar por fecha (usar fecha más reciente del análisis)
    if not all_flags:
        # No hay flags, retornar DataFrame vacío con estructura correcta
        dates = df_top["date"].unique()
        return pd.DataFrame({
            "date": dates,
            "overload_score": 0,
            "overload_flags": "",
            "exercise_specific_recos": "",
            "advanced_lifts": "|".join([k for k, v in advanced_map.items() if v])
        })
    
    # Calcular score total
    total_score = sum(f.severity for f in all_flags)
    total_score = min(total_score, 100)  # Cap at 100
    
    # Combinar flags y recomendaciones
    flag_strs = [f"{f.flag_type}_{f.exercise.upper()}" for f in all_flags]
    all_recos = []
    for f in all_flags:
        all_recos.extend(f.recommendations)
    
    # Crear resultado por fecha
    latest_date = max(f.date_detected for f in all_flags)
    
    result = pd.DataFrame([{
        "date": pd.to_datetime(latest_date),
        "overload_score": total_score,
        "overload_flags": "|".join(flag_strs),
        "exercise_specific_recos": "|".join(all_recos[:5]),  # Top 5 recos
        "advanced_lifts": "|".join([k for k, v in advanced_map.items() if v]),
        "n_flags": len(all_flags),
        "flag_details": [f.__dict__ for f in all_flags]
    }])
    
    return result


# ============================================================================
# INTEGRACIÓN CON DECISION ENGINE
# ============================================================================

def apply_overload_caps(
    readiness_score: float,
    overload_score: float,
    config: OverloadConfig = None
) -> Tuple[float, str]:
    """
    Aplica caps de readiness basados en overload_score.
    
    Returns:
        (readiness_capped, reason)
    """
    if config is None:
        config = OverloadConfig()
    
    if pd.isna(overload_score) or overload_score <= 0:
        return readiness_score, ""
    
    if overload_score >= 60:
        cap = config.cap_score_60
        reason = "NEURAL_OVERLOAD_SEVERE"
    elif overload_score >= 45:
        cap = config.cap_score_45
        reason = "NEURAL_OVERLOAD_HIGH"
    elif overload_score >= 30:
        cap = config.cap_score_30
        reason = "NEURAL_OVERLOAD_MOD"
    else:
        return readiness_score, ""
    
    if readiness_score > cap:
        return cap, reason
    
    return readiness_score, ""


def merge_overload_into_daily(
    df_daily: pd.DataFrame,
    df_overload: pd.DataFrame
) -> pd.DataFrame:
    """
    Integra resultados de overload en el DataFrame diario.
    
    Añade columnas:
    - overload_score
    - overload_flags
    - exercise_specific_recos
    - readiness_score (con caps aplicados)
    - reason_codes (actualizado)
    """
    if df_overload.empty:
        df_daily["overload_score"] = 0
        df_daily["overload_flags"] = ""
        df_daily["exercise_specific_recos"] = ""
        return df_daily
    
    # Merge por fecha
    df_daily = df_daily.copy()
    df_daily["date"] = pd.to_datetime(df_daily["date"])
    df_overload["date"] = pd.to_datetime(df_overload["date"])
    
    # Para simplicidad, aplicar el overload más reciente a todos los días recientes
    latest_overload = df_overload.iloc[-1]
    
    df_daily["overload_score"] = latest_overload["overload_score"]
    df_daily["overload_flags"] = latest_overload["overload_flags"]
    df_daily["exercise_specific_recos"] = latest_overload["exercise_specific_recos"]
    
    # Aplicar caps
    config = OverloadConfig()
    
    def apply_caps_row(row):
        capped, reason = apply_overload_caps(
            row.get("readiness_score", 50),
            row["overload_score"],
            config
        )
        return pd.Series({"readiness_capped": capped, "overload_reason": reason})
    
    caps_df = df_daily.apply(apply_caps_row, axis=1)
    df_daily["readiness_score_original"] = df_daily.get("readiness_score", 50)
    df_daily["readiness_score"] = caps_df["readiness_capped"]
    
    # Actualizar reason_codes
    def update_reasons(row):
        current = row.get("reason_codes", "")
        overload_reason = caps_df.loc[row.name, "overload_reason"]
        if overload_reason:
            if current and current != "NONE":
                return f"{current}|{overload_reason}"
            return overload_reason
        return current
    
    df_daily["reason_codes"] = df_daily.apply(update_reasons, axis=1)
    
    return df_daily


# ============================================================================
# CROSS-CHECK CON RECUPERACIÓN
# ============================================================================

def cross_check_with_recovery(
    flags: List[LiftFlag],
    sleep_hours: float,
    sleep_p50: float,
    acwr: float
) -> Tuple[List[LiftFlag], str]:
    """
    Ajusta severidad de flags basado en contexto de recuperación.
    
    Si sueño bajo o ACWR alto → aumenta severidad 10-15%
    Si sueño ok y ACWR ok pero hay drift → enfatiza fatiga neural
    
    Returns:
        (flags_ajustados, causa_principal)
    """
    if not flags:
        return flags, "NONE"
    
    # Detectar problema de recuperación
    recovery_issue = False
    if pd.notna(sleep_hours) and pd.notna(sleep_p50):
        if sleep_hours < sleep_p50 - 0.5:
            recovery_issue = True
    
    if pd.notna(acwr) and acwr > 1.3:
        recovery_issue = True
    
    adjusted_flags = []
    for flag in flags:
        new_flag = LiftFlag(
            flag_type=flag.flag_type,
            exercise=flag.exercise,
            severity=flag.severity,
            evidence=flag.evidence.copy(),
            recommendations=flag.recommendations.copy(),
            date_detected=flag.date_detected
        )
        
        if recovery_issue:
            # Aumentar severidad 15%
            new_flag.severity = int(flag.severity * 1.15)
            new_flag.evidence["recovery_adjusted"] = True
            
            # Añadir recomendación de recuperación
            if "Prioriza sueño y recuperación" not in new_flag.recommendations:
                new_flag.recommendations.insert(0, "Prioriza sueño y recuperación antes de intensificar")
        else:
            # No hay problema de recuperación → fatiga neural/programación
            new_flag.evidence["likely_cause"] = "neural_fatigue_or_programming"
            if "PLATEAU" in flag.flag_type or "DRIFT" in flag.flag_type:
                new_flag.recommendations.append("Causa probable: acumulación de fatiga neural o exceso de RIR0")
        
        adjusted_flags.append(new_flag)
    
    cause = "RECOVERY_DRIVEN" if recovery_issue else "NEURAL_DRIVEN"
    return adjusted_flags, cause


# ============================================================================
# FUNCIÓN PRINCIPAL DE ANÁLISIS
# ============================================================================

def analyze_neuromuscular_overload(
    df_exercise: pd.DataFrame,
    df_daily: pd.DataFrame = None,
    key_lifts: List[str] = None,
    config: OverloadConfig = None
) -> Dict:
    """
    Función principal: analiza sobrecarga neuromuscular.
    
    Args:
        df_exercise: DataFrame con datos de ejercicios
        df_daily: DataFrame con métricas diarias (opcional, para cross-check)
        key_lifts: Lista de ejercicios clave a analizar
        config: Configuración de umbrales
    
    Returns:
        Dict con:
        - top_sets: DataFrame de top sets extraídos
        - advanced_map: Dict de ejercicios avanzados
        - flags: Lista de LiftFlag detectados
        - overload_df: DataFrame con scores diarios
        - summary: Resumen del análisis
    """
    if config is None:
        config = OverloadConfig()
    
    # 1. Extraer top sets
    df_top = extract_top_sets(df_exercise)
    
    # 2. Clasificar lifts avanzados
    advanced_map = classify_advanced_lifts(df_top)
    
    # 3. Detectar flags para cada lift
    if key_lifts is None:
        key_lifts = [ex for ex in df_top["exercise_norm"].unique() if is_key_lift(ex)]
    
    all_flags = []
    for exercise in key_lifts:
        flags = detect_lift_flags(df_top, exercise, advanced_map, config)
        all_flags.extend(flags)
    
    # 4. Cross-check con recuperación si hay datos diarios
    cause = "UNKNOWN"
    if df_daily is not None and not df_daily.empty:
        latest = df_daily.iloc[-1]
        sleep_p50 = df_daily["sleep_hours"].median() if "sleep_hours" in df_daily else 7.0
        all_flags, cause = cross_check_with_recovery(
            all_flags,
            latest.get("sleep_hours", 7.0),
            sleep_p50,
            latest.get("acwr_7_28", 1.0)
        )
    
    # 5. Calcular overload diario
    df_overload = compute_daily_overload(df_top, key_lifts, advanced_map, config)
    
    # 6. Crear resumen
    summary = {
        "n_key_lifts_analyzed": len(key_lifts),
        "n_advanced_lifts": sum(1 for v in advanced_map.values() if v),
        "n_flags_detected": len(all_flags),
        "total_overload_score": sum(f.severity for f in all_flags),
        "primary_cause": cause,
        "flags_by_type": {},
        "affected_exercises": list(set(f.exercise for f in all_flags))
    }
    
    for flag in all_flags:
        ftype = flag.flag_type
        if ftype not in summary["flags_by_type"]:
            summary["flags_by_type"][ftype] = 0
        summary["flags_by_type"][ftype] += 1
    
    return {
        "top_sets": df_top,
        "advanced_map": advanced_map,
        "flags": all_flags,
        "overload_df": df_overload,
        "summary": summary
    }


# ============================================================================
# VALIDACIÓN CON CASOS DE PRUEBA
# ============================================================================

def validate_with_test_cases():
    """
    Valida el detector con los casos de prueba especificados.
    
    Caso 1: Press militar
        Semana A: 75×5@RIR0
        Semana B: 75×3@RIR0
        → Debe disparar FIXED_LOAD_DRIFT + HIGH_VOLATILITY
    
    Caso 2: Press militar
        75×3@RIR2 → 75×3@RIR0
        → Debe disparar PLATEAU_EFFORT_RISE
    """
    print("=" * 60)
    print("VALIDACIÓN CON CASOS DE PRUEBA")
    print("=" * 60)
    
    # Caso 1: Fixed load drift + volatility
    print("\n--- CASO 1: Drift + Volatility ---")
    test_data_1 = pd.DataFrame([
        {"date": "2026-01-01", "exercise": "Press Militar", "load_kg": 75, "reps": 5, "rir": 0},
        {"date": "2026-01-03", "exercise": "Press Militar", "load_kg": 75, "reps": 4, "rir": 1},
        {"date": "2026-01-05", "exercise": "Press Militar", "load_kg": 75, "reps": 5, "rir": 0},
        {"date": "2026-01-08", "exercise": "Press Militar", "load_kg": 75, "reps": 3, "rir": 0},  # DRIFT aquí
    ])
    
    result_1 = analyze_neuromuscular_overload(test_data_1)
    print(f"Flags detectados: {len(result_1['flags'])}")
    for flag in result_1['flags']:
        print(f"  - {flag.flag_type}: {flag.exercise} (severidad: {flag.severity})")
        print(f"    Recos: {flag.recommendations[:2]}")
    
    # Caso 2: Plateau with effort rise
    print("\n--- CASO 2: Plateau + Effort Rise ---")
    test_data_2 = pd.DataFrame([
        {"date": "2026-01-01", "exercise": "Press Militar", "load_kg": 75, "reps": 3, "rir": 3},
        {"date": "2026-01-03", "exercise": "Press Militar", "load_kg": 75, "reps": 3, "rir": 2},
        {"date": "2026-01-05", "exercise": "Press Militar", "load_kg": 75, "reps": 3, "rir": 1},
        {"date": "2026-01-08", "exercise": "Press Militar", "load_kg": 75, "reps": 3, "rir": 0},  # PLATEAU aquí
    ])
    
    result_2 = analyze_neuromuscular_overload(test_data_2)
    print(f"Flags detectados: {len(result_2['flags'])}")
    for flag in result_2['flags']:
        print(f"  - {flag.flag_type}: {flag.exercise} (severidad: {flag.severity})")
        print(f"    Recos: {flag.recommendations[:2]}")
    
    print("\n" + "=" * 60)
    print("VALIDACIÓN COMPLETADA")
    print("=" * 60)


if __name__ == "__main__":
    validate_with_test_cases()
