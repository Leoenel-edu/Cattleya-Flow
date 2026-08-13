"""ReporteController - CU-04: Generar Reportes de Productividad.

Restringido a Administrador y Supervisor (RB-02, RS-02).
"""
from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.api.deps import requiere_roles
from backend.core.database import get_db
from backend.models.enums import Rol
from backend.models.usuario import Usuario
from backend.schemas import SolicitarReporteRequest
from backend.services.reporte_service import ReporteService

router = APIRouter(prefix="/api/reportes", tags=["Reportes"])

admin_o_supervisor = requiere_roles(Rol.ADMIN, Rol.SUPERVISOR)


@router.get("/metricas")
def metricas(
    periodo: str = Query("hoy", description="hoy | semana | mes"),
    usuarioId: int | None = Query(None, description="opt [filtrar por empleado]"),
    usuario: Usuario = Depends(admin_o_supervisor),
    db: Session = Depends(get_db),
):
    """GET /api/reportes/metricas -> Map<metricas> para pintar la pantalla.

    Calcula sin generar archivo: la pantalla de reportes necesita las cifras al
    entrar, no un PDF.
    """
    return ReporteService(db).calcularMetricas(periodo, usuarioId)


@router.post("", status_code=status.HTTP_202_ACCEPTED)
def solicitar(
    datos: SolicitarReporteRequest,
    tareas: BackgroundTasks,
    usuario: Usuario = Depends(admin_o_supervisor),
    db: Session = Depends(get_db),
):
    """POST /api/reportes -> 202 Accepted, reporteId

    Responde de inmediato y genera el archivo en segundo plano: es el patron
    asincrono del diagrama, pensado para periodos con muchos registros.
    """
    servicio = ReporteService(db)
    reporte = servicio.solicitar(
        periodo=datos.periodo,
        tipo=datos.tipo,
        formato=datos.formato,
        solicitante=usuario,
        usuario_id=datos.usuarioId,
    )

    tareas.add_task(servicio.generarArchivo, reporte.id, datos.periodo, datos.usuarioId)

    return {
        "mensaje": "Reporte en generacion",
        "reporteId": reporte.id,
        "estado": reporte.estado,
    }


@router.get("/{reporte_id}")
def estado(
    reporte_id: int,
    usuario: Usuario = Depends(admin_o_supervisor),
    db: Session = Depends(get_db),
):
    """GET /api/reportes/{id} -> estado de la generacion (para el polling)."""
    return ReporteService(db).estado(reporte_id)


@router.get("/{reporte_id}/descargar")
def descargar(
    reporte_id: int,
    usuario: Usuario = Depends(admin_o_supervisor),
    db: Session = Depends(get_db),
):
    """GET /api/reportes/{id}/descargar -> archivo PDF/Excel"""
    ruta, nombre = ReporteService(db).obtenerArchivo(reporte_id)
    tipo_mime = (
        "application/pdf"
        if nombre.endswith(".pdf")
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return FileResponse(path=ruta, filename=nombre, media_type=tipo_mime)
