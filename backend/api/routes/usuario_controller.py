"""UsuarioController - CU-05: Gestionar Usuarios.

Todos los endpoints exigen rol Administrador (RF-07).
"""
from fastapi import APIRouter, BackgroundTasks, Depends, Response, status
from sqlalchemy.orm import Session

from backend.api.deps import requiere_roles
from backend.core.database import get_db
from backend.models.enums import Rol
from backend.models.usuario import Usuario
from backend.schemas import CambiarActivoRequest, CambiarRolRequest, CrearUsuarioRequest
from backend.services.smtp_service import SMTPService
from backend.services.usuario_service import UsuarioService

router = APIRouter(prefix="/api/usuarios", tags=["Usuarios"])

solo_admin = requiere_roles(Rol.ADMIN)


@router.get("")
def listar(
    usuario: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """GET /api/usuarios -> lista completa de cuentas"""
    return {"usuarios": UsuarioService(db).listar()}


@router.post("", status_code=status.HTTP_201_CREATED)
def crear(
    datos: CrearUsuarioRequest,
    tareas: BackgroundTasks,
    usuario: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """POST /api/usuarios -> 201 Created, { id, nombre, rol }

    El correo de bienvenida se encola como tarea en segundo plano: es el
    mensaje asincrono (-)) hacia SMTP del diagrama. Si el servidor de correo
    esta caido, el usuario igual queda creado.
    """
    creado, passwordTemporal = UsuarioService(db).crear(
        nombre=datos.nombre,
        apellido=datos.apellido,
        email=datos.email,
        rol=datos.rol,
        autor=usuario,
    )

    tareas.add_task(
        SMTPService.enviarBienvenida,
        email=creado["email"],
        passwordTemporal=passwordTemporal,
        nombre=creado["name"],
    )

    return {
        "mensaje": "Usuario creado exitosamente",
        "usuario": creado,
        # Se devuelve solo porque el SMTP corre en modo simulado y sin esto no
        # habria forma de conocer la contrasena para la demostracion.
        # Con un servidor de correo real, quitar esta linea.
        "passwordTemporal": passwordTemporal,
    }


@router.patch("/{usuario_id}/rol")
def cambiarRol(
    usuario_id: int,
    datos: CambiarRolRequest,
    usuario: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """PATCH /api/usuarios/{id}/rol -> 200 OK"""
    actualizado = UsuarioService(db).cambiarRol(usuario_id, datos.rol, usuario)
    return {"mensaje": "Rol actualizado", "usuario": actualizado}


@router.patch("/{usuario_id}")
def cambiarActivo(
    usuario_id: int,
    datos: CambiarActivoRequest,
    usuario: Usuario = Depends(solo_admin),
    db: Session = Depends(get_db),
):
    """PATCH /api/usuarios/{id} {activo: false} -> 200 OK"""
    actualizado = UsuarioService(db).cambiarActivo(usuario_id, datos.activo, usuario)
    estado = "activado" if datos.activo else "desactivado"
    return {"mensaje": f"Usuario {estado}", "usuario": actualizado}
