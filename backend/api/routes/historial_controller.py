"""HistorialController - CU-06: Consultar Historial de Limpieza."""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.api.deps import usuario_actual
from backend.core.database import get_db
from backend.models.usuario import Usuario
from backend.services.errors import FormatoInvalido
from backend.services.generador_archivo import GeneradorArchivo
from backend.services.historial_service import HistorialService

router = APIRouter(prefix="/api/historial", tags=["Historial"])


@router.get("")
def consultar(
    habitacion: str | None = Query(None, description="Numero de habitacion"),
    desde: datetime | None = Query(None, description="Fecha inicial (ISO)"),
    hasta: datetime | None = Query(None, description="Fecha final (ISO)"),
    usuario: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    """GET /api/historial?habitacion=X&desde=Y&hasta=Z -> { registros, historial }"""
    return HistorialService(db).consultar(habitacion, desde, hasta)


@router.get("/exportar")
def exportar(
    formato: str = Query("pdf", description="pdf | excel"),
    habitacion: str | None = Query(None),
    desde: datetime | None = Query(None),
    hasta: datetime | None = Query(None),
    usuario: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    """GET /api/historial/exportar?formato=PDF -> archivo

    opt [exportar registro] de CU-06. A diferencia de los reportes de CU-04,
    aqui la descarga es sincrona: el historial filtrado es pequeno y el
    supervisor espera el archivo en el momento.
    """
    datos = HistorialService(db).consultar(habitacion, desde, hasta)
    registros = datos["registros"]

    # Se reutiliza GeneradorArchivo dandole la forma de "metricas" que espera,
    # tratando cada registro como una fila. Evita duplicar la logica de PDF/Excel.
    metricas = {
        "totalHabitaciones": len(registros),
        "tiempoPromedio": (
            round(sum(r["durationMin"] for r in registros) / len(registros))
            if registros
            else 0
        ),
        "personalActivo": len({r["employee"] for r in registros}),
        "eficienciaGlobal": 0,
        "empleados": [
            {
                "name": f"Hab. {r['room']} - {r['employee']}",
                "rooms": 1,
                "avgMin": r["durationMin"],
                "eff": 0,
            }
            for r in registros
        ],
    }

    formato_normalizado = formato.lower().strip()
    contenido, nombre = GeneradorArchivo.exportar(
        metricas,
        formato_normalizado,
        f"Historial{' hab. ' + habitacion if habitacion else ''}",
    )

    tipo_mime = (
        "application/pdf"
        if formato_normalizado == "pdf"
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return Response(
        content=contenido,
        media_type=tipo_mime,
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/registro/{registro_id}")
def detalleRegistro(
    registro_id: int,
    usuario: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    """opt [ver detalle de registro]: modal con observaciones completas."""
    return HistorialService(db).obtenerDetalleRegistro(registro_id)
