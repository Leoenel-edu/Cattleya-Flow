"""Repositorio base: operaciones comunes de acceso a datos.

La capa de servicios nunca escribe SQL ni consultas de SQLAlchemy; llama a un
repositorio. Ese es el limite entre logica de negocio y persistencia.
"""
from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from backend.core.database import Base

T = TypeVar("T", bound=Base)


class BaseRepository(Generic[T]):
    modelo: type[T]

    def __init__(self, db: Session):
        self.db = db

    def obtenerPorId(self, entidad_id: int) -> T | None:
        return self.db.get(self.modelo, entidad_id)

    def obtenerTodas(self) -> list[T]:
        return list(self.db.query(self.modelo).all())

    def guardar(self, entidad: T) -> T:
        self.db.add(entidad)
        self.db.commit()
        self.db.refresh(entidad)
        return entidad

    def agregar(self, entidad: T) -> T:
        """Agrega sin hacer commit: permite agrupar varias escrituras en una
        sola transaccion desde el servicio."""
        self.db.add(entidad)
        return entidad

    def confirmar(self) -> None:
        self.db.commit()
