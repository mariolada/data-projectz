"""
Conexión a la base de datos
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from .models import Base

# Ruta de la base de datos SQLite local
DATABASE_PATH = Path("data/app.db")
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

# URL de conexión (SQLite para desarrollo local)
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"

# Crear motor de BD
engine = create_engine(
    DATABASE_URL, 
    echo=False,  # Cambiar a True para ver SQL generado (debug)
    connect_args={"check_same_thread": False}  # Necesario para SQLite + Streamlit
)

# Crear sesión
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    Inicializa la base de datos creando todas las tablas.
    Se ejecuta al inicio de la app.
    """
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    Obtiene una sesión de base de datos.
    Usar con context manager o try/finally.
    
    Ejemplo:
        db = next(get_db())
        try:
            # usar db
        finally:
            db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
