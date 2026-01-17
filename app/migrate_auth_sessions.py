"""
Script de migración para agregar columnas profile_picture_url, gender y menstrual_cycle_data a auth_sessions
"""
import sqlite3
from pathlib import Path

def migrate_auth_sessions():
    db_path = Path("data/app.db")
    
    if not db_path.exists():
        print("Base de datos no existe, no se requiere migración")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Verificar si las columnas ya existen
    cursor.execute("PRAGMA table_info(auth_sessions)")
    columns = [col[1] for col in cursor.fetchall()]
    
    changes_made = False
    
    # Agregar profile_picture_url si no existe
    if 'profile_picture_url' not in columns:
        print("Agregando columna profile_picture_url...")
        cursor.execute("ALTER TABLE auth_sessions ADD COLUMN profile_picture_url VARCHAR")
        changes_made = True
        print("✅ Columna profile_picture_url agregada")
    else:
        print("✓ Columna profile_picture_url ya existe")
    
    # Agregar gender si no existe
    if 'gender' not in columns:
        print("Agregando columna gender...")
        cursor.execute("ALTER TABLE auth_sessions ADD COLUMN gender VARCHAR")
        changes_made = True
        print("✅ Columna gender agregada")
    else:
        print("✓ Columna gender ya existe")
    
    # Agregar menstrual_cycle_data si no existe
    if 'menstrual_cycle_data' not in columns:
        print("Agregando columna menstrual_cycle_data...")
        cursor.execute("ALTER TABLE auth_sessions ADD COLUMN menstrual_cycle_data TEXT")
        changes_made = True
        print("✅ Columna menstrual_cycle_data agregada")
    else:
        print("✓ Columna menstrual_cycle_data ya existe")
    
    if changes_made:
        conn.commit()
        print("\n✅ Migración completada exitosamente")
    else:
        print("\n✓ No se requirieron cambios")
    
    conn.close()

if __name__ == "__main__":
    migrate_auth_sessions()
