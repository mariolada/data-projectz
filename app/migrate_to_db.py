"""
Script de migración: CSV → SQLite
Migra los datos existentes en CSV a la nueva base de datos SQLite
"""
import sys
from pathlib import Path
import pandas as pd
from datetime import datetime
import shutil

# Añadir el directorio app al path
sys.path.insert(0, str(Path(__file__).parent))

from database.connection import init_db, get_db
from database.repositories import TrainingRepository, ExerciseRepository, MoodRepository

# Rutas de archivos CSV
TRAINING_CSV = Path("data/raw/training.csv")
EXERCISES_CSV = Path("data/raw/exercises.csv")
MOOD_CSV = Path("data/raw/mood_daily.csv")


def backup_csvs():
    """Crear backup de los CSVs antes de migrar"""
    backup_dir = Path("data/backup_csvs")
    backup_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    files_to_backup = [TRAINING_CSV, EXERCISES_CSV, MOOD_CSV]
    
    for csv_file in files_to_backup:
        if csv_file.exists():
            backup_file = backup_dir / f"{csv_file.stem}_{timestamp}{csv_file.suffix}"
            shutil.copy2(csv_file, backup_file)
            print(f"✅ Backup: {csv_file.name} → {backup_file.name}")
    
    return backup_dir


def migrate_exercises(db):
    """Migrar ejercicios"""
    if not EXERCISES_CSV.exists():
        print("⚠️ No se encontró exercises.csv, saltando...")
        return 0
    
    print("\n📦 Migrando ejercicios...")
    df = pd.read_csv(EXERCISES_CSV)
    
    count = 0
    for _, row in df.iterrows():
        exercise_name = str(row.get('exercise', '')).strip()
        if exercise_name:
            ExerciseRepository.add(db, exercise_name)
            count += 1
    
    print(f"✅ Migrados {count} ejercicios")
    return count


def migrate_trainings(db):
    """Migrar entrenamientos"""
    if not TRAINING_CSV.exists():
        print("⚠️ No se encontró training.csv, saltando...")
        return 0
    
    print("\n🏋️ Migrando entrenamientos...")
    df = pd.read_csv(TRAINING_CSV)
    
    # Convertir fecha si es necesario
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date']).dt.date
    
    count = 0
    for _, row in df.iterrows():
        training_data = {
            'date': row.get('date'),
            'exercise': row.get('exercise', ''),
            'sets': int(row.get('sets', 3)),
            'reps': int(row.get('reps', 8)),
            'weight': float(row.get('weight', 0.0)),
            'rpe': float(row.get('rpe', 7.0)) if pd.notna(row.get('rpe')) else 7.0,
            'rir': float(row.get('rir', 2.0)) if pd.notna(row.get('rir')) else 2.0,
            'session_name': str(row.get('session_name', '')) if pd.notna(row.get('session_name')) else ''
        }
        
        TrainingRepository.create(db, training_data)
        count += 1
    
    print(f"✅ Migrados {count} entrenamientos")
    return count


def migrate_mood(db):
    """Migrar datos de mood/estado diario"""
    if not MOOD_CSV.exists():
        print("⚠️ No se encontró mood_daily.csv, saltando...")
        return 0
    
    print("\n😊 Migrando datos de mood...")
    df = pd.read_csv(MOOD_CSV)
    
    # Convertir fecha si es necesario
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date']).dt.date
    
    count = 0
    for _, row in df.iterrows():
        mood_data = {
            'date': row.get('date'),
            'sleep_hours': float(row.get('sleep_hours', 0)) if pd.notna(row.get('sleep_hours')) else None,
            'sleep_quality': int(row.get('sleep_quality', 5)) if pd.notna(row.get('sleep_quality')) else None,
            'fatigue': int(row.get('fatigue', 5)) if pd.notna(row.get('fatigue')) else None,
            'soreness': int(row.get('soreness', 5)) if pd.notna(row.get('soreness')) else None,
            'stress': int(row.get('stress', 5)) if pd.notna(row.get('stress')) else None,
            'motivation': int(row.get('motivation', 5)) if pd.notna(row.get('motivation')) else None,
            'pain_flag': int(row.get('pain_flag', 0)) if pd.notna(row.get('pain_flag')) else 0,
            'pain_location': str(row.get('pain_location', '')) if pd.notna(row.get('pain_location')) else '',
            'readiness': float(row.get('readiness', 0)) if pd.notna(row.get('readiness')) else None
        }
        
        MoodRepository.create_or_update(db, mood_data)
        count += 1
    
    print(f"✅ Migrados {count} registros de mood")
    return count


def verify_migration(db):
    """Verificar que los datos se migraron correctamente"""
    print("\n🔍 Verificando migración...")
    
    exercises = ExerciseRepository.get_all(db)
    print(f"✅ Ejercicios en BD: {len(exercises)}")
    
    trainings_df = TrainingRepository.get_all(db)
    print(f"✅ Entrenamientos en BD: {len(trainings_df)} registros")
    
    mood_df = MoodRepository.get_all(db)
    print(f"✅ Registros de mood en BD: {len(mood_df)}")
    
    return {
        'exercises': len(exercises),
        'trainings': len(trainings_df),
        'mood': len(mood_df)
    }


if __name__ == "__main__":
    print("="*60)
    print("🚀 INICIANDO MIGRACIÓN CSV → SQLite")
    print("="*60)
    
    # 1. Crear backup
    print("\n📋 PASO 1: Creando backup de archivos CSV...")
    backup_dir = backup_csvs()
    print(f"✅ Backup guardado en: {backup_dir}")
    
    # 2. Inicializar BD
    print("\n📋 PASO 2: Inicializando base de datos...")
    init_db()
    print("✅ Base de datos inicializada")
    
    # 3. Migrar datos
    print("\n📋 PASO 3: Migrando datos...")
    db = next(get_db())
    
    try:
        total_exercises = migrate_exercises(db)
        total_trainings = migrate_trainings(db)
        total_mood = migrate_mood(db)
        
        # 4. Verificar
        print("\n📋 PASO 4: Verificando datos migrados...")
        stats = verify_migration(db)
        
        print("\n" + "="*60)
        print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("="*60)
        print(f"📊 Resumen:")
        print(f"   - Ejercicios: {stats['exercises']}")
        print(f"   - Entrenamientos: {stats['trainings']}")
        print(f"   - Registros mood: {stats['mood']}")
        print(f"\n💾 Backup guardado en: {backup_dir}")
        print(f"📁 Base de datos: data/app.db")
        print("\n✅ ¡Puedes empezar a usar la aplicación con la nueva BD!")
        
    except Exception as e:
        print(f"\n❌ ERROR durante la migración: {e}")
        print(f"⚠️ Los archivos CSV originales están intactos")
        print(f"📋 Backup disponible en: {backup_dir}")
        raise
    
    finally:
        db.close()
