"""Entidad RegistroLimpieza del diagrama de clases (seccion 1.1).

Es el nucleo de RF-04 (guardar quien limpio, cuando empezo y cuando termino)
y la fuente de datos de los reportes de productividad (CU-04).
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.core.tiempo import ahora
from backend.models.enums import EstadoHabitacion


class RegistroLimpieza(Base):
    __tablename__ = "registros_limpieza"

    # --- Atributos del diagrama de clases ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    horaInicio: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    horaFin: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    estadoFinal: Mapped[str] = mapped_column(
        String(20), default=EstadoHabitacion.EN_LIMPIEZA.value, nullable=False
    )
    observaciones: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # --- Claves foraneas que materializan las relaciones de la seccion 1.2 ---
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False, index=True)
    habitacion_id: Mapped[int] = mapped_column(
        ForeignKey("habitaciones.id"), nullable=False, index=True
    )

    usuario: Mapped["Usuario"] = relationship(back_populates="registros")  # noqa: F821
    habitacion: Mapped["Habitacion"] = relationship(back_populates="registros")  # noqa: F821

    # --- Metodos del diagrama de clases ---
    def calcularDuracion(self) -> int:
        """Duracion de la limpieza en minutos.

        Devuelve 0 si aun no termina, en lugar de None: los reportes suman
        duraciones y un None obligaria a filtrar en cada punto de uso.
        """
        if self.horaFin is None:
            return 0
        delta = self.horaFin - self.horaInicio
        return max(0, int(delta.total_seconds() // 60))

    def registrarFin(self, hora: datetime | None = None, estado: str = EstadoHabitacion.LISTA.value) -> None:
        """Cierra el registro cuando la habitacion queda lista.

        Corresponde a `registrarFin(hora, estado)` del opt [estado = Lista] de CU-02.
        """
        self.horaFin = hora or ahora()
        self.estadoFinal = estado

    @property
    def estaCompletado(self) -> bool:
        return self.horaFin is not None

    def __repr__(self) -> str:
        return f"<RegistroLimpieza {self.id} hab={self.habitacion_id} {self.calcularDuracion()}min>"
