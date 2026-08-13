"""Capa de Datos: las 6 entidades del diagrama de clases unificado.

Importarlas aqui las registra en `Base.metadata`, que es lo que permite a
`crear_tablas()` construir el esquema completo.
"""
from backend.models.enums import (
    ETIQUETAS_ESTADO,
    ETIQUETAS_ROL,
    NAVEGACION_POR_ROL,
    ROLES_PUEDEN_ENSUCIAR,
    TRANSICIONES_VALIDAS,
    EstadoHabitacion,
    Rol,
)
from backend.models.habitacion import Habitacion
from backend.models.historial_accion import HistorialAccion
from backend.models.notificacion import Notificacion
from backend.models.registro_limpieza import RegistroLimpieza
from backend.models.reporte import Reporte
from backend.models.usuario import Usuario

__all__ = [
    "Usuario",
    "Habitacion",
    "RegistroLimpieza",
    "HistorialAccion",
    "Reporte",
    "Notificacion",
    "Rol",
    "EstadoHabitacion",
    "TRANSICIONES_VALIDAS",
    "ROLES_PUEDEN_ENSUCIAR",
    "ETIQUETAS_ESTADO",
    "ETIQUETAS_ROL",
    "NAVEGACION_POR_ROL",
]
