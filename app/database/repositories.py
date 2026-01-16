"""
Repositorios - Operaciones CRUD para cada tabla
"""
from sqlalchemy.orm import Session
from .models import Training, Mood, Exercise, UserProfile
from datetime import date, datetime
import pandas as pd
from typing import List, Optional
import json


class TrainingRepository:
    """Operaciones sobre la tabla de entrenamientos"""
    
    @staticmethod
    def create(db: Session, training_data: dict, user_id: str = 'default_user'):
        """Guarda un entrenamiento individual"""
        training_data['user_id'] = user_id
        training = Training(**training_data)
        db.add(training)
        db.commit()
        db.refresh(training)
        return training
    
    @staticmethod
    def get_by_date(db: Session, date_value: date, user_id: str = 'default_user') -> pd.DataFrame:
        """Obtiene entrenamientos de una fecha específica"""
        trainings = db.query(Training).filter(
            Training.date == date_value,
            Training.user_id == user_id
        ).all()
        
        if not trainings:
            return pd.DataFrame(columns=['date', 'exercise', 'sets', 'reps', 'weight', 'rpe', 'rir', 'session_name'])
        
        data = [{
            'date': t.date,
            'exercise': t.exercise,
            'sets': t.sets,
            'reps': t.reps,
            'weight': t.weight,
            'rpe': t.rpe,
            'rir': t.rir,
            'session_name': t.session_name
        } for t in trainings]
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    
    @staticmethod
    def get_all(db: Session, user_id: str = 'default_user') -> pd.DataFrame:
        """Obtiene todos los entrenamientos del usuario"""
        trainings = db.query(Training).filter(
            Training.user_id == user_id
        ).order_by(Training.date.desc()).all()
        
        if not trainings:
            return pd.DataFrame(columns=['date', 'exercise', 'sets', 'reps', 'weight', 'rpe', 'rir', 'session_name'])
        
        data = [{
            'date': t.date,
            'exercise': t.exercise,
            'sets': t.sets,
            'reps': t.reps,
            'weight': t.weight,
            'rpe': t.rpe,
            'rir': t.rir,
            'session_name': t.session_name
        } for t in trainings]
        
        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    
    @staticmethod
    def delete_by_date(db: Session, date_value: date, user_id: str = 'default_user'):
        """Elimina todos los entrenamientos de una fecha (para reemplazar)"""
        db.query(Training).filter(
            Training.date == date_value,
            Training.user_id == user_id
        ).delete()
        db.commit()


class ExerciseRepository:
    """Operaciones sobre la tabla de ejercicios"""
    
    @staticmethod
    def get_all(db: Session, user_id: str = 'default_user') -> List[str]:
        """Obtiene lista de nombres de ejercicios del usuario"""
        exercises = db.query(Exercise).filter(
            Exercise.user_id == user_id
        ).order_by(Exercise.name).all()
        return [e.name for e in exercises]
    
    @staticmethod
    def add(db: Session, name: str, user_id: str = 'default_user') -> Exercise:
        """Añade un ejercicio si no existe ya"""
        # Normalizar nombre
        name = " ".join(str(name).strip().split())
        
        # Verificar si ya existe
        existing = db.query(Exercise).filter(
            Exercise.name == name,
            Exercise.user_id == user_id
        ).first()
        
        if existing:
            return existing
        
        # Crear nuevo
        exercise = Exercise(name=name, user_id=user_id)
        db.add(exercise)
        db.commit()
        db.refresh(exercise)
        return exercise
    
    @staticmethod
    def add_multiple(db: Session, names: List[str], user_id: str = 'default_user'):
        """Añade múltiples ejercicios de una vez"""
        for name in names:
            ExerciseRepository.add(db, name, user_id)


class MoodRepository:
    """Operaciones sobre la tabla de mood/estado diario"""
    
    @staticmethod
    def create_or_update(db: Session, mood_data: dict, user_id: str = 'default_user'):
        """Crea o actualiza el mood de un día específico"""
        mood_data['user_id'] = user_id
        date_value = mood_data.get('date')
        
        # Buscar si ya existe
        existing = db.query(Mood).filter(
            Mood.date == date_value,
            Mood.user_id == user_id
        ).first()
        
        if existing:
            # Actualizar
            for key, value in mood_data.items():
                setattr(existing, key, value)
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # Crear nuevo
            mood = Mood(**mood_data)
            db.add(mood)
            db.commit()
            db.refresh(mood)
            return mood
    
    @staticmethod
    def get_by_date(db: Session, date_value: date, user_id: str = 'default_user') -> Optional[dict]:
        """Obtiene el mood de una fecha específica"""
        mood = db.query(Mood).filter(
            Mood.date == date_value,
            Mood.user_id == user_id
        ).first()
        
        if not mood:
            return None
        
        return {
            'date': mood.date,
            'sleep_hours': mood.sleep_hours,
            'sleep_quality': mood.sleep_quality,
            'fatigue': mood.fatigue,
            'soreness': mood.soreness,
            'stress': mood.stress,
            'motivation': mood.motivation,
            'pain_flag': mood.pain_flag,
            'pain_location': mood.pain_location,
            'readiness': mood.readiness
        }
    
    @staticmethod
    def get_all(db: Session, user_id: str = 'default_user') -> pd.DataFrame:
        """Obtiene todos los registros de mood"""
        moods = db.query(Mood).filter(
            Mood.user_id == user_id
        ).order_by(Mood.date.desc()).all()
        
        if not moods:
            return pd.DataFrame()
        
        data = [{
            'date': m.date,
            'sleep_hours': m.sleep_hours,
            'sleep_quality': m.sleep_quality,
            'fatigue': m.fatigue,
            'soreness': m.soreness,
            'stress': m.stress,
            'motivation': m.motivation,
            'pain_flag': m.pain_flag,
            'pain_location': m.pain_location,
            'readiness': m.readiness
        } for m in moods]
        
        return pd.DataFrame(data)


class UserProfileRepository:
    """Operaciones sobre el perfil de usuario (JSON en DB)"""

    DEFAULT_PROFILE = {
        'archetype': {'archetype': 'unknown', 'confidence': 0, 'reason': ''},
        'adjustment_factors': {
            'sleep_weight': 0.25,
            'performance_weight': 0.25,
            'fatigue_sensitivity': 1.0,
            'stress_sensitivity': 1.0,
            'recovery_speed': 1.0,
            'sleep_responsive': True,
        },
        'sleep_responsiveness': {},
        'insights': [],
        'data_quality': {},
    }

    @staticmethod
    def get(db: Session, user_id: str = 'default_user') -> dict:
        """Obtiene el perfil del usuario como dict JSON."""
        rec = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if not rec or not rec.data:
            return UserProfileRepository.DEFAULT_PROFILE.copy()
        try:
            return json.loads(rec.data)
        except Exception:
            return UserProfileRepository.DEFAULT_PROFILE.copy()

    @staticmethod
    def create_or_update(db: Session, profile_data: dict, user_id: str = 'default_user') -> UserProfile:
        """Crea o actualiza el perfil del usuario con JSON serializado."""
        now = datetime.utcnow()
        serialized = json.dumps(profile_data, ensure_ascii=False)
        existing = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
        if existing:
            existing.data = serialized
            existing.last_updated = now
            db.commit()
            db.refresh(existing)
            return existing
        rec = UserProfile(user_id=user_id, data=serialized, last_updated=now)
        db.add(rec)
        db.commit()
        db.refresh(rec)
        return rec
