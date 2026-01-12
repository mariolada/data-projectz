# 🚀 Instrucciones Rápidas - Sistema Personalizado

## Ejecutar Todo en 4 Pasos

### 1. Generar datos de ejemplo
```powershell
python gen_example_data.py
```
✅ Genera CSVs de ejemplo con 35 días de histórico

### 2. Procesar datos
```powershell
python -m src.pipeline --train data/raw/training.csv --sleep data/raw/sleep.csv --out data/processed
```
✅ Calcula métricas, ACWR, volumen, etc.

### 3. Generar recomendaciones + perfil personalizado
```powershell
python -m src.decision_engine --daily data/processed/daily.csv --out data/processed
```
✅ Genera:
- `recommendations_daily.csv` → Recomendaciones diarias
- `user_profile.json` → **NUEVO** Perfil personalizado

### 4. Lanzar la app
```powershell
python -m streamlit run app/streamlit_app.py
```
✅ Abre en http://localhost:8501

---

## 📊 Qué Aprende el Sistema

El `user_profile.json` contiene:

### 1. Sleep Responsiveness
- ¿Cuánto te afecta el sueño?
- Correlación: -1 a 1
- Interpretación: "Sueño es crítico para ti" o "Otros factores te afectan más"

### 2. User Archetype
- ¿Qué tipo de atleta eres?
- `short_sleeper`, `needs_sleep`, `consistent_performer`, etc.

### 3. Adjustment Factors
- Pesos personalizados para la fórmula:
  - Sleep weight (default 0.25 → ajustado)
  - Performance weight (default 0.25 → ajustado)
  - ACWR weight (default 0.15 → ajustado)
  - Fatigue sensitivity (default 1.0 → ajustado)
  - Recovery speed (default 1.0 → ajustado)

### 4. Insights
- "Eres short_sleeper: No necesitas 8h"
- "Toleras bien ACWR alto"
- "Tu recuperación es predecible"

---

## 🎮 Usando la App

### Hay 3 vistas:

1. **📅 Día**
   - Análisis detallado de un día específico
   - Histórico, readiness, recomendaciones

2. **🎯 Modo Hoy** (NUEVO)
   - Entrada instantánea: ¿Cómo te sientes AHORA?
   - Muestra tu perfil personal (archetype, insights, factores)
   - Recomendaciones adaptadas a ti

3. **📊 Semana**
   - Análisis semanal
   - Tendencias, ACWR, volumen acumulado

### "🎯 Modo Hoy" - Cómo funciona

**Paso 1:** Expandir "📊 Tu Perfil Personal"
- Ver tu arquetipo
- Ver cómo el sueño te afecta
- Ver tus insights personalizados

**Paso 2:** Elegir modo de entrada
- ⚡ Rápido (20s) → 3-4 preguntas
- 📋 Completo → 15-20 preguntas detalladas

**Paso 3:** Responder preguntas
- Sueño, calidad, fatiga, estrés, agujetas, motivación
- Banderas rojas: dolor, enfermedad, último entreno duro
- Objetivo de hoy, tiempo disponible

**Paso 4:** Obtener recomendación personalizada
- Readiness adaptado a TI
- Qué hacer hoy
- Factores que influyen en tu decisión

---

## 📊 Ejemplo Práctico

Supongamos que eres "short_sleeper":

```
Tu Perfil: SHORT_SLEEPER
├─ Media de sueño: 6.2h
├─ Sueño te afecta: POCO (correlación 0.28)
├─ Recovery speed: RÁPIDA (1.1x)
└─ Insights: "No necesitas 8h", "Otros factores te afectan más"

Hoy (Modo Hoy):
├─ Dormiste: 6h
├─ Calidad: 4/5
├─ Fatiga: 2/10
└─ Estrés: 3/10

Recomendación:
├─ Readiness: 72 (bueno)
├─ Acción: "Entrena normal"
└─ Razón: "A pesar de dormir 6h, es SUFICIENTE para ti"
```

Sin personalización, el sistema sería más conservador con solo 6h.

---

## 🔄 Cómo Evoluciona

**Día 1-7:** "Insuficientes datos para análisis"
**Día 8-28:** "Análisis con confianza media"
**Día 29+:** "Análisis con alta confianza (>28 días)"

Cada vez que ejecutas:
```bash
python -m src.decision_engine --daily data/processed/daily.csv --out data/processed
```

El `user_profile.json` se actualiza con nuevo análisis.

---

## 📱 Modo Hoy vs Histórico

### "Modo Hoy" (instantáneo)
- Tú ingresas datos AHORA
- Recomendación instantánea
- No se guarda automáticamente

### "Día" (histórico)
- Muestra datos ya registrados
- Análisis con contexto histórico
- Comparación vs tus baselines

---

## 🎯 Cuándo Usar Cada Uno

| Situación | Vista | Por qué |
|-----------|-------|--------|
| Es mañana, quiero entrenar | Modo Hoy | Recomendación instantánea |
| Revisar un día pasado | Día | Ver análisis histórico |
| Planificar la semana | Semana | Ver tendencias |
| Entender mi perfil | Modo Hoy (expandible) | Ver archetype e insights |

---

## 💾 Archivos Generados

```
data/
├─ raw/
│  ├─ training.csv       (entrenamientos)
│  ├─ sleep.csv          (sueño histórico)
│  └─ mood_daily.csv     (estado diario)
│
└─ processed/
   ├─ daily.csv          (procesado)
   ├─ weekly.csv         (agregado semanal)
   ├─ recommendations_daily.csv
   ├─ flags_daily.csv
   └─ user_profile.json  (NUEVO - tu perfil)
```

---

## 🔧 Cambiar Datos

**Para agregar nuevos entrenamientos:**
1. Edita `data/raw/training.csv`
2. Agrega filas con: date, exercise, sets, reps, weight, rpe, rir

**Para agregar nuevo sueño:**
1. Edita `data/raw/sleep.csv`
2. Agrega filas con: date, sleep_hours, sleep_quality

**Para regenerar todo:**
```bash
python gen_example_data.py              # Resetea datos
python -m src.pipeline ...              # Procesa
python -m src.decision_engine ...       # Analiza + personaliza
```

---

## 🐛 Si algo falla

**"No se abre la app"**
```bash
pip install streamlit plotly scipy pandas numpy
python -m streamlit run app/streamlit_app.py
```

**"Falta user_profile.json"**
```bash
python -m src.decision_engine --daily data/processed/daily.csv --out data/processed
```

**"Error en personalization_engine"**
```bash
pip install scipy
```

---

## 📊 Qué Significa Cada Métrica

| Métrica | Rango | Significado |
|---------|-------|-------------|
| Readiness | 0-100 | Disponibilidad para entrenar (0=descansa, 100=máximo) |
| Sleep hours | 0-12 | Total de horas dormidas en 24h |
| Sleep quality | 1-5 | Percepción de calidad (1=horrible, 5=perfecto) |
| Fatigue | 0-10 | Sensación de cansancio (0=fresco, 10=exhausta) |
| Stress | 0-10 | Estrés mental (0=relajado, 10=muy estresado) |
| Soreness | 0-10 | DOMS/agujetas (0=nada, 10=muy dolorido) |
| ACWR | 0-2 | Carga aguda/28d (0.8-1.3=óptimo, >1.5=peligro) |

---

## ✨ Lo Mejor: No Pierdes Nada

- ✅ La app sigue siendo igual de interactiva
- ✅ "Modo Hoy" sigue siendo temporal
- ✅ Puedes ignorar el perfil si quieres
- ✅ TODO es voluntario y contextual

La personalización es un **plus** que te ayuda, no una imposición.

---

**¡Listo! Tu app está completa y lista para usar.** 🚀
