"""Dependencias compartidas por los controladores: sesion, usuario y permisos."""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.security import decodificar_jwt
from backend.models.enums import Rol
from backend.models.usuario import Usuario

esquema_bearer = HTTPBearer(auto_error=False)


def usuario_actual(
    credenciales: HTTPAuthorizationCredentials | None = Depends(esquema_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    """Resuelve el usuario a partir del token JWT del header Authorization.

    Todo endpoint que la use queda protegido: sin token valido no se ejecuta
    (RF-01: login obligatorio antes de entrar a cualquier parte).
    """
    no_autorizado = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Sesion invalida o expirada. Inicia sesion de nuevo.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credenciales is None:
        raise no_autorizado

    payload = decodificar_jwt(credenciales.credentials)
    if payload is None or "sub" not in payload:
        raise no_autorizado

    usuario = db.get(Usuario, int(payload["sub"]))
    if usuario is None:
        raise no_autorizado

    # Una cuenta desactivada despues de emitir el token debe perder el acceso
    # de inmediato, sin esperar a que el token expire.
    if not usuario.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta desactivada. Contacta al administrador.",
        )

    return usuario


def requiere_roles(*roles_permitidos: Rol):
    """Restringe un endpoint a ciertos roles (RF-06).

    Uso:  @router.get(..., dependencies=[Depends(requiere_roles(Rol.ADMIN))])
    """
    valores = {r.value for r in roles_permitidos}

    def verificador(usuario: Usuario = Depends(usuario_actual)) -> Usuario:
        if usuario.rol not in valores:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Tu rol no tiene permiso para esta operacion",
            )
        return usuario

    return verificador
