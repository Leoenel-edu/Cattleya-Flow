"""Acceso a datos de Habitacion."""
from sqlalchemy.orm import Session

from backend.models.habitacion import Habitacion
from backend.repositories.base_repository import BaseRepository


class HabitacionRepository(BaseRepository[Habitacion]):
    modelo = Habitacion

    def obtenerTodas(self, filtros: dict | None = None) -> list[Habitacion]:
        """`obtenerTodas(filtros?: Map)` de CU-03.

        El filtrado ocurre aqui, en la capa de datos, y no en el frontend:
        asi el panel no descarga 24 habitaciones para mostrar 6.
        """
        consulta = self.db.query(Habitacion)
        filtros = filtros or {}

        if filtros.get("piso") is not None:
            consulta = consulta.filter(Habitacion.piso == filtros["piso"])
        if filtros.get("tipo"):
            consulta = consulta.filter(Habitacion.tipo == filtros["tipo"])
        if filtros.get("estado"):
            consulta = consulta.filter(Habitacion.estado == filtros["estado"])

        return list(consulta.order_by(Habitacion.numero).all())

    def buscarPorNumero(self, numero: str) -> Habitacion | None:
        return self.db.query(Habitacion).filter(Habitacion.numero == str(numero)).first()

    def contarPorEstado(self) -> dict[str, int]:
        """Alimenta las tarjetas de estadisticas del panel."""
        from sqlalchemy import func

        filas = (
            self.db.query(Habitacion.estado, func.count(Habitacion.id))
            .group_by(Habitacion.estado)
            .all()
        )
        return {estado: total for estado, total in filas}
