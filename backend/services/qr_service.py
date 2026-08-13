"""Servicio Externo: generacion de codigos QR por habitacion.

Cubre el "API / Libreria de Codigos QR" que el documento lista entre los
servicios externos, y el mensaje `escanearQR(codigoHabitacion)` con el que
arranca el diagrama de secuencia de CU-02.

Como funciona el escaneo
------------------------
El QR no codifica un numero suelto, sino una URL:

    http://<ip-del-servidor>:8000/?hab=101

Asi lo lee la camara nativa de cualquier celular, sin necesidad de un escaner
dentro de la aplicacion. Es una decision deliberada: un escaner propio usaria
`getUserMedia`, que los navegadores solo permiten sobre HTTPS o localhost. Desde
un telefono real apuntando a `http://192.168.x.x:8000` la camara quedaria
bloqueada y el flujo no funcionaria.
"""
import socket
from io import BytesIO
from pathlib import Path

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas as pdf_canvas
from reportlab.lib.utils import ImageReader

from backend.core.config import settings
from backend.core.tiempo import ahora


def detectar_ip_lan() -> str:
    """IP del servidor dentro de la red local.

    Se abre un socket UDP hacia una direccion externa (no se envia nada) solo
    para que el sistema operativo revele que interfaz de red usaria. Es mas
    fiable que `gethostbyname(gethostname())`, que en Windows suele devolver
    127.0.0.1 y dejaria los QR apuntando al propio telefono.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        # Sin red: los QR solo serviran desde la misma maquina.
        return "127.0.0.1"
    finally:
        sock.close()


def url_base() -> str:
    """Direccion que se incrusta en los QR."""
    if settings.BASE_URL:
        return settings.BASE_URL.rstrip("/")
    return f"http://{detectar_ip_lan()}:{settings.PUERTO}"


def url_habitacion(numero: str) -> str:
    """Enlace directo a una habitacion: al abrirlo, la app muestra sus botones
    de estado."""
    return f"{url_base()}/?hab={numero}"


def generar_qr_png(contenido: str, tamano_caja: int = 10) -> bytes:
    """Devuelve la imagen PNG del QR en memoria."""
    qr = qrcode.QRCode(
        version=None,
        # Correccion de errores alta: un QR pegado en la puerta de una
        # habitacion se ensucia y se raya, y aun asi debe leerse.
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=tamano_caja,
        border=2,
    )
    qr.add_data(contenido)
    qr.make(fit=True)

    imagen = qr.make_image(fill_color="#5A4351", back_color="white")
    buffer = BytesIO()
    imagen.save(buffer, format="PNG")
    return buffer.getvalue()


def generar_hoja_pdf(habitaciones: list[dict]) -> Path:
    """Hoja imprimible con un QR por habitacion, para pegar en las puertas.

    Se entrega como PDF y no como pagina HTML porque las imagenes de una pagina
    web no pueden enviar el token de sesion en la cabecera; el PDF viaja por el
    mismo canal autenticado que los reportes.
    """
    destino = settings.REPORTES_DIR / f"codigos-qr-{ahora().strftime('%Y%m%d-%H%M%S')}.pdf"
    lienzo = pdf_canvas.Canvas(str(destino), pagesize=A4)
    ancho_pagina, alto_pagina = A4

    COLUMNAS = 3
    FILAS = 4
    POR_PAGINA = COLUMNAS * FILAS
    LADO_QR = 4.2 * cm
    MARGEN_X = 1.8 * cm
    MARGEN_SUPERIOR = 3.2 * cm
    PASO_X = (ancho_pagina - 2 * MARGEN_X) / COLUMNAS
    PASO_Y = 6.4 * cm

    base = url_base()

    for indice, habitacion in enumerate(habitaciones):
        posicion = indice % POR_PAGINA

        if posicion == 0:
            if indice > 0:
                lienzo.showPage()
            # Encabezado de pagina
            lienzo.setFont("Helvetica-Bold", 16)
            lienzo.setFillColor(colors.HexColor("#E8489E"))
            lienzo.drawString(MARGEN_X, alto_pagina - 1.8 * cm, "Cattleya-Flow")
            lienzo.setFont("Helvetica", 9)
            lienzo.setFillColor(colors.HexColor("#5A4351"))
            lienzo.drawString(
                MARGEN_X,
                alto_pagina - 2.3 * cm,
                "Codigos QR por habitacion - pegar en la puerta. Escanear con la camara del celular.",
            )
            lienzo.setFont("Helvetica", 7)
            lienzo.setFillColor(colors.HexColor("#B08A9C"))
            lienzo.drawString(MARGEN_X, alto_pagina - 2.7 * cm, f"Servidor: {base}")

        columna = posicion % COLUMNAS
        fila = posicion // COLUMNAS
        x = MARGEN_X + columna * PASO_X
        y = alto_pagina - MARGEN_SUPERIOR - (fila + 1) * PASO_Y + 1.2 * cm

        # Marco de recorte
        lienzo.setStrokeColor(colors.HexColor("#F3D9E6"))
        lienzo.setLineWidth(0.5)
        lienzo.roundRect(x - 0.3 * cm, y - 0.9 * cm, PASO_X - 0.4 * cm, PASO_Y - 0.6 * cm, 6, stroke=1, fill=0)

        # QR
        png = generar_qr_png(url_habitacion(habitacion["numero"]), tamano_caja=8)
        lienzo.drawImage(
            ImageReader(BytesIO(png)),
            x + 0.35 * cm,
            y,
            width=LADO_QR,
            height=LADO_QR,
            preserveAspectRatio=True,
        )

        # Numero de habitacion
        lienzo.setFont("Helvetica-Bold", 20)
        lienzo.setFillColor(colors.HexColor("#E8489E"))
        lienzo.drawCentredString(x + 0.35 * cm + LADO_QR / 2, y + LADO_QR + 0.35 * cm, str(habitacion["numero"]))

        # Piso y tipo
        lienzo.setFont("Helvetica", 8)
        lienzo.setFillColor(colors.HexColor("#B08A9C"))
        lienzo.drawCentredString(
            x + 0.35 * cm + LADO_QR / 2,
            y - 0.45 * cm,
            f"Piso {habitacion['floor']} - {habitacion['type']}",
        )

    lienzo.showPage()
    lienzo.save()
    return destino
