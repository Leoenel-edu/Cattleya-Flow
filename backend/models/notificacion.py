"""Entidad Notificacion del diagrama de clases (seccion 1.1)."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.core.tiempo import ahora


class Notificacion(Base):
    __tablename__ = "notificaciones"

    # --- Atributos del diagrama de clases ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mensaje: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), default="info", nullable=False)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=ahora, nullable=False)
    leida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    usuario_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id"), nullable=True, index=True
    )
    usuario: Mapped["Usuario | None"] = relationship(back_populates="notificaciones")  # noqa: F821

    # --- Metodos del diagrama de clases ---
    @classmethod
    def createNotificacion(cls, msg: str, tipo: str = "info") -> "Notificacion":
        """Fabrica definida en el diagrama: `createNotificacion(msg, tipo)`."""
        return cls(mensaje=msg, tipo=tipo)

    def marcarLeida(self) -> None:
        self.leida = True

    def __repr__(self) -> str:
        return f"<Notificacion {self.id} {self.tipo}: {self.mensaje[:30]}>"
