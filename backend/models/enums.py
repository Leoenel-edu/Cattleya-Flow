"""Valores fijos del dominio y la maquina de estados de una habitacion."""
from enum import Enum


class Rol(str, Enum):
    """Los cuatro actores del sistema (RF-06)."""

    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    RECEPCION = "recepcion"
    LIMPIEZA = "limpieza"


class EstadoHabitacion(str, Enum):
    """Estados del ciclo de limpieza (RF-03)."""

    SUCIA = "dirty"
    EN_LIMPIEZA = "cleaning"
    LISTA = "clean"


# Maquina de estados que implementa Habitacion.validarTransicion().
#
# El ciclo definido en el documento es: Sucia -> En Limpieza -> Lista.
# Las reglas adicionales y su justificacion:
#
#   * Sucia -> Lista           PROHIBIDA. Es el caso que el documento cita como
#                              transicion invalida: no se puede declarar lista una
#                              habitacion sin registrar que fue limpiada, porque
#                              entonces RegistroLimpieza no tendria horaInicio y el
#                              reporte de productividad (CU-04) no podria calcular
#                              la duracion.
#   * En Limpieza -> Sucia     PERMITIDA. La limpieza puede interrumpirse.
#   * Lista -> Sucia           PERMITIDA solo para recepcion/supervisor/admin.
#                              Representa el check-out del huesped, no un paso del
#                              ciclo de limpieza. Ver TRANSICIONES_POR_ROL.
TRANSICIONES_VALIDAS: dict[EstadoHabitacion, set[EstadoHabitacion]] = {
    EstadoHabitacion.SUCIA: {EstadoHabitacion.EN_LIMPIEZA},
    EstadoHabitacion.EN_LIMPIEZA: {EstadoHabitacion.LISTA, EstadoHabitacion.SUCIA},
    EstadoHabitacion.LISTA: {EstadoHabitacion.SUCIA},
}

# Restriccion por rol sobre la transicion Lista -> Sucia (check-out).
# El personal de limpieza no marca habitaciones como sucias: eso lo determina
# la salida del huesped, que conoce recepcion.
ROLES_PUEDEN_ENSUCIAR: set[Rol] = {Rol.RECEPCION, Rol.SUPERVISOR, Rol.ADMIN}

ETIQUETAS_ESTADO: dict[str, str] = {
    EstadoHabitacion.SUCIA.value: "Sucia",
    EstadoHabitacion.EN_LIMPIEZA.value: "En limpieza",
    EstadoHabitacion.LISTA.value: "Lista",
}

ETIQUETAS_ROL: dict[str, str] = {
    Rol.ADMIN.value: "Administrador",
    Rol.SUPERVISOR.value: "Supervisor",
    Rol.RECEPCION.value: "Recepcion",
    Rol.LIMPIEZA.value: "Personal de Limpieza",
}

# Pantallas visibles por rol (RF-06: "cada uno ve solo lo que le toca").
# El backend es la fuente de verdad; el frontend solo dibuja lo que recibe.
NAVEGACION_POR_ROL: dict[str, list[str]] = {
    Rol.ADMIN.value: ["panel", "cambiar", "historial", "reportes", "usuarios"],
    Rol.SUPERVISOR.value: ["panel", "historial", "reportes"],
    Rol.RECEPCION.value: ["panel", "historial"],
    Rol.LIMPIEZA.value: ["cambiar", "historial"],
}
