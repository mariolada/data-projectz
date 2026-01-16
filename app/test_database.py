"""
Script de prueba para verificar que la base de datos se crea correctamente
"""
import sys
from pathlib import Path

# Añadir el directorio app al path
sys.path.insert(0, str(Path(__file__).parent))

from database.connection import init_db, get_db
from database.repositories import TrainingRepository, ExerciseRepository
from datetime import date

if __name__ == "__main__":
    print("🔧 Inicializando base de datos...")
    init_db()
    print("✅ Base de datos creada en: data/app.db")
    
    print("\n🧪 Probando inserción de datos...")
    db = next(get_db())
    
    try:
        # Probar insertar un ejercicio
        ExerciseRepository.add(db, "Press Banca")
        print("✅ Ejercicio insertado")
        
        # Probar insertar un entrenamiento
        training_data = {
            'date': date.today(),
            'exercise': 'Press Banca',
            'sets': 3,
            'reps': 8,
            'weight': 80.0,
            'rpe': 7,
            'rir': 2,
            'session_name': 'Prueba'
        }
        TrainingRepository.create(db, training_data)
        print("✅ Entrenamiento insertado")
        
        # Leer datos
        exercises = ExerciseRepository.get_all(db)
        print(f"✅ Ejercicios en BD: {exercises}")
        
        trainings_df = TrainingRepository.get_all(db)
        print(f"✅ Entrenamientos en BD: {len(trainings_df)} registros")
        print(trainings_df)
        
        print("\n✅ ¡TODO FUNCIONA CORRECTAMENTE!")
        
    finally:
        db.close()
