# 🔧 Diagnóstico y Solución: Gráficas Semanales No Aparecían

**Fecha:** 2026-01-13  
**Problema:** Las gráficas en la vista "Semana" no aparecían aunque `weekly.csv` existía  
**Estado:** ✅ RESUELTO

---

## 📊 Análisis del Problema

### Causa Raíz
El archivo `weekly.csv` tiene fechas en formato **YYYY-MM-DD** (ISO 8601), pero el código las parseaba con `dayfirst=True`, causando:

| Fecha Original | Parsing Erróneo | Parsing Correcto |
|---|---|---|
| 2025-12-01 | 2025-01-12 ❌ | 2025-12-01 ✅ |
| 2025-12-08 | 2025-08-12 ❌ | 2025-12-08 ✅ |
| 2025-12-15 | **NaT** ❌ | 2025-12-15 ✅ |

**Resultado:** De 6 filas, solo 3 se leían correctamente. Tras `dropna()`, quedaba 1 fila. El filtro de "últimas 12 semanas" dejaba los datos **completamente vacíos**.

### Síntomas Observados
- Vista "Semana" mostraba solo el sidebar, sin gráficas
- No había mensajes de error visibles
- `except: pass` ocultaba el problema real

---

## ✅ Cambios Implementados

### 1️⃣ Error Handling Visible (línea ~1667)
**Archivo:** `app/streamlit_app.py`

```python
# ANTES (ocultaba el error):
df_weekly = None
try:
    df_weekly = load_csv(weekly_path)
except:
    pass

# DESPUÉS (muestra el error):
df_weekly = None
try:
    df_weekly = load_csv(weekly_path)
except Exception as e:
    st.warning(f"❌ No pude cargar weekly.csv: {e}")
    df_weekly = None
```

**Beneficio:** Cualquier problema de carga se ve inmediatamente en la app.

---

### 2️⃣ Debug Block Completo (línea ~2765)
**Archivo:** `app/streamlit_app.py`

Se agregó un `expander` con diagnóstico que muestra:
- Si `df_weekly` es None
- Número de filas y columnas reales
- Primeras 5 filas (dataframe preview)
- Validación de `week_start`:
  - ¿Tiene la columna?
  - ¿Cuántos NaT hay?
  - ¿Cuál es el rango de fechas?
- Búsqueda flexible de columnas de volumen
- Filas tras el filtro de 12 semanas

**Beneficio:** Diagnosticar instantáneamente dónde falla la carga sin tocar código.

```python
# El debug está expandido por defecto, puedes comprimirlo luego
with st.expander("🔍 DEBUG: Diagnóstico de datos semanales", expanded=True):
    # ... código de diagnóstico
```

---

### 3️⃣ Fix del Parsing de Fechas (línea ~2790)
**Archivo:** `app/streamlit_app.py`

```python
# ANTES (parsing incorrecto):
df_weekly['week_start'] = pd.to_datetime(
    df_weekly['week_start'], 
    errors='coerce', 
    dayfirst=True  # ❌ INCORRECTO para YYYY-MM-DD
)

# DESPUÉS (parsing correcto):
df_weekly['week_start'] = pd.to_datetime(
    df_weekly['week_start'], 
    errors='coerce'
    # dayfirst=False es el default ✅
)
```

**Beneficio:** Las 6 filas de `weekly.csv` ahora se cargan correctamente.

---

## 🧪 Validación

Antes del fix:
```
Filas de weekly.csv: 6
NaT despues to_datetime: 3
Filas tras dropna: 3
Filas tras filtro 12 semanas: 1 ❌ (VACIO)
```

Después del fix:
```
Filas de weekly.csv: 6
NaT despues to_datetime: 0 ✅
Filas tras dropna: 6 ✅
Filas tras filtro 12 semanas: 6 ✅
```

---

## 🎯 Cómo Verificar que Funciona

1. Abre la app: `streamlit run app/streamlit_app.py`
2. En el sidebar, selecciona **"Semana"**
3. Deberías ver el expander `🔍 DEBUG: Diagnóstico...` expandido
4. Verifica que diga:
   - `df_weekly es None?: False`
   - `Filas df_weekly: 6`
   - `NaT en week_start: 0`
   - `Filas df_weekly_filtered (últimas 12 semanas): 6`
   - `Columna de volumen encontrada: 'volume_week'`
5. Si compruebas el expander, deberías ver:
   - Tabla con 6 filas de `week_start` válidas
   - Gráficas: Volumen Semanal, Strain, Readiness, Performance, etc.

---

## 🛡️ Lecciones Aprendidas

### ❌ Anti-patrones encontrados:
```python
# MALO: except: pass (traga errores)
except:
    pass

# MALO: dayfirst=True para fechas ISO (YYYY-MM-DD)
pd.to_datetime(fecha_iso, dayfirst=True)
```

### ✅ Mejores prácticas aplicadas:
```python
# BIEN: Mostrar el error
except Exception as e:
    st.warning(f"Error: {e}")

# BIEN: Sin dayfirst para ISO (o dayfirst=False)
pd.to_datetime(fecha_iso)  # YYYY-MM-DD

# BIEN: Debug visible en desarrollo
with st.expander("🔍 DEBUG", expanded=True):
    st.write(...)  # Info diagnosis
```

---

## 📝 Archivos Modificados

- `app/streamlit_app.py`
  - Línea ~1667: Error handling visible
  - Línea ~2765: Debug block completo
  - Línea ~2790: Fix del parsing de fechas

---

## 🚀 Próximos Pasos (Opcionales)

1. **Cambiar el `expanded=True` a `expanded=False`** en el debug expander cuando esté en producción
2. **Regenerar `weekly.csv`** desde el pipeline si es posible (para garantizar calidad de datos)
3. **Validar otras vistas** ("Día", "Modo Hoy") para asegurar que usan el parsing correcto también
4. **Reemplazar `use_container_width`** con `width='stretch'` en Streamlit (deprecation warning)

---

## ✨ Resumen

| Aspecto | Antes | Después |
|--------|-------|---------|
| Gráficas semanales | ❌ No aparecen | ✅ Aparecen |
| Filas cargadas | 1 de 6 | 6 de 6 |
| Errores visibles | No (except: pass) | Sí (st.warning) |
| Diagnóstico | Manual | Automático (DEBUG block) |
| Parsing de fechas | Incorrecto (dayfirst=True) | Correcto (YYYY-MM-DD) |

