"""ReporteController - CU-04: Generar Reportes de Productividad.

Restringido a Administrador y Supervisor (RB-02, RS-02).
"""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.api.deps import requiere_roles
from backend.core.database import get_db
from backend.models.enums import Rol
from backend.models.usuario import Usuario
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


@router.get("/exportar")
def exportar(
    periodo: str = Query("hoy", description="hoy | semana | mes"),
    formato: str = Query("excel", description="excel | pdf"),
    usuarioId: int | None = Query(None, description="opt [filtrar por empleado]"),
    usuario: Usuario = Depends(admin_o_supervisor),
    db: Session = Depends(get_db),
):
    """GET /api/reportes/exportar -> archivo PDF/Excel.

    buscarPorPeriodo -> calcularMetricas -> exportar del diagrama, en una
    sola peticion sincrona (ver docstring de ReporteService.exportar).
    """
    contenido, nombre = ReporteService(db).exportar(periodo, formato, usuario, usuarioId)
    tipo_mime = (
        "application/pdf"
        if nombre.endswith(".pdf")
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return Response(
        content=contenido,
        media_type=tipo_mime,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )
