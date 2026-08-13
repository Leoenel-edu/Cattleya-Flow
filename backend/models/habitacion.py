"""Entidad Habitacion del diagrama de clases (seccion 1.1).

Aqui vive la maquina de estados del ciclo de limpieza. La regla de negocio
`validarTransicion` esta en la entidad, no en el controlador: es la restriccion
que el diagrama de clases impone y la que hace que CU-02 se bifurque en un alt.
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.core.tiempo import ahora
from backend.models.enums import (
    ETIQUETAS_ESTADO,
    ROLES_PUEDEN_ENSUCIAR,
    TRANSICIONES_VALIDAS,
    EstadoHabitacion,
    Rol,
)


class Habitacion(Base):
    __tablename__ = "habitaciones"

    # --- Atributos del diagrama de clases ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    numero: Mapped[str] = mapped_column(String(10), unique=True, nullable=False)
    piso: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    estado: Mapped[str] = mapped_column(
        String(20), default=EstadoHabitacion.SUCIA.value, nullable=False, index=True
    )
    ultimaActualizacion: Mapped[datetime] = mapped_column(
        DateTime, default=ahora, nullable=False
    )

    # --- Relaciones (seccion 1.2) ---
    # Habitacion -> RegistroLimpieza : Composicion 1 a 0..*
    # Es composicion: si la habitacion desaparece, sus registros no tienen
    # sentido por si solos, de ahi el cascade delete-orphan.
    registros: Mapped[list["RegistroLimpieza"]] = relationship(  # noqa: F821
        back_populates="habitacion",
        cascade="all, delete-orphan",
        order_by="RegistroLimpieza.horaInicio.desc()",
    )

    # --- Metodos del diagrama de clases ---
    @staticmethod
    def validarTransicion(estadoActual: str, estadoNuevo: str, rol: str | None = None) -> bool:
        """Decide si el cambio de estado esta permitido.

        Devuelve Boolean, tal como lo define el diagrama de clases. El
        parametro `rol` es opcional para no romper la firma original: solo
        interviene en la transicion de check-out (Lista -> Sucia).
        """
        try:
            actual = EstadoHabitacion(estadoActual)
            nuevo = EstadoHabitacion(estadoNuevo)
        except ValueError:
            return False  # estado inexistente

        if actual == nuevo:
            return False  # no es una transicion

        if nuevo not in TRANSICIONES_VALIDAS.get(actual, set()):
            return False

        # Check-out: solo recepcion/supervisor/admin devuelven una habitacion
        # lista al estado sucia.
        if actual == EstadoHabitacion.LISTA and nuevo == EstadoHabitacion.SUCIA:
            if rol is not None and Rol(rol) not in ROLES_PUEDEN_ENSUCIAR:
                return False

        return True

    @staticmethod
    def estadosPermitidosDesde(estadoActual: str, rol: str | None = None) -> list[str]:
        """Los estados a los que se puede pasar. Alimenta el mensaje de error
        "Mostrar estados validos" del flujo alternativo de CU-02.
        """
        return [
            estado.value
            for estado in EstadoHabitacion
            if Habitacion.validarTransicion(estadoActual, estado.value, rol)
        ]

    def cambiarEstado(self, nuevoEstado: str, usuario) -> None:
        """Aplica el cambio. No valida: la validacion es responsabilidad de
        `validarTransicion` y el servicio la ejecuta antes de llamar aqui.
        """
        self.estado = nuevoEstado
        self.ultimaActualizacion = ahora()

    def obtenerHistorial(self) -> list["RegistroLimpieza"]:  # noqa: F821
        """CU-06: acceso al historial a traves de la entidad raiz."""
        return list(self.registros)

    @property
    def estadoEtiqueta(self) -> str:
        return ETIQUETAS_ESTADO.get(self.estado, self.estado)

    def __repr__(self) -> str:
        return f"<Habitacion {self.numero} piso {self.piso} ({self.estado})>"
