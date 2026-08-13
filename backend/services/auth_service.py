"""CU-01: Autenticarse en el Sistema.

Implementa el diagrama de secuencia de Bolanos Melanie, incluidos sus tres
flujos alternativos: credenciales invalidas (401), cuenta desactivada (403)
y el opt [primer login].
"""
from sqlalchemy.orm import Session

from backend.core.security import generar_jwt, verificar_password
from backend.core.tiempo import ahora
from backend.models.enums import NAVEGACION_POR_ROL
from backend.models.usuario import Usuario
from backend.repositories.historial_repository import HistorialRepository
from backend.repositories.usuario_repository import UsuarioRepository
from backend.services.errors import CredencialesInvalidas, CuentaDesactivada


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.usuarios = UsuarioRepository(db)
        self.historial = HistorialRepository(db)

    def login(self, email: str, password: str) -> dict:
        """Valida credenciales y devuelve el token de sesion.

        Sigue el orden exacto del diagrama de secuencia:
        buscarPorEmail -> bcrypt.compare -> generarJWT -> registrar en historial.
        """
        usuario = self.usuarios.buscarPorEmail(email)

        # alt [credenciales invalidas]
        # Se responde igual si el email no existe o si la contrasena esta mal.
        # Distinguirlos permitiria averiguar que correos estan registrados.
        if usuario is None or not verificar_password(password, usuario.passwordHash):
            raise CredencialesInvalidas("Credenciales incorrectas")

        # alt [cuenta desactivada]
        # Se comprueba DESPUES de la contrasena: si fuera antes, cualquiera
        # podria descubrir que cuentas existen probando correos al azar.
        if not usuario.activo:
            raise CuentaDesactivada(
                "Cuenta desactivada. Contacta al administrador."
            )

        token = generar_jwt(usuario.id, usuario.rol)

        # opt [primer login]: si nunca ha entrado, el frontend puede pedir
        # cambio de contrasena.
        primerLogin = usuario.ultimoAcceso is None

        usuario.ultimoAcceso = ahora()
        self.historial.registrar(
            accion="login",
            entidad="Usuario",
            entidad_id=usuario.id,
            usuario_id=usuario.id,
            detalle=f"{usuario.nombreCompleto} inicio sesion",
        )
        self.db.commit()

        return {
            "token": token,
            "rol": usuario.rol,
            "rolEtiqueta": usuario.rolEtiqueta,
            "nombre": usuario.nombreCompleto,
            "usuarioId": usuario.id,
            "primerLogin": primerLogin,
            # El backend decide que ve cada rol (RF-06).
            "navegacion": NAVEGACION_POR_ROL.get(usuario.rol, []),
        }

    def logout(self, usuario: Usuario) -> None:
        """`logout(token): void`.

        Con JWT sin estado no hay sesion que destruir en el servidor: el
        cliente descarta el token y este caduca solo. Lo que si queda es el
        rastro de auditoria.
        """
        self.historial.registrar(
            accion="logout",
            entidad="Usuario",
            entidad_id=usuario.id,
            usuario_id=usuario.id,
            detalle=f"{usuario.nombreCompleto} cerro sesion",
        )
        self.db.commit()
