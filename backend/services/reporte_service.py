"""CU-04: Generar Reportes de Productividad.

Implementa el diagrama de secuencia de Martinez Jostin: buscarPorPeriodo ->
calcularMetricas -> exportar (asincrono) -> 202 Accepted -> descargar.
"""
from datetime import datetime, time, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.tiempo import ahora
from backend.models.registro_limpieza import RegistroLimpieza
from backend.models.reporte import Reporte
from backend.models.usuario import Usuario
from backend.repositories.base_repository import BaseRepository
from backend.repositories.habitacion_repository import HabitacionRepository
from backend.repositories.registro_repository import RegistroRepository
from backend.services.errors import FormatoInvalido, NoEncontrado
from backend.services.generador_archivo import FORMATOS_SOPORTADOS, GeneradorArchivo


class ReporteRepository(BaseRepository[Reporte]):
    modelo = Reporte


class ReporteService:
    def __init__(self, db: Session):
        self.db = db
        self.registros = RegistroRepository(db)
        self.habitaciones = HabitacionRepository(db)
        self.reportes = ReporteRepository(db)

    # ------------------------------------------------------------- periodos
    @staticmethod
    def resolverPeriodo(periodo: str) -> tuple[datetime, datetime, str]:
        """Traduce 'hoy' | 'semana' | 'mes' a un rango de fechas concreto."""
        hoy = ahora().date()
        inicioHoy = datetime.combine(hoy, time.min)
        finHoy = datetime.combine(hoy, time.max)

        if periodo == "semana":
            inicio = inicioHoy - timedelta(days=inicioHoy.weekday())
            return inicio, finHoy, "Semana actual"
        if periodo == "mes":
            inicio = datetime.combine(hoy.replace(day=1), time.min)
            return inicio, finHoy, "Mes actual"
        return inicioHoy, finHoy, "Hoy"

    # ---------------------------------------------------------- calculo
    def calcularMetricas(
        self, periodo: str = "hoy", usuario_id: int | None = None
    ) -> dict:
        """`calcularMetricas(registros): Map` de la clase Reporte.

        Las cifras salen de los RegistroLimpieza reales, no de valores fijos:
        cada limpieza completada las recalcula.
        """
        inicio, fin, etiqueta = self.resolverPeriodo(periodo)

        # opt [filtrar por empleado]
        registros = self.registros.buscarPorPeriodo(inicio, fin, usuario_id)

        porEmpleado: dict[str, dict] = {}
        for registro in registros:
            if registro.usuario is None:
                continue
            nombre = registro.usuario.nombreCompleto
            acumulado = porEmpleado.setdefault(
                nombre, {"name": nombre, "rooms": 0, "totalMin": 0}
            )
            acumulado["rooms"] += 1
            acumulado["totalMin"] += registro.calcularDuracion()

        empleados = []
        for datos in porEmpleado.values():
            # `rooms` nunca es 0 aqui: solo existe la entrada si se sumo al
            # menos un registro. Aun asi la division va protegida, porque el
            # diagrama senala explicitamente el riesgo de division por cero.
            promedio = round(datos["totalMin"] / datos["rooms"]) if datos["rooms"] else 0
            empleados.append(
                {
                    "name": datos["name"],
                    "rooms": datos["rooms"],
                    "avgMin": promedio,
                    "eff": self._calcularEficiencia(promedio),
                }
            )
        empleados.sort(key=lambda e: e["rooms"], reverse=True)

        totalHabitaciones = sum(e["rooms"] for e in empleados)
        if totalHabitaciones:
            # Promedio ponderado: quien limpio 8 habitaciones pesa mas que
            # quien limpio 1. Un promedio simple de promedios distorsionaria.
            tiempoPromedio = round(
                sum(e["avgMin"] * e["rooms"] for e in empleados) / totalHabitaciones
            )
            eficienciaGlobal = round(
                sum(e["eff"] * e["rooms"] for e in empleados) / totalHabitaciones
            )
        else:
            tiempoPromedio = 0
            eficienciaGlobal = 0

        estadisticas = self.habitaciones.contarPorEstado()

        return {
            "periodo": etiqueta,
            "periodoClave": periodo,
            "desde": inicio.isoformat(),
            "hasta": fin.isoformat(),
            "totalHabitaciones": totalHabitaciones,
            "limpiasAhora": estadisticas.get("clean", 0),
            "tiempoPromedio": tiempoPromedio,
            "personalActivo": len(empleados),
            "eficienciaGlobal": eficienciaGlobal,
            "empleados": empleados,
        }

    @staticmethod
    def _calcularEficiencia(promedioMin: int) -> int:
        """100% al cumplir el tiempo objetivo; baja al excederlo.

        Se acota entre 50 y 100 para que un unico registro atipico (una
        limpieza de 3 horas por olvido de marcar el fin) no hunda la metrica
        a valores negativos.
        """
        if promedioMin <= 0:
            return 0
        bruta = 100 - (promedioMin - settings.TIEMPO_IDEAL_LIMPIEZA_MIN) * settings.PENALIZACION_POR_MINUTO
        return max(50, min(100, round(bruta)))

    # ------------------------------------------------------------ generacion
    def solicitar(
        self, periodo: str, tipo: str, formato: str, solicitante: Usuario, usuario_id: int | None = None
    ) -> Reporte:
        """POST /api/reportes -> 202 Accepted, reporteId.

        Valida y registra el reporte; el archivo se escribe despues en segundo
        plano (ver `generarArchivo`), tal como modela el mensaje asincrono del
        diagrama.
        """
        formato = (formato or "").lower().strip()

        # alt [formato invalido] - se valida antes de crear nada.
        if formato not in FORMATOS_SOPORTADOS:
            raise FormatoInvalido(
                f"Formato no soportado: '{formato}'",
                extra={"formatosValidos": sorted(FORMATOS_SOPORTADOS)},
            )

        _, _, etiqueta = self.resolverPeriodo(periodo)

        reporte = Reporte(
            tipo=tipo or "productividad",
            formato=formato,
            periodo=etiqueta,
            estado="procesando",
            solicitante_id=solicitante.id,
        )
        return self.reportes.guardar(reporte)

    def generarArchivo(self, reporte_id: int, periodo: str, usuario_id: int | None = None) -> None:
        """Tarea en segundo plano: calcula, escribe el archivo y marca listo.

        Cualquier excepcion se captura y se refleja en el estado del reporte:
        si escapara, moriria en el hilo de background sin que nadie se entere y
        el reporte quedaria "procesando" para siempre.
        """
        reporte = self.reportes.obtenerPorId(reporte_id)
        if reporte is None:
            return

        try:
            metricas = self.calcularMetricas(periodo, usuario_id)
            ruta = GeneradorArchivo.exportar(metricas, reporte.formato, reporte.periodo)
            reporte.rutaArchivo = str(ruta)
            reporte.estado = "listo"
        except Exception as exc:  # noqa: BLE001
            reporte.estado = "error"
            reporte.rutaArchivo = None
            import logging

            logging.getLogger(__name__).exception("Fallo al generar el reporte %s: %s", reporte_id, exc)
        finally:
            self.db.commit()

    def obtenerArchivo(self, reporte_id: int) -> tuple[Path, str]:
        """GET /api/reportes/{id}/descargar -> (ruta, nombre)"""
        reporte = self.reportes.obtenerPorId(reporte_id)
        if reporte is None:
            raise NoEncontrado(f"El reporte {reporte_id} no existe")
        if reporte.estado == "error":
            raise NoEncontrado("El reporte fallo al generarse. Intenta de nuevo.")
        if not reporte.estaListo:
            raise NoEncontrado("El reporte aun se esta generando")

        ruta = Path(reporte.rutaArchivo)
        if not ruta.exists():
            raise NoEncontrado("El archivo del reporte ya no esta disponible")

        return ruta, ruta.name

    def estado(self, reporte_id: int) -> dict:
        reporte = self.reportes.obtenerPorId(reporte_id)
        if reporte is None:
            raise NoEncontrado(f"El reporte {reporte_id} no existe")
        return {
            "id": reporte.id,
            "tipo": reporte.tipo,
            "formato": reporte.formato,
            "periodo": reporte.periodo,
            "estado": reporte.estado,
            "listo": reporte.estaListo,
            "fechaGeneracion": reporte.fechaGeneracion.isoformat(),
        }
