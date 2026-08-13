"""Contratos de entrada y salida de la API (Pydantic).

Validan la forma de los datos en la frontera del sistema, antes de que
lleguen a la capa de negocio.
"""
from pydantic import BaseModel, Field, field_validator

from backend.models.enums import EstadoHabitacion, Rol


# ------------------------------------------------------------------ CU-01
class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=160)
    password: str = Field(..., min_length=1, max_length=128)


class LoginResponse(BaseModel):
    token: str
    rol: str
    rolEtiqueta: str
    nombre: str
    usuarioId: int
    primerLogin: bool
    navegacion: list[str]


# ------------------------------------------------------------------ CU-02
class CambiarEstadoRequest(BaseModel):
    estado: str
    observaciones: str = Field(default="", max_length=500)

    @field_validator("estado")
    @classmethod
    def estado_valido(cls, v: str) -> str:
        if v not in {e.value for e in EstadoHabitacion}:
            validos = ", ".join(e.value for e in EstadoHabitacion)
            raise ValueError(f"Estado desconocido '{v}'. Validos: {validos}")
        return v


# ------------------------------------------------------------------ CU-05
class CrearUsuarioRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=80)
    apellido: str = Field(default="", max_length=80)
    email: str = Field(..., min_length=5, max_length=160)
    rol: str

    @field_validator("rol")
    @classmethod
    def rol_valido(cls, v: str) -> str:
        if v not in {r.value for r in Rol}:
            validos = ", ".join(r.value for r in Rol)
            raise ValueError(f"Rol desconocido '{v}'. Validos: {validos}")
        return v

    @field_validator("email")
    @classmethod
    def email_valido(cls, v: str) -> str:
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("El correo no tiene un formato valido")
        return v.strip().lower()


class CambiarRolRequest(BaseModel):
    rol: str

    @field_validator("rol")
    @classmethod
    def rol_valido(cls, v: str) -> str:
        if v not in {r.value for r in Rol}:
            raise ValueError(f"Rol desconocido '{v}'")
        return v


class CambiarActivoRequest(BaseModel):
    activo: bool


# ------------------------------------------------------------------ CU-04
class SolicitarReporteRequest(BaseModel):
    periodo: str = Field(default="hoy")
    tipo: str = Field(default="productividad")
    formato: str = Field(default="excel")
    usuarioId: int | None = None
