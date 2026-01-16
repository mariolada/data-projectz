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


class AuthSession(Base):
    """Sesiones OAuth persistidas para no perder login en F5/ctrl+F5."""
    __tablename__ = 'auth_sessions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)          # sub (google) o email
    provider = Column(String, nullable=False)         # google, github, etc.
    email = Column(String, nullable=True)
    display_name = Column(String, nullable=True)
    profile_picture_url = Column(String, nullable=True)  # URL de foto de Google
    gender = Column(String, nullable=True)             # 'male', 'female', 'other'
    session_token_hash = Column(String, nullable=False, unique=True)
    refresh_token = Column(Text, nullable=True)
    access_token = Column(Text, nullable=True)
    id_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)      # expiración del access token
    session_expires_at = Column(DateTime, nullable=True)  # expiración del session cookie
    created_at = Column(DateTime, default=datetime.utcnow)


class PKCEState(Base):
    """Almacena state/code_verifier pares para PKCE flow."""
    __tablename__ = 'pkce_states'

    id = Column(Integer, primary_key=True, autoincrement=True)
    state = Column(String, nullable=False, unique=True)
    code_verifier = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
