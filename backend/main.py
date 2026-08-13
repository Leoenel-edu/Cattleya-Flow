"""Punto de entrada de la aplicacion Cattleya-Flow.

Ensambla las capas:
    api/         Presentacion  (controladores REST + WebSocket)
    services/    Logica de Negocio
    repositories/Acceso a Datos
    models/      Entidades
"""
import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from backend.api.routes import (
    auth_controller,
    habitacion_controller,
    historial_controller,
    reporte_controller,
    usuario_controller,
)
from backend.core.config import settings
from backend.core.database import crear_tablas
from backend.services.errors import ErrorNegocio

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cattleya")

# Se ejecuta al importar el modulo (no en el lifespan): en Vercel cada
# instancia serverless arranca ejecutando este archivo directamente, y el
# runtime de Python no garantiza que los eventos de lifespan de ASGI corran.
crear_tablas()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("%s v%s iniciado", settings.APP_NAME, settings.APP_VERSION)
    logger.info("Interfaz:      http://127.0.0.1:8000")
    logger.info("Documentacion: http://127.0.0.1:8000/docs")
    yield
    logger.info("Servidor detenido")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Sistema de Gestion de Limpieza Hotelera - Hotel Cattleya Real",
    lifespan=lifespan,
)

# El frontend se sirve desde el mismo origen, asi que CORS no es necesario en
# la configuracion por defecto. Se deja abierto para permitir abrir la interfaz
# con Live Server u otro puerto durante el desarrollo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------- manejo de errores
@app.exception_handler(ErrorNegocio)
async def manejar_error_negocio(request: Request, exc: ErrorNegocio):
    """Traduce las excepciones de dominio al codigo HTTP de cada flujo
    alternativo. Gracias a esto, los servicios no importan nada de FastAPI.
    """
    cuerpo = {"detail": exc.mensaje, **exc.extra}
    return JSONResponse(status_code=exc.codigo_http, content=cuerpo)


# ------------------------------------------------------------ controladores
app.include_router(auth_controller.router)
app.include_router(habitacion_controller.router)
app.include_router(usuario_controller.router)
app.include_router(historial_controller.router)
app.include_router(reporte_controller.router)


@app.get("/api/estado")
def estado_sistema():
    """Diagnostico rapido: confirma que el backend responde."""
    return {"sistema": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/api/config")
def config_publica():
    """Configuracion publica que el frontend necesita para conectarse a
    Supabase Realtime (CU-03, RNF-04). SUPABASE_ANON_KEY esta pensada para
    exponerse en el cliente: Supabase la limita con Row Level Security, no
    con secreto, igual que una API key publica de Google Maps.
    """
    return {
        "supabaseUrl": settings.SUPABASE_URL,
        "supabaseAnonKey": settings.SUPABASE_ANON_KEY,
    }


# ------------------------------------------------------------- frontend
class ArchivosSinCache(StaticFiles):
    """Archivos estaticos que el navegador debe revalidar en cada carga.

    Sin esto, el navegador se queda con la version guardada de un .js o .css y
    puede mezclar HTML nuevo con codigo viejo, produciendo errores que no
    existen en el codigo fuente y que no se reproducen en otra maquina.

    `no-cache` no desactiva la cache: obliga a preguntar al servidor si el
    archivo cambio. Si no cambio, la respuesta sigue siendo un 304 vacio, asi
    que no hay coste de red apreciable.
    """

    def is_not_modified(self, response_headers, request_headers) -> bool:
        response_headers.setdefault("Cache-Control", "no-cache")
        return super().is_not_modified(response_headers, request_headers)

    async def get_response(self, path: str, scope):
        respuesta = await super().get_response(path, scope)
        respuesta.headers.setdefault("Cache-Control", "no-cache")
        return respuesta


# Se monta al final: las rutas /api/* y /ws/* tienen prioridad sobre los
# archivos estaticos.
if settings.FRONTEND_DIR.exists():
    app.mount(
        "/css", ArchivosSinCache(directory=settings.FRONTEND_DIR / "css"), name="css"
    )
    app.mount("/js", ArchivosSinCache(directory=settings.FRONTEND_DIR / "js"), name="js")
    app.mount(
        "/assets",
        # Las imagenes si se cachean: pesan mas de 1 MB y casi nunca cambian.
        StaticFiles(directory=settings.FRONTEND_DIR / "assets"),
        name="assets",
    )

    def _version_estaticos() -> int:
        """Marca de tiempo del .js o .css modificado mas recientemente.

        Cambia sola en cuanto se edita cualquier archivo del frontend.
        """
        archivos = [
            *(settings.FRONTEND_DIR / "js").glob("*.js"),
            *(settings.FRONTEND_DIR / "css").glob("*.css"),
        ]
        return int(max((a.stat().st_mtime for a in archivos), default=0))

    @app.get("/", include_in_schema=False)
    def interfaz():
        """Sirve la interfaz con las rutas de los .js y .css versionadas.

        Convierte  src="/js/qr.js"  en  src="/js/qr.js?v=1784259..."

        `Cache-Control: no-cache` no basta: un navegador que ya tenia el archivo
        guardado de antes puede seguir usandolo sin preguntar, y entonces mezcla
        HTML nuevo con codigo viejo. Al cambiar la URL, el archivo guardado deja
        de corresponder y el navegador se ve obligado a pedir el nuevo. Es la
        unica forma fiable de que un celular recoja los cambios sin que su dueño
        tenga que borrar el historial a mano.
        """
        html = (settings.FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
        html = re.sub(
            r'(src|href)="(/(?:js|css)/[^"?]+)"',
            rf'\1="\2?v={_version_estaticos()}"',
            html,
        )
        return HTMLResponse(html, headers={"Cache-Control": "no-cache"})
