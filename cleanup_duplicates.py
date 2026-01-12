#!/usr/bin/env python
"""
Script para remover funciones duplicadas de streamlit_app.py
Mantiene solo las funciones que NO están en los módulos importados
"""

import re

filepath = r"c:\Users\mario.lada\Desktop\data-projectz\app\streamlit_app.py"

# Leer el archivo
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Funciones a remover (están duplicadas en los módulos importados)
functions_to_remove = [
    # Carga de datos (en data/loader.py)
    r"@st\.cache_data\ndef load_csv\(.*?\n    return df\n\n",
    r"@st\.cache_data\ndef load_user_profile\(.*?\n    except:\n        return \{\}\n\n",
    
    # Formatters (en data/formatters.py)
    r"def get_readiness_zone\(readiness\):\n.*?return \(\"Muy baja\", \"🔴\", \"#FF4444\"\)\n\n",
    r"def get_days_until_acwr\(df_daily, selected_date\):\n.*?return len\(filtered\)\n\n",
    r"def format_acwr_display\(acwr, days_available\):\n.*?return f\"\{round\(float\(acwr\), 3\)\}\"\n\n",
    r"def get_confidence_level\(df_daily, selected_date\):\n.*?return \"Alta \(>28 días\)\", \"✅\"\n",
    
    # Plan generation (en calculations/plans.py)
    r"def generate_actionable_plan\(readiness, pain_flag, pain_location,.*?\n    return f\"\{emoji\} \{zone\}\", plan, rules\n\n",
    
    # Readiness calculations (en calculations/readiness_calc.py)
    r"def calculate_readiness_from_inputs\(sleep_hours, sleep_quality,.*?\n    return readiness_score\n\n",
    r"def calculate_readiness_from_inputs_v2\(\n.*?\n    return readiness_score\n\n",
    
    # Charts (en charts/daily_charts.py y charts/weekly_charts.py)
    r"def create_readiness_chart\(data.*?\n    return fig\n\n",
    r"def create_volume_chart\(data.*?\n    return fig\n\n",
    r"def create_sleep_chart\(data.*?\n    return fig\n\n",
    r"def create_acwr_chart\(data.*?\n    return fig\n\n",
    r"def create_performance_chart\(data.*?\n    return fig\n\n",
    r"def create_strain_chart\(data.*?\n    return fig\n",
    r"def create_weekly_volume_chart\(data.*?\n    return fig\n\n",
    r"def create_weekly_strain_chart\(data.*?\n    return fig\n\n",
    
    # Plan generation v2 (en calculations/plans.py)
    r"def generate_actionable_plan_v2\(.*?\n    return zone_display, plan, rules\n\n",
    
    # Injury risk v2 (en calculations/injury_risk.py)
    r"def calculate_injury_risk_score_v2\(.*?\n    \}\n\n",
    
    # Render section title (en ui/components.py)
    r"def render_section_title\(text, accent=\"#B266FF\"\):\n.*?\"\"\", unsafe_allow_html=True\)\n\n",
]

print(f"Archivo original: {len(content)} caracteres, {content.count(chr(10))} líneas")

# Contar funciones encontradas
for i, pattern in enumerate(functions_to_remove):
    matches = len(re.findall(pattern, content, re.DOTALL))
    print(f"Patrón {i}: {matches} coincidencia(s)")

# No vamos a hacer los reemplazos en este script, solo contar
print(f"\nUsaremos una estrategia de reemplazo individual más segura en el editor.")
