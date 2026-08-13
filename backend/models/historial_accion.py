"""Entidad HistorialAccion del diagrama de clases (seccion 1.1).

Bitacora de auditoria: cada accion que modifica datos deja rastro aqui
(RNF-06, retencion de 12 meses).
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.core.tiempo import ahora


class HistorialAccion(Base):
    __tablename__ = "historial_acciones"

    # --- Atributos del diagrama de clases ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    accion: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    fecha: Mapped[datetime] = mapped_column(
        DateTime, default=ahora, nullable=False, index=True
    )
    entidadAfectada: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entidadId: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    # Fuera del diagrama: texto legible para la pantalla de historial.
    # Evita que el frontend tenga que reconstruir la frase a partir de los ids.
    detalle: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    # --- Relacion (seccion 1.2): Usuario -> HistorialAccion, 1 a 0..* ---
    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id"), nullable=True, index=True
    )
    usuario: Mapped["Usuario | None"] = relationship(back_populates="acciones")  # noqa: F821

    def __repr__(self) -> str:
        return f"<HistorialAccion {self.accion} {self.entidadAfectada}#{self.entidadId}>"
