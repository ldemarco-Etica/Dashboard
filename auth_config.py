import streamlit as st
from typing import Optional
import bcrypt

ROLE_PERMISSIONS = {
    'admin': [
        'Home', 'AUM', 'TEV', 'Duration', 'Allocazioni', 
        'Analisi titoli', 'Lookthrough', 'Movimentazioni', 
        'Limiti Regolamentari', 'Limiti da CDA', 'Turnover'
    ],
    'analyst': [
        'Home', 'AUM', 'TEV', 'Duration', 'Allocazioni', 
        'Analisi titoli', 'Lookthrough', 'Movimentazioni', 'Turnover'
    ],
    'viewer': [
        'Home', 'AUM', 'TEV', 'Duration'
    ]
}

def email_to_key(email: str) -> str:
    """Converte email in chiave (es: ldemarco@eticasgr.it -> ldemarco)"""
    return email.split('@')[0].lower()

def get_user_role(email: str) -> str:
    """Recupera il ruolo dell'utente"""
    users = st.secrets.get("users", {})
    key = email_to_key(email)
    role_key = f"{key}_role"
    return users.get(role_key, st.secrets["auth"].get("default_role", "viewer"))

def get_user_permissions(email: str) -> list:
    """Recupera le permission dell'utente basate sul ruolo"""
    role = get_user_role(email)
    return ROLE_PERMISSIONS.get(role, ROLE_PERMISSIONS['viewer'])

def can_access_page(email: str, page_name: str) -> bool:
    """Verifica se l'utente può accedere a una pagina"""
    return page_name in get_user_permissions(email)

def is_valid_user(email: str) -> bool:
    """Verifica se l'utente esiste nei secrets"""
    users = st.secrets.get("users", {})
    key = email_to_key(email)
    password_key = f"{key}_password"
    return password_key in users

def verify_password(email: str, password: str) -> bool:
    """Verifica la password dell'utente"""
    if not is_valid_user(email):
        return False
    
    users = st.secrets.get("users", {})
    key = email_to_key(email)
    password_key = f"{key}_password"
    stored_hash = users.get(password_key, "")
    
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored_hash.encode("utf-8"))
    except Exception:
        return False
