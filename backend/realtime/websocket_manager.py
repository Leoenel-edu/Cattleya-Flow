"""Modulo WebSocket (Tiempo Real).

Cumple RNF-04 / RS-01: un cambio de estado debe verse en todos los clientes
en menos de 5 segundos. Como el servidor empuja el evento apenas ocurre, la
latencia real es de milisegundos, no de segundos.

El broadcast es asincrono a proposito (mensaje -) en el diagrama de CU-02):
el personal de limpieza recibe su 200 OK sin esperar a que todos los clientes
conectados acusen recibo.
"""
import asyncio
import logging

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class WebSocketManager:
    """Mantiene las conexiones abiertas y les difunde eventos."""

    def __init__(self) -> None:
        self._conexiones: set[WebSocket] = set()
        self._lock = asyncio.Lock()
        # Bucle de eventos principal. Se fija al arrancar (ver registrar_loop).
        self._loop: asyncio.AbstractEventLoop | None = None

    def registrar_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        """Guarda el bucle donde corre la aplicacion.

        Es imprescindible: los servicios se ejecutan en un hilo del threadpool
        (FastAPI hace eso con los endpoints declarados `def`), y desde ahi
        `asyncio.get_running_loop()` falla. Sin esta referencia, el broadcast
        no tendria a donde publicarse y los cambios no llegarian a nadie.
        """
        self._loop = loop

    async def conectar(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self._conexiones.add(websocket)
        logger.info("WebSocket conectado (%d activos)", len(self._conexiones))

    async def desconectar(self, websocket: WebSocket) -> None:
        async with self._lock:
            self._conexiones.discard(websocket)
        logger.info("WebSocket desconectado (%d activos)", len(self._conexiones))

    async def broadcast(self, evento: str, datos: dict) -> None:
        """Envia un evento a todos los clientes suscritos.

        Un cliente puede haberse desconectado sin avisar; si el envio falla se
        descarta esa conexion en lugar de dejar que el error interrumpa la
        difusion al resto.
        """
        mensaje = {"evento": evento, "datos": datos}

        async with self._lock:
            destinos = list(self._conexiones)

        caidas: list[WebSocket] = []
        for conexion in destinos:
            try:
                await conexion.send_json(mensaje)
            except Exception:
                caidas.append(conexion)

        if caidas:
            async with self._lock:
                for conexion in caidas:
                    self._conexiones.discard(conexion)

        logger.info(
            "Broadcast '%s' a %d cliente(s)", evento, len(destinos) - len(caidas)
        )

    @property
    def loop(self) -> asyncio.AbstractEventLoop | None:
        return self._loop

    @property
    def total_conexiones(self) -> int:
        return len(self._conexiones)


# Instancia unica compartida por toda la aplicacion.
manager = WebSocketManager()


def notificar_cambio_estado(habitacion_dict: dict) -> None:
    """Puente entre el codigo sincrono (los servicios) y el asincrono.

    Los servicios corren en un hilo de trabajo sin bucle de eventos propio, asi
    que no pueden usar `await`. `run_coroutine_threadsafe` encola el broadcast
    en el bucle principal y devuelve el control de inmediato: el cliente que
    provoco el cambio no espera a que se propague, tal como exige el mensaje
    asincrono del diagrama de CU-02.
    """
    loop = manager.loop

    if loop is None or loop.is_closed():
        # Sin bucle registrado no hay a donde publicar. Ocurre de forma normal
        # en scripts y pruebas; con clientes conectados significa que el
        # tiempo real esta roto, y eso no puede pasar en silencio.
        if manager.total_conexiones:
            logger.warning(
                "Bucle de eventos no registrado: %d cliente(s) no recibiran el cambio",
                manager.total_conexiones,
            )
        return

    corutina = manager.broadcast("habitacionActualizada", habitacion_dict)

    try:
        if loop.is_running():
            asyncio.run_coroutine_threadsafe(corutina, loop)
        else:
            corutina.close()
    except Exception as exc:  # noqa: BLE001
        # Un fallo al propagar no debe tumbar el cambio de estado, que ya
        # esta confirmado en la base de datos.
        corutina.close()
        logger.error("No se pudo emitir el broadcast: %s", exc)
