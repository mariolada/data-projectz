"""
Set Classifier - Clasificación automática de sets de entrenamiento.

Este módulo clasifica automáticamente los sets en:
- TOP: Set(s) de mayor intensidad relativa (top set)
- BACKOFF: Sets con carga reducida post-top set
- WORK: Sets de trabajo efectivo (no warmup, no backoff)
- WARMUP: Sets de calentamiento (carga baja, RIR alto)
- UNKNOWN: Datos insuficientes para clasificar

El usuario NO etiqueta nada. El algoritmo lo infiere automáticamente.

Autor: data-projectz v2.0
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional, Tuple, List
from enum import Enum


# ============================================================================
# ENUMS Y CONFIGURACIÓN
# ============================================================================

class SetRole(Enum):
    """Roles posibles de un set dentro de una sesión."""
    TOP = "TOP"
    BACKOFF = "BACKOFF"
    WORK = "WORK"
    WARMUP = "WARMUP"
    UNKNOWN = "UNKNOWN"


@dataclass
class SetClassifierConfig:
    """
    Configuración para el clasificador de sets.
    
    Attributes:
        warmup_threshold: Proporción máxima de carga vs top para ser warmup (default 0.70 = 70%)
        backoff_drop_pct: Caída mínima de carga vs top para ser backoff (default 0.07 = 7%)
        multi_top_within_pct: Margen para considerar múltiples TOP sets (default 0.02 = 2%)
        min_sets_for_detection: Mínimo de sets para aplicar clasificación (default 2)
        warmup_min_rir: RIR mínimo típico de warmup si está disponible (default 3)
        warmup_max_intensity: Intensity score máximo para considerar warmup (default 0.65)
    """
    warmup_threshold: float = 0.70
    backoff_drop_pct: float = 0.07
    multi_top_within_pct: float = 0.02
    min_sets_for_detection: int = 2
    warmup_min_rir: float = 3.0
    warmup_max_intensity: float = 0.65


# ============================================================================
# FUNCIONES DE CÁLCULO BASE
# ============================================================================

def estimate_e1rm(load: float, reps: float, rir: Optional[float] = None, 
                  rpe: Optional[float] = None) -> float:
    """
    Estima el 1RM usando fórmula Epley modificada.
    
    Prioridad de datos:
    1. Si hay RIR: usa reps efectivas = reps + rir * 0.5
    2. Si solo hay RPE: convierte a RIR aproximado
    3. Si no hay RIR/RPE: usa Epley simple
    
    Args:
        load: Peso en kg
        reps: Repeticiones realizadas
        rir: Reps in Reserve (opcional)
        rpe: Rate of Perceived Exertion (opcional)
    
    Returns:
        Estimación de 1RM en kg
    """
    if pd.isna(load) or pd.isna(reps) or load <= 0 or reps <= 0:
        return np.nan
    
    # Determinar RIR efectivo
    effective_rir = None
    
    if rir is not None and not pd.isna(rir):
        effective_rir = max(0, rir)
    elif rpe is not None and not pd.isna(rpe):
        # Conversión RPE → RIR: RIR ≈ 10 - RPE
        effective_rir = max(0, 10 - rpe)
    
    # Calcular reps efectivas (ajustadas por RIR)
    if effective_rir is not None:
        # Las reps "disponibles" son las hechas + las que quedaban en reserva
        # Factor 0.5 porque RIR es una estimación, no exacto
        reps_effective = reps + effective_rir * 0.5
    else:
        reps_effective = reps
    
    # Fórmula Epley: e1RM = load × (1 + reps/30)
    e1rm = load * (1.0 + reps_effective / 30.0)
    
    return float(e1rm)


def calculate_rir_bonus(rir: Optional[float]) -> float:
    """
    Calcula bonus de intensidad basado en RIR.
    
    Lógica:
    - RIR ≤ 1: Muy cerca del fallo → bonus máximo (1.0)
    - RIR ≤ 2: Cerca del fallo → bonus alto (0.8)
    - RIR ≤ 3: Moderado → bonus medio (0.6)
    - RIR > 3: Lejos del fallo → bonus bajo (0.4)
    - RIR desconocido → bonus neutro (0.5)
    """
    if rir is None or pd.isna(rir):
        return 0.5  # Neutro si no hay datos
    
    if rir <= 1:
        return 1.0
    elif rir <= 2:
        return 0.8
    elif rir <= 3:
        return 0.6
    else:
        return 0.4


def calculate_intensity_score(load: float, e1rm: float, rir: Optional[float],
                               max_load_session: float, max_e1rm_session: float) -> float:
    """
    Calcula score de intensidad combinando carga, e1RM y proximidad al fallo.
    
    Fórmula:
    intensity_score = 0.45 * load_norm + 0.45 * e1rm_norm + 0.10 * rir_bonus
    
    Args:
        load: Peso del set
        e1rm: e1RM estimado del set
        rir: RIR del set (opcional)
        max_load_session: Carga máxima de la sesión (para normalizar)
        max_e1rm_session: e1RM máximo de la sesión (para normalizar)
    
    Returns:
        Score de intensidad entre 0 y 1
    """
    # Evitar división por cero
    if max_load_session <= 0 or max_e1rm_session <= 0:
        return 0.0
    
    if pd.isna(load) or pd.isna(e1rm):
        return 0.0
    
    # Normalizar
    load_norm = min(1.0, load / max_load_session)
    e1rm_norm = min(1.0, e1rm / max_e1rm_session)
    rir_bonus = calculate_rir_bonus(rir)
    
    # Combinar (pesos: 45% load, 45% e1rm, 10% RIR bonus)
    intensity_score = 0.45 * load_norm + 0.45 * e1rm_norm + 0.10 * rir_bonus
    
    return float(np.clip(intensity_score, 0, 1))


# ============================================================================
# CLASIFICACIÓN DE SETS
# ============================================================================

def _get_effective_rir(row: pd.Series) -> Optional[float]:
    """Extrae RIR efectivo de un row, convirtiendo RPE si es necesario."""
    if 'rir' in row and not pd.isna(row.get('rir')):
        return float(row['rir'])
    elif 'rpe' in row and not pd.isna(row.get('rpe')):
        return max(0, 10 - float(row['rpe']))
    return None


def classify_session_sets(df_session: pd.DataFrame, 
                          config: SetClassifierConfig) -> pd.DataFrame:
    """
    Clasifica los sets de UNA sesión (un ejercicio, un día).
    
    Args:
        df_session: DataFrame con sets de una sesión (un date + exercise)
        config: Configuración del clasificador
    
    Returns:
        DataFrame con columnas añadidas: set_role, top_set_id, intensity_score, estimated_e1rm
    """
    df = df_session.copy()
    n_sets = len(df)
    
    # Inicializar columnas
    df['set_role'] = SetRole.UNKNOWN.value
    df['top_set_id'] = None
    df['intensity_score'] = 0.0
    df['estimated_e1rm'] = np.nan
    
    # Si hay muy pocos sets, no podemos clasificar bien
    if n_sets < config.min_sets_for_detection:
        if n_sets == 1:
            # Un solo set → probablemente TOP
            df['set_role'] = SetRole.TOP.value
        return df
    
    # Verificar columnas mínimas
    if 'load' not in df.columns or 'reps' not in df.columns:
        return df  # No hay datos suficientes
    
    # =========================================================================
    # PASO 1: Calcular e1RM para cada set
    # =========================================================================
    df['_rir_effective'] = df.apply(_get_effective_rir, axis=1)
    
    df['estimated_e1rm'] = df.apply(
        lambda r: estimate_e1rm(
            r.get('load', np.nan),
            r.get('reps', np.nan),
            r['_rir_effective'],
            r.get('rpe')
        ),
        axis=1
    )
    
    # =========================================================================
    # PASO 2: Calcular intensity_score
    # =========================================================================
    max_load = df['load'].max()
    max_e1rm = df['estimated_e1rm'].max()
    
    if pd.isna(max_load) or max_load <= 0:
        return df  # No hay datos válidos
    
    if pd.isna(max_e1rm) or max_e1rm <= 0:
        max_e1rm = max_load * 1.2  # Fallback
    
    df['intensity_score'] = df.apply(
        lambda r: calculate_intensity_score(
            r.get('load', 0),
            r.get('estimated_e1rm', 0),
            r['_rir_effective'],
            max_load,
            max_e1rm
        ),
        axis=1
    )
    
    # =========================================================================
    # PASO 3: Identificar TOP set(s)
    # =========================================================================
    max_intensity = df['intensity_score'].max()
    threshold_top = max_intensity * (1 - config.multi_top_within_pct)
    
    # TOP = sets con intensity_score >= threshold_top
    top_mask = df['intensity_score'] >= threshold_top
    top_indices = df[top_mask].index.tolist()
    
    # Asignar top_set_id (el primer TOP como referencia)
    primary_top_idx = top_indices[0] if top_indices else None
    
    for idx in top_indices:
        df.loc[idx, 'set_role'] = SetRole.TOP.value
        df.loc[idx, 'top_set_id'] = primary_top_idx
    
    # Datos del TOP set para comparaciones
    if primary_top_idx is not None:
        top_load = df.loc[primary_top_idx, 'load']
        top_reps = df.loc[primary_top_idx, 'reps']
        top_e1rm = df.loc[primary_top_idx, 'estimated_e1rm']
    else:
        top_load = max_load
        top_reps = df['reps'].max()
        top_e1rm = max_e1rm
    
    # =========================================================================
    # PASO 4: Clasificar resto de sets (en orden de prioridad)
    # =========================================================================
    for idx, row in df.iterrows():
        if df.loc[idx, 'set_role'] == SetRole.TOP.value:
            continue  # Ya clasificado como TOP
        
        load = row.get('load', 0)
        reps = row.get('reps', 0)
        rir = row['_rir_effective']
        intensity = row['intensity_score']
        
        # Evitar división por cero
        if top_load <= 0:
            continue
        
        load_ratio = load / top_load
        
        # ----- WARMUP -----
        # Condiciones: load bajo (< warmup_threshold) Y (RIR alto O intensity_score bajo)
        is_warmup = False
        if load_ratio <= config.warmup_threshold:
            if rir is not None and rir >= config.warmup_min_rir:
                is_warmup = True
            elif intensity < config.warmup_max_intensity:
                is_warmup = True
        
        if is_warmup:
            df.loc[idx, 'set_role'] = SetRole.WARMUP.value
            df.loc[idx, 'top_set_id'] = primary_top_idx
            continue
        
        # ----- BACKOFF -----
        # Condiciones: load reducido (< 1 - backoff_drop_pct) Y no es warmup
        backoff_threshold = 1 - config.backoff_drop_pct
        is_backoff = False
        
        if load_ratio < backoff_threshold:
            # Verificar que no sea simplemente un warmup mal clasificado
            if intensity >= config.warmup_max_intensity:
                is_backoff = True
            # También considerar si reps son >= top_reps (típico de backoff)
            elif reps >= top_reps:
                is_backoff = True
        
        if is_backoff:
            df.loc[idx, 'set_role'] = SetRole.BACKOFF.value
            df.loc[idx, 'top_set_id'] = primary_top_idx
            continue
        
        # ----- WORK -----
        # Todo lo demás que no es TOP, WARMUP, BACKOFF
        df.loc[idx, 'set_role'] = SetRole.WORK.value
        df.loc[idx, 'top_set_id'] = primary_top_idx
    
    # Limpiar columna temporal
    df = df.drop(columns=['_rir_effective'])
    
    return df


def classify_sets(df: pd.DataFrame, 
                  config: Optional[SetClassifierConfig] = None) -> pd.DataFrame:
    """
    Clasifica todos los sets de un DataFrame de entrenamiento.
    
    Agrupa por (date, exercise) y aplica clasificación a cada sesión.
    
    Args:
        df: DataFrame con columnas: date, exercise, load, reps, [rir], [rpe], [set_index]
        config: Configuración del clasificador (usa defaults si None)
    
    Returns:
        DataFrame original + columnas: set_role, top_set_id, intensity_score, estimated_e1rm
    """
    if config is None:
        config = SetClassifierConfig()
    
    df = df.copy()
    
    # Asegurar que date es datetime
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    
    # Normalizar nombre de ejercicio
    if 'exercise' in df.columns:
        df['exercise'] = df['exercise'].str.lower().str.strip()
    
    # Verificar columnas mínimas
    required_cols = ['date', 'exercise', 'load', 'reps']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas requeridas: {missing}")
    
    # Ordenar por fecha y set_index si existe
    sort_cols = ['date', 'exercise']
    if 'set_index' in df.columns:
        sort_cols.append('set_index')
    elif 'timestamp' in df.columns:
        sort_cols.append('timestamp')
    
    df = df.sort_values(sort_cols).reset_index(drop=True)
    
    # Aplicar clasificación por sesión
    result_dfs = []
    
    for (date, exercise), group in df.groupby(['date', 'exercise']):
        classified = classify_session_sets(group, config)
        result_dfs.append(classified)
    
    if not result_dfs:
        return df
    
    result = pd.concat(result_dfs, ignore_index=True)
    
    return result


# ============================================================================
# FUNCIONES DE ANÁLISIS (útiles para el Neural Overload Detector)
# ============================================================================

def get_top_sets_summary(df_classified: pd.DataFrame) -> pd.DataFrame:
    """
    Extrae resumen de TOP sets por ejercicio y fecha.
    
    Args:
        df_classified: DataFrame ya clasificado con classify_sets()
    
    Returns:
        DataFrame con una fila por (date, exercise) con datos del TOP set
    """
    top_sets = df_classified[df_classified['set_role'] == SetRole.TOP.value].copy()
    
    if top_sets.empty:
        return pd.DataFrame()
    
    # Si hay múltiples TOP sets, tomar el de mayor intensity_score
    summary = top_sets.loc[
        top_sets.groupby(['date', 'exercise'])['intensity_score'].idxmax()
    ].copy()
    
    # Renombrar columnas para claridad
    summary = summary.rename(columns={
        'load': 'top_load',
        'reps': 'top_reps',
        'estimated_e1rm': 'top_e1rm',
        'intensity_score': 'top_intensity'
    })
    
    # Añadir RIR/RPE del top set si existen
    if 'rir' in summary.columns:
        summary = summary.rename(columns={'rir': 'top_rir'})
    if 'rpe' in summary.columns:
        summary = summary.rename(columns={'rpe': 'top_rpe'})
    
    return summary


def get_session_structure(df_classified: pd.DataFrame, 
                          date: str, exercise: str) -> dict:
    """
    Obtiene estructura detallada de una sesión específica.
    
    Args:
        df_classified: DataFrame clasificado
        date: Fecha de la sesión
        exercise: Nombre del ejercicio
    
    Returns:
        Dict con estructura de la sesión
    """
    mask = (
        (df_classified['date'] == pd.to_datetime(date)) & 
        (df_classified['exercise'].str.lower() == exercise.lower())
    )
    session = df_classified[mask]
    
    if session.empty:
        return {'found': False}
    
    structure = {
        'found': True,
        'date': str(date),
        'exercise': exercise,
        'total_sets': len(session),
        'n_warmup': len(session[session['set_role'] == SetRole.WARMUP.value]),
        'n_top': len(session[session['set_role'] == SetRole.TOP.value]),
        'n_work': len(session[session['set_role'] == SetRole.WORK.value]),
        'n_backoff': len(session[session['set_role'] == SetRole.BACKOFF.value]),
        'sets': []
    }
    
    for _, row in session.iterrows():
        set_info = {
            'load': row.get('load'),
            'reps': row.get('reps'),
            'rir': row.get('rir') if 'rir' in row and not pd.isna(row.get('rir')) else None,
            'rpe': row.get('rpe') if 'rpe' in row and not pd.isna(row.get('rpe')) else None,
            'role': row['set_role'],
            'intensity_score': round(row['intensity_score'], 3),
            'e1rm': round(row['estimated_e1rm'], 1) if not pd.isna(row['estimated_e1rm']) else None
        }
        structure['sets'].append(set_info)
    
    return structure


# ============================================================================
# TESTS
# ============================================================================

def run_tests():
    """
    Ejecuta tests de clasificación con casos conocidos.
    """
    print("=" * 60)
    print("TESTS DE SET CLASSIFIER")
    print("=" * 60)
    
    config = SetClassifierConfig()
    
    # =========================================================================
    # TEST 1: Peso muerto con TOP + BACKOFF
    # =========================================================================
    print("\n📋 TEST 1: Peso muerto (TOP + BACKOFF)")
    print("-" * 40)
    
    df1 = pd.DataFrame({
        'date': ['2026-01-10', '2026-01-10'],
        'exercise': ['peso muerto', 'peso muerto'],
        'set_index': [1, 2],
        'load': [150, 130],
        'reps': [4, 6],
        'rir': [1, 2]
    })
    
    result1 = classify_sets(df1, config)
    print(result1[['load', 'reps', 'rir', 'set_role', 'intensity_score', 'estimated_e1rm']])
    
    # Verificar
    assert result1.iloc[0]['set_role'] == 'TOP', "150×4@RIR1 debe ser TOP"
    assert result1.iloc[1]['set_role'] == 'BACKOFF', "130×6@RIR2 debe ser BACKOFF"
    print("✅ TEST 1 PASADO")
    
    # =========================================================================
    # TEST 2: Press banca con múltiples WORK sets
    # =========================================================================
    print("\n📋 TEST 2: Press banca (WORK sets + BACKOFF)")
    print("-" * 40)
    
    df2 = pd.DataFrame({
        'date': ['2026-01-10', '2026-01-10', '2026-01-10'],
        'exercise': ['press banca', 'press banca', 'press banca'],
        'set_index': [1, 2, 3],
        'load': [100, 100, 90],
        'reps': [5, 5, 8],
        'rir': [2, 2, 3]
    })
    
    result2 = classify_sets(df2, config)
    print(result2[['load', 'reps', 'rir', 'set_role', 'intensity_score', 'estimated_e1rm']])
    
    # Verificar
    top_count = (result2['set_role'] == 'TOP').sum()
    assert top_count >= 1, "Debe haber al menos 1 TOP"
    assert result2.iloc[2]['set_role'] == 'BACKOFF', "90×8@RIR3 debe ser BACKOFF"
    print("✅ TEST 2 PASADO")
    
    # =========================================================================
    # TEST 3: Sesión con WARMUP
    # =========================================================================
    print("\n📋 TEST 3: Sesión con warmups")
    print("-" * 40)
    
    df3 = pd.DataFrame({
        'date': ['2026-01-10', '2026-01-10', '2026-01-10'],
        'exercise': ['sentadilla', 'sentadilla', 'sentadilla'],
        'set_index': [1, 2, 3],
        'load': [60, 100, 110],
        'reps': [5, 3, 1],
        'rir': [5, 2, 1]
    })
    
    result3 = classify_sets(df3, config)
    print(result3[['load', 'reps', 'rir', 'set_role', 'intensity_score', 'estimated_e1rm']])
    
    # Verificar
    assert result3.iloc[2]['set_role'] == 'TOP', "110×1@RIR1 debe ser TOP"
    assert result3.iloc[0]['set_role'] == 'WARMUP', "60×5@RIR5 debe ser WARMUP"
    print("✅ TEST 3 PASADO")
    
    # =========================================================================
    # TEST 4: Sin RIR (solo load/reps)
    # =========================================================================
    print("\n📋 TEST 4: Sin RIR/RPE (solo load y reps)")
    print("-" * 40)
    
    df4 = pd.DataFrame({
        'date': ['2026-01-10', '2026-01-10', '2026-01-10'],
        'exercise': ['curl biceps', 'curl biceps', 'curl biceps'],
        'set_index': [1, 2, 3],
        'load': [12, 20, 20],  # 12 es 60% de 20 → claramente warmup
        'reps': [10, 8, 8]
    })
    
    result4 = classify_sets(df4, config)
    print(result4[['load', 'reps', 'set_role', 'intensity_score', 'estimated_e1rm']])
    
    # Verificar: 12×10 debe ser WARMUP (load 60% del top = 20)
    assert result4.iloc[0]['set_role'] == 'WARMUP', "12×10 debe ser WARMUP (60% de 20)"
    print("✅ TEST 4 PASADO")
    
    # =========================================================================
    # TEST 5: Múltiples TOP sets (cluster/doubles)
    # =========================================================================
    print("\n📋 TEST 5: Múltiples TOP sets (cluster)")
    print("-" * 40)
    
    df5 = pd.DataFrame({
        'date': ['2026-01-10', '2026-01-10', '2026-01-10'],
        'exercise': ['press militar', 'press militar', 'press militar'],
        'set_index': [1, 2, 3],
        'load': [75, 75, 60],
        'reps': [5, 5, 8],
        'rir': [0, 1, 3]
    })
    
    result5 = classify_sets(df5, config)
    print(result5[['load', 'reps', 'rir', 'set_role', 'intensity_score', 'estimated_e1rm']])
    
    # Verificar: ambos 75×5 pueden ser TOP o al menos uno
    top_count5 = (result5['set_role'] == 'TOP').sum()
    assert top_count5 >= 1, "Debe haber al menos 1 TOP"
    print("✅ TEST 5 PASADO")
    
    # =========================================================================
    # TEST 6: Sesión completa realista
    # =========================================================================
    print("\n📋 TEST 6: Sesión completa realista")
    print("-" * 40)
    
    df6 = pd.DataFrame({
        'date': ['2026-01-10'] * 7,
        'exercise': ['press banca'] * 7,
        'set_index': [1, 2, 3, 4, 5, 6, 7],
        'load': [60, 80, 100, 110, 110, 95, 95],
        'reps': [8, 5, 3, 3, 4, 6, 6],
        'rir': [5, 4, 3, 1, 1, 2, 3]
    })
    
    result6 = classify_sets(df6, config)
    print(result6[['load', 'reps', 'rir', 'set_role', 'intensity_score', 'estimated_e1rm']])
    
    # Mostrar estructura
    structure = get_session_structure(result6, '2026-01-10', 'press banca')
    print(f"\nEstructura: {structure['n_warmup']} warmup, {structure['n_top']} top, "
          f"{structure['n_work']} work, {structure['n_backoff']} backoff")
    
    assert structure['n_warmup'] >= 1, "Debe haber al menos 1 warmup"
    assert structure['n_top'] >= 1, "Debe haber al menos 1 TOP"
    print("✅ TEST 6 PASADO")
    
    print("\n" + "=" * 60)
    print("✅ TODOS LOS TESTS PASADOS")
    print("=" * 60)


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    run_tests()
