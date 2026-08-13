"""Manejo del tiempo en todo el sistema.

Decision: se trabaja con datetime "naive" en hora local del hotel.

Por que, y no UTC:
  * Las columnas DateTime de SQLite/SQLAlchemy no guardan zona horaria. Al leer
    devuelven un datetime naive. Si se escribieran datetimes "aware" y se
    compararan con lo leido, Python lanzaria
    "can't subtract offset-naive and offset-aware datetimes".
  * El sistema atiende un solo hotel en una sola zona (Ecuador, sin horario de
    verano). Guardar en UTC obligaria a convertir en cada lectura, y una hora
    sin convertir mostraria "12:45" donde el personal espera "07:45".

Regla: ningun modulo llama a datetime.now() directamente; todos usan ahora().
La unica excepcion es la firma de los JWT, que usa UTC por exigencia del
estandar (ver core/security.py).
"""
from datetime import datetime


def ahora() -> datetime:
    """Fecha y hora actual del hotel, sin zona horaria."""
    return datetime.now()


def a_naive(momento: datetime | None) -> datetime | None:
    """Quita la zona horaria de un datetime que venga de fuera.

    Las fechas que llegan por query string pueden traer offset (?desde=...Z).
    Compararlas contra columnas naive fallaria, asi que se normalizan al entrar.
    """
    if momento is None:
        return None
    if momento.tzinfo is not None:
        return momento.replace(tzinfo=None)
    return momento
