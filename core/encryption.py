"""
Módulo de cifrado central usando Fernet (AES-128-CBC + HMAC-SHA256).
La clave se carga desde settings.FERNET_KEY.
"""
from cryptography.fernet import Fernet
from django.conf import settings


def get_fernet() -> Fernet:
    """Devuelve una instancia de Fernet inicializada con la clave del proyecto."""
    key = settings.FERNET_KEY
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


def encrypt(value: str) -> str:
    """Cifra un string y devuelve el resultado en Base64 (safe para almacenar en DB)."""
    if value is None or value == '':
        return value
    f = get_fernet()
    return f.encrypt(str(value).encode()).decode()


def decrypt(value: str) -> str:
    """Descifra un token Fernet y devuelve el string original."""
    if value is None or value == '':
        return value
    # Si el valor no está cifrado (datos viejos en texto plano), lo devuelve tal cual
    try:
        f = get_fernet()
        return f.decrypt(str(value).encode()).decode()
    except Exception:
        # Valor en texto plano (datos previos a la migración)
        return value
