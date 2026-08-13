"""CU-02 (Cambiar Estado de Habitacion) y CU-03 (Consultar Panel de Disponibilidad).

Implementa los diagramas de secuencia de Damian Emily y Guaraca Dayana.
"""
from sqlalchemy.orm import Session

from backend.core.tiempo import ahora as ahora_hotel
from backend.models.enums import ETIQUETAS_ESTADO, EstadoHabitacion
from backend.models.habitacion import Habitacion
from backend.models.registro_limpieza import RegistroLimpieza
from backend.models.usuario import Usuario
from backend.repositories.habitacion_repository import HabitacionRepository
from backend.repositories.historial_repository import HistorialRepository
from backend.repositories.registro_repository import RegistroRepository
from backend.services.errors import NoEncontrado, TransicionInvalida
from backend.services.notificacion_service import NotificacionService


class HabitacionService:
    def __init__(self, db: Session):
        self.db = db
        self.habitaciones = HabitacionRepository(db)
        self.registros = RegistroRepository(db)
        self.historial = HistorialRepository(db)
        self.notificaciones = NotificacionService(db)

    # ------------------------------------------------------------- CU-03
    def listar(self, filtros: dict | None = None) -> list[dict]:
        """Panel de disponibilidad. `obtenerTodas()` con filtros opcionales."""
        habitaciones = self.habitaciones.obtenerTodas(filtros)
        return [self._serializar(h) for h in habitaciones]

    def obtenerEstadisticas(self) -> dict:
        conteo = self.habitaciones.contarPorEstado()
        return {
            "total": sum(conteo.values()),
            "clean": conteo.get(EstadoHabitacion.LISTA.value, 0),
            "cleaning": conteo.get(EstadoHabitacion.EN_LIMPIEZA.value, 0),
            "dirty": conteo.get(EstadoHabitacion.SUCIA.value, 0),
        }

    def obtenerDetalle(self, habitacion_id: int) -> dict:
        habitacion = self.habitaciones.obtenerPorId(habitacion_id)
        if habitacion is None:
            raise NoEncontrado(f"La habitacion {habitacion_id} no existe")
        return self._serializar(habitacion)

    def obtenerPorNumero(self, numero: str, rol: str) -> dict:
        """Resuelve la habitacion que codifica un QR (CU-02, escanearQR).

        Devuelve el detalle junto con las transiciones que ese rol puede
        aplicar, para que la pantalla ofrezca solo botones que funcionan en
        lugar de dejar que el usuario descubra el 422 a golpes.
        """
        habitacion = self.habitaciones.buscarPorNumero(numero)
        if habitacion is None:
            raise NoEncontrado(f"La habitacion {numero} no existe")

        datos = self._serializar(habitacion)
        validos = Habitacion.estadosPermitidosDesde(habitacion.estado, rol)
        datos["estadosValidos"] = validos
        datos["estadosValidosEtiquetas"] = [ETIQUETAS_ESTADO[e] for e in validos]
        return datos

    # ------------------------------------------------------------- CU-02
    def cambiarEstado(
        self,
        habitacion_id: int,
        nuevoEstado: str,
        usuario: Usuario,
        observaciones: str = "",
    ) -> dict:
        """Cambia el estado de una habitacion siguiendo el diagrama de CU-02.

        Orden: buscar -> validarTransicion -> crear/cerrar RegistroLimpieza ->
        cambiarEstado -> registrar en historial -> broadcast asincrono.
        """
        # alt [habitacion no encontrada]
        habitacion = self.habitaciones.obtenerPorId(habitacion_id)
        if habitacion is None:
            raise NoEncontrado(f"La habitacion {habitacion_id} no existe")

        estadoAnterior = habitacion.estado

        # alt [transicion invalida]
        if not Habitacion.validarTransicion(estadoAnterior, nuevoEstado, usuario.rol):
            validos = Habitacion.estadosPermitidosDesde(estadoAnterior, usuario.rol)
            raise TransicionInvalida(
                f"No se puede pasar de '{ETIQUETAS_ESTADO.get(estadoAnterior, estadoAnterior)}' "
                f"a '{ETIQUETAS_ESTADO.get(nuevoEstado, nuevoEstado)}'",
                extra={
                    "estadoActual": estadoAnterior,
                    "estadosValidos": validos,
                    "estadosValidosEtiquetas": [ETIQUETAS_ESTADO[e] for e in validos],
                },
            )

        ahora = ahora_hotel()

        # Al empezar a limpiar se abre el registro (RF-04: quien y a que hora).
        if nuevoEstado == EstadoHabitacion.EN_LIMPIEZA.value:
            self.registros.agregar(
                RegistroLimpieza(
                    horaInicio=ahora,
                    estadoFinal=EstadoHabitacion.EN_LIMPIEZA.value,
                    observaciones=observaciones,
                    usuario_id=usuario.id,
                    habitacion_id=habitacion.id,
                )
            )

        # opt [estado = Lista]: se cierra el registro abierto y se notifica.
        if nuevoEstado == EstadoHabitacion.LISTA.value:
            registro = self.registros.buscarAbiertoPorHabitacion(habitacion.id)
            if registro is None:
                # No deberia ocurrir: para llegar a Lista hay que haber pasado
                # por En Limpieza, que es donde se abre el registro. Si pasa
                # (datos migrados a mano, seed incompleto), se crea uno cerrado
                # en el momento en vez de perder la trazabilidad.
                registro = RegistroLimpieza(
                    horaInicio=ahora,
                    usuario_id=usuario.id,
                    habitacion_id=habitacion.id,
                    observaciones=observaciones,
                )
                self.registros.agregar(registro)
            if observaciones:
                registro.observaciones = observaciones
            registro.registrarFin(ahora, EstadoHabitacion.LISTA.value)

            self.notificaciones.crear(
                mensaje=f"Habitacion {habitacion.numero} lista ({registro.calcularDuracion()} min)",
                tipo="success",
            )

        habitacion.cambiarEstado(nuevoEstado, usuario)

        self.historial.registrar(
            accion="cambiarEstado",
            entidad="Habitacion",
            entidad_id=habitacion.id,
            usuario_id=usuario.id,
            detalle=(
                f"{ETIQUETAS_ESTADO.get(estadoAnterior, estadoAnterior)} -> "
                f"{ETIQUETAS_ESTADO.get(nuevoEstado, nuevoEstado)}"
            ),
        )

        self.db.commit()
        self.db.refresh(habitacion)

        # broadcast(habitacionId, nuevoEstado): lo hace Supabase Realtime al
        # detectar el UPDATE en la tabla "habitaciones" (ver GET /api/config
        # y frontend/js/realtime.js), no el backend.
        return self._serializar(habitacion)

    # -------------------------------------------------------- serializacion
    def _serializar(self, habitacion: Habitacion) -> dict:
        """Convierte la entidad al contrato que consume el frontend.

        Se calculan aqui `employee`, `timeStart` y `timeEnd` a partir del ultimo
        registro para que el panel no tenga que pedir los registros por separado.
        """
        ultimo = habitacion.registros[0] if habitacion.registros else None

        empleado = None
        horaInicio = None
        horaFin = None

        if ultimo is not None:
            # Si la habitacion esta sucia, el registro anterior ya no describe
            # su estado presente: mostrarlo haria creer que alguien la esta
            # limpiando ahora.
            if habitacion.estado != EstadoHabitacion.SUCIA.value:
                empleado = ultimo.usuario.nombreCompleto if ultimo.usuario else None
                horaInicio = ultimo.horaInicio.strftime("%H:%M") if ultimo.horaInicio else None
                horaFin = ultimo.horaFin.strftime("%H:%M") if ultimo.horaFin else None

        return {
            "id": habitacion.id,
            "numero": habitacion.numero,
            "floor": habitacion.piso,
            "type": habitacion.tipo,
            "status": habitacion.estado,
            "statusLabel": habitacion.estadoEtiqueta,
            "employee": empleado,
            "timeStart": horaInicio,
            "timeEnd": horaFin,
            "ultimaActualizacion": habitacion.ultimaActualizacion.isoformat(),
        }
