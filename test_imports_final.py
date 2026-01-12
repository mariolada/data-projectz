#!/usr/bin/env python
"""Test imports from streamlit_app.py"""

import sys
from pathlib import Path

# Add paths
app_dir = Path(r"c:\Users\mario.lada\Desktop\data-projectz\app")
project_root = app_dir.parent
src_dir = project_root / "src"

sys.path.insert(0, str(app_dir))
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(src_dir))

try:
    # Import config
    from config import COLORS, READINESS_ZONES, DEFAULT_READINESS_WEIGHTS, DAILY_PATH, USER_PROFILE_PATH
    print("✅ Config imports OK")
    
    # Import UI
    from ui.theme import get_theme_css
    from ui.components import render_section_title
    print("✅ UI imports OK")
    
    # Import Charts
    from charts.daily_charts import (
        create_readiness_chart,
        create_volume_chart,
        create_sleep_chart,
        create_acwr_chart,
        create_performance_chart,
        create_strain_chart
    )
    from charts.weekly_charts import create_weekly_volume_chart, create_weekly_strain_chart
    print("✅ Charts imports OK")
    
    # Import Calculations
    from calculations.readiness_calc import (
        calculate_readiness_from_inputs_v2,
        calculate_readiness_from_inputs
    )
    from calculations.injury_risk import calculate_injury_risk_score_v2, calculate_injury_risk_score
    from calculations.plans import generate_actionable_plan_v2, generate_actionable_plan
    print("✅ Calculations imports OK")
    
    # Import Data
    from data.loader import load_csv, load_user_profile
    from data.formatters import (
        get_readiness_zone,
        get_days_until_acwr,
        get_confidence_level,
        format_acwr_display
    )
    print("✅ Data imports OK")
    
    # Import Personalization
    from personalization_engine import (
        calculate_personal_baselines,
        contextualize_readiness,
        detect_fatigue_type,
        suggest_weekly_sequence
    )
    print("✅ Personalization imports OK")
    
    print("\n✅✅✅ ALL IMPORTS SUCCESSFUL ✅✅✅")
    
except Exception as e:
    print(f"❌ Import error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
