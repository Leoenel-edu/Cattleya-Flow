"""Entidad Reporte del diagrama de clases (seccion 1.1).

Guarda la metadata de cada reporte generado (CU-04). El calculo de metricas
y la escritura del archivo viven en ReporteService y GeneradorArchivo: esta
clase solo describe el reporte, no lo produce.
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.core.tiempo import ahora


class Reporte(Base):
    __tablename__ = "reportes"

    # --- Atributos del diagrama de clases ---
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(40), nullable=False)
    fechaGeneracion: Mapped[datetime] = mapped_column(
        DateTime, default=ahora, nullable=False
    )
    formato: Mapped[str] = mapped_column(String(10), nullable=False)
    periodo: Mapped[str] = mapped_column(String(40), nullable=False)

    # Fuera del diagrama: ruta del archivo en disco y estado de la generacion
    # asincrona. CU-04 responde 202 Accepted y el archivo se escribe despues,
    # asi que hace falta saber si ya esta listo.
    rutaArchivo: Mapped[str | None] = mapped_column(String(255), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="procesando", nullable=False)

    solicitante_id: Mapped[int | None] = mapped_column(
        ForeignKey("usuarios.id"), nullable=True
    )
    solicitante: Mapped["Usuario | None"] = relationship()  # noqa: F821

    @property
    def estaListo(self) -> bool:
        return self.estado == "listo" and self.rutaArchivo is not None

    def __repr__(self) -> str:
        return f"<Reporte {self.id} {self.tipo}/{self.formato} ({self.estado})>"
