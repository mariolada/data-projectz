# Sistema de Análisis de Rendimiento Deportivo

Este proyecto está diseñado como una experiencia inmersiva inspirada en "Solo Leveling", con una estética de videojuego que transforma el análisis de rendimiento deportivo en una aventura interactiva. El sistema cruza datos de entrenamiento de fuerza con variables de recuperación (principalmente sueño) para extraer métricas objetivas e insights accionables sobre progresión, fatiga y planificación de cargas.

## Características principales
- **Ingesta de datos**: Archivos CSV exportados desde wearables o introducidos manualmente.
- **Procesamiento**: Limpieza, normalización y cálculo de métricas con Pandas y NumPy.
- **Extracción de insights**: Reglas determinísticas y análisis descriptivo.
- **Visualización**: Interfaz web con Streamlit, diseñada con una temática de videojuego, incluyendo gráficos dinámicos y elementos interactivos.
- **Almacenamiento**: CSV en fases iniciales y SQLite para persistencia estructurada.

## Estructura del proyecto
- `data/raw/`: Datos históricos (training.csv, sleep.csv).
- `data/processed/`: Datos procesados y calculados.
- `notebooks/`: Prototipos y análisis exploratorio.
- `src/`: Código fuente (pipeline, decision_engine, features, analysis, insights).
- `app/`: Interfaz Streamlit.

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