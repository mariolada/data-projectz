# 🚀 Guía Rápida - Cómo Usar los Módulos Refactorizados

## 📌 TL;DR (Resumen Ultra-Corto)

El dashboard ha sido refactorizado en 10 módulos. **TODO FUNCIONA** sin cambios en la interfaz.

### Para entender la estructura
```bash
# 1. Lee esto primero (5 min)
cat ARQUITECTURA_MODULAR.md

# 2. Luego esto (3 min)
cat REFACTORIZACION_COMPLETADA.md

# 3. Run tests para validar
python test_integration.py
```

---

## 📚 Documentación Disponible

| Archivo | Propósito | Lectura |
|---------|----------|---------|
| **ARQUITECTURA_MODULAR.md** | Guía COMPLETA de cada módulo | 15 min |
| **REFACTORIZACION_COMPLETADA.md** | Resumen ejecutivo + próximos pasos | 5 min |
| **CAMBIOS_REALIZADOS.md** | Qué archivos se crearon/modificaron | 3 min |
| **README.md** | Documentación general del proyecto | 10 min |

---

## 🎯 Si quieres...

### 📖 Entender la arquitectura modular
```bash
open ARQUITECTURA_MODULAR.md
# O abre en VS Code: Ctrl+Shift+O en el archivo
```

### 🧪 Validar que todo funciona
```bash
python test_integration.py
# Verifica que todos los módulos importan y funcionan
```

### 💻 Ver ejemplo de uso en código
Ver sección "Flujo de importes típico en `streamlit_app.py`" en:
- `README.md` → sección "🏗️ Arquitectura Modular"
- `ARQUITECTURA_MODULAR.md` → sección "🔄 Flujo de importes en streamlit_app.py"

### 🔧 Agregar una nueva feature
1. Lee `ARQUITECTURA_MODULAR.md` → "🚀 Cómo agregar features"
2. Elige módulo o crea nuevo
3. Actualiza `__init__.py` del módulo
4. Importa en `streamlit_app.py`

### 📊 Ver qué se creó exactamente
```bash
open CAMBIOS_REALIZADOS.md
# Tabla completa de archivos creados/modificados
```

---

## 🗂️ Estructura Visual

```
app/
├── config.py              ← Constantes (COLORS, READINESS_ZONES, etc.)
│
├── ui/                    ← Estilos y componentes visuales
│   ├── theme.py          ← CSS gaming-dark (550 líneas)
│   └── components.py     ← Títulos reutilizables
│
├── charts/               ← Gráficas Plotly
│   ├── daily_charts.py   ← 6 gráficas diarias
│   └── weekly_charts.py  ← 2 gráficas semanales
│
├── calculations/         ← Lógica de cálculo
│   ├── readiness_calc.py ← Fórmula de readiness (v1 y v2)
│   ├── injury_risk.py    ← Riesgo de lesión
│   └── plans.py          ← Generación de planes
│
└── data/                 ← Cargar y formatear datos
    ├── loader.py        ← CSV y JSON
    └── formatters.py    ← Zonas, confianza, etc.
```

---

## ⚡ Ejemplos Rápidos

### Usar readiness
```python
from app.calculations import calculate_readiness_from_inputs_v2

score = calculate_readiness_from_inputs_v2(
    sleep_hours=7.5,
    sleep_quality=4,
    fatigue=3,
    soreness=2,
    stress=5,
    motivation=8,
    pain_flag=False,
    perceived_readiness=7
)
print(f"Readiness: {score}/100")  # Readiness: 70/100
```

### Usar zona
```python
from app.data.formatters import get_readiness_zone

zona, emoji, color = get_readiness_zone(70)
print(f"{emoji} {zona} ({color})")  # 🟡 Media (#FFB81C)
```

### Usar plan
```python
from app.calculations import generate_actionable_plan_v2

zone, plan, rules = generate_actionable_plan_v2(
    readiness=70,
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

print(zone)  # 🟡 MEDIA
for rec in plan:
    print(f"  • {rec}")
for rule in rules:
    print(f"  ✓ {rule}")
```

### Usar gráfica
```python
import pandas as pd
from app.charts import create_readiness_chart

# data debe ser Series con índice datetime
data = pd.Series([70, 75, 68, 72], 
                 index=pd.date_range('2024-01-01', periods=4))

fig = create_readiness_chart(data, "Mi Readiness")
fig.show()  # O st.plotly_chart(fig) en Streamlit
```

### Usar CSS
```python
import streamlit as st
from app.ui.theme import get_theme_css

st.markdown(get_theme_css(), unsafe_allow_html=True)
st.write("Ahora todo tiene estilo gaming-dark 🎮")
```

---

## ✨ Ventajas de los Módulos

| Ventaja | Cómo lo ves |
|---------|-----------|
| **Más legible** | Cada módulo hace UNA cosa |
| **Más mantenible** | Error en readiness? Mira `calculations/readiness_calc.py` |
| **Más testeable** | `pytest app/calculations/` sin Streamlit |
| **Más reutilizable** | Importa cualquier módulo en otro proyecto |
| **Mejor documentado** | Cada función tiene docstring detallado |

---

## 🎓 Aprendizaje Progresivo

### Nivel 1: Usuario (15 min)
- Lee esta página
- Ejecuta `python test_integration.py`
- ¡Listo!

### Nivel 2: Desarrollador (1 hora)
- Lee `ARQUITECTURA_MODULAR.md`
- Entiende cómo importar cada módulo
- Entiende cómo agregar features

### Nivel 3: Arquitecto (2-3 horas)
- Lee código de cada módulo
- Entiende diseño y decisiones
- Eres capaz de refactorizar más

---

## ❓ Preguntas Frecuentes

**P: ¿El dashboard sigue igual?**
A: Sí, 100% idéntico. Solo el código interno está organizado.

**P: ¿Debo cambiar cómo uso el dashboard?**
A: No. Usa `streamlit run app/streamlit_app.py` como siempre.

**P: ¿Cómo importo un módulo?**
A: `from app.calculations import calculate_readiness_from_inputs_v2`

**P: ¿Qué pasa si me equivoco?**
A: Los tests te avisan: `python test_integration.py`

**P: ¿Dónde está el CSS?**
A: En `app/ui/theme.py` (~550 líneas)

**P: ¿Dónde está la fórmula de readiness?**
A: En `app/calculations/readiness_calc.py` (~140 líneas)

**P: ¿Puedo usar esto en otro proyecto?**
A: Sí. Copia el folder `app/` e importa lo que necesites.

---

## 🚨 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'app.calculations'"
```bash
# Asegúrate de estar en la carpeta raíz
cd /path/to/data-projectz
python test_integration.py  # ← Debe funcionar
```

### Error: "ImportError: cannot import name 'X' from 'app.Y'"
```bash
# Verifica que el nombre está en __init__.py
cat app/calculations/__init__.py
# Debe incluir "X" en __all__
```

### Error: "Readiness calculation returns None"
```bash
# Verifica todos los parámetros están presentes
from app.calculations import calculate_readiness_from_inputs_v2
help(calculate_readiness_from_inputs_v2)  # Ver docstring
```

---

## 📞 Contacto Rápido

| Necesito... | Mira... |
|-----------|---------|
| Entender toda la arquitectura | ARQUITECTURA_MODULAR.md |
| Ver cambios específicos | CAMBIOS_REALIZADOS.md |
| Resumen ejecutivo | REFACTORIZACION_COMPLETADA.md |
| Ejemplos de código | README.md (sección 🏗️) |
| Validar que funciona | `python test_integration.py` |

---

## 🎉 Conclusión

Los módulos están **listos para usar**. 

Próximo paso: Actualizar `streamlit_app.py` para importar de módulos (mantiene funcionalidad 100% idéntica).

**¿Preguntas? Lee ARQUITECTURA_MODULAR.md** 📖
