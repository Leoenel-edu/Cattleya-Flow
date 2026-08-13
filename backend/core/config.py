"""Configuracion central del sistema Cattleya-Flow.

Todo valor que dependa del entorno (claves, rutas, cadena de conexion) se lee
aqui y en ningun otro lugar. Asi la capa de negocio nunca conoce el entorno.
"""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Raiz del proyecto: .../Cattleya-Flow
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Parametros del sistema. Se sobreescriben con variables de entorno o .env"""

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_prefix="CATTLEYA_",
        extra="ignore",
    )

    # --- Identidad ---
    APP_NAME: str = "Cattleya-Flow"
    APP_VERSION: str = "1.0.0"

    # --- Seguridad (CU-01, RNF-02) ---
    SECRET_KEY: str = "clave-de-desarrollo-no-usar-en-produccion"
    ALGORITHM: str = "HS256"
    TOKEN_EXPIRE_MINUTES: int = 480  # 8 horas = una jornada laboral

    # --- Persistencia ---
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'database' / 'cattleya.db'}"

    # --- Tiempo real (CU-03, RNF-04) ---
    # El panel se suscribe directo a los cambios de la tabla "habitaciones" en
    # Supabase Realtime (ver GET /api/config). SUPABASE_ANON_KEY es publica por
    # diseno: Supabase la protege con Row Level Security, no con secreto.
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""

    # --- Codigos QR ---
    # Puerto en el que se publica el servidor. Se usa para armar la URL que
    # llevan los QR de las habitaciones.
    PUERTO: int = 8000
    # Direccion base de los QR. Si se deja vacia se detecta la IP de la red
    # local automaticamente. Fijarla solo si el sistema se publica en un
    # dominio (ej. https://cattleya.hotel.com).
    BASE_URL: str = ""

    # --- Reglas de negocio ---
    # Tiempo objetivo de limpieza por habitacion, en minutos.
    # Se usa para calcular la eficiencia en los reportes (CU-04).
    TIEMPO_IDEAL_LIMPIEZA_MIN: int = 40
    # Puntos de eficiencia perdidos por cada minuto sobre el objetivo.
    PENALIZACION_POR_MINUTO: int = 2
    # Meses que se conserva el historial de auditoria (RNF-06).
    RETENCION_HISTORIAL_MESES: int = 12

    # --- Rutas ---
    @property
    def FRONTEND_DIR(self) -> Path:
        return BASE_DIR / "frontend"


settings = Settings()
