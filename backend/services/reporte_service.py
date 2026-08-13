"""CU-04: Generar Reportes de Productividad.

Implementa el diagrama de secuencia de Martinez Jostin: buscarPorPeriodo ->
calcularMetricas -> exportar -> descargar.

La generacion es sincrona (una sola peticion, sin 202 Accepted + polling):
en un entorno serverless (Vercel) una tarea en segundo plano puede no
sobrevivir despues de que la respuesta se envia, y el archivo generado no
tiene donde persistir entre una peticion y la siguiente. El reporte es
pequeno (una tabla de metricas), asi que generarlo en el mismo request no
introduce una espera perceptible.
"""
from datetime import datetime, time, timedelta

from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.tiempo import ahora
from backend.models.registro_limpieza import RegistroLimpieza
from backend.models.reporte import Reporte
from backend.models.usuario import Usuario
from backend.repositories.base_repository import BaseRepository
from backend.repositories.habitacion_repository import HabitacionRepository
from backend.repositories.registro_repository import RegistroRepository
from backend.services.generador_archivo import GeneradorArchivo


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
    def exportar(
        self, periodo: str, formato: str, solicitante: Usuario, usuario_id: int | None = None
    ) -> tuple[bytes, str]:
        """GET /api/reportes/exportar -> archivo PDF/Excel.

        calcularMetricas -> exportar, en la misma peticion. Se deja constancia
        en `Reporte` (RNF-06: auditoria) de quien pidio que reporte y cuando,
        aunque el archivo en si no se guarde en ningun lado.
        """
        _, _, etiqueta = self.resolverPeriodo(periodo)
        metricas = self.calcularMetricas(periodo, usuario_id)
        contenido, nombre = GeneradorArchivo.exportar(metricas, formato, etiqueta)

        self.reportes.guardar(
            Reporte(
                tipo="productividad",
                formato=formato.lower().strip(),
                periodo=etiqueta,
                solicitante_id=solicitante.id,
            )
        )

        return contenido, nombre
