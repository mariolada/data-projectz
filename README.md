# Sistema de Análisis de Rendimiento Deportivo

Este proyecto está diseñado como una experiencia inmersiva inspirada en "Solo Leveling", con una estética de videojuego que transforma el análisis de rendimiento deportivo en una aventura interactiva. El sistema cruza datos de entrenamiento de fuerza con variables de recuperación (principalmente sueño) para extraer métricas objetivas e insights accionables sobre progresión, fatiga y planificación de cargas.

## Características principales
- **Ingesta de datos**: Archivos CSV exportados desde wearables o introducidos manualmente.
- **Procesamiento**: Limpieza, normalización y cálculo de métricas con Pandas y NumPy.
- **Extracción de insights**: Reglas determinísticas y análisis descriptivo.
- **Visualización**: Interfaz web con Streamlit, diseñada con una temática de videojuego, incluyendo gráficos dinámicos y elementos interactivos.
- **Almacenamiento**: CSV en fases iniciales y SQLite para persistencia estructurada.

## Estructura del proyecto
```
data-projectz/
├── data/
│   ├── raw/                    ← Datos históricos crudos
│   │   ├── training.csv
│   │   └── sleep.csv
│   └── processed/              ← Datos procesados por pipeline
│       ├── daily.csv
│       ├── daily_exercise.csv
│       ├── weekly.csv
│       └── user_profile.json
│
├── src/                        ← Pipeline y engine (genera datos)
│   ├── pipeline.py            ← Procesa raw → processed
│   ├── decision_engine.py     ← Genera recomendaciones
│   ├── personalization_engine.py ← Algoritmos de cálculo
│   ├── features.py
│   ├── analysis.py
│   └── insights.py
│
├── app/                        ← Dashboard Streamlit (MODULAR)
│   ├── streamlit_app.py        ← MAIN: Punto de entrada
│   ├── config.py               ← Constantes globales
│   ├── ui/
│   │   ├── theme.py           ← CSS gaming-dark (~550 líneas)
│   │   └── components.py      ← UI reutilizables
│   ├── charts/
│   │   ├── daily_charts.py    ← 6 gráficas diarias (readiness, volume, sleep, ACWR, performance, strain)
│   │   └── weekly_charts.py   ← 2 gráficas semanales
│   ├── calculations/
│   │   ├── readiness_calc.py  ← Fórmula de readiness
│   │   ├── injury_risk.py     ← Riesgo de lesión
│   │   └── plans.py           ← Generación de planes
│   └── data/
│       ├── loader.py          ← Cargar CSV/JSON
│       └── formatters.py      ← Formatear datos
│
├── notebooks/                  ← Prototipado y exploración
│   ├── exploration.ipynb
│   └── estructura_proyecto.ipynb
│
├── gen_example_data.py         ← Script para generar datos de ejemplo
├── requirements.txt            ← Dependencias (Streamlit, Pandas, Plotly, NumPy)
├── README.md                   ← Este archivo
├── ARQUITECTURA_MODULAR.md     ← Documentación detallada de módulos
└── .gitignore
```

## Instalación
1. Clona este repositorio.
2. Instala las dependencias con `pip install -r requirements.txt`.

## Uso

### Pipeline completo
```bash
# 1. Procesa datos crudos: calcula métricas de entrenamiento
python -m src.pipeline --train data/raw/training.csv --sleep data/raw/sleep.csv --out data/processed

# 2. Calcula readiness y recomendaciones
python -m src.decision_engine --daily data/processed/daily.csv --out data/processed

# 3. Lanza la interfaz web
streamlit run app/streamlit_app.py
```

---

## 🏗️ Arquitectura Modular del Dashboard (`app/`)

La interfaz Streamlit ha sido **refactorizada en módulos independientes** para mejorar mantenibilidad, escalabilidad y testabilidad. Cada módulo tiene responsabilidad única:

### Estructura de carpetas
```
app/
├── streamlit_app.py          ← MAIN: Orquesta todos los módulos
├── config.py                 ← CONSTANTES: Rutas, colores, zonas
├── ui/                       ← UI: CSS y componentes visuales
│   ├── theme.py             ← Gaming-dark CSS (~550 líneas)
│   └── components.py        ← Badges, títulos reutilizables
├── charts/                   ← GRÁFICAS: Plotly builders
│   ├── daily_charts.py      ← 6 gráficas diarias
│   └── weekly_charts.py     ← 2 gráficas semanales
├── calculations/            ← LÓGICA: Algoritmos de cálculo
│   ├── readiness_calc.py    ← Fórmula de Readiness
│   ├── injury_risk.py       ← Riesgo de lesión
│   └── plans.py             ← Generación de planes
└── data/                    ← DATOS: Cargar y formatear
    ├── loader.py            ← load_csv, load_user_profile
    └── formatters.py        ← Formateo de zonas, confianza, etc.
```

### 📦 Módulos principales

#### `config.py` - Configuración Global
Centraliza constantes: rutas, paleta de colores, zonas de readiness, opciones de formulario.

```python
from config import COLORS, READINESS_ZONES, DAILY_PATH

COLORS["green"]  # "#00D084"
READINESS_ZONES["HIGH"]  # {"min": 75, "name": "Alta", ...}
```

#### `ui/theme.py` - Estilo CSS
Contiene toda la estética gaming-dark: gradientes, animaciones del toggle, hover effects, responsive.

```python
from ui.theme import get_theme_css
st.markdown(get_theme_css(), unsafe_allow_html=True)
```

#### `ui/components.py` - Componentes Reutilizables
Elementos UI comunes: títulos con acento, badges, helpers de formato.

```python
from ui.components import render_section_title
render_section_title("Tu Readiness HOY", accent="#00D084")
```

#### `charts/daily_charts.py` - Gráficas Diarias
6 builders Plotly: readiness, volume, sleep, ACWR, performance, strain.

- ✅ Datetime-aware: Coerciona índices a `datetime64[ns]` para que tickformat funcione
- ✅ Formato español: Fechas en `dd/mm/YYYY`
- ✅ Colores gaming: Gradientes neón

```python
from charts.daily_charts import create_readiness_chart

fig = create_readiness_chart(data, title="Readiness")
st.plotly_chart(fig, use_container_width=True)
```

#### `charts/weekly_charts.py` - Gráficas Semanales
Bar charts agregados: volumen y strain semanal.

#### `calculations/readiness_calc.py` - Cálculo de Readiness
Implementa `calculate_readiness_from_inputs_v2()`:
- 25% Percepción personal (si presente)
- 30% Recuperación (sueño, siesta, alcohol)
- 26% Estado físico (fatiga, estrés, energía, rigidez)
- 15% Motivación
- Penalizaciones: dolor, enfermedad, cafeína enmascarando fatiga

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
    perceived_readiness=7
)
# readiness = int (0–100)
```

#### `calculations/injury_risk.py` - Riesgo de Lesión
Calcula riesgo combinando readiness, ACWR, sueño, dolor, rigidez, enfermedad.

```python
from calculations.injury_risk import calculate_injury_risk_score_v2

risk = calculate_injury_risk_score_v2(
    readiness_score=70,
    acwr=1.1,
    sleep_hours=7,
    performance_index=0.95,
    effort_level=7,
    pain_flag=False,
    pain_severity=0,
    stiffness=2,
    sick_flag=False
)
# risk = {'risk_level': 'low', 'score': 22, 'emoji': '🟢', ...}
```

#### `calculations/plans.py` - Plan Accionable
Genera recomendaciones ultra-específicas:
- Zona de readiness (🟢 ALTA, 🟡 MEDIA, 🔴 BAJA)
- Intensidad RIR recomendada
- Ajustes por tipo de fatiga
- **Mapeo de dolor**: Si duele hombro → evita press, dominadas, etc.
- **Reglas concretas**: Qué hacer y qué evitar

```python
from calculations.plans import generate_actionable_plan_v2

zone, plan, rules = generate_actionable_plan_v2(
    readiness=75,
    pain_flag=True,
    pain_zone="Hombro",
    pain_severity=5,
    pain_type="Dolor",
    fatigue=4,
    soreness=2,
    stiffness=1,
    sick_flag=False,
    session_goal="Hipertrofia",
    fatigue_analysis={"type": "central", "target_split": "push"}
)

# zone = "🟢 ALTA"
# plan = ["**Zona**: 🟢 ALTA", "**Recomendación**: Push day...", ...]
# rules = ["✅ Calienta progresivamente", "❌ STOP si duele hombro", ...]
```

#### `data/loader.py` - Carga de Datos
- `load_csv(path)`: Carga CSV normalizado a datetime
- `load_user_profile(path)`: Lee JSON o retorna defaults

```python
from data.loader import load_csv, load_user_profile

df = load_csv("data/processed/daily.csv")
profile = load_user_profile("data/processed/user_profile.json")
```

#### `data/formatters.py` - Formateo de Datos
Helpers para traducir métricas a textos/colores legibles:

```python
from data.formatters import get_readiness_zone, get_confidence_level

zona, emoji, color = get_readiness_zone(82)
# ("Alta", "🟢", "#00D084")

conf_text, emoji = get_confidence_level(df, selected_date)
# ("80% confianza (10 datos)", "📊")
```

### 🔄 Flujo de importes típico en `streamlit_app.py`

```python
# === Setup ===
from config import COLORS, READINESS_ZONES, DAILY_PATH
from ui.theme import get_theme_css
from ui.components import render_section_title

# === Cargar datos ===
from data.loader import load_csv, load_user_profile
from data.formatters import get_readiness_zone

# === Cálculos ===
from calculations.readiness_calc import calculate_readiness_from_inputs_v2
from calculations.injury_risk import calculate_injury_risk_score_v2
from calculations.plans import generate_actionable_plan_v2

# === Gráficas ===
from charts.daily_charts import create_readiness_chart
from charts.weekly_charts import create_weekly_volume_chart

# === En main() ===
st.markdown(get_theme_css(), unsafe_allow_html=True)
render_section_title("Tu Readiness HOY", accent=COLORS["green"])

df = load_csv(DAILY_PATH)
readiness = calculate_readiness_from_inputs_v2(...)
zone, plan, rules = generate_actionable_plan_v2(...)

fig = create_readiness_chart(df['readiness_score'], "Readiness")
st.plotly_chart(fig)
```

### ✅ Ventajas de la Modularización
| Aspecto | Antes | Después |
|---------|-------|---------|
| Líneas de código | 2647 | ~500 (main) + 10 módulos |
| Encontrar función | Buscar en 2647 líneas | Ir a módulo específico |
| Testing | Imposible | Cada módulo testeable |
| Reutilización | Copiar código | Importar módulo |
| Escalabilidad | Agregar feature = caos | Nuevo módulo, cero conflictos |

### 🚀 Cómo agregar features
**Ejemplo: Nueva métrica en readiness**
1. Edita `calculations/readiness_calc.py`
2. Listo. No toques otros archivos.

**Ejemplo: Nueva gráfica**
1. Agrega función a `charts/daily_charts.py` (o nuevo archivo `charts/metrics.py`)
2. Actualiza `charts/__init__.py` con export
3. Usa en `streamlit_app.py`

### 📖 Para más detalles
Consulta [ARQUITECTURA_MODULAR.md](./ARQUITECTURA_MODULAR.md) con ejemplos de código y documentación exhaustiva.

---

## 📊 Escalas de entrada (Modo Hoy)

Para mantener consistencia y facilitar cálculos, todas las escalas están estandarizadas:

| Variable | Escala | Significado |
|----------|--------|-------------|
| **sleep_hours** | 0–12 | Horas de sueño (decimales permitidos: 7.5h = 7h 30min) |
| **sleep_quality** | 1–5 | Calidad percibida del sueño (1=Muy malo, 5=Excelente) |
| **fatigue** | 0–10 | Nivel de fatiga/cansancio (0=Fresco, 10=Muy cansado) |
| **soreness** | 0–10 | Agujetas/dolor muscular (0=Ninguno, 10=Mucho) |
| **stress** | 0–10 | Estrés mental (0=Relajado, 10=Muy estresado) |
| **motivation** | 0–10 | Motivación/ganas de entrenar (0=Ninguna, 10=Máxima) |

### Normalización interna
Todas las variables se normalizan a 0–1 antes de alimentar la fórmula de readiness:
- `sleep_hours`: (valor - 6.0) / (7.5 - 6.0) → [0, 1]
- `sleep_quality`: (valor - 1) / 4 → [0, 1]
- `fatigue`, `soreness`, `stress`: 1 - (valor / 10) → [0, 1] (inversas: mayor valor = menor puntuación)
- `motivation`: valor / 10 → [0, 1]

---

## 🔄 Gestión de datos de sueño

El sistema maneja **dos fuentes** de datos de sueño para máxima flexibilidad:

### `sleep.csv` (histórico consolidado)
- Datos históricos de wearables o entrada manual previa
- Fuente de verdad para fechas pasadas
- Tiene: `date`, `sleep_hours`, `sleep_quality`

### `mood_daily.csv` (entrada instantánea del usuario)
- Generado por **Modo Hoy** en Streamlit
- El usuario ingresa sueño + estado actual (fatiga, estrés, etc.) en tiempo real
- Tiene: `date`, `sleep_hours`, `sleep_quality`, `fatigue`, `soreness`, `stress`, `motivation`, `pain_flag`, `pain_location`, `readiness_instant`

### ⚡ Regla de prioridad en el pipeline
Cuando se procesa un día, la lógica es:

```
SI existe mood_daily para esa fecha
  → USA mood_daily.sleep_hours y mood_daily.sleep_quality
SINO
  → USA sleep.csv
```

**Beneficio**: El usuario puede override datos del pasado con entradas instantáneas nuevas sin perder el histórico.

---

## 📈 Flujo de datos

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              DATOS CRUDOS                               │
└────────────────────┬──────────────────────────────┬──────────────────────┘
                     │                              │
             ┌───────▼────────┐          ┌──────────▼────────┐
             │ training.csv   │          │   sleep.csv       │
             │ (raw)          │          │   (raw)           │
             └────────────────┘          └───────────────────┘
                     │                              │
                     └──────────────────┬───────────┘
                                        │
                                   ┌────▼──────────────┐
                                   │ pipeline.py       │
                                   │ • Metrics         │
                                   │ • ACWR            │
                                   │ • Performance     │
                                   └────┬─────┬──┬─────┘
                                        │     │  │
                ┌───────────────────────┘     │  └─────────────────┐
                │                             │                    │
       ┌────────▼──────────┐    ┌────────────▼──────┐    ┌────────▼────┐
       │ daily_exercise.csv│    │ daily.csv         │    │ weekly.csv   │
       │ (processed)       │    │ (processed)       │    │ (processed)  │
       └───────────────────┘    └────────┬──────────┘    └──────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
         ┌──────────▼──────────┐ ┌──────▼──────────┐  ┌──────▼────────┐
         │ decision_engine.py  │ │ mood_daily.csv  │  │ (usuario app)  │
         │ • Readiness         │ │ (entrada usuario)│  │ • Modo Hoy     │
         │ • Recommendations   │ └─────┬───────────┘  │ • Input form   │
         └──────────┬──────────┘       │              └────────────────┘
                    │                  │
         ┌──────────▼──────────┐       │
         │recommendations_     │       │
         │daily.csv            │       │
         └─────────────────────┘       │
                    │                  │
                    └──────┬───────────┘
                           │
                    ┌──────▼─────────┐
                    │ streamlit_app  │
                    │ • Dashboard    │
                    │ • Día view     │
                    │ • Modo Hoy     │
                    │ • Semana view  │
                    └────────────────┘
```

---

## 🎯 Métricas principales

### Readiness Score (0–100)
Ponderación:
- 40% Sueño (sleep_hours + sleep_quality)
- 30% Performance Index
- 20% ACWR (Acute:Chronic Workload Ratio)
- 10% RIR

### Zonas de Readiness
- **🟢 Alta (≥75)**: Push day, busca PRs
- **🟡 Media (55–74)**: Mantén técnica
- **🔴 Muy baja (<55)**: Deload, técnica

### ACWR (Aguda:Crónica)
Ratio carga última semana / promedio 4 semanas:
- < 0.8: Deload
- 0.8–1.3: Óptimo
- 1.3–1.5: Alerta elevada
- > 1.5: Riesgo de lesión

---

## 📋 Licencia
Este proyecto está bajo la licencia MIT.