"""
Utilidades para exportar datos de la base de datos a CSV
(útil para pipelines legacy que aún leen CSV)
"""
import sys
from pathlib import Path

# Añadir app al path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from database.connection import get_db
from database.repositories import TrainingRepository, MoodRepository


def export_training_to_csv(output_path: str = "data/raw/training.csv"):
    """Exporta todos los entrenamientos de la BD a CSV"""
    db = next(get_db())
    try:
        df = TrainingRepository.get_all(db)
        
        if not df.empty:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_path, index=False)
            print(f"✅ Exportados {len(df)} entrenamientos a {output_path}")
            return True
        else:
            print("⚠️ No hay entrenamientos para exportar")
            return False
    finally:
        db.close()


def export_mood_to_csv(output_path: str = "data/raw/mood_daily.csv"):
    """Exporta todos los registros de mood de la BD a CSV"""
    db = next(get_db())
    try:
        df = MoodRepository.get_all(db)
        
        if not df.empty:
            # Renombrar columna 'readiness' a 'readiness_instant' para compatibilidad
            if 'readiness' in df.columns:
                df = df.rename(columns={'readiness': 'readiness_instant'})
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            df.to_csv(output_path, index=False)
            print(f"✅ Exportados {len(df)} registros de mood a {output_path}")
            return True
        else:
            print("⚠️ No hay registros de mood para exportar")
            return False
    finally:
        db.close()


def export_all_to_csv():
    """Exporta todos los datos de la BD a CSVs (para pipelines legacy)"""
    print("🔄 Exportando datos de BD a CSV...")
    export_training_to_csv()
    export_mood_to_csv()
    print("✅ Exportación completa")


if __name__ == "__main__":
    export_all_to_csv()
