"""
Modelos de base de datos - Definición de tablas
"""
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()


class Training(Base):
    """Tabla de entrenamientos - almacena cada serie de ejercicio"""
    __tablename__ = 'trainings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, default='default_user', nullable=False)
    date = Column(Date, nullable=False)
    exercise = Column(String, nullable=False)
    sets = Column(Integer)
    reps = Column(Integer)
    weight = Column(Float)
    rpe = Column(Float)
    rir = Column(Float)
    session_name = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)


class Mood(Base):
    """Tabla de estado diario - humor, sueño, fatiga, etc."""
    __tablename__ = 'mood'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, default='default_user', nullable=False)
    date = Column(Date, nullable=False, unique=True)
    sleep_hours = Column(Float)
    sleep_quality = Column(Integer)
    fatigue = Column(Integer)
    soreness = Column(Integer)
    stress = Column(Integer)
    motivation = Column(Integer)
    pain_flag = Column(Integer)
    pain_location = Column(Text)
    readiness = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)


class Exercise(Base):
    """Tabla de ejercicios - banco de ejercicios del usuario"""
    __tablename__ = 'exercises'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, default='default_user', nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class UserProfile(Base):
    """Tabla de perfil del usuario - JSON serializado con datos de perfil"""
    __tablename__ = 'user_profile'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, default='default_user', nullable=False, unique=True)
    data = Column(Text, nullable=False)  # JSON serializado del perfil
    last_updated = Column(DateTime, default=datetime.utcnow)
