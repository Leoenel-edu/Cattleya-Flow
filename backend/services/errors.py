"""Errores de negocio.

La capa de servicios lanza estas excepciones; la capa de presentacion las
traduce a codigos HTTP. Asi el servicio no importa nada de FastAPI y podria
reutilizarse desde una tarea programada o un script.

Cada excepcion corresponde a un flujo alternativo de los diagramas de secuencia.
"""


class ErrorNegocio(Exception):
    """Raiz de todos los errores de dominio."""

    codigo_http = 400

    def __init__(self, mensaje: str, extra: dict | None = None):
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.extra = extra or {}


class CredencialesInvalidas(ErrorNegocio):
    """CU-01, alt [credenciales invalidas] -> 401"""

    codigo_http = 401


class CuentaDesactivada(ErrorNegocio):
    """CU-01, alt [cuenta desactivada] -> 403"""

    codigo_http = 403


class SinPermiso(ErrorNegocio):
    """RF-06: el rol no tiene acceso a la operacion -> 403"""

    codigo_http = 403


class NoEncontrado(ErrorNegocio):
    """CU-02 alt [habitacion no encontrada], CU-04/CU-06 alt [sin registros] -> 404"""

    codigo_http = 404


class EmailDuplicado(ErrorNegocio):
    """CU-05, alt [email duplicado] -> 409"""

    codigo_http = 409


class TransicionInvalida(ErrorNegocio):
    """CU-02, alt [transicion invalida] -> 422

    Lleva en `extra` los estados validos, para que el frontend pueda
    "Mostrar estados validos" como indica el diagrama.
    """

    codigo_http = 422


class FormatoInvalido(ErrorNegocio):
    """CU-04, alt [formato invalido] -> 400"""

    codigo_http = 400
