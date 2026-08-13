"""Conexion a la base de datos: la frontera de la capa de persistencia.

Ningun otro modulo crea conexiones. Los repositorios reciben una `Session`
por inyeccion de dependencias, lo que permite cambiar SQLite por PostgreSQL
tocando solo `settings.DATABASE_URL`.
"""
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.core.config import settings

es_sqlite = settings.DATABASE_URL.startswith("sqlite")

if es_sqlite:
    # Asegura que la carpeta database/ exista antes de crear el archivo .db
    ruta_db = settings.DATABASE_URL.replace("sqlite:///", "")
    Path(ruta_db).parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    # SQLite bloquea el acceso desde otros hilos por defecto; FastAPI usa varios.
    connect_args={"check_same_thread": False} if es_sqlite else {},
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """Clase base de la que heredan las 6 entidades del diagrama de clases."""


def get_db():
    """Dependencia de FastAPI: entrega una sesion y garantiza que se cierre."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def crear_tablas() -> None:
    """Crea el esquema a partir de los modelos. Se invoca al arrancar."""
    from backend import models  # noqa: F401  (registra las entidades en Base)

    Base.metadata.create_all(bind=engine)
