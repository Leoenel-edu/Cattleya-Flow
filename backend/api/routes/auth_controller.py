"""AuthController - CU-01: Autenticarse en el Sistema."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.api.deps import usuario_actual
from backend.core.database import get_db
from backend.models.enums import NAVEGACION_POR_ROL
from backend.models.usuario import Usuario
from backend.schemas import LoginRequest, LoginResponse
from backend.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["Autenticacion"])


@router.post("/login", response_model=LoginResponse)
def login(datos: LoginRequest, db: Session = Depends(get_db)):
    """POST /api/auth/login {email, password} -> { token, rol, nombre }

    Los errores de negocio (401 credenciales, 403 desactivada) los traduce a
    HTTP el manejador registrado en main.py.
    """
    return AuthService(db).login(datos.email, datos.password)


@router.post("/logout")
def logout(usuario: Usuario = Depends(usuario_actual), db: Session = Depends(get_db)):
    """POST /api/auth/logout -> registra el cierre de sesion en la auditoria."""
    AuthService(db).logout(usuario)
    return {"mensaje": "Sesion cerrada"}


@router.get("/yo")
def perfil(usuario: Usuario = Depends(usuario_actual)):
    """GET /api/auth/yo -> permite al frontend restaurar la sesion tras un F5
    sin volver a pedir credenciales."""
    return {
        "usuarioId": usuario.id,
        "nombre": usuario.nombreCompleto,
        "email": usuario.email,
        "rol": usuario.rol,
        "rolEtiqueta": usuario.rolEtiqueta,
        "navegacion": NAVEGACION_POR_ROL.get(usuario.rol, []),
    }
