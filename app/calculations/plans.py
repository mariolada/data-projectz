"""
Generación de Plan Accionable de Entrenamiento
Módulo: calculations/plans.py
"""


def generate_actionable_plan_v2(
    readiness, pain_flag, pain_zone, pain_severity, pain_type,
    fatigue, soreness, stiffness, sick_flag, session_goal, fatigue_analysis
):
    """
    Versión mejorada: genera plan ultra-específico con pain_zone y fatigue_type.
    
    Parámetros:
    -----------
    readiness : int
        Score de readiness (0–100)
    pain_flag : bool
        ¿Hay dolor localizado?
    pain_zone : str or None
        Zona del dolor (e.g., "Hombro", "Espalda baja", "Rodilla")
    pain_severity : int
        Severidad del dolor (0–10)
    pain_type : str or None
        Tipo de dolor (e.g., "Dolor", "Rigidez", "Inflamación")
    fatigue : int
        Fatiga general (0–10)
    soreness : int
        Agujetas (0–10)
    stiffness : int
        Rigidez articular (0–10)
    sick_flag : bool
        ¿Enfermo?
    session_goal : str
        Objetivo de sesión (e.g., "Fuerza", "Hipertrofia", "Resistencia")
    fatigue_analysis : dict
        Dict con keys:
            - 'type': str ('central', 'peripheral', 'metabolic')
            - 'target_split': str (e.g., 'push', 'pull', 'legs')
    
    Retorna:
    --------
    tuple: (zone_display, plan, rules)
        - zone_display: str (e.g., "🟢 ALTA", "🟡 MEDIA", "🔴 BAJA")
        - plan: list[str] (recomendaciones de entrenamiento)
        - rules: list[str] (reglas concretas a seguir)
    """
    
    plan = []
    rules = []
    zone_display = ""
    
    # Override si enfermo
    if sick_flag:
        zone_display = "ENFERMO - NO ENTRENAR"
        plan.append("🤒 **Estado**: Enfermo detectado")
        plan.append("⛔ **Recomendación**: DESCANSO TOTAL hasta recuperación")
        plan.append("💊 Prioriza: hidratación, sueño, nutrición")
        rules.append("❌ NO entrenar bajo ninguna circunstancia")
        rules.append("❌ Evita ejercicio hasta estar 100% sano")
        return zone_display, plan, rules
    
    # Clasificar readiness
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
    
    # Adaptar por tipo de fatiga
    plan.append("")
    plan.append(f"**Tipo de fatiga**: {fatigue_analysis['type'].upper()}")
    plan.append(f"**Split recomendado**: {fatigue_analysis['target_split'].upper()}")
    
    # Dolor localizado - RECOMENDACIONES MUY ESPECÍFICAS
    if pain_flag and pain_zone:
        plan.append("")
        plan.append(f"🩹 **Dolor detectado**: {pain_zone} ({pain_severity}/10, {pain_type})")
        
        # Mapear zona → ejercicios evitar/OK
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
    
    # Rigidez articular
    if stiffness >= 7:
        plan.append("")
        plan.append(f"🦴 **Rigidez alta** ({stiffness}/10): añade +15 min calentamiento")
        plan.append("🔥 Foam roll + movilidad dinámica obligatoria")
    
    # === REGLAS BASE (siempre visibles) ===
    rules.append("✅ Calienta progresivamente (5-10 min mínimo)")
    rules.append("✅ Respeta RIR indicado, no lo fuerces")
    rules.append("✅ Hidratación constante durante sesión")
    
    # Reglas específicas según condiciones
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


def generate_actionable_plan(readiness, pain_flag, pain_location, fatigue, soreness, session_goal="fuerza"):
    """
    Versión original (sin pain_zone específico, sin fatigue_analysis).
    Se mantiene por compatibilidad.
    
    Retorna: (zone_display, plan, rules)
    """
    
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
    
    # Reglas concretas
    if readiness >= 80:
        rules.append("✅ Busca PRs o máximos hoy")
        rules.append("✅ Siente libertad de empujar en los 3 últimos sets")
    elif readiness >= 55:
        rules.append("⚖️ Mantén intensidad, cuida forma")
        rules.append("⚖️ Si algo duele, sustituye el ejercicio")
    else:
        rules.append("⛔ Evita RIR≤1 hoy")
        rules.append("⛔ Recorta 1–2 series por ejercicio")
    
    # Pain management
    if pain_flag and pain_location:
        rules.append(f"🩹 Dolor en {pain_location}: evita movimientos bruscos, sustituye si es necesario")
    
    # Fatiga management
    if fatigue >= 7:
        rules.append("😴 Fatiga alta: reduce volumen en 20%, alarga descansos")
    
    # Soreness management
    if soreness >= 7:
        rules.append("🤕 Agujetas: calentamiento largo, movimiento ligero, accesorios >12 reps")
    
    return f"{emoji} {zone}", plan, rules
