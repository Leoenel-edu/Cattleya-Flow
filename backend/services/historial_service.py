"""CU-06: Consultar Historial de Limpieza.

Implementa el diagrama de secuencia de Onate Leonel: consulta las dos fuentes
(RegistroLimpieza e HistorialAccion) y las devuelve juntas.
"""
from datetime import datetime, time

from sqlalchemy.orm import Session

from backend.core.tiempo import a_naive
from backend.models.registro_limpieza import RegistroLimpieza
from backend.repositories.habitacion_repository import HabitacionRepository
from backend.repositories.historial_repository import HistorialRepository
from backend.repositories.registro_repository import RegistroRepository
from backend.services.errors import NoEncontrado


class HistorialService:
    def __init__(self, db: Session):
        self.db = db
        self.registros = RegistroRepository(db)
        self.historial = HistorialRepository(db)
        self.habitaciones = HabitacionRepository(db)

    def consultar(
        self,
        numeroHabitacion: str | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
    ) -> dict:
        """GET /api/historial?habitacion=X&desde=Y&hasta=Z

        Devuelve {registros, historial} tal como el diagrama de CU-06.
        """
        # El navegador puede enviar las fechas con offset (?desde=...Z).
        # Las columnas son naive, asi que se normalizan al entrar.
        desde = a_naive(desde)
        hasta = a_naive(hasta)

        habitacion_id = None
        if numeroHabitacion:
            habitacion = self.habitaciones.buscarPorNumero(numeroHabitacion)
            if habitacion is None:
                raise NoEncontrado(f"La habitacion {numeroHabitacion} no existe")
            habitacion_id = habitacion.id

        # `hasta` llega como fecha (00:00). Sin esto, filtrar "hasta hoy"
        # excluiria todo lo ocurrido hoy despues de medianoche.
        if hasta is not None and hasta.time() == time(0, 0):
            hasta = datetime.combine(hasta.date(), time(23, 59, 59))

        registros = self.registros.buscarPorHabitacion(habitacion_id, desde, hasta)

        # alt [historial vacio]: no se lanza 404. El diagrama lo modela como
        # error, pero una tabla vacia es un resultado legitimo de un filtro, y
        # el frontend ya muestra "Sin registros". Devolver 404 obligaria a
        # tratar un caso normal como excepcion.
        acciones = self.historial.buscarPorEntidad(
            entidad="Habitacion",
            entidad_id=habitacion_id,
            fechaInicio=desde,
            fechaFin=hasta,
        )

        return {
            "registros": [self._serializarRegistro(r) for r in registros],
            "historial": [
                {
                    "id": a.id,
                    "accion": a.accion,
                    "fecha": a.fecha.isoformat(),
                    "entidadAfectada": a.entidadAfectada,
                    "entidadId": a.entidadId,
                    "detalle": a.detalle,
                    "usuario": a.usuario.nombreCompleto if a.usuario else "Sistema",
                }
                for a in acciones
            ],
            "total": len(registros),
        }

    def obtenerDetalleRegistro(self, registro_id: int) -> dict:
        """opt [ver detalle de registro]: el modal con la informacion completa."""
        registro = self.registros.obtenerPorId(registro_id)
        if registro is None:
            raise NoEncontrado(f"El registro {registro_id} no existe")
        return self._serializarRegistro(registro, incluirObservaciones=True)

    @staticmethod
    def _serializarRegistro(registro: RegistroLimpieza, incluirObservaciones: bool = False) -> dict:
        datos = {
            "id": registro.id,
            "room": registro.habitacion.numero if registro.habitacion else "-",
            "roomId": registro.habitacion_id,
            "employee": registro.usuario.nombreCompleto if registro.usuario else "-",
            "start": registro.horaInicio.strftime("%H:%M") if registro.horaInicio else "-",
            "end": registro.horaFin.strftime("%H:%M") if registro.horaFin else "-",
            "fecha": registro.horaInicio.strftime("%d/%m/%Y") if registro.horaInicio else "-",
            "duration": f"{registro.calcularDuracion()} min" if registro.estaCompletado else "En curso",
            "durationMin": registro.calcularDuracion(),
            "status": registro.estadoFinal,
        }
        if incluirObservaciones:
            datos["observaciones"] = registro.observaciones or "Sin observaciones"
        return datos
