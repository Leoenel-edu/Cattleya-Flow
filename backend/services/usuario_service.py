"""CU-05: Gestionar Usuarios.

Implementa el diagrama de secuencia de Onate Leonel, con sus tres bloques alt
secuenciales: crear (con validacion fail-fast de email duplicado), modificar rol
y desactivar cuenta.
"""
import secrets
import string

from sqlalchemy.orm import Session

from backend.core.security import hashear_password
from backend.core.tiempo import ahora
from backend.models.enums import ETIQUETAS_ROL, Rol
from backend.models.usuario import Usuario
from backend.repositories.historial_repository import HistorialRepository
from backend.repositories.usuario_repository import UsuarioRepository
from backend.services.errors import EmailDuplicado, ErrorNegocio, NoEncontrado
from backend.services.notificacion_service import NotificacionService


def generarPasswordTemporal(longitud: int = 10) -> str:
    """Contrasena temporal para el correo de bienvenida.

    Usa `secrets` y no `random`: este ultimo es predecible y no sirve para
    generar credenciales.
    """
    alfabeto = string.ascii_letters + string.digits
    return "".join(secrets.choice(alfabeto) for _ in range(longitud))


class UsuarioService:
    def __init__(self, db: Session):
        self.db = db
        self.usuarios = UsuarioRepository(db)
        self.historial = HistorialRepository(db)
        self.notificaciones = NotificacionService(db)

    def listar(self) -> list[dict]:
        return [self._serializar(u) for u in self.usuarios.obtenerTodas()]

    def crear(self, nombre: str, apellido: str, email: str, rol: str, autor: Usuario) -> tuple[dict, str]:
        """Crea un usuario. Devuelve (usuario, passwordTemporal).

        La contrasena temporal se retorna para que el controlador la entregue a
        SMTP en segundo plano; nunca se guarda en claro ni se expone en la API.
        """
        email = email.strip().lower()

        if rol not in {r.value for r in Rol}:
            raise ErrorNegocio(f"Rol invalido: {rol}")

        # alt [email duplicado] - validacion fail-fast: se verifica ANTES de
        # cualquier escritura en BD, como exige el diagrama.
        if self.usuarios.buscarPorEmail(email) is not None:
            raise EmailDuplicado("Email ya registrado")

        passwordTemporal = generarPasswordTemporal()
        usuario = self.usuarios.crear(
            nombre=nombre.strip(),
            apellido=apellido.strip(),
            email=email,
            passwordHash=hashear_password(passwordTemporal),
            rol=rol,
        )

        self.historial.registrar(
            accion="crear",
            entidad="Usuario",
            entidad_id=usuario.id,
            usuario_id=autor.id,
            detalle=f"Creo a {usuario.nombreCompleto} con rol {ETIQUETAS_ROL.get(rol, rol)}",
        )
        self.db.commit()

        return self._serializar(usuario), passwordTemporal

    def cambiarRol(self, usuario_id: int, nuevoRol: str, autor: Usuario) -> dict:
        """alt [modificar rol] -> PATCH /api/usuarios/{id}/rol"""
        usuario = self.usuarios.obtenerPorId(usuario_id)
        if usuario is None:
            raise NoEncontrado(f"El usuario {usuario_id} no existe")

        if nuevoRol not in {r.value for r in Rol}:
            raise ErrorNegocio(f"Rol invalido: {nuevoRol}")

        # Un administrador que se quita a si mismo el rol admin quedaria sin
        # acceso a esta pantalla y sin forma de revertirlo desde la interfaz.
        if usuario.id == autor.id and nuevoRol != Rol.ADMIN.value:
            raise ErrorNegocio("No puedes quitarte a ti mismo el rol de Administrador")

        rolAnterior = usuario.rol
        usuario.cambiarRol(nuevoRol)

        self.historial.registrar(
            accion="modificar",
            entidad="Usuario",
            entidad_id=usuario.id,
            usuario_id=autor.id,
            detalle=(
                f"Rol de {usuario.nombreCompleto}: "
                f"{ETIQUETAS_ROL.get(rolAnterior, rolAnterior)} -> {ETIQUETAS_ROL.get(nuevoRol, nuevoRol)}"
            ),
        )
        self.notificaciones.crear(
            mensaje=f"Tu rol cambio a {ETIQUETAS_ROL.get(nuevoRol, nuevoRol)}",
            tipo="info",
            usuario_id=usuario.id,
        )
        self.db.commit()
        return self._serializar(usuario)

    def cambiarActivo(self, usuario_id: int, activo: bool, autor: Usuario) -> dict:
        """alt [desactivar cuenta] -> PATCH /api/usuarios/{id} {activo: false}

        No se elimina el registro: el atributo `activo: Boolean` del diagrama
        permite el borrado logico, conservando la trazabilidad de las limpiezas
        que esa persona ya realizo.
        """
        usuario = self.usuarios.obtenerPorId(usuario_id)
        if usuario is None:
            raise NoEncontrado(f"El usuario {usuario_id} no existe")

        # Desactivarse a si mismo cerraria la sesion en curso sin poder volver.
        if usuario.id == autor.id and not activo:
            raise ErrorNegocio("No puedes desactivar tu propia cuenta")

        usuario.activo = activo

        self.historial.registrar(
            accion="desactivar" if not activo else "activar",
            entidad="Usuario",
            entidad_id=usuario.id,
            usuario_id=autor.id,
            detalle=f"{usuario.nombreCompleto} fue {'desactivado' if not activo else 'activado'}",
        )
        self.notificaciones.crear(
            mensaje=(
                "Tu cuenta fue desactivada. Contacta al administrador."
                if not activo
                else "Tu cuenta fue reactivada."
            ),
            tipo="warn" if not activo else "success",
            usuario_id=usuario.id,
        )
        self.db.commit()
        return self._serializar(usuario)

    def _serializar(self, usuario: Usuario) -> dict:
        return {
            "id": usuario.id,
            "name": usuario.nombreCompleto,
            "nombre": usuario.nombre,
            "apellido": usuario.apellido,
            "email": usuario.email,
            "role": usuario.rol,
            "roleLabel": usuario.rolEtiqueta,
            "active": usuario.activo,
            "last": self._formatearUltimoAcceso(usuario),
        }

    @staticmethod
    def _formatearUltimoAcceso(usuario: Usuario) -> str:
        if usuario.ultimoAcceso is None:
            return "Nunca"

        acceso = usuario.ultimoAcceso
        dias = (ahora().date() - acceso.date()).days
        hora = acceso.strftime("%H:%M")

        if dias == 0:
            return f"Hoy {hora}"
        if dias == 1:
            return f"Ayer {hora}"
        return acceso.strftime("%d/%m/%Y %H:%M")
