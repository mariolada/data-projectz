# 🔬 Documentación Técnica de Algoritmos

## Índice
1. [Readiness Score](#1-readiness-score)
2. [Decision Engine (Recomendaciones)](#2-decision-engine)
3. [Neural Overload Detector](#3-neural-overload-detector)
4. [Flujo Completo](#4-flujo-completo)

---

## 1. READINESS SCORE

### 📍 Ubicación: `app/calculations/readiness.py` → `calculate_readiness_from_inputs_v2()`

### Concepto
El Readiness Score (0-100) responde a la pregunta: **"¿Cuánto puedo dar hoy?"**

Combina percepción subjetiva + métricas objetivas para generar una puntuación que guía la intensidad del entrenamiento.

### Arquitectura de la Fórmula

```
READINESS = Percepción + Sueño + Estado + Motivación - Penalizaciones
```

### Distribución de Pesos

| Componente | Peso Base | Peso Efectivo | Puntos Max |
|------------|-----------|---------------|------------|
| ⭐ Percepción | 18% directo | 18% | 18 pts |
| 🌙 Sueño | 38% × 0.85 | 32.3% | 32 pts |
| 💪 Estado | 42% × 0.85 | 35.7% | 36 pts |
| 🎯 Motivación | 18% × 0.85 | 15.3% | 15 pts |
| **TOTAL** | - | ~100% | ~100 pts |

---

### Componente 1: Percepción Personal (18%)

```python
perceived_score = perceived_readiness / 10  # Normalizar 0-10 → 0-1
perceived_component = 0.18 * perceived_score
base_weight_multiplier = 0.85  # Deja 85% para métricas objetivas
```

**Justificación del 18%**: La intuición es valiosa pero puede ser sesgada. Hay días que te sientes mal pero estás bien fisiológicamente (y viceversa). Este peso equilibra lo subjetivo con lo objetivo.

---

### Componente 2: Sueño (32% efectivo)

#### Cálculo Base
```python
# Horas: escala 5-7.5h (generosa)
sleep_hours_score = np.clip((sleep_hours - 5.0) / (7.5 - 5.0), 0, 1)
#   5h = 0.0 | 6.25h = 0.5 | 7.5h+ = 1.0

# Calidad: escala 1-5
sleep_quality_score = (sleep_quality - 1) / 4
#   1 = 0.0 | 3 = 0.5 | 5 = 1.0

# Combinar: horas pesan más (60%) porque son más objetivas
sleep_base = (sleep_hours_score * 0.6 + sleep_quality_score * 0.4)
```

#### Personalización por Baseline Histórico
```python
if baselines.get('sleep', {}).get('p50'):  # Tu mediana histórica
    delta_sleep = sleep_hours - your_baseline
    
    if delta_sleep < -1.5:  # Déficit severo (>1.5h bajo tu media)
        sleep_context_bonus = -0.03 * (abs(delta_sleep) - 1.5)
    elif delta_sleep > 0.5:  # Bonus por dormir mejor que tu media
        sleep_context_bonus = min(delta_sleep * 0.02, 0.05)
```

#### Modificadores de Sueño

| Factor | Efecto | Lógica |
|--------|--------|--------|
| Siesta 20min | +3% | Power nap óptimo |
| Siesta 45min | +5% | REM parcial |
| Siesta 90min | +7% | Ciclo completo |
| Sueño fragmentado | -5 pts | Calidad degradada |
| Alcohol noche anterior | -12 pts | Afecta arquitectura del sueño |

#### Fórmula Final Sueño
```python
sleep_component = base_weight_multiplier * 0.38 * (
    sleep_base + nap_bonus + sleep_context_bonus
) - disruption_penalty - alcohol_penalty
```

---

### Componente 3: Estado Físico (36% efectivo)

#### Transformación de Inputs
```python
# Transformar inputs (0-10) a scores (0-1)
fatigue_score = 1 - (fatigue / 10)    # Fatiga BAJA = score ALTO
stress_score = 1 - (stress / 10)       # Estrés BAJO = score ALTO
energy_score = energy / 10             # Energía ALTA = score ALTO
soreness_score = 1 - (soreness / 10)   # Dolor BAJO = score ALTO
```

#### Pesos Internos del Estado

| Subcomponente | Peso | Justificación |
|---------------|------|---------------|
| Energía | 40% | Indicador más fiable de capacidad actual |
| Fatiga | 35% | Afecta directamente el rendimiento |
| Estrés | 20% | Impacto moderado (algunos rinden bien estresados) |
| Dolor muscular | 5% | Normal post-entreno, no siempre es malo |

#### Personalización por Sensibilidad
```python
# Si históricamente la fatiga te afecta mucho → sensitivity > 1.0
fatigue_sensitivity = adjustment_factors.get('fatigue_sensitivity', 1.0)

# Cap en 1.15 para que no domine demasiado
adjusted_fatigue = fatigue_score * min(fatigue_sensitivity, 1.15)
```

#### Penalizaciones Contextuales
```python
# Rigidez solo penaliza si es severa (>3/10)
stiffness_penalty = (max(0, stiffness - 3) / 10) * 0.03

# Fatiga crítica (>7) + persona sensible → penalización extra
if fatigue > 7 and fatigue_sensitivity > 1.1:
    fatigue_context = -0.03
```

#### Fórmula Final Estado
```python
state_component = base_weight_multiplier * 0.42 * (
    0.40 * energy_score +
    0.35 * fatigue_score * min(fatigue_sensitivity, 1.15) +
    0.20 * stress_score * min(stress_sensitivity, 1.15) +
    0.05 * soreness_score
) - stiffness_penalty + fatigue_context
```

---

### Componente 4: Motivación (15% efectivo)

```python
motivation_score = motivation / 10
motivation_component = base_weight_multiplier * 0.18 * motivation_score
```

**Justificación del 15%**: La motivación predice esfuerzo pero no capacidad física. Un atleta muy motivado pero fatigado sigue siendo un atleta fatigado.

---

### Penalizaciones por Flags

| Flag | Penalización | Condición |
|------|--------------|-----------|
| Dolor físico | -15 pts | Cualquier dolor reportado |
| Enfermedad nivel 1 | -5 pts | Malestar leve |
| Enfermedad nivel 2 | -8 pts | Síntomas moderados |
| Enfermedad nivel 3 | -15 pts | Enfermo |
| Enfermedad nivel 4 | -25 pts | Muy enfermo |
| Enfermedad nivel 5 | -35 pts | Debería estar en cama |
| Cafeína alta + fatiga | -5 pts | Solo si cafeína ≥3 Y fatiga ≥7 |

```python
# Sick: escala gradual (no binario)
sick_penalty_map = {0: 0.0, 1: 0.05, 2: 0.08, 3: 0.15, 4: 0.25, 5: 0.35}

# Cafeína: solo penaliza si enmascara fatiga real
if caffeine >= 3 and fatigue >= 7:
    caffeine_mask = 0.05  # Posible enmascaramiento de fatiga
```

---

### Fórmula Final Completa

```python
readiness_0_1 = (
    perceived_component +      # 0-0.18
    sleep_component +          # 0-0.32
    state_component +          # 0-0.36
    motivation_component       # 0-0.15
    - pain_penalty             # 0-0.15
    - sick_penalty             # 0-0.35
    - caffeine_mask            # 0-0.05
)

readiness_0_1 = np.clip(readiness_0_1, 0, 1)
readiness_score = int(round(readiness_0_1 * 100))  # 0-100
```

### Interpretación del Score

| Rango | Nivel | Recomendación |
|-------|-------|---------------|
| 85-100 | 🟢 Excelente | Día para empujar, buscar PRs |
| 70-84 | 🟢 Bueno | Entrenamiento normal |
| 55-69 | 🟡 Moderado | Reducir volumen 15-20% |
| 40-54 | 🟠 Bajo | Reducir significativamente, técnica |
| <40 | 🔴 Crítico | Descanso o actividad muy ligera |

---

## 2. DECISION ENGINE

### 📍 Ubicación: `src/decision_engine.py` → `generate_recommendations()`

### Concepto
El Decision Engine toma el readiness score y lo combina con métricas de entrenamiento para generar recomendaciones específicas y actionables.

### Scores de Componentes Objetivos

Antes de generar recomendaciones, calcula scores normalizados (0-1) de métricas objetivas:

```python
# Sueño (horas)
score_sleep_hours(hours) = clip((hours - 6.0) / 1.5, 0, 1)
#   6h = 0.0 | 6.75h = 0.5 | 7.5h+ = 1.0

# Rendimiento (Performance Index)
score_performance(pi) = clip((pi - 0.98) / 0.04, 0, 1)
#   0.98 = 0.0 | 1.00 = 0.5 | 1.02 = 1.0

# ACWR (Acute:Chronic Workload Ratio)
score_acwr(x):
    0.8-1.3  → 1.0 (zona óptima, sweet spot)
    1.3-1.5  → 0.6-1.0 (elevado, cuidado)
    >1.5     → 0.0-0.6 (riesgo alto de lesión)
    <0.8     → 0.6-0.7 (poco estímulo, desentrenamiento)

# RIR para fatiga
score_rir_for_fatigue(rir):
    ≤0.5  → 0.0 (muy fatigante)
    1-3   → 1.0 (productivo sin agotar)
    >3    → 0.8 (poco estímulo pero ok para readiness)
```

### Flags de Detección

```python
# Poco estímulo: RIR alto + esfuerzo bajo
flag_understim = (rir >= 4.0) and (effort <= 6.5)

# Día muy exigente: cerca del fallo + esfuerzo alto
flag_high_strain_day = (rir <= 1.0) and (effort >= 8.5)
```

### Matriz de Decisiones

```python
def generate_recommendations(row):
    rs = row["readiness_score"]
    has_overload = row.get("overload_score", 0) >= 30
    
    # ═══════════════════════════════════════════════════════════
    # ZONA ALTA (≥80) - Push day
    # ═══════════════════════════════════════════════════════════
    if rs >= 80:
        if has_overload:
            # Alto readiness PERO sobrecarga neural → precaución
            return "Normal+", "Mantén carga, evita RIR0 en lifts afectados"
        if row["flag_understim"]:
            # Alto readiness + poco estímulo reciente → empujar
            return "Push day", "+1 set (key lift) OR target RIR 1–2"
        # Alto readiness, todo bien → progresar
        return "Push day", "+2.5% load (key lift) if PI>=1.01 else +1 set"
    
    # ═══════════════════════════════════════════════════════════
    # ZONA MEDIA (65-79) - Normal
    # ═══════════════════════════════════════════════════════════
    if 65 <= rs < 80:
        if has_overload:
            return "Normal", "Mantén volumen, RIR 2-3, no máximos"
        if row["acwr_7_28"] > 1.3:
            # ACWR elevado → reducir volumen aunque readiness ok
            return "Normal", "Maintain load, -10% volume"
        return "Normal", "Maintain (target RIR 1–2)"
    
    # ═══════════════════════════════════════════════════════════
    # ZONA BAJA (50-64) - Reduce
    # ═══════════════════════════════════════════════════════════
    if 50 <= rs < 65:
        if has_overload:
            return "Reduce", "-20% vol en lifts afectados, RIR 3+"
        if row["performance_index"] >= 1.00:
            # Readiness bajo pero rendimiento ok → reducir conservador
            return "Reduce", "-15% volume, keep technique, RIR 2-3"
        return "Reduce", "-20% volume, avoid RIR<=1"
    
    # ═══════════════════════════════════════════════════════════
    # ZONA CRÍTICA (<50) - Deload/Rest
    # ═══════════════════════════════════════════════════════════
    if has_overload:
        return "Deload", "Deload obligatorio: -40% vol, evita lifts afectados"
    if row["sleep_hours"] < 6.0:
        return "Deload/Rest", "-40% volume, RIR 3-5 OR rest day"
    return "Deload/Rest", "-30–50% volume, target RIR 3–5"
```

### Reason Codes (Explicación de Decisiones)

```python
def reason_codes(row):
    codes = []
    if row["sleep_hours"] < 6.5:
        codes.append("LOW_SLEEP")
    if row["acwr_7_28"] > 1.5:
        codes.append("HIGH_ACWR")
    if row["performance_index"] < 0.98:
        codes.append("PERF_DROP")
    if row["effort_mean"] >= 8.5:
        codes.append("HIGH_EFFORT")
    if row["fatigue_flag"]:
        codes.append("FATIGUE")
    if row["flag_high_strain_day"]:
        codes.append("HIGH_STRAIN_DAY")
    if row.get("overload_flags"):
        codes.append("NEURAL_OVERLOAD")
    return "|".join(codes) if codes else "NONE"
```

| Código | Significado |
|--------|-------------|
| `LOW_SLEEP` | Sueño < 6.5h |
| `HIGH_ACWR` | Ratio carga aguda/crónica > 1.5 |
| `PERF_DROP` | Performance Index < 0.98 |
| `HIGH_EFFORT` | Esfuerzo medio ≥ 8.5 |
| `FATIGUE` | Flag de fatiga activo |
| `HIGH_STRAIN_DAY` | Día de alta exigencia (RIR≤1 + effort≥8.5) |
| `UNDERSTIM` | Poco estímulo (RIR≥4 + effort≤6.5) |
| `NEURAL_OVERLOAD` | Sobrecarga neuromuscular detectada |

---

## 3. NEURAL OVERLOAD DETECTOR

### 📍 Ubicación: `src/neural_overload_detector.py`

### Concepto
Detecta **fatiga del sistema nervioso central (SNC)** que no se ve en métricas simples de entrenamiento. El SNC tarda más en recuperarse que los músculos, y su fatiga acumulada puede llevar a:
- Estancamiento prolongado
- Mayor riesgo de lesión
- Pérdida de motivación
- Síndrome de sobreentrenamiento

### Las 4 Señales de Sobrecarga

---

#### 1️⃣ SUSTAINED_NEAR_FAILURE

**Qué detecta**: Ir al fallo muscular o muy cerca, repetidamente.

**Por qué es problemático**: El entrenamiento al fallo es muy demandante para el SNC. Hacerlo consistentemente no permite recuperación neural.

**Severidad**: 25-30 puntos

```python
def detect_sustained_near_failure(df_ex, config, is_advanced):
    k = config.near_failure_k_sessions  # 3 normal, 2 para avanzados
    recent = df_ex.tail(k)
    
    # Contar sesiones de alta intensidad
    intensity_flag = (
        (recent["top_rir"] <= 1) |   # RIR 0-1
        (recent["top_rpe"] >= 9)      # RPE 9-10
    )
    proportion = intensity_flag.mean()
    mean_rir = recent["top_rir"].mean()
    
    # Dispara si 2/3+ sesiones son intensas Y media RIR ≤ 1
    if proportion >= 0.66 and mean_rir <= 1.0:
        return LiftFlag(
            flag_type="SUSTAINED_NEAR_FAILURE",
            severity=25,
            recommendations=[
                f"Evita RIR0 en {exercise} durante 7 días",
                f"Top set a RIR2 + 2 backoff sets",
                f"Reduce sets -20%"
            ]
        )
```

---

#### 2️⃣ FIXED_LOAD_DRIFT

**Qué detecta**: Rendimiento cayendo aunque uses la misma carga.

**Por qué es problemático**: Indica que el cuerpo no puede mantener el output con el mismo input. Señal clara de fatiga acumulada.

**Severidad**: 20-25 puntos

```python
def detect_fixed_load_drift(df_ex, config, is_advanced):
    recent = df_ex.tail(config.window_sessions)
    last = recent.iloc[-1]
    
    # Buscar sesiones con carga similar (±2.5kg)
    comparable = sessions_with_load(last["top_load"], tolerance=2.5)
    
    baseline_reps = comparable["top_reps"].median()
    baseline_rir = comparable["top_rir"].median()
    baseline_e1rm = comparable["top_e1rm"].median()
    
    # Detectar caídas
    rep_drop = last["top_reps"] <= baseline_reps - 1
    rir_drop = last["top_rir"] <= baseline_rir - 1
    e1rm_drop = last["top_e1rm"] < baseline_e1rm * 0.97  # -3%
    
    if rep_drop or rir_drop or e1rm_drop:
        return LiftFlag(
            flag_type="FIXED_LOAD_DRIFT",
            severity=20,
            evidence={
                "baseline_reps": baseline_reps,
                "current_reps": last["top_reps"],
                "drift_type": ["reps", "rir", "e1rm"]
            },
            recommendations=[
                f"Micro-deload: -5% carga o +2 RIR por 1 semana",
                f"Cambia estímulo: pausas, tempo, rep range 6-8",
                f"No busques PR esta semana"
            ]
        )
```

---

#### 3️⃣ HIGH_VOLATILITY

**Qué detecta**: Rendimiento errático (oscila mucho entre sesiones).

**Por qué es problemático**: La inconsistencia indica que el sistema no está estabilizado. Puede ser fatiga neural o recuperación insuficiente.

**Severidad**: 10-13 puntos

```python
def detect_high_volatility(df_ex, config, is_advanced):
    recent = df_ex.tail(config.window_sessions)
    comparable = sessions_with_same_load(recent)
    
    # Métricas de volatilidad
    rep_range = comparable["top_reps"].max() - comparable["top_reps"].min()
    e1rm_cv = comparable["top_e1rm"].std() / comparable["top_e1rm"].mean()
    
    # Proporción de sesiones a RIR bajo
    low_rir_share = (comparable["top_rir"] <= 1).mean()
    
    # Volatilidad + intensidad alta = problema
    is_volatile = (rep_range >= 2) or (e1rm_cv > 0.04)
    
    if is_volatile and low_rir_share >= 0.5:
        return LiftFlag(
            flag_type="HIGH_VOLATILITY",
            severity=10,
            evidence={
                "rep_range": rep_range,
                "e1rm_cv": e1rm_cv,
                "low_rir_share": low_rir_share
            },
            recommendations=[
                f"Aumenta consistencia: misma estructura y descanso",
                f"Controla fatiga: máx 1 top set pesado por sesión",
                f"Máx 1 set @RIR0/semana; usa top set @RIR1 + backoffs"
            ]
        )
```

---

#### 4️⃣ PLATEAU_EFFORT_RISE

**Qué detecta**: Estancamiento + esfuerzo creciente.

**Por qué es problemático**: Estás trabajando más duro para obtener los mismos resultados. El ratio esfuerzo/resultado está empeorando.

**Severidad**: 15-18 puntos

```python
def detect_plateau_effort_rise(df_ex, config, is_advanced):
    recent = df_ex.tail(config.window_sessions)
    
    # Verificar plateau de carga (<3% cambio)
    load_first = recent.iloc[:len(recent)//2]["top_load"].median()
    load_last = recent.iloc[len(recent)//2:]["top_load"].median()
    is_plateau = abs(load_last - load_first) / load_first < 0.03
    
    if not is_plateau:
        return None
    
    # Verificar tendencia de esfuerzo (RIR bajando = esfuerzo subiendo)
    rir_first = recent.iloc[:half]["top_rir"].mean()
    rir_second = recent.iloc[half:]["top_rir"].mean()
    effort_rising = (rir_second - rir_first) < -0.7
    
    if effort_rising:
        return LiftFlag(
            flag_type="PLATEAU_EFFORT_RISE",
            severity=15,
            evidence={
                "load_change_pct": load_change_pct,
                "rir_first_half": rir_first,
                "rir_second_half": rir_second
            },
            recommendations=[
                f"Cambio de estímulo necesario",
                f"Varía rep ranges, tempo, o variantes del ejercicio",
                f"Considera deload de 1 semana"
            ]
        )
```

---

### Overload Score y Caps de Readiness

El sistema suma la severidad de todos los flags activos:

```python
overload_score = sum(flag.severity for flag in active_flags)
```

Luego aplica **caps** (límites) al readiness basado en el overload score:

```python
if overload_score >= 60:
    readiness = min(readiness, 45)  # Máximo 45 aunque te sientas bien
elif overload_score >= 45:
    readiness = min(readiness, 55)  # Máximo 55
elif overload_score >= 30:
    readiness = min(readiness, 65)  # Máximo 65
```

**Justificación**: Puedes sentirte bien subjetivamente pero tener fatiga neural acumulada. Los caps previenen que ignores señales objetivas de sobrecarga.

---

### Configuración Adaptativa por Nivel de Atleta

```python
@dataclass
class OverloadConfig:  # Configuración normal
    near_failure_k_sessions: int = 3
    near_failure_proportion: float = 0.66  # 2/3 de sesiones
    drift_e1rm_drop_pct: float = 0.03      # 3% caída

@dataclass  
class AdvancedConfig(OverloadConfig):  # Para atletas avanzados
    near_failure_k_sessions: int = 2       # Más sensible (2 sesiones)
    near_failure_proportion: float = 0.50  # 1/2 de sesiones
    drift_e1rm_drop_pct: float = 0.015     # 1.5% caída (más estricto)
```

**Por qué diferente para avanzados**:
- Progresan más lento (mantener carga es normal, no señal de problema)
- Mayor sensibilidad a fatiga neural (años de entrenamiento acumululado)
- Señales "finas" son más relevantes (pequeñas caídas importan más)

### Clasificación Automática de Nivel

```python
def classify_advanced_lifts(df_top):
    for exercise in exercises:
        n_sessions = count_sessions(exercise)
        
        if n_sessions < 6:
            level = "NOVICE"
        elif n_sessions < 12:
            level = "INTERMEDIATE"
        else:
            # Avanzado si: muchas sesiones + carga estable (CV < 5%)
            cv_load = load_std / load_mean
            level = "ADVANCED" if cv_load < 0.05 else "INTERMEDIATE"
```

---

## 4. FLUJO COMPLETO

### Diagrama del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    INPUTS DEL USUARIO                            │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Sueño: horas, calidad, fragmentado                       │    │
│  │ Estado: fatiga, estrés, energía, dolor                   │    │
│  │ Subjetivo: intuición (0-10), motivación                  │    │
│  │ Flags: alcohol, cafeína, enfermedad, dolor físico        │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────┬───────────────────────────────────────────┘
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              CALCULATE_READINESS_FROM_INPUTS_V2                  │
│                                                                  │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐             │
│  │Percepción│  │  Sueño  │  │ Estado  │  │Motivación│            │
│  │   18%    │  │   32%   │  │   36%   │  │   15%   │             │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘             │
│       │            │            │            │                   │
│       └────────────┴─────┬──────┴────────────┘                   │
│                          ▼                                       │
│                  - Penalizaciones                                │
│                  (dolor, enfermedad, cafeína)                    │
│                          ▼                                       │
│              READINESS SCORE (0-100)                             │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│              NEURAL OVERLOAD DETECTOR                            │
│                                                                  │
│  Analiza historial de ejercicios (últimas 6-10 sesiones)        │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │ Sustained    │  │  Fixed Load  │  │    High      │           │
│  │ Near Failure │  │    Drift     │  │  Volatility  │           │
│  │   25 pts     │  │   20 pts     │  │   10 pts     │           │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘           │
│         │                 │                 │                    │
│  ┌──────┴─────────────────┴─────────────────┴───────┐           │
│  │              OVERLOAD SCORE                       │           │
│  │  Suma de severidades de flags activos             │           │
│  └──────────────────────┬───────────────────────────┘           │
│                         ▼                                        │
│              ¿Overload ≥ 30? → CAP READINESS                     │
│              (≥30→max 65, ≥45→max 55, ≥60→max 45)                │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                  DECISION ENGINE                                 │
│                                                                  │
│  Inputs: Readiness + ACWR + Performance Index + Flags           │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ IF readiness ≥ 80 AND !overload                          │    │
│  │    → "Push day" - "+2.5% carga en lift principal"        │    │
│  │                                                          │    │
│  │ IF readiness 65-79                                       │    │
│  │    → "Normal" - "Mantén carga, target RIR 1-2"           │    │
│  │                                                          │    │
│  │ IF readiness 50-64                                       │    │
│  │    → "Reduce" - "-15-20% volumen"                        │    │
│  │                                                          │    │
│  │ IF readiness < 50 OR overload ≥ 60                       │    │
│  │    → "Deload" - "-40% volumen o descanso"                │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  + Genera reason_codes: LOW_SLEEP|HIGH_ACWR|PERF_DROP|etc       │
└─────────────────────┬───────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                    OUTPUT FINAL                                  │
│                                                                  │
│  🎯 Readiness: 78                                                │
│  📊 Recomendación: Normal                                        │
│  💡 Acción: "Mantén carga, target RIR 1-2"                       │
│  ⚠️ Razones: MOD_READINESS|ELEVATED_ACWR                         │
│  🧠 Sobrecarga neural: Ninguna / [flags específicos]             │
└─────────────────────────────────────────────────────────────────┘
```

---

### Ejemplo Completo

**Inputs del usuario:**
- Sueño: 7h, calidad 4/5, sin fragmentación
- Intuición: 8/10
- Fatiga: 3/10, Estrés: 4/10, Energía: 8/10
- Motivación: 9/10
- Flags: ninguno

**Cálculo Readiness:**
```
Percepción: 0.18 × (8/10) = 0.144 → 14.4 pts
Sueño: 0.85 × 0.38 × [(0.8×0.6 + 0.75×0.4)] = 0.85 × 0.38 × 0.78 = 0.252 → 25.2 pts
Estado: 0.85 × 0.42 × [0.4×0.8 + 0.35×0.7 + 0.2×0.6 + 0.05×1.0] = 0.254 → 25.4 pts
Motivación: 0.85 × 0.18 × 0.9 = 0.138 → 13.8 pts
Penalizaciones: 0

TOTAL: 14.4 + 25.2 + 25.4 + 13.8 = 78.8 → 79 pts
```

**Neural Overload Check:**
- Últimas 6 sesiones de Press Banca: RIR promedio 2.1
- No hay SUSTAINED_NEAR_FAILURE ✓
- No hay FIXED_LOAD_DRIFT ✓
- No hay HIGH_VOLATILITY ✓
- Overload Score: 0

**Decision Engine:**
```
Readiness 79 + No overload + ACWR 1.1 (ok)
→ Recomendación: "Normal"
→ Acción: "Mantén carga, target RIR 1-2"
→ Reason codes: MOD_READINESS
```

---

## Notas Finales

### Filosofía del Sistema

1. **Equilibrio subjetivo/objetivo**: La percepción importa, pero no domina. Los datos objetivos (sueño, historial) moderan la subjetividad.

2. **Personalización real**: Los baselines y sensibilidades se calculan de TU historial, no de promedios poblacionales.

3. **Prevención sobre reacción**: El neural overload detector busca patrones ANTES de que llegues a sobreentrenamiento real.

4. **Actionable outputs**: Cada recomendación incluye acciones específicas ("+2.5% carga", "-20% volumen") en lugar de consejos vagos.

### Limitaciones Conocidas

- Requiere ~14+ días de datos para personalización efectiva
- Los baselines de sueño asumen consistencia (shift workers pueden tener ruido)
- El neural overload detector funciona mejor con datos de ejercicios principales (no accesorios)

---

## 5. READINESS v3 "NASA"

### 📍 Ubicación: `app/calculations/readiness_v3.py` → `calculate_readiness_from_inputs_v3()`

### Concepto

Readiness v3 es una evolución del algoritmo v2 con las siguientes mejoras:

1. **Curvas sigmoides** en lugar de lineales (transiciones suaves)
2. **Confidence score** según datos disponibles
3. **Consistency bonus** por estabilidad en los últimos 7 días
4. **Momentum bonus** por tendencia positiva
5. **Penalizaciones proporcionales** (no fijas)
6. **Explicaciones humanas** del score

### Funciones de Curvas

```python
# Sigmoid: transición suave centrada
sigmoid(x, center=0.5, steepness=10.0)
#   Retorna 0→1 con curva S centrada en 'center'

# Smoothstep: interpolación Hermite
smoothstep(x, edge0=0.0, edge1=1.0) = 3t² - 2t³
#   Transición ultra suave entre edge0 y edge1

# Smootherstep: aún más suave
smootherstep(x) = 6t⁵ - 15t⁴ + 10t³

# Soft clip: recorte gradual (no abrupto)
soft_clip(x, lo, hi, softness=0.1)
#   Usa tanh para suavizar en los bordes

# Saturating curve: sube rápido, luego satura
saturating_curve(x, saturation_point=0.8) = 1 - e^(-kx)
#   90% del máximo en saturation_point
```

### Arquitectura v3

```
┌────────────────────────────────────────────────────────────┐
│                    CORE READINESS (80%)                     │
│                                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ Sueño   │  │ Estado  │  │Percepción│  │Motivación│       │
│  │  32%    │  │  36%    │  │   18%   │  │   14%   │        │
│  │(curvas) │  │(sigmoid)│  │(smooth) │  │(satur.) │        │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘        │
│       │            │            │            │              │
│       └────────────┴─────┬──────┴────────────┘              │
│                          ▼                                  │
│                   SCORE BASE                                │
└────────────────────────────┬───────────────────────────────┘
                             │
┌────────────────────────────┴───────────────────────────────┐
│                   MODIFIERS (+0-8%)                         │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ Consistency  │  │   Momentum   │                        │
│  │   0-6 pts    │  │   0-3 pts    │                        │
│  └──────────────┘  └──────────────┘                        │
└────────────────────────────┬───────────────────────────────┘
                             │
┌────────────────────────────┴───────────────────────────────┐
│                 PENALIZACIONES (suaves)                     │
│                                                             │
│  Pain: 0-20% (proporcional a contexto)                     │
│  Sick: 0-40% (curva sigmoid, no escalones)                 │
│  Alcohol: 0-15% (según impacto en sueño)                   │
│  Sleep disruption: 0-8%                                    │
│  Caffeine mask: 0-3% (solo si cafeína+fatiga altas)        │
└────────────────────────────────────────────────────────────┘
```

### Scoring por Componente

#### Sueño (32%)

```python
# Centrado en tu baseline personal (o 7h fallback)
# Asimétrico: penaliza más dormir menos que dormir más

if hours < center:
    score = smootherstep(normalized, -0.2, 0.6) * 0.85
else:
    score = 0.85 + saturating_curve(bonus) * 0.15
```

| Horas vs Baseline | Score Aprox |
|-------------------|-------------|
| +1h o más | 0.95-1.0 |
| +0 a +1h | 0.85-0.95 |
| -0.5h a 0 | 0.75-0.85 |
| -1.5h | 0.55-0.65 |
| -2h o más | 0.30-0.50 |

#### Fatiga/Estrés (con sigmoid)

```python
# Sigmoid centrada en 0.6 (fatiga 6/10 es el punto crítico)
raw_score = 1.0 - sigmoid(fatigue/10, center=0.60, steepness=6.0)

# Fatiga 0-2 siempre da score alto (≥0.92)
```

| Fatiga | Score |
|--------|-------|
| 0-2 | 0.92-1.0 |
| 3-4 | 0.78-0.88 |
| 5-6 | 0.55-0.70 |
| 7-8 | 0.30-0.45 |
| 9-10 | 0.15-0.25 |

#### Energía (saturating curve)

```python
# Sube rápido de 0-6, luego satura
score = saturating_curve(energy/10, saturation_point=0.65)

# Boost para energía ≥7
if energy >= 7:
    score += (energy/10 - 0.7) * 0.25
```

#### Motivación (saturante)

```python
# Motivación 6 ya es "suficiente" (satura en 0.6)
score = saturating_curve(motivation/10, saturation_point=0.6)
```

**Justificación**: Motivación 10 no debe "salvar" un día con mal sueño y alta fatiga.

### Confidence Score

```python
def calculate_confidence(df_daily, inputs):
    # 60% basado en días de histórico
    if days >= 28: days_score = 0.95
    elif days >= 14: days_score = 0.70
    elif days >= 7: days_score = 0.45
    else: days_score = 0.20
    
    # 40% basado en completitud de inputs
    completeness = inputs_presentes / inputs_clave
    
    score = days_score * 0.60 + completeness * 0.40
```

| Días | Confidence | Nivel |
|------|------------|-------|
| <7 | 0.25-0.45 | low |
| 7-14 | 0.45-0.65 | medium |
| 14-28 | 0.65-0.85 | medium-high |
| ≥28 | 0.85-0.97 | high |

**Uso del Confidence**:
- `confidence_mod = 0.5 + confidence_score * 0.5` (rango 0.5-1.0)
- Penalizaciones se multiplican por `confidence_mod`
- Si confidence es baja, el sistema es más conservador

### Consistency Bonus

```python
# Bonus por estabilidad en últimos 7 días (máx +6 pts)

# Sueño estable (std < 0.5h): +2 pts
# Fatiga controlada (0 días >7): +2 pts
# Readiness sin dientes de sierra (std < 8): +2 pts
```

**Filosofía**: Premia hábitos buenos, pero NO castiga inconsistencia (solo no da bonus).

### Momentum Bonus

```python
# Bonus por tendencia positiva (máx +3 pts)

# Performance Index mejorando: +2 pts
# Readiness subiendo vs semana anterior: +1 pt
```

### Penalizaciones v3 (proporcionales)

#### Pain (0-20%)

```python
base_penalty = 0.08  # 8% base si hay dolor

# Agravantes:
if soreness > 6: +30%
if stiffness > 5: +20%
if zona crítica (espalda/hombro/rodilla): +25%

# Cap máximo: 20%
```

#### Sick (curva sigmoid)

```python
# En vez de escalones {1: 5%, 2: 8%, 3: 15%...}
penalty = sigmoid(sick_level/5, center=0.35, steepness=6.0) * 0.40
```

| Sick Level | Penalización |
|------------|--------------|
| 1 | ~5% |
| 2 | ~12% |
| 3 | ~22% |
| 4 | ~32% |
| 5 | ~38% |

### Output de v3

```python
{
    'readiness_score': 79,  # 0-100
    'readiness_0_1': 0.79,
    'confidence': 'high',
    'confidence_score': 0.92,
    'components': {
        'sleep': 25.0,
        'state': 30.0,
        'perceived': 16.0,
        'motivation': 13.0,
        'bonuses': 6.0,
        'penalties': -3.0
    },
    'explanations': [
        "Sueño: +25 pts (7.0h cerca de tu mediana, cal normal)",
        "Estado: +30 pts (energía buena, fatiga normal, estrés normal)",
        "Percepción: +16 pts (bien)",
        "Motivación: +13 pts (alta)",
        "Consistencia: +6 pts (sueño estable, fatiga controlada)",
        "Confidence: high (30 días de datos)"
    ],
    'debug': {...}
}
```

### Comparativa v2 vs v3

| Aspecto | v2 | v3 |
|---------|----|----|
| Transiciones | Lineales | Sigmoides/smooth |
| Pain penalty | -15 fijo | 8-20% proporcional |
| Sick penalty | Escalones | Curva continua |
| Baseline aware | Parcial | Completo con confidence |
| Bonus estabilidad | No | +0-6 pts |
| Bonus momentum | No | +0-3 pts |
| Explicaciones | Ninguna | 4-6 strings |
| Punitivo | Moderado | Mínimo |

---

*Documentación generada para el proyecto data-projectz*
*Última actualización: Enero 2026*
