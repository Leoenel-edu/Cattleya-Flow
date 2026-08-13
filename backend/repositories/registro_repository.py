"""Acceso a datos de RegistroLimpieza."""
from datetime import datetime

from sqlalchemy.orm import Session, joinedload

from backend.models.registro_limpieza import RegistroLimpieza
from backend.repositories.base_repository import BaseRepository


class RegistroRepository(BaseRepository[RegistroLimpieza]):
    modelo = RegistroLimpieza

    def _consultaBase(self):
        # joinedload evita el problema N+1: sin esto, listar 50 registros
        # dispararia 100 consultas extra para traer usuario y habitacion.
        return self.db.query(RegistroLimpieza).options(
            joinedload(RegistroLimpieza.usuario),
            joinedload(RegistroLimpieza.habitacion),
        )

    def buscarPorPeriodo(
        self, fechaInicio: datetime, fechaFin: datetime, usuario_id: int | None = None
    ) -> list[RegistroLimpieza]:
        """`buscarPorPeriodo(fechaInicio, fechaFin)` de CU-04.

        Solo devuelve registros cerrados (con horaFin): un reporte de
        productividad no puede promediar limpiezas que aun no terminan.
        """
        consulta = self._consultaBase().filter(
            RegistroLimpieza.horaInicio >= fechaInicio,
            RegistroLimpieza.horaInicio <= fechaFin,
            RegistroLimpieza.horaFin.isnot(None),
        )
        if usuario_id is not None:
            consulta = consulta.filter(RegistroLimpieza.usuario_id == usuario_id)
        return list(consulta.order_by(RegistroLimpieza.horaInicio.desc()).all())

    def buscarPorHabitacion(
        self,
        habitacion_id: int | None = None,
        fechaInicio: datetime | None = None,
        fechaFin: datetime | None = None,
    ) -> list[RegistroLimpieza]:
        """`buscarPorHabitacion(id, fechaInicio, fechaFin)` de CU-06.

        Los tres parametros son opcionales para que la pantalla de historial
        pueda cargar sin filtros la primera vez.
        """
        consulta = self._consultaBase()
        if habitacion_id is not None:
            consulta = consulta.filter(RegistroLimpieza.habitacion_id == habitacion_id)
        if fechaInicio is not None:
            consulta = consulta.filter(RegistroLimpieza.horaInicio >= fechaInicio)
        if fechaFin is not None:
            consulta = consulta.filter(RegistroLimpieza.horaInicio <= fechaFin)
        return list(consulta.order_by(RegistroLimpieza.horaInicio.desc()).all())

    def buscarAbiertoPorHabitacion(self, habitacion_id: int) -> RegistroLimpieza | None:
        """El registro de limpieza en curso, si existe.

        Cuando una habitacion pasa a "Lista" hay que cerrar el registro que se
        abrio al empezar; este metodo lo localiza.
        """
        return (
            self.db.query(RegistroLimpieza)
            .filter(
                RegistroLimpieza.habitacion_id == habitacion_id,
                RegistroLimpieza.horaFin.is_(None),
            )
            .order_by(RegistroLimpieza.horaInicio.desc())
            .first()
        )

    def obtenerCompletados(self, limite: int = 200) -> list[RegistroLimpieza]:
        return list(
            self._consultaBase()
            .filter(RegistroLimpieza.horaFin.isnot(None))
            .order_by(RegistroLimpieza.horaInicio.desc())
            .limit(limite)
            .all()
        )
