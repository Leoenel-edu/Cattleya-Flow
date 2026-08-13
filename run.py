"""Arranca el servidor de Cattleya-Flow.

    python run.py

Abre http://127.0.0.1:8000 en esta computadora, o la direccion de red que se
imprime al arrancar si entras desde un celular.
"""
import uvicorn

from backend.core.config import settings
from backend.services.qr_service import detectar_ip_lan

if __name__ == "__main__":
    ip = detectar_ip_lan()

    print()
    print("  Cattleya-Flow")
    print("  " + "-" * 46)
    print(f"  En esta computadora : http://127.0.0.1:{settings.PUERTO}")
    print(f"  Desde el celular    : http://{ip}:{settings.PUERTO}")
    print(f"  API (documentacion) : http://127.0.0.1:{settings.PUERTO}/docs")
    print()
    print("  Los codigos QR apuntan a la direccion del celular.")
    print("  El telefono debe estar en la misma red WiFi.")
    print()

    uvicorn.run(
        "backend.main:app",
        # 0.0.0.0 y no 127.0.0.1: escucha en todas las interfaces de red.
        # Atado solo a 127.0.0.1 el servidor acepta unicamente conexiones de
        # esta misma maquina, y los codigos QR no abririan nada desde un
        # celular aunque estuviera en la misma WiFi.
        host="0.0.0.0",  # noqa: S104
        port=settings.PUERTO,
        reload=True,  # recarga automatica al guardar cambios
        reload_dirs=["backend"],
    )
