"""Acceso a datos de Usuario."""
from sqlalchemy.orm import Session

from backend.core.crypto import indice_busqueda
from backend.models.usuario import Usuario
from backend.repositories.base_repository import BaseRepository


class UsuarioRepository(BaseRepository[Usuario]):
    modelo = Usuario

    def buscarPorEmail(self, email: str) -> Usuario | None:
        """`buscarPorEmail(email)` de CU-01 y CU-05.

        El email se guarda cifrado con AES-256 (RNF-02), y AES-256 usa un
        nonce aleatorio: el mismo email produce un valor distinto cada vez,
        asi que no se puede comparar `emailCifrado == valor`. Se busca por
        `emailIndice`, un HMAC determinista del email normalizado — el mismo
        email siempre da el mismo HMAC, y el HMAC no puede revertirse para
        recuperar el email (a diferencia del cifrado, que si es reversible).
        """
        return (
            self.db.query(Usuario)
            .filter(Usuario.emailIndice == indice_busqueda(email))
            .first()
        )

    def obtenerTodas(self) -> list[Usuario]:
        return list(self.db.query(Usuario).order_by(Usuario.id).all())

    def obtenerActivos(self) -> list[Usuario]:
        return list(self.db.query(Usuario).filter(Usuario.activo.is_(True)).all())

    def crear(self, nombre: str, apellido: str, email: str, passwordHash: str, rol: str) -> Usuario:
        usuario = Usuario(
            nombre=nombre,
            apellido=apellido,
            email=email.strip().lower(),
            passwordHash=passwordHash,
            rol=rol,
            activo=True,
        )
        return self.guardar(usuario)
