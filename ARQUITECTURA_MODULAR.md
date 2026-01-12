# 📋 Guía de Estructura Modular - app/

**Actualización:** El código de `app/streamlit_app.py` ha sido refactorizado en módulos independientes y reutilizables. Esta guía explica la nueva estructura.

## 🏗️ Arquitectura Modular

```
app/
├── streamlit_app.py          ← MAIN: Punto de entrada única
├── config.py                 ← CONFIGURACIÓN: Constantes, rutas, colores
├── ui/                       ← UI: Estilos y componentes visuales
│   ├── __init__.py
│   ├── theme.py             ← CSS gaming-dark, colores neón
│   └── components.py        ← Badges, títulos, helpers UI
├── charts/                   ← GRÁFICAS: Plotly builders
│   ├── __init__.py
│   ├── daily_charts.py      ← Readiness, Volume, Sleep, ACWR, Performance, Strain
│   └── weekly_charts.py     ← Volume semanal, Strain semanal
├── calculations/            ← LÓGICA: Cálculos y decisiones
│   ├── __init__.py
│   ├── readiness_calc.py    ← calculate_readiness_from_inputs_v2
│   ├── injury_risk.py       ← calculate_injury_risk_score_v2
│   └── plans.py             ← generate_actionable_plan_v2
└── data/                    ← DATOS: Cargar, formatear, vistas
    ├── __init__.py
    ├── loader.py            ← load_csv, load_user_profile
    └── formatters.py        ← Zonas, confianza, formatos
```

---

## 📚 Módulos Disponibles

### 1️⃣ `config.py` - Configuración Global
**Responsabilidad:** Centralizar constantes, rutas, colores y opciones del formulario.

**Contenido clave:**
```python
# Paths
DAILY_PATH = "data/processed/daily.csv"
USER_PROFILE_PATH = "data/processed/user_profile.json"

# Colors (gaming theme)
COLORS = {
    "purple": "#B266FF",
    "green": "#00D084",
    "aqua": "#4ECDC4",
    ...
}

# Readiness zones
READINESS_ZONES = {
    "HIGH": {"min": 75, "name": "Alta", "emoji": "🟢"},
    "MEDIUM": {"min": 55, "name": "Media", "emoji": "🟡"},
    ...
}

# Form defaults
GOALS = ["Fuerza", "Hipertrofia", "Resistencia", ...]
NAPS = [0, 20, 45, 90]
```

**Usar en `streamlit_app.py`:**
```python
from config import COLORS, READINESS_ZONES, DAILY_PATH

print(COLORS["green"])  # "#00D084"
```

---

### 2️⃣ `ui/theme.py` - Estilos CSS
**Responsabilidad:** Alojar todo el CSS de la aplicación (gaming-dark theme).

**Contenido:**
- Paleta de colores (`--purple`, `--green`, etc.)
- Estilos de cards, badges, botones
- CSS del toggle pill "Rápido/Preciso"
- Estilos responsive

**Usar:**
```python
from ui.theme import get_theme_css

st.markdown(get_theme_css(), unsafe_allow_html=True)
```

---

### 3️⃣ `ui/components.py` - Componentes Visuales
**Responsabilidad:** Componentes de UI reutilizables (sin lógica).

**Contenido:**
- `render_section_title(text, accent)` → Renderiza titulos de sección estilizados

**Usar:**
```python
from ui.components import render_section_title

render_section_title("Tu Readiness HOY", accent="#00D084")
```

---

### 4️⃣ `charts/daily_charts.py` - Gráficas Diarias
**Responsabilidad:** Builders de Plotly para gráficas de tiempo-serie.

**Funciones:**
- `create_readiness_chart(data, title)`
- `create_volume_chart(data, title)`
- `create_sleep_chart(data, title)`
- `create_acwr_chart(data, title)`
- `create_performance_chart(data, title)`
- `create_strain_chart(data, title)`

**Particularidades:**
- ✅ Todas coercen el índice a `datetime64[ns]` para que `tickformat='%d/%m/%Y'` funcione
- ✅ Usan colores de `config.COLORS` (posible en futuro)
- ✅ Retornan `fig` de Plotly listo para `st.plotly_chart()`

**Usar:**
```python
from charts.daily_charts import create_readiness_chart

rts = df_filtered.set_index('date')['readiness_score'].sort_index()
fig = create_readiness_chart(rts, "Readiness")
st.plotly_chart(fig, use_container_width=True)
```

---

### 5️⃣ `charts/weekly_charts.py` - Gráficas Semanales
**Responsabilidad:** Bar charts para datos semanales.

**Funciones:**
- `create_weekly_volume_chart(data, title)`
- `create_weekly_strain_chart(data, title)`

**Usar:**
```python
from charts.weekly_charts import create_weekly_volume_chart

vol_data = df_weekly_filtered.set_index('week_start')['volume_week'].sort_index()
fig = create_weekly_volume_chart(vol_data, "Volumen Semanal")
st.plotly_chart(fig, use_container_width=True)
```

---

### 6️⃣ `calculations/readiness_calc.py` - Cálculo de Readiness
**Responsabilidad:** Algoritmo de readiness instantáneo desde inputs del usuario.

**Funciones:**
- `calculate_readiness_from_inputs_v2(sleep_hours, sleep_quality, fatigue, ...)` → `int` (0–100)
  - Integra sueño, fatiga, estrés, motivación
  - **Peso clave:** `perceived_readiness` (25% del score)
  - Maneja excepciones: alcohol, cafeína, enfermedad

**Usar:**
```python
from calculations.readiness_calc import calculate_readiness_from_inputs_v2

readiness = calculate_readiness_from_inputs_v2(
    sleep_hours=7.5,
    sleep_quality=4,
    fatigue=3,
    soreness=2,
    stress=5,
    motivation=8,
    pain_flag=False,
    perceived_readiness=7  # 0-10
)
print(readiness)  # e.g., 72
```

---

### 7️⃣ `calculations/injury_risk.py` - Riesgo de Lesión
**Responsabilidad:** Calcular riesgo de lesión considerando readiness, ACWR, dolor, etc.

**Funciones:**
- `calculate_injury_risk_score_v2(readiness_score, acwr, sleep_hours, ...)` → `dict`
  - Retorna: `{'risk_level': 'high'|'medium'|'low', 'score': int, 'emoji': str, 'factors': list, 'action': str}`
  - Penaliza: dolor severo, rigidez, enfermedad, último entreno muy exigente

**Usar:**
```python
from calculations.injury_risk import calculate_injury_risk_score_v2

risk = calculate_injury_risk_score_v2(
    readiness_score=45,
    acwr=1.4,
    sleep_hours=6,
    performance_index=0.95,
    effort_level=8,
    pain_flag=True,
    pain_severity=6,
    sick_flag=False
)
print(risk['emoji'])  # '🟡' (medium)
print(risk['action'])  # "Precaución. Entrena pero sin buscar máximos..."
```

---

### 8️⃣ `calculations/plans.py` - Plan Accionable
**Responsabilidad:** Generar plan específico de entrenamiento basado en condiciones del día.

**Funciones:**
- `generate_actionable_plan_v2(readiness, pain_flag, pain_zone, ..., fatigue_analysis)` → `(zone_display, plan, rules)`
  - `zone_display`: "🟢 ALTA", "🟡 MEDIA", "🔴 BAJA"
  - `plan`: `list[str]` de recomendaciones (sin emojis internos, limpios)
  - `rules`: `list[str]` de reglas concretas

**Usar:**
```python
from calculations.plans import generate_actionable_plan_v2

zone, plan, rules = generate_actionable_plan_v2(
    readiness=70,
    pain_flag=True,
    pain_zone="Hombro",
    pain_severity=5,
    pain_type="Dolor",
    fatigue=6,
    soreness=4,
    stiffness=3,
    sick_flag=False,
    session_goal="Hipertrofia",
    fatigue_analysis={"type": "central", "target_split": "push"}
)

for rec in plan:
    st.write(rec)
for rule in rules:
    st.write(rule)
```

---

### 9️⃣ `data/loader.py` - Cargar Datos
**Responsabilidad:** Funciones de carga y caché.

**Funciones:**
- `load_csv(path: str)` → `pd.DataFrame` (con fecha normalizada)
- `load_user_profile(profile_path: str)` → `dict` (perfil JSON o default)

**Usar:**
```python
from data.loader import load_csv, load_user_profile

df_daily = load_csv("data/processed/daily.csv")
profile = load_user_profile("data/processed/user_profile.json")
```

---

### 🔟 `data/formatters.py` - Formatear Datos
**Responsabilidad:** Helpers para traducir métricas a textos/formatos legibles.

**Funciones:**
- `get_readiness_zone(readiness: float)` → `(zona_str, emoji, color_hex)`
- `get_days_until_acwr(df_daily, selected_date)` → `int`
- `get_confidence_level(df_daily, selected_date)` → `(text, emoji)`
- `format_acwr_display(acwr, days_available)` → `str`
- `format_reason_codes(reason_codes_str)` → `list[str]`

**Usar:**
```python
from data.formatters import get_readiness_zone, get_confidence_level

zona, emoji, color = get_readiness_zone(82)
print(zona, emoji)  # "Alta", "🟢"

conf_text, conf_emoji = get_confidence_level(df_daily, selected_date)
st.info(f"{conf_emoji} {conf_text}")
```

---

## 🔄 Flujo de Importes en `streamlit_app.py`

**Ejemplo de un flujo de "Modo Hoy":**

```python
# 1. Setup
from config import COLORS, DEFAULT_READINESS_WEIGHTS, USER_PROFILE_PATH
from ui import get_theme_css, render_section_title
from ui.theme import get_theme_css

# 2. Aplicar CSS
st.markdown(get_theme_css(), unsafe_allow_html=True)

# 3. Cargar datos
from data.loader import load_csv, load_user_profile
df_daily = load_csv("data/processed/recommendations_daily.csv")
profile = load_user_profile(USER_PROFILE_PATH)

# 4. UI inputs
sleep_h = st.number_input("Horas de sueño", min_value=0.0, max_value=12.0, value=7.5)
perceived = st.slider("Sensación Personal", 0, 10, 5)

# 5. Calcular
from calculations.readiness_calc import calculate_readiness_from_inputs_v2
readiness = calculate_readiness_from_inputs_v2(
    sleep_hours=sleep_h,
    sleep_quality=4,
    fatigue=5,
    soreness=2,
    stress=4,
    motivation=7,
    pain_flag=False,
    perceived_readiness=perceived
)

# 6. Evaluar riesgo
from calculations.injury_risk import calculate_injury_risk_score_v2
risk = calculate_injury_risk_score_v2(readiness, 1.1, sleep_h, 1.0, 6)

# 7. Generar plan
from calculations.plans import generate_actionable_plan_v2
zone, plan, rules = generate_actionable_plan_v2(
    readiness, False, None, 0, None, 5, 2, 3, False, "Fuerza", {"type": "central"}
)

# 8. Renderizar
render_section_title("Tu Readiness HOY", accent="#00D084")
st.write(f"**Readiness:** {readiness}/100 {zone}")
for rec in plan:
    st.write(rec)

# 9. Gráficas
from charts.daily_charts import create_readiness_chart
fig = create_readiness_chart(df_daily.set_index('date')['readiness_score'], "Readiness")
st.plotly_chart(fig, use_container_width=True)
```

---

## ✨ Ventajas de la Modularización

| Aspecto | Antes | Después |
|--------|--------|---------|
| **Lineas de código** | 2647 líneas | 1 archivo principal + 10 módulos (cada uno ≤300 líneas) |
| **Mantenibilidad** | Difícil encontrar función | Fácil: cada módulo es independiente |
| **Testing** | No testeable | Cada módulo testeable por separado |
| **Reutilización** | Código copiado | Importa y usa en otros proyectos |
| **Documentación** | Mezclada en el código | Cada módulo documentado claramente |
| **Escalabilidad** | Agregar features → Caos | Agregar features → Nuevo módulo, ninguna colisión |
| **Debugging** | "El error está en streamlit_app.py en algún lado" | "El error está en `calculations/plans.py`, línea X" |

---

## 🚀 Cómo Agregar Nuevas Features

### Ejemplo: Agregar un nuevo tipo de gráfica

1. **Crea la función en `charts/`**
   ```python
   # charts/daily_charts.py
   def create_hrv_chart(data, title="HRV"):
       fig = go.Figure()
       # ... lógica
       return fig
   ```

2. **Actualiza `charts/__init__.py`**
   ```python
   from .daily_charts import create_hrv_chart
   __all__ = [..., "create_hrv_chart"]
   ```

3. **Usa en `streamlit_app.py`**
   ```python
   from charts import create_hrv_chart
   fig = create_hrv_chart(df_daily['hrv'])
   st.plotly_chart(fig)
   ```

### Ejemplo: Agregar una métrica de calculoreadiness

1. **Edita `calculations/readiness_calc.py`**
   ```python
   def calculate_readiness_from_inputs_v2(..., hrv_avg=None):
       # ... agregar hrv_component
   ```

2. **Listo.** No necesitas tocar otros módulos.

---

## 📖 Nomenclatura y Convenciones

- ✅ Nombres descriptivos: `create_readiness_chart`, `calculate_readiness_from_inputs_v2`, `get_confidence_level`
- ✅ Versiones explícitas: `_v2` indica "mejorado", rompe compatibilidad
- ✅ Módulos en minúsculas: `daily_charts.py`, `readiness_calc.py`
- ✅ Funciones en snake_case: `get_readiness_zone`, `format_reason_codes`
- ✅ Constantes en MAYÚS: `READINESS_ZONES`, `COLORS`, `DEFAULT_READINESS_WEIGHTS`
- ✅ Docstrings cortos pero claros: `"""Crea gráfica de readiness con estilo gaming y gradient."""`

---

## 🔍 Debugging & Introspección

### Ver qué importa un módulo
```python
import app.calculations.plans as plans
print(plans.__all__)
# ['generate_actionable_plan_v2']
```

### Ver configuración global
```python
from config import COLORS, READINESS_ZONES, GOALS
print(COLORS)  # diccionario de colores
print(READINESS_ZONES)  # zonas con emojis
```

### Ver disponible en charts
```python
from charts import *
print(dir())  # lista todas las funciones disponibles
```

---

## 📝 Próximos Pasos (Hoja de Ruta)

- [ ] Agregar `calculations/stats.py` para análisis histórico
- [ ] Crear `calculations/ml_models.py` para predicciones
- [ ] Tests unitarios para `calculations/`
- [ ] API rest en `app/api.py` (FastAPI)
- [ ] Exportar `config` a `.env` para producción
- [ ] Database layer en `data/db.py` (SQLite/PostgreSQL)

