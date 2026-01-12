# 🎯 Sistema de Personalización Implementado

## ¿Qué se cambió?

Se implementó un **sistema inteligente de personalización** que aprende del histórico del usuario y adapta las recomendaciones según cómo realmente le afectan los factores a CADA persona.

---

## 🔄 Flujo de Ejecución

### **Pipeline Original** (sin personalización)
```
training.csv + sleep.csv
    ↓
pipeline.py (normaliza, calcula ACWR, volume)
    ↓
daily.csv (datos procesados)
    ↓
decision_engine.py (readiness genérico)
    ↓
recommendations_daily.csv
```

### **Pipeline Mejorado** (CON personalización)
```
training.csv + sleep.csv
    ↓
pipeline.py
    ↓
daily.csv
    ↓
decision_engine.py (NUEVO: + personalization_engine)
    ├─ Calcula readiness genérico (base)
    ├─ Analiza correlaciones personales:
    │  ├─ Sleep responsiveness (¿te afecta el sueño?)
    │  ├─ User archetype (¿qué tipo de atleta eres?)
    │  └─ ACWR tolerance (¿toleras picos de carga?)
    ├─ Genera adjustment factors personalizados
    ├─ Calcula readiness_score_personalized
    └─ Exporta user_profile.json
    ↓
recommendations_daily.csv + user_profile.json
    ↓
Streamlit App (lee perfil + adapta "Modo Hoy")
```

---

## 📊 Nuevas Funciones en `personalization_engine.py`

### 1️⃣ `analyze_sleep_responsiveness(df_daily)`
**¿Cuánto te afecta realmente el sueño?**
- Calcula correlación de Pearson entre `sleep_hours` y `readiness_score`
- Retorna: 
  - `correlation`: coeficiente (-1 a 1)
  - `strength`: 'none', 'weak', 'moderate', 'strong'
  - `sleep_responsive`: bool (¿sensible al sueño?)

**Ejemplo:**
```json
{
  "correlation": 0.72,
  "strength": "strong",
  "sleep_responsive": true,
  "interpretation": "Sueño es CRÍTICO para tu readiness"
}
```

### 2️⃣ `detect_user_archetype(df_daily)`
**¿Qué tipo de atleta eres?**
Detecta arquetipos como:
- `short_sleeper`: Rindes bien con <7h
- `standard`: Necesitas 7-7.5h (media)
- `needs_sleep`: Necesitas 8h+
- `consistent_performer`: Tu readiness es muy predecible
- `variable_performer`: Fluctúas mucho
- `high_acwr_tolerator`: Toleras bien picos de carga
- `acwr_sensitive`: Los picos te afectan mucho

**Ejemplo:**
```json
{
  "archetype": "short_sleeper",
  "confidence": 0.85,
  "reason": "Tienes media ~6.2h pero readiness decente (>60)"
}
```

### 3️⃣ `calculate_personal_adjustment_factors(df_daily)`
**Pesos personalizados para la fórmula de readiness**
Ajusta los pesos de cada componente según:
- Si sueño correlaciona alto → aumenta `sleep_weight` (default 0.25 → 0.35)
- Si eres "short_sleeper" → baja `sleep_weight` (0.15)
- Si toleras ACWR alto → baja `acwr_weight`
- Calcula `fatigue_sensitivity` (1.0 = normal, >1.0 = muy sensible)
- Calcula `recovery_speed` (qué tan rápido recuperas)

**Ejemplo:**
```json
{
  "sleep_weight": 0.35,        // Aumentado: sueño te afecta
  "performance_weight": 0.25,
  "acwr_weight": 0.08,          // Reducido: toleras picos
  "fatigue_sensitivity": 1.3,   // Muy sensible a fatiga
  "recovery_speed": 1.0         // Normal
}
```

### 4️⃣ `create_user_profile(df_daily)`
**Perfil completo personalizado**
Combina todo y genera un JSON con:
- Sleep responsiveness
- Archetype + confidence
- Adjustment factors
- Insights automáticos ("Eres short_sleeper", "Toleras bien ACWR", etc.)
- Data quality (cuántos días de histórico)

---

## 🔧 Cambios en `decision_engine.py`

### Nueva función: `compute_readiness_with_personalisation()`
Calcula readiness usando los `adjustment_factors` personalizados:
```python
readiness_personalized = (
    sleep_weight * sleep_score +
    perf_weight * perf_score +
    acwr_weight * acwr_score +
    ...
)
```

### Exportación automática de perfil
Al ejecutar decision_engine:
```bash
python -m src.decision_engine --daily data/processed/daily.csv --out data/processed
```

Genera:
- `recommendations_daily.csv` (como antes)
- `flags_daily.csv` (como antes)
- **`user_profile.json`** (NUEVO)

Salida del pipeline:
```
📊 Factores de ajuste calculados:
   Sleep weight: 0.35 (default: 0.25)
   Performance weight: 0.25 (default: 0.25)
   ACWR weight: 0.08 (default: 0.15)
   Fatigue sensitivity: 1.30x (default: 1.0)

✓ User profile guardado: data/processed/user_profile.json
  Archetype: short_sleeper
  Insights: 3 descubrimientos
```

---

## 📱 Integración en Streamlit App

### "Modo Hoy" ahora muestra tu perfil

Cuando abres **"🎯 Modo Hoy"**, la app:
1. Carga `user_profile.json` automáticamente
2. Muestra un expandible **"📊 Tu Perfil Personal"** con:
   - Tu arquetipo (ej: "SHORT_SLEEPER")
   - Si el sueño te afecta (correlación)
   - Insights personalizados
   - Tus adjustment factors vs defaults

3. Adapta las recomendaciones según tus factores personales
4. El usuario sigue pudiendo ingresar datos en tiempo real

**Ejemplo visual:**
```
📊 Tu Perfil Personal [expandible]
├─ Arquetipo: SHORT_SLEEPER
│  └─ Tienes media ~6.2h pero readiness decente
├─ Sueño te afecta: Poco ⚠️
│  └─ Correlación: 0.28
├─ Insights:
│  • ✨ Eres short_sleeper: Tienes media ~6.2h pero readiness decente
│  • 😴 Sueño tiene POCO efecto en tu readiness
│  • ⚡ Tu recuperación es predecible y rápida
├─ Factores de personalización:
│  • Sleep Weight: 0.15 (-0.10 vs default)
│  • Performance Weight: 0.25 (+0.00 vs default)
│  • Fatigue Sensitivity: 1.20x (+0.20x vs normal)
```

---

## ✨ Valor para el usuario

### **Antes (sistema genérico):**
- "Tu readiness es 65 (score genérico)"
- "Duerme 7.5h" (recomendación igual para todos)
- "El sueño pesa 25% en tu readiness" (default)

### **Ahora (sistema personalizado):**
- "Tu readiness es 68 (basado en TU historial)"
- "Dormir 6.5h es suficiente para ti (eres short_sleeper)"
- "El sueño pesa 15% en TU readiness (no es tu factor clave)"
- "Detectamos que toleras bien ACWR alto (puedes aprovechar picos de carga)"
- "⚡ Tu recuperación es predecible → planifica entrenamientos con más confianza"

---

## 📊 Archivos Generados

```
data/processed/
├─ daily.csv                      (procesado)
├─ weekly.csv                     (procesado)
├─ recommendations_daily.csv      (recomendaciones)
├─ flags_daily.csv                (debug)
└─ user_profile.json             (NUEVO - perfil personalizado)
    ├─ sleep_responsiveness
    ├─ archetype
    ├─ adjustment_factors
    ├─ insights
    ├─ last_updated
    └─ data_quality
```

---

## 🚀 Cómo ejecutar

### Paso 1: Generar datos
```bash
python gen_example_data.py
```

### Paso 2: Pipeline de procesamiento
```bash
python -m src.pipeline --train data/raw/training.csv --sleep data/raw/sleep.csv --out data/processed
```

### Paso 3: Decision Engine + Personalización (NUEVO)
```bash
python -m src.decision_engine --daily data/processed/daily.csv --out data/processed
```

Esto genera:
- `recommendations_daily.csv`
- `user_profile.json` ← **NUEVO**

### Paso 4: Lanzar app
```bash
streamlit run app/streamlit_app.py
```

---

## 📚 Requisitos nuevos

Se agregó `scipy` para análisis estadístico:
```
pandas
numpy
scipy            # NUEVO - para correlaciones
streamlit
matplotlib
plotly
```

---

## 🎯 Próximas mejoras posibles

1. **Machine Learning ligero**: Predicción de readiness basada en patrones personales
2. **Detección de anomalías**: "Detectamos cambio en tu patrón de sueño hace 3 días"
3. **Recomendaciones dinámicas por ejercicio**: "Eres mejor en press vs sentadilla según histórico"
4. **Integración con cafeína/alcohol**: Aprender cómo estos afectan ESPECÍFICAMENTE a ti
5. **Persistencia de perfil**: Guardar y evolucionar el perfil a lo largo del tiempo
6. **A/B testing**: "Probemos si reduzco 10% carga, ¿mejora recuperación?"

---

## ✅ Resumen

✔️ **Sistema de análisis**: Calcula correlaciones personales
✔️ **Detección de arquetipos**: Identifica qué tipo de atleta eres
✔️ **Adjustment factors**: Pesos dinámicos por usuario
✔️ **Perfil exportable**: JSON listo para Streamlit
✔️ **UI integrada**: "Modo Hoy" muestra tu perfil personal
✔️ **Sin perder funcionalidad**: El "Modo Hoy" sigue siendo interactivo y temporal

**La app ahora realmente APRENDE y se adapta a cada usuario.** 🚀
