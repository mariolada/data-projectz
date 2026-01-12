"""
Test de integración: Verificar que todos los módulos funcionan juntos
Archivo: test_integration.py
"""

def test_all_imports():
    """Prueba que todos los módulos se importan correctamente."""
    
    # === Importes de config ===
    from app.config import COLORS, READINESS_ZONES, DEFAULT_READINESS_WEIGHTS
    
    # === Importes de UI ===
    from app.ui.theme import get_theme_css
    from app.ui.components import render_section_title
    
    # === Importes de datos ===
    from app.data.loader import load_csv, load_user_profile
    from app.data.formatters import get_readiness_zone
    
    # === Importes de cálculos ===
    from app.calculations import (
        calculate_readiness_from_inputs_v2,
        calculate_injury_risk_score_v2,
        generate_actionable_plan_v2
    )
    
    # === Importes de gráficas ===
    from app.charts import (
        create_readiness_chart,
        create_volume_chart,
        create_sleep_chart,
        create_weekly_volume_chart
    )
    
    print("✅ TODAS LAS IMPORTACIONES EXITOSAS")
    return True


def test_calculations():
    """Prueba que los cálculos funcionan."""
    from app.calculations import (
        calculate_readiness_from_inputs_v2,
        generate_actionable_plan_v2
    )
    from app.data.formatters import get_readiness_zone
    
    # Test: Función de readiness
    readiness_score = calculate_readiness_from_inputs_v2(
        sleep_hours=7.5,
        sleep_quality=4,
        fatigue=3,
        soreness=2,
        stress=5,
        motivation=8,
        pain_flag=False,
        perceived_readiness=7
    )
    print(f"✅ calculate_readiness_from_inputs_v2() = {readiness_score}/100")
    
    # Test: Función de zona
    zone_name, emoji, color = get_readiness_zone(readiness_score)
    print(f"✅ get_readiness_zone({readiness_score}) = {emoji} {zone_name} ({color})")
    
    # Test: Plan de acción
    zone_display, plan, rules = generate_actionable_plan_v2(
        readiness=readiness_score,
        pain_flag=False,
        pain_zone=None,
        pain_severity=0,
        pain_type=None,
        fatigue=3,
        soreness=2,
        stiffness=1,
        sick_flag=False,
        session_goal="Hipertrofia",
        fatigue_analysis={"type": "central", "target_split": "push"}
    )
    print(f"✅ generate_actionable_plan_v2() = {zone_display}")
    print(f"   → {len(plan)} recomendaciones, {len(rules)} reglas")
    
    return True


def test_constants():
    """Prueba que las constantes son accesibles."""
    from app.config import COLORS, READINESS_ZONES
    
    print(f"\n✅ COLORES Y ZONAS DISPONIBLES:")
    print(f"   COLORS['green'] = {COLORS['green']}")
    print(f"   READINESS_ZONES['HIGH']['name'] = {READINESS_ZONES['HIGH']['name']}")
    
    return True


if __name__ == "__main__":
    print("🧪 INICIANDO TESTS DE INTEGRACIÓN MODULAR\n")
    print("=" * 60)
    
    test_all_imports()
    print()
    test_constants()
    print()
    test_calculations()
    
    print("\n" + "=" * 60)
    print("🎉 TODOS LOS TESTS PASARON - REFACTORIZACIÓN EXITOSA")
