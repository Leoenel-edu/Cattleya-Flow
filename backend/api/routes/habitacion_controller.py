"""HabitacionController - CU-02 (Cambiar Estado) y CU-03 (Panel de Disponibilidad)."""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.api.deps import requiere_roles, usuario_actual
from backend.core.database import get_db
from backend.models.enums import Rol
from backend.models.usuario import Usuario
from backend.schemas import CambiarEstadoRequest
from backend.services.habitacion_service import HabitacionService
from backend.services.qr_service import generar_hoja_pdf, url_base

router = APIRouter(prefix="/api/habitaciones", tags=["Habitaciones"])


@router.get("")
def listar(
    piso: int | None = Query(None, description="Filtrar por piso"),
    tipo: str | None = Query(None, description="Filtrar por tipo de habitacion"),
    estado: str | None = Query(None, description="dirty | cleaning | clean"),
    usuario: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    """GET /api/habitaciones?piso=2&tipo=Suite -> [{id, numero, piso, tipo, estado}]"""
    servicio = HabitacionService(db)
    filtros = {"piso": piso, "tipo": tipo, "estado": estado}
    return {
        "habitaciones": servicio.listar(filtros),
        "estadisticas": servicio.obtenerEstadisticas(),
    }


# --------------------------------------------------------------------- QR
# Estas rutas se declaran ANTES de /{habitacion_id}: ese parametro esta tipado
# como int, y si se declararan despues, "qr" y "numero" no se convertirian a
# entero y la peticion moriria con un 422 en vez de llegar aqui.


@router.get("/qr/hoja")
def hojaQR(
    usuario: Usuario = Depends(requiere_roles(Rol.ADMIN, Rol.SUPERVISOR)),
    db: Session = Depends(get_db),
):
    """GET /api/habitaciones/qr/hoja -> PDF imprimible con un QR por habitacion.

    Se pega en cada puerta. El personal lo escanea con la camara del celular
    y la aplicacion abre directamente esa habitacion (CU-02, escanearQR).
    """
    habitaciones = HabitacionService(db).listar()
    contenido, nombre = generar_hoja_pdf(habitaciones)
    return Response(
        content=contenido,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{nombre}"'},
    )


@router.get("/qr/info")
def infoQR(usuario: Usuario = Depends(usuario_actual)):
    """Direccion que llevan los QR. Sirve para avisar al administrador si
    apuntan a localhost (no funcionarian desde un celular)."""
    base = url_base()
    return {
        "urlBase": base,
        "esLocalhost": "127.0.0.1" in base or "localhost" in base,
    }


@router.get("/numero/{numero}")
def porNumero(
    numero: str,
    usuario: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    """GET /api/habitaciones/numero/101 -> habitacion + estados que este rol
    puede aplicar. Es el destino del enlace que codifica el QR."""
    return HabitacionService(db).obtenerPorNumero(numero, usuario.rol)


@router.get("/{habitacion_id}")
def detalle(
    habitacion_id: int,
    usuario: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    """GET /api/habitaciones/{id} -> Habitacion (estado actual)"""
    return HabitacionService(db).obtenerDetalle(habitacion_id)


@router.patch("/{habitacion_id}/estado")
def cambiarEstado(
    habitacion_id: int,
    datos: CambiarEstadoRequest,
    usuario: Usuario = Depends(usuario_actual),
    db: Session = Depends(get_db),
):
    """PATCH /api/habitaciones/{id}/estado -> 200 OK, estado actualizado

    Un 422 con la lista de estados validos indica transicion no permitida;
    un 404, habitacion inexistente.
    """
    habitacion = HabitacionService(db).cambiarEstado(
        habitacion_id=habitacion_id,
        nuevoEstado=datos.estado,
        usuario=usuario,
        observaciones=datos.observaciones,
    )
    return {"mensaje": "Estado actualizado", "habitacion": habitacion}
