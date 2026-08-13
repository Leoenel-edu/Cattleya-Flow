"""Primitivas de seguridad: hashing de contrasenas y tokens de sesion.

Cubre RNF-02 (contrasenas con bcrypt, nunca en texto plano) y la parte
criptografica de CU-01 (login con JWT).
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from backend.core.config import settings


# ---------------------------------------------------------------- contrasenas
def hashear_password(password: str) -> str:
    """Genera el hash bcrypt que se guarda en Usuario.passwordHash.

    bcrypt incluye un salt aleatorio dentro del propio hash, por eso dos
    usuarios con la misma contrasena tienen hashes distintos.
    """
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verificar_password(password_plano: str, password_hash: str) -> bool:
    """Compara la contrasena ingresada contra el hash almacenado.

    Equivale a `bcrypt.compare(password, passwordHash)` del diagrama CU-01.
    """
    try:
        return bcrypt.checkpw(
            password_plano.encode("utf-8"), password_hash.encode("utf-8")
        )
    except (ValueError, TypeError):
        # Hash corrupto o con formato invalido: se trata como credencial incorrecta
        # en lugar de propagar el error al usuario.
        return False


# --------------------------------------------------------------------- tokens
def generar_jwt(usuario_id: int, rol: str) -> str:
    """Crea el token de sesion. Corresponde a `generarJWT(usuario.id, usuario.rol)`."""
    ahora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id),
        "rol": rol,
        "iat": ahora,
        "exp": ahora + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decodificar_jwt(token: str) -> dict | None:
    """Valida firma y expiracion. Devuelve el payload, o None si no es valido."""
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None
