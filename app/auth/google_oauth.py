"""
Flujo OAuth2 para Google con PKCE.
"""
import base64
import hashlib
import os
from typing import Tuple, Dict

from authlib.integrations.requests_client import OAuth2Session
import streamlit as st


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def _get_google_secrets() -> Tuple[str, str]:
    client_id = st.secrets["google"]["client_id"]
    client_secret = st.secrets["google"]["client_secret"]
    return client_id, client_secret


def _code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("utf-8")


def _redirect_uri() -> str:
    # Streamlit solo maneja la raíz /, no rutas específicas
    # El redirect URI debe ser SOLO http://localhost:8501/
    host = os.getenv("PUBLIC_HOST", "http://localhost:8501")
    return f"{host}/"


def build_authorization_url(state: str, code_verifier: str) -> str:
    """Construye la URL de autorización de Google con PKCE."""
    from urllib.parse import urlencode
    
    client_id, client_secret = _get_google_secrets()
    redirect_uri = _redirect_uri()
    
    code_challenge = _code_challenge(code_verifier)
    
    params = {
        "client_id": client_id,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": redirect_uri,
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "access_type": "offline",
        "prompt": "consent",
    }
    
    # Usar urlencode para encodificar correctamente la URL
    query_string = urlencode(params)
    auth_url = f"{GOOGLE_AUTH_URL}?{query_string}"
    
    # DEBUG: Mostrar la URL (sin parámetros sensibles)
    print(f"[DEBUG] Redirect URI siendo enviado: {redirect_uri}")
    print(f"[DEBUG] Auth URL: {auth_url[:150]}...")
    
    return auth_url


def exchange_code_for_token(code: str, code_verifier: str) -> Dict:
    """Intercambia el código por tokens usando PKCE."""
    client_id, client_secret = _get_google_secrets()
    redirect_uri = _redirect_uri()
    
    client = OAuth2Session(
        client_id,
        client_secret,
    )
    
    token = client.fetch_token(
        GOOGLE_TOKEN_URL,
        code=code,
        code_verifier=code_verifier,
        redirect_uri=redirect_uri,
    )
    return token


def fetch_userinfo(access_token: str) -> Dict:
    """Obtiene la información del usuario desde Google usando el access_token."""
    import requests
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(GOOGLE_USERINFO_URL, headers=headers)
    response.raise_for_status()
    return response.json()
