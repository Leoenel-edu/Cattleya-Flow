"""Acceso a datos de HistorialAccion (bitacora de auditoria)."""
from datetime import datetime

from sqlalchemy.orm import joinedload

from backend.models.historial_accion import HistorialAccion
from backend.repositories.base_repository import BaseRepository


class HistorialRepository(BaseRepository[HistorialAccion]):
    modelo = HistorialAccion

    def registrar(
        self,
        accion: str,
        entidad: str,
        entidad_id: int,
        usuario_id: int | None = None,
        detalle: str = "",
    ) -> HistorialAccion:
        """`registrar(accion, entidad, id)` del diagrama de clases.

        No hace commit: se confirma junto con la operacion que lo origina,
        de modo que si esa operacion falla, el log tampoco queda escrito.
        """
        entrada = HistorialAccion(
            accion=accion,
            entidadAfectada=entidad,
            entidadId=entidad_id,
            usuario_id=usuario_id,
            detalle=detalle,
        )
        return self.agregar(entrada)

    def buscarPorEntidad(
        self,
        entidad: str,
        entidad_id: int | None = None,
        fechaInicio: datetime | None = None,
        fechaFin: datetime | None = None,
    ) -> list[HistorialAccion]:
        """`buscarPorEntidad(id)` de CU-06."""
        consulta = self.db.query(HistorialAccion).options(
            joinedload(HistorialAccion.usuario)
        )
        consulta = consulta.filter(HistorialAccion.entidadAfectada == entidad)
        if entidad_id is not None:
            consulta = consulta.filter(HistorialAccion.entidadId == entidad_id)
        if fechaInicio is not None:
            consulta = consulta.filter(HistorialAccion.fecha >= fechaInicio)
        if fechaFin is not None:
            consulta = consulta.filter(HistorialAccion.fecha <= fechaFin)
        return list(consulta.order_by(HistorialAccion.fecha.desc()).all())

    def obtenerRecientes(self, limite: int = 100) -> list[HistorialAccion]:
        return list(
            self.db.query(HistorialAccion)
            .options(joinedload(HistorialAccion.usuario))
            .order_by(HistorialAccion.fecha.desc())
            .limit(limite)
            .all()
        )
