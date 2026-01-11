"""
Personalization Engine: Baselines, fatiga diferenciada, riesgo de lesión.
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, List, Any


def calculate_personal_baselines(df_daily: pd.DataFrame, min_days: int = 7) -> Dict[str, Any]:
    """
    Calcula percentiles personales (p50, p75, p90) para readiness, volume, sleep.
    
    Args:
        df_daily: DataFrame con histórico diario
        min_days: mínimo de datos requeridos para calcular percentiles (default 7)
    
    Retorna dict con estadísticas por métrica o vacío si faltan datos.
    Útil para contextualizar "hoy estás bajo" vs "normalmente estás aquí".
    """
    if df_daily.empty:
        return {}
    
    baselines = {}
    data_quality = len(df_daily)
    
    # Readiness percentiles
    if 'readiness_score' in df_daily.columns:
        readiness = df_daily['readiness_score'].dropna()
        if len(readiness) >= min_days:
            baselines['readiness'] = {
                'p50': readiness.quantile(0.5),
                'p75': readiness.quantile(0.75),
                'p90': readiness.quantile(0.9),
                'mean': readiness.mean(),
                'std': readiness.std(),
                'n': len(readiness)
            }
    
    # Volume percentiles
    if 'volume' in df_daily.columns:
        volume = df_daily['volume'].dropna()
        if len(volume) >= min_days:
            baselines['volume'] = {
                'p50': volume.quantile(0.5),
                'p75': volume.quantile(0.75),
                'p90': volume.quantile(0.9),
                'mean': volume.mean(),
                'n': len(volume)
            }
    
    # Sleep percentiles
    if 'sleep_hours' in df_daily.columns:
        sleep = df_daily['sleep_hours'].dropna()
        if len(sleep) >= min_days:
            baselines['sleep'] = {
                'p50': sleep.quantile(0.5),
                'p25': sleep.quantile(0.25),
                'mean': sleep.mean(),
                'n': len(sleep)
            }
    
    # ACWR percentiles
    if 'acwr_7_28' in df_daily.columns:
        acwr = df_daily['acwr_7_28'].dropna()
        if len(acwr) >= min_days:
            baselines['acwr'] = {
                'p50': acwr.quantile(0.5),
                'p75': acwr.quantile(0.75),
                'mean': acwr.mean(),
                'n': len(acwr)
            }
    
    # Add data quality flag
    baselines['_data_quality'] = {
        'total_days': data_quality,
        'sufficient': data_quality >= min_days,
        'min_required': min_days
    }
    
    return baselines


def contextualize_readiness(readiness_score: int, baselines: Dict) -> Tuple[str, str, float]:
    """
    Contextualiza readiness contra el p50/p75 personal del usuario.
    
    Retorna (contexto, recomendación_corta, delta)
    Ej: ("Bajo vs tu media (62)", "🔴 Cuida hoy", -4)
    """
    if 'readiness' not in baselines or not baselines['_data_quality']['sufficient']:
        return ("Sin histórico suficiente", "N/D", 0)
    
    personal_p50 = baselines['readiness']['p50']
    personal_p75 = baselines['readiness']['p75']
    delta = readiness_score - personal_p50
    
    if readiness_score >= personal_p75:
        return (f"Alto (p75: {personal_p75:.0f}, +{delta:.0f})", "🟢 Día de empuje", delta)
    elif readiness_score >= personal_p50:
        return (f"Normal (p50: {personal_p50:.0f}, {delta:+.0f})", "🟡 Entrena como siempre", delta)
    else:
        return (f"Bajo vs tu media ({personal_p50:.0f}, {delta:+.0f})", "🔴 Cuida hoy", delta)


def detect_fatigue_type(
    sleep_hours: float,
    sleep_quality: int,
    stress: int,
    fatigue: int,
    soreness: int,
    pain_flag: bool,
    pain_location: str,
    baselines: Dict,
    readiness_instant: int = 50
) -> Dict[str, Any]:
    """
    Diferencia entre fatiga central (sueño/estrés) y periférica (agujetas/dolor local).
    
    NUEVO: Recibe readiness_instant para coordinación. Si readiness < 50, 
    nunca retorna 'fresh' (override conservador).
    
    Retorna dict con:
    - type: 'central', 'peripheral', 'mixed', 'fresh', 'fatigued'
    - reason: explicación concisa
    - target_split: 'upper' / 'lower' / 'rest' / 'cardio' para UI
    - recommendations: lista de acciones (redirigir vs bajar)
    """
    
    # Detectar fatiga central
    sleep_baseline = baselines.get('sleep', {}).get('p50', 7.0)
    central_factors = 0
    
    if sleep_hours < sleep_baseline - 0.5:
        central_factors += 2  # Muy bajo
    elif sleep_hours < sleep_baseline:
        central_factors += 1  # Bajo
    
    if sleep_quality <= 2:
        central_factors += 1
    
    if stress >= 7:
        central_factors += 1
    
    if fatigue >= 7:
        central_factors += 1
    
    # Detectar fatiga periférica (solo si pain_flag es True)
    peripheral_factors = 0
    
    if soreness >= 7:
        peripheral_factors += 2
    
    if pain_flag and pain_location and pain_location.strip() != '':
        peripheral_factors += 2
    
    # Helper para intensidad sugerida según readiness
    def intensity_hint_for(readiness: int) -> str:
        if readiness >= 80:
            return "Push: RIR 1–2 (considera PRs si técnica sólida)"
        elif readiness >= 55:
            return "Normal: RIR 2–3 (técnica impecable)"
        else:
            return "Conservador: RIR 3–5 (reduce carga)"

    # Clasificar CON OVERRIDE si readiness es bajo
    if central_factors >= 3 and peripheral_factors < 2:
        return {
            'type': 'central',
            'reason': f'Sueño bajo ({sleep_hours}h < {sleep_baseline:.1f}h) + estrés/fatiga alta',
            'primary_issue': 'CNS fatigue',
            'target_split': 'rest',
            'intensity_hint': intensity_hint_for(readiness_instant),
            'recommendations': [
                'Sesión técnica / accesorios ligeros',
                'Cardio Z2 suave o movilidad',
                'Evita complejos pesados (sentadilla, peso muerto)',
                'Prioriza dormir +1-2h hoy'
            ]
        }
    elif peripheral_factors >= 2 and central_factors < 2:
        target = 'upper' if 'inferior' in (pain_location or '').lower() or 'pierna' in (pain_location or '').lower() else 'lower'
        return {
            'type': 'peripheral',
            'reason': f'Agujetas/dolor alto en {pain_location or "músculos"}',
            'primary_issue': 'Local soreness',
            'target_split': target,
            'intensity_hint': intensity_hint_for(readiness_instant),
            'recommendations': [
                f'Tren {"superior" if target == "upper" else "inferior"} OK',
                f'Evita el área de {pain_location or "dolor"}',
                'Movilidad + stretching prolongado (15-20 min)',
                'Frío local si hay hinchazón'
            ]
        }
    elif central_factors >= 2 and peripheral_factors >= 2:
        return {
            'type': 'mixed',
            'reason': f'Fatiga central ({sleep_hours}h sueño) + periférica ({soreness}/10 agujetas)',
            'primary_issue': 'Overreaching',
            'target_split': 'rest',
            'intensity_hint': "Deload: RIR 3–5 (reduce volumen -30%)",
            'recommendations': [
                'Reduce volumen general -20%',
                'Considera actividad ligera (cardio Z2, movilidad)',
                'Descansa mínimo 2 días o deload completo'
            ]
        }
    else:
        # === OVERRIDE: Si readiness < 50, no es "fresh" ===
        if readiness_instant < 50:
            # Readiness bajo pero síntomas no lo explican → fatiga oculta/acumulada
            return {
                'type': 'fatigued',
                'reason': f'Readiness bajo ({readiness_instant}/100) a pesar de síntomas normales en superficie',
                'primary_issue': 'Fatiga acumulada / falta de recuperación',
                'target_split': 'rest',
                'intensity_hint': "Conservador: RIR 3–5 (reduce volumen -20%)",
                'recommendations': [
                    'Síntomas no alarman pero el score indica fatiga acumulada',
                    'Reduce volumen -20% como mínimo',
                    'Prioriza recuperación pasiva: sueño extra, estrés bajo',
                    'Si persiste, considera deload completo'
                ]
            }
        else:
            # Readiness OK y síntomas OK → fresh
            # Recomendar PRs solo si readiness alto
            recs: List[str]
            if readiness_instant >= 80:
                recs = [
                    'Puedes empujar hoy',
                    'Considera buscar PRs si técnica sólida',
                    'Siente libertad total'
                ]
            else:
                recs = [
                    'Entrena normal (prioriza técnica)',
                    'Mantén control de tempo y ejecución',
                    'Evita forzar si notas fatiga'
                ]
            return {
                'type': 'fresh',
                'reason': f'Bien descansado ({sleep_hours}h, estrés {stress}/10)',
                'primary_issue': None,
                'target_split': 'upper',
                'intensity_hint': intensity_hint_for(readiness_instant),
                'recommendations': recs
            }


def calculate_injury_risk_score(
    readiness_score: int,
    acwr: float,
    sleep_hours: float,
    performance_index: float,
    effort_level: int,
    pain_flag: bool = False,
    baselines: Dict = None,
    days_high_strain: int = 0
) -> Dict[str, Any]:
    """
    Score simple de riesgo de lesión (0-100).
    
    Factores:
    - ACWR >1.5 (riesgo agudo)
    - Sueño <6.5h (sin recuperación)
    - Performance cayendo + effort alto (acumulación)
    - 2+ días de alta exigencia (fatiga acumulada)
    - Dolor localizado (pain_flag=True)
    
    Retorna dict con:
    - risk_level: 'low'/'medium'/'high'
    - score: 0-100
    - factors: list de factores que contribuyen
    - confidence: 'high'/'medium'/'low' según data quality
    - action: qué hacer
    """
    
    if baselines is None:
        baselines = {}
    
    risk_score = 0
    factors = []
    data_points = 0
    
    # ACWR risk (normalizado)
    if pd.notna(acwr):
        if acwr > 1.5:
            risk_score += 30
            factors.append(f'ACWR muy alto ({acwr:.2f})')
        elif acwr > 1.3:
            risk_score += 15
            factors.append(f'ACWR elevado ({acwr:.2f})')
        data_points += 1
    
    # Sleep risk
    if sleep_hours < 6.5:
        risk_score += 25
        factors.append(f'Sueño muy bajo ({sleep_hours}h)')
    elif sleep_hours < 7:
        risk_score += 10
        factors.append(f'Sueño bajo ({sleep_hours}h)')
    data_points += 1
    
    # Performance + effort mismatch
    if pd.notna(performance_index) and effort_level >= 8:
        if performance_index < 0.98:
            risk_score += 20
            factors.append('Performance cayendo + esfuerzo alto')
        elif performance_index < 1.0:
            risk_score += 10
            factors.append('Performance estable pero esfuerzo alto')
        data_points += 1
    
    # High strain consecutive days
    if days_high_strain >= 2:
        risk_score += 15
        factors.append(f'{days_high_strain}+ días de alta exigencia')
    
    # Readiness check
    if readiness_score < 40:
        risk_score += 10
        factors.append('Readiness muy bajo')
    
    # Fatiga reportada (nuevo factor - considera effort_level como proxy de CNS fatigue)
    if effort_level >= 8:
        risk_score += 12
        factors.append('Fatiga CNS alta reportada')
    
    # Dolor localizado (nuevo factor)
    if pain_flag:
        risk_score += 8
        factors.append('Dolor localizado detectado')
    
    # Data quality assessment
    if data_points < 2:
        factors.append('⚠️ Pocos datos para evaluación confiable')
        confidence = 'low'
    elif data_points < 3:
        confidence = 'medium'
    else:
        confidence = 'high'
    
    # Cap at 100
    risk_score = min(risk_score, 100)
    
    # Classify
    if risk_score >= 60:
        level = 'high'
        emoji = '🔴'
        action = 'DELOAD OBLIGATORIO. Reduce volumen -30%, evita máximos.'
    elif risk_score >= 35:
        level = 'medium'
        emoji = '🟡'
        action = 'Precaución. Entrena pero sin buscar máximos. Foco en técnica.'
    else:
        level = 'low'
        emoji = '🟢'
        action = 'Bajo riesgo. Puedes entrenar normal.'
    
    return {
        'risk_level': level,
        'score': risk_score,
        'emoji': emoji,
        'factors': factors,
        'confidence': confidence,
        'action': action
    }


def suggest_weekly_sequence(
    last_7_days_strain: List[float],
    last_7_days_monotony: float,
    last_7_days_readiness_mean: float,
    baselines: Dict = None,
    last_week_high_days: int = 0
) -> Dict[str, Any]:
    """
    Sugiere secuencia de próxima semana basada en tendencias personales.
    
    Lógica:
    - Si strain alto (vs p75 personal) + monotony alto → intercala + deload
    - Si readiness baja → deload obligatorio
    - Baseline: push-normal-normal-push-reduce-deload-rest
    
    Args:
        baselines: dict con percentiles personales (para comparar strain)
    
    Retorna dict con:
    - sequence: list de 7 dicts {day, type, description}
    - reasoning: por qué esta secuencia
    """
    
    if baselines is None:
        baselines = {}
    
    # Normalizar contra p75 personal si está disponible
    strain_p75 = baselines.get('_strain_p75')
    
    # Si no hay baseline de strain, usar comparación directa vs mean
    if strain_p75 is not None and strain_p75 > 0:
        strain_mean = np.mean(last_7_days_strain)
        strain_percentile = strain_mean / strain_p75  # Ahora sí tiene sentido (0.5 = bajo, 1.0 = p75, >1 = muy alto)
    else:
        # Fallback: asumir que están en rango razonable (no normalizar)
        strain_percentile = 0.5  # neutral si no hay datos
    
    sequence = [
        {'day': 'Lun', 'type': 'push', 'description': 'Push day intenso'},
        {'day': 'Mar', 'type': 'normal', 'description': 'Volumen normal'},
        {'day': 'Mié', 'type': 'normal', 'description': 'Técnica + accesorios'},
        {'day': 'Jue', 'type': 'push', 'description': 'Push day secundario'},
        {'day': 'Vie', 'type': 'reduce', 'description': 'Reduce -20%'},
        {'day': 'Sáb', 'type': 'deload', 'description': 'Deload suave'},
        {'day': 'Dom', 'type': 'rest', 'description': 'Descanso total'}
    ]
    
    reasoning = "Baseline: push-normal-normal-push-reduce-deload-rest"
    
    # Ajustar si strain fue alto (vs p75 personal)
    if strain_percentile > 0.8:
        sequence[1] = {'day': 'Mar', 'type': 'reduce', 'description': 'Reduce post-alta carga'}
        reasoning = f"Strain alto ({strain_percentile:.1%} vs p75) → reduce en Mar"
    
    # Si monotony fue muy alta (>1.5 en escala clásica)
    if last_7_days_monotony > 1.5:
        sequence[2] = {'day': 'Mié', 'type': 'switch', 'description': 'Cambia patrón (tren opuesto)'}
        reasoning = f"Monotony alta ({last_7_days_monotony:.2f}) → intercala en Mié"
    
    # Si readiness fue muy baja
    if last_7_days_readiness_mean < 50:
        sequence[4] = {'day': 'Vie', 'type': 'deload', 'description': 'Deload completo'}
        sequence[5] = {'day': 'Sáb', 'type': 'rest', 'description': 'Descanso'}
        reasoning = f"Readiness baja ({last_7_days_readiness_mean:.0f}) → deload en Vie-Sáb"
    
    return {
        'sequence': sequence,
        'reasoning': reasoning,
        'avg_strain_percentile': strain_percentile,
        'monotony': last_7_days_monotony,
        'readiness_mean': last_7_days_readiness_mean
    }
