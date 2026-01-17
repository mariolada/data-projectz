"""Gestión de sesiones OAuth persistentes."""
import secrets
from datetime import datetime
from typing import Optional, Tuple

from database.connection import get_db
from database.repositories import AuthSessionRepository, PKCEStateRepository


def generate_state_and_verifier() -> Tuple[str, str]:
    state = secrets.token_urlsafe(16)
    code_verifier = secrets.token_urlsafe(64)
    return state, code_verifier


def save_pkce_pair(state: str, code_verifier: str) -> None:
    """Guarda el par state/code_verifier en la BD para recuperarlo después."""
    db = next(get_db())
    try:
        PKCEStateRepository.save(db, state, code_verifier)
    finally:
        db.close()


def get_code_verifier(state: str) -> Optional[str]:
    """
    Recupera el code_verifier usando el state (SIN eliminarlo).
    Intenta coincidencia exacta primero, luego parcial si es necesario.
    """
    if not state:
        return None
    
    db = next(get_db())
    try:
        # Intento 1: coincidencia exacta
        rec = PKCEStateRepository.get_by_state(db, state)
        if rec:
            return rec.code_verifier
        
        # Intento 2: búsqueda con LIKE (en caso de URL encoding)
        # Esto es para manejar casos donde el state se URL-encode
        import urllib.parse
        unquoted_state = urllib.parse.unquote(state)
        if unquoted_state != state:
            rec = PKCEStateRepository.get_by_state(db, unquoted_state)
            if rec:
                return rec.code_verifier
        
        return None
    except Exception as e:
        print(f"Error recuperando code_verifier: {e}")
        return None
    finally:
        db.close()


def delete_pkce_state(state: str) -> None:
    """Elimina el estado PKCE después de usarlo exitosamente."""
    db = next(get_db())
    try:
        PKCEStateRepository.delete(db, state)
    finally:
        db.close()


def create_persistent_session(*, provider: str, user_id: str, email: str, display_name: str,
                              access_token: str, refresh_token: str = None, id_token: str = None,
                              expires_at: Optional[datetime] = None, profile_picture_url: str = None,
                              gender: str = None) -> str:
    """Crea una sesión persistida y retorna el token sin hash para el query param."""
    session_token = secrets.token_urlsafe(32)
    db = next(get_db())
    try:
        AuthSessionRepository.create(
            db,
            raw_session_token=session_token,
            user_id=user_id,
            provider=provider,
            email=email,
            display_name=display_name,
            refresh_token=refresh_token,
            access_token=access_token,
            id_token=id_token,
            access_expires_at=expires_at,
            profile_picture_url=profile_picture_url,
            gender=gender,
        )
        return session_token
    finally:
        db.close()


def restore_session(raw_session_token: str):
    db = next(get_db())
    try:
        return AuthSessionRepository.get_by_session_token(db, raw_session_token)
    finally:
        db.close()


def drop_session(raw_session_token: str):
    db = next(get_db())
    try:
        AuthSessionRepository.delete(db, raw_session_token)
    finally:
        db.close()


def save_menstrual_cycle_data(raw_session_token: str, cycle_data_json: str) -> bool:
    """Guarda los datos del ciclo menstrual para la sesión actual."""
    db = next(get_db())
    try:
        result = AuthSessionRepository.update_menstrual_cycle_data(db, raw_session_token, cycle_data_json)
        return result is not None
    finally:
        db.close()


def save_gender(raw_session_token: str, gender: str) -> bool:
    """Guarda el género para la sesión actual."""
    db = next(get_db())
    try:
        result = AuthSessionRepository.update_gender(db, raw_session_token, gender)
        return result is not None
    finally:
        db.close()


def get_gender(raw_session_token: str) -> Optional[str]:
    """Recupera el género guardado para la sesión actual."""
    session = restore_session(raw_session_token)
    if session:
        return session.gender
    return None
