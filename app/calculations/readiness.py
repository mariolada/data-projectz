"""
Readiness calculations: Todas las funciones de cálculo de readiness, zonas, riesgo y planes.
"""
import numpy as np
import pandas as pd
from pathlib import Path
import sys

# Añadir src al path para importar personalization_engine
sys.path.append(str(Path(__file__).parent.parent.parent / 'src'))
from personalization_engine import calculate_injury_risk_score


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


def get_anti_fatigue_flag(df_daily, selected_date):
    """Detecta si hay 2+ días seguidos de HIGH_STRAIN_DAY."""
    if 'readiness_score' not in df_daily.columns:
        return False
    
    sorted_df = df_daily.sort_values('date')
    selected_idx = sorted_df[sorted_df['date'] == selected_date].index
    
    if len(selected_idx) == 0:
        return False
    
    idx = selected_idx[0]
    if idx == 0:
        return False
    
    current_readiness = sorted_df.loc[idx, 'readiness_score']
    prev_readiness = sorted_df.loc[idx - 1, 'readiness_score']
    
    return pd.notna(current_readiness) and pd.notna(prev_readiness) and current_readiness < 50 and prev_readiness < 50


def format_reason_codes(reason_codes_str):
    """Convierte string de reason codes a lista legible."""
    if pd.isna(reason_codes_str) or reason_codes_str == '':
        return []
    codes = str(reason_codes_str).split('|')
    
    code_map = {
        'LOW_SLEEP': ' Sueño insuficiente',
        'HIGH_ACWR': ' Carga aguda muy alta',
        'PERF_DROP': ' Rendimiento en caída',
        'HIGH_EFFORT': 'Esfuerzo muy alto',
        'FATIGA': '⚠️ Fatiga detectada'
    }
    
    return [code_map.get(c.strip(), c.strip()) for c in codes if c.strip()]


def get_lift_recommendations(df_exercises, readiness_score, readiness_zone):
    """Genera recomendaciones por lift basadas en readiness."""
    if df_exercises.empty:
        return []
    
    recs = []
    for idx, row in df_exercises.head(3).iterrows():
        exercise = row['exercise']
        
        if readiness_zone == "Alta":
            action = f"+2.5% o +1 rep @ RIR2"
        elif readiness_zone == "Media":
            action = f"Mantener, técnica, RIR2–3"
        else:
            action = f"-10% sets, RIR3–4"
        
        recs.append(f"**{exercise}**: {action}")
    
    return recs


def calculate_readiness_from_inputs_v2(
    sleep_hours, sleep_quality, fatigue, soreness, stress, motivation, pain_flag,
    nap_mins=0, sleep_disruptions=False, energy=7, stiffness=2, 
    caffeine=0, alcohol=False, sick_level=0, perceived_readiness=None,
    baselines=None, adjustment_factors=None
):
    """
    Cálculo contextualizado de readiness v2 (legacy, usado por compatibilidad).
    
    Retorna: (readiness_score, breakdown_dict)
    """
    
    if baselines is None:
        baselines = {}
    if adjustment_factors is None:
        adjustment_factors = {
            'sleep_weight': 0.30,
            'fatigue_sensitivity': 1.0,
            'stress_sensitivity': 1.0,
            'sleep_responsive': True
        }
    
    # === 1. PERCEPCIÓN PERSONAL (anclaje inicial) ===
    # La percepción es importante pero no debe dominar el score
    if perceived_readiness is not None:
        perceived_score = perceived_readiness / 10
        perceived_component = 0.18 * perceived_score  # Reducido para dar más peso a métricas objetivas
        base_weight_multiplier = 0.85  # El 85% restante se reparte entre otros componentes
    else:
        perceived_component = 0
        base_weight_multiplier = 1.0
    
    breakdown = {
        'perceived_component': perceived_component * 100 if perceived_readiness else 0,
        'components': {},
        'context_adjustments': {},
        'notes': []
    }
    
    # === 2. RECUPERACIÓN (SUEÑO) ===
    # Sleep hours: 6h = 0.5, 7h = 0.83, 7.5h+ = 1.0 (más generoso)
    sleep_hours_score = np.clip((sleep_hours - 5.0) / (7.5 - 5.0), 0, 1)
    sleep_quality_score = (sleep_quality - 1) / 4  # 1=0, 5=1
    
    # Combinar horas y calidad
    sleep_base = (sleep_hours_score * 0.6 + sleep_quality_score * 0.4)
    
    # PERSONALIZACIÓN: Comparar contra tu baseline (impacto reducido)
    sleep_context_bonus = 0
    if baselines.get('sleep', {}).get('p50'):
        your_baseline = baselines['sleep']['p50']
        delta_sleep = sleep_hours - your_baseline
        
        if delta_sleep < -1.5:  # Solo penalizar si déficit > 1.5h
            sleep_deficit = abs(delta_sleep) - 1.5
            if adjustment_factors.get('sleep_responsive', True):
                sleep_context_bonus = -0.03 * sleep_deficit  # Reducido de 0.05
                breakdown['notes'].append(f"⚠️ Déficit de sueño notable: {abs(delta_sleep):.1f}h bajo tu media")
            else:
                sleep_context_bonus = -0.015 * sleep_deficit
        elif delta_sleep > 0.5:
            sleep_context_bonus = min(delta_sleep * 0.02, 0.05)  # Pequeño bonus
    
    # Bonus siesta
    nap_bonus = 0
    if nap_mins == 20:
        nap_bonus = 0.03
    elif nap_mins == 45:
        nap_bonus = 0.05
    elif nap_mins == 90:
        nap_bonus = 0.07
    
    # Penalizaciones (reducidas)
    disruption_penalty = 0.05 if sleep_disruptions else 0  # Reducido de 0.08
    alcohol_penalty = 0.12 if alcohol else 0  # Reducido de 0.20
    
    # Componente final de sueño (38% del restante = ~32 pts max)
    sleep_component = base_weight_multiplier * 0.38 * (
        sleep_base + nap_bonus + sleep_context_bonus
    ) - disruption_penalty - alcohol_penalty
    
    sleep_component = max(0, sleep_component)  # No puede ser negativo
    breakdown['components']['sleep'] = sleep_component * 100
    
    # === 3. ESTADO (FATIGA, ESTRÉS, ENERGÍA) ===
    fatigue_score = 1 - (fatigue / 10)
    stress_score = 1 - (stress / 10)
    energy_score = energy / 10
    soreness_score = 1 - (soreness / 10)
    
    # Sensibilidades personalizadas (impacto moderado)
    fatigue_sensitivity = adjustment_factors.get('fatigue_sensitivity', 1.0)
    stress_sensitivity = adjustment_factors.get('stress_sensitivity', 1.0)
    
    # Solo penalizar extra si fatiga es MUY alta (>7)
    fatigue_context = 0
    if fatigue > 7 and fatigue_sensitivity > 1.1:
        fatigue_context = -0.03  # Reducido de 0.08
        breakdown['notes'].append(f"⚠️ Fatiga muy alta detectada")
    
    # Stiffness muy tolerante (solo impacta si es muy alto)
    stiffness_penalty = (max(0, stiffness - 3) / 10) * 0.03  # Solo penaliza si >3
    
    # Componente estado (42% del restante = ~35 pts max)
    # Con inputs perfectos debe aportar ~35 pts
    state_component = base_weight_multiplier * 0.42 * (
        0.40 * energy_score +
        0.35 * fatigue_score * min(fatigue_sensitivity, 1.15) +
        0.20 * stress_score * min(stress_sensitivity, 1.15) +
        0.05 * soreness_score
    ) - stiffness_penalty + fatigue_context
    
    state_component = max(0, state_component)
    breakdown['components']['state'] = state_component * 100
    
    # === 4. MOTIVACIÓN (18% del restante = ~15 pts max)
    motivation_score = motivation / 10
    motivation_component = base_weight_multiplier * 0.18 * motivation_score
    breakdown['components']['motivation'] = motivation_component * 100
    
    # === 5. PENALIZACIONES FLAGS (más tolerantes) ===
    pain_penalty = 0.15 if pain_flag else 0  # Reducido de 0.25
    
    # Sick penalty más gradual
    sick_penalty_map = {0: 0.0, 1: 0.05, 2: 0.08, 3: 0.15, 4: 0.25, 5: 0.35}
    sick_penalty = sick_penalty_map.get(sick_level, 0.0)
    
    # Cafeína: solo penalizar si fatiga es ALTA
    caffeine_mask = 0
    if caffeine >= 3 and fatigue >= 7:  # Más restrictivo
        caffeine_mask = 0.05  # Reducido de 0.08
        breakdown['notes'].append(f"☕ Cafeína alta + fatiga → posible enmascaramiento")
    
    breakdown['context_adjustments'] = {
        'pain_penalty': -pain_penalty * 100,
        'sick_penalty': -sick_penalty * 100,
        'caffeine_mask': -caffeine_mask * 100
    }
    
    # === FÓRMULA FINAL ===
    readiness_0_1 = (perceived_component + sleep_component + state_component + motivation_component 
                    - pain_penalty - sick_penalty - caffeine_mask)
    
    readiness_0_1 = np.clip(readiness_0_1, 0, 1)
    readiness_score = int(round(readiness_0_1 * 100))
    
    breakdown['final_score'] = readiness_score
    
    return readiness_score, breakdown


def generate_personalized_insights(baselines, adjustment_factors, user_profile, df_daily):
    """
    Genera insights específicos sobre cómo variables afectan a ESTE usuario.
    Basado en evidencia histórica, no en promedios poblacionales.
    
    Retorna: dict con insights actionables
    """
    insights = {
        'sleep': '',
        'fatigue': '',
        'stress': '',
        'recovery': '',
        'archetype': ''
    }
    
    # Sleep insights
    if adjustment_factors.get('sleep_responsive'):
        sleep_baseline = baselines.get('sleep', {}).get('p50', 7.5)
        insights['sleep'] = f"TU PATRÓN: Eres SENSIBLE al sueño. Tu media es {sleep_baseline:.1f}h. Cada hora bajo este punto penaliza tu readiness. Recomendación: Prioriza 7.5-8h consistentemente."
    else:
        insights['sleep'] = "TU PATRÓN: NO eres muy sensible al sueño (algunos días rindes bien con <7h). Pero cuidado: mala CALIDAD sí afecta. Enfócate en dormir sin interrupciones."
    
    # Fatigue sensitivity
    fatigue_sens = adjustment_factors.get('fatigue_sensitivity', 1.0)
    if fatigue_sens > 1.2:
        insights['fatigue'] = "ERES HIPERSENSIBLE A LA FATIGA. Tu readiness cae rápido con volumen alto. Estrategia: Deloads cada 4-5 semanas, no cada 6."
    elif fatigue_sens < 0.8:
        insights['fatigue'] = "TOLERAS BIEN LA FATIGA. Puedes hacer bloques de alta carga sin colapsar. Pero no la ignores: acumula igual, solo lo ves después."
    else:
        insights['fatigue'] = "SENSIBILIDAD NORMAL a fatiga. Sigue protocolos estándar de periodización."
    
    # Recovery pattern
    if baselines.get('readiness', {}).get('std', 0) > 15:
        insights['recovery'] = "TU READINESS ES VARIABLE (fluctúa mucho). Indica: sensibilidad a carga semanal. Recomienda: tracking diario de carga + sleep + estrés."
    else:
        insights['recovery'] = "TU READINESS ES ESTABLE. Buen patrón de recuperación o poca variabilidad en entrenamientos. Mantén consistencia."
    
    # Archetype
    user_arch = user_profile.get('archetype', {}).get('archetype', 'unknown')
    if user_arch == 'short_sleeper':
        insights['archetype'] = " Eres SHORT SLEEPER: Rindes bien con <7h. Aprovechia para máximo volumen, pero cuidado con fatiga acumulada."
    elif user_arch == 'acwr_sensitive':
        insights['archetype'] = " Eres ACWR-SENSIBLE: ACWR alto (>1.5) te reduce readiness rápido. Monitorea ACWR semanal."
    elif user_arch == 'consistent_performer':
        insights['archetype'] = " Eres CONSISTENT: Tu readiness es predecible. Ventaja: puedes planificar bloques con confianza."
    
    return insights


def get_readiness_zone(readiness):
    """Retorna (zone_text, emoji, color) basado en readiness score."""
    if readiness is None or pd.isna(readiness):
        return "N/D", "❓", "#999999"
    
    readiness = float(readiness)
    
    if readiness >= 80:
        return "Alta", "🟢", "#00D084"
    elif readiness >= 55:
        return "Media", "🟡", "#FFB81C"
    else:
        return "Muy baja", "🔴", "#FF6B6B"


def get_days_until_acwr(df_daily, selected_date):
    """Retorna días disponibles para el cálculo de ACWR (necesita 28 días para precisión)."""
    sorted_df = df_daily.sort_values('date')
    selected_idx = sorted_df[sorted_df['date'] == selected_date].index
    
    if len(selected_idx) == 0:
        return 0
    
    idx = selected_idx[0]
    days_count = idx + 1
    return min(days_count, 28)


def format_acwr_display(acwr_value, days_available):
    """Formatea el valor de ACWR con advertencia de confianza según días disponibles."""
    if acwr_value is None or pd.isna(acwr_value):
        return "—"
    
    acwr_str = f"{acwr_value:.2f}"
    
    if days_available < 7:
        return f"{acwr_str} ⚠️"
    elif days_available < 28:
        return f"{acwr_str} ℹ️"
    else:
        return acwr_str


def generate_actionable_plan(readiness, pain_flag, pain_location, fatigue, soreness, session_goal="fuerza"):
    """Genera un plan accionable basado en readiness y condiciones."""
    
    plan = []
    rules = []
    
    if readiness >= 80:
        zone = "Alta"
        emoji = "🟢"
        reco = "Push day"
        intensity_rir = "RIR 1–2 (máximo 1–2 reps de reserva)"
        volume_adjust = "+10% sets en lifts clave"
    elif readiness >= 55:
        zone = "Media"
        emoji = "🟡"
        reco = "Normal"
        intensity_rir = "RIR 2–3 (técnica impecable)"
        volume_adjust = "Mantén volumen, prioriza técnica"
    else:
        zone = "Muy baja"
        emoji = "🔴"
        reco = "Reduce / Deload"
        intensity_rir = "RIR 3–5 (conservador)"
        volume_adjust = "-20% sets, accesorio ligero"
    
    plan.append(f"**Recomendación:** {reco}")
    plan.append(f"**Intensidad:** {intensity_rir}")
    plan.append(f"**Volumen:** {volume_adjust}")
    
    if readiness >= 80:
        rules.append("✅ Busca PRs o máximos hoy")
        rules.append("✅ Siente libertad de empujar en los 3 últimos sets")
    elif readiness >= 55:
        rules.append("⚖️ Mantén intensidad, cuida forma")
        rules.append("⚖️ Si algo duele, sustituye el ejercicio")
    else:
        rules.append("⛔ Evita RIR≤1 hoy")
        rules.append("⛔ Recorta 1–2 series por ejercicio")
    
    if pain_flag and pain_location:
        rules.append(f"🩹 Dolor en {pain_location}: evita movimientos bruscos, sustituye si es necesario")
    
    if fatigue >= 7:
        rules.append(" Fatiga alta: reduce volumen en 20%, alarga descansos")
    
    if soreness >= 7:
        rules.append(" Agujetas: calentamiento largo, movimiento ligero, accesorios >12 reps")
    
    return f"{emoji} {zone}", plan, rules


def calculate_injury_risk_score_v2(
    readiness_score, acwr, sleep_hours, performance_index, effort_level,
    pain_flag=False, pain_severity=0, stiffness=0, sick_level=0, 
    last_hard=False, baselines=None, days_high_strain=0
):
    """Versión mejorada con pain_severity, stiffness, sick_level."""
    
    base_risk = calculate_injury_risk_score(
        readiness_score, acwr, sleep_hours, performance_index, effort_level,
        pain_flag, baselines, days_high_strain
    )
    
    extra_score = 0
    extra_factors = []
    
    if pain_severity >= 7:
        extra_score += 15
        extra_factors.append(f'Dolor severo ({pain_severity}/10)')
    elif pain_severity >= 5:
        extra_score += 8
        extra_factors.append(f'Dolor moderado ({pain_severity}/10)')
    
    if stiffness >= 7:
        extra_score += 10
        extra_factors.append(f'Rigidez articular alta ({stiffness}/10)')
    
    if sick_level >= 5:
        extra_score += 35
        extra_factors.append(f'⚠️ Estado grave de enfermedad (nivel {sick_level}/5)')
    elif sick_level >= 3:
        extra_score += 25
        extra_factors.append(f'⚠️ Estado moderado de enfermedad (nivel {sick_level}/5)')
    elif sick_level >= 1:
        extra_score += 10
        extra_factors.append(f'Estado leve de enfermedad (nivel {sick_level}/5)')
    
    if last_hard:
        extra_score += 8
        extra_factors.append('Último entreno muy exigente (48h)')
    
    new_score = min(base_risk['score'] + extra_score, 100)
    
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


def generate_actionable_plan_v2(
    readiness, pain_flag, pain_zone, pain_severity, pain_type,
    fatigue, soreness, stiffness, sick_level, session_goal, fatigue_analysis
):
    """Versión mejorada: genera plan ultra-específico con pain_zone y fatigue_type."""
    
    plan = []
    rules = []
    zone_display = ""
    
    if sick_level >= 3:
        zone_display = "ENFERMO - NO ENTRENAR"
        plan.append(f" **Estado**: Enfermo (nivel {sick_level}/5)")
        plan.append("⛔ **Recomendación**: DESCANSO TOTAL hasta recuperación")
        plan.append(" Prioriza: hidratación, sueño, nutrición")
        rules.append("❌ NO entrenar bajo ninguna circunstancia")
        rules.append("❌ Evita ejercicio hasta estar 100% sano")
        return zone_display, plan, rules
    elif sick_level >= 1:
        plan.append(f"⚠️ Malestar leve detectado (nivel {sick_level}/5)")
        plan.append("Considera deload o descanso si empeora")
    
    if readiness >= 80:
        zone_display = "🟢 ALTA"
        reco = "Push day - busca PRs"
        intensity_rir = "RIR 1–2"
        volume_adjust = "+10% sets"
    elif readiness >= 55:
        zone_display = "🟡 MEDIA"
        reco = "Normal - mantén técnica"
        intensity_rir = "RIR 2–3"
        volume_adjust = "Volumen estándar"
    else:
        zone_display = "🔴 BAJA"
        reco = "Deload - reduce carga"
        intensity_rir = "RIR 3–5"
        volume_adjust = "-20% sets"
    
    plan.append(f"**Zona**: {zone_display}")
    plan.append(f"**Recomendación base**: {reco}")
    plan.append(f"**Intensidad**: {intensity_rir}")
    plan.append(f"**Volumen**: {volume_adjust}")
    
    plan.append("")
    plan.append(f"**Tipo de fatiga**: {fatigue_analysis['type'].upper()}")
    plan.append(f"**Split recomendado**: {fatigue_analysis['target_split'].upper()}")
    
    if pain_flag and pain_zone:
        plan.append("")
        plan.append(f"🩹 **Dolor detectado**: {pain_zone} ({pain_severity}/10, {pain_type})")
        
        avoid_movements = []
        ok_movements = []
        
        if pain_zone in ["Hombro"]:
            avoid_movements = ["Press banca", "Press militar", "Fondos", "Dominadas"]
            ok_movements = ["Sentadilla", "Peso muerto", "Curl piernas", "Prensa"]
        elif pain_zone in ["Codo", "Muñeca"]:
            avoid_movements = ["Press banca agarre cerrado", "Curl", "Extensiones tríceps"]
            ok_movements = ["Pierna completa", "Sentadilla", "Peso muerto (trap bar)"]
        elif pain_zone in ["Espalda baja"]:
            avoid_movements = ["Peso muerto convencional", "Buenos días", "Sentadilla baja"]
            ok_movements = ["Prensa", "Extensiones cuádriceps", "Curl femoral", "Press banca"]
        elif pain_zone in ["Rodilla"]:
            avoid_movements = ["Sentadilla profunda", "Extensiones", "Saltos"]
            ok_movements = ["Tren superior completo", "Curl femoral (con precaución)"]
        elif pain_zone in ["Tobillo"]:
            avoid_movements = ["Sentadilla", "Peso muerto", "Gemelos de pie"]
            ok_movements = ["Tren superior", "Prensa (ángulo reducido)"]
        else:
            avoid_movements = ["Movimientos que generen dolor"]
            ok_movements = ["Patrones opuestos a la zona afectada"]
        
        plan.append(f"❌ **Evita hoy**: {', '.join(avoid_movements)}")
        plan.append(f"✅ **Puedes hacer**: {', '.join(ok_movements)}")
        
        if pain_severity >= 7:
            plan.append(f"⚠️ **Severidad alta**: considera fisio o valoración médica")
    
    if stiffness >= 7:
        plan.append("")
        plan.append(f"🦴 **Rigidez alta** ({stiffness}/10): añade +15 min calentamiento")
        plan.append("🔥 Foam roll + movilidad dinámica obligatoria")
    
    rules.append("✅ Calienta progresivamente (5-10 min mínimo)")
    rules.append("✅ Respeta RIR indicado, no lo fuerces")
    rules.append("✅ Hidratación constante durante sesión")
    
    if pain_flag and pain_severity >= 5:
        rules.append(f"❌ STOP inmediato si dolor {pain_zone} empeora durante ejercicio")
        rules.append("✅ Movilidad suave post-sesión (15 min)")
    
    if fatigue >= 8:
        rules.append("⚠️ Fatiga muy alta: reduce volumen -30% mínimo")
        rules.append("⚠️ Si empiezas a notar mareo/náusea, termina sesión")
    
    if stiffness >= 7:
        rules.append("🧊 Considera terapia de frío/calor pre-sesión")
        rules.append("⚠️ No fuerces ROM (rango de movimiento) limitado")
    
    if readiness < 55:
        rules.append("⚠️ Prioriza técnica sobre carga hoy")
        rules.append("✅ Reduce tempo (más lento = menos estrés CNS)")
    
    return zone_display, plan, rules

from .readiness_v3 import calculate_readiness_from_inputs_v3_compat
