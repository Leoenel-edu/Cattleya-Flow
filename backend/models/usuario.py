"""Entidad Usuario del diagrama de clases (seccion 1.1)."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.crypto import cifrar, descifrar, indice_busqueda
from backend.core.database import Base
from backend.core.security import verificar_password
from backend.core.tiempo import ahora
from backend.models.enums import ETIQUETAS_ROL


class Usuario(Base):
    __tablename__ = "usuarios"

    # --- Atributos del diagrama de clases ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    apellido: Mapped[str] = mapped_column(String(80), nullable=False, default="")

    # RNF-02: "los datos sensibles debera encriptarlos con AES-256 cuando
    # estan guardados". El email se guarda cifrado (columna real en la BD);
    # `email` es una propiedad de Python que cifra/descifra de forma
    # transparente, para que el resto del codigo lo use como si fuera texto
    # plano sin manejar criptografia directamente.
    #
    # `emailIndice` es un HMAC determinista del email normalizado (ver
    # core/crypto.py). AES-256 usa un nonce aleatorio, asi que el mismo email
    # produce un cifrado distinto cada vez: no se puede buscar con
    # `WHERE emailCifrado = ?`. El indice si es determinista y permite
    # `WHERE emailIndice = ?` para el login y la validacion de duplicados,
    # sin poder revertirse para recuperar el email (no es cifrado, es hash).
    emailCifrado: Mapped[str] = mapped_column(String(255), nullable=False)
    emailIndice: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    passwordHash: Mapped[str] = mapped_column(String(120), nullable=False)
    rol: Mapped[str] = mapped_column(String(20), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fechaCreacion: Mapped[datetime] = mapped_column(DateTime, default=ahora, nullable=False)

    # Fuera del diagrama: se usa para la columna "Ult. acceso" de la pantalla
    # de gestion de usuarios (CU-05). No altera el modelo de dominio.
    ultimoAcceso: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # --- Relaciones (seccion 1.2) ---
    # Usuario -> RegistroLimpieza : Asociacion 1 a 0..*
    registros: Mapped[list["RegistroLimpieza"]] = relationship(  # noqa: F821
        back_populates="usuario"
    )
    # Usuario -> HistorialAccion : Asociacion 1 a 0..*
    acciones: Mapped[list["HistorialAccion"]] = relationship(  # noqa: F821
        back_populates="usuario"
    )
    notificaciones: Mapped[list["Notificacion"]] = relationship(  # noqa: F821
        back_populates="usuario"
    )

    # --- Email: cifrado en la BD, texto plano en Python ---
    @property
    def email(self) -> str:
        return descifrar(self.emailCifrado)

    @email.setter
    def email(self, valor: str) -> None:
        normalizado = valor.strip().lower()
        self.emailCifrado = cifrar(normalizado)
        self.emailIndice = indice_busqueda(normalizado)

    # --- Metodos del diagrama de clases ---
    def validarCredenciales(self, password: str) -> bool:
        """Verdadero solo si la contrasena coincide Y la cuenta esta activa.

        El flujo alternativo "cuenta desactivada" de CU-01 necesita distinguir
        ambos casos (401 vs 403), por eso AuthService consulta `activo` aparte
        en vez de depender solo de este metodo.
        """
        return self.activo and verificar_password(password, self.passwordHash)

    def cambiarRol(self, nuevoRol: str) -> None:
        """CU-05, flujo alternativo [modificar rol]."""
        self.rol = nuevoRol

    @property
    def nombreCompleto(self) -> str:
        return f"{self.nombre} {self.apellido}".strip()

    @property
    def rolEtiqueta(self) -> str:
        return ETIQUETAS_ROL.get(self.rol, self.rol)

    def __repr__(self) -> str:
        return f"<Usuario {self.id} {self.email} ({self.rol})>"
