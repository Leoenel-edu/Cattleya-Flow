"""Servicio Externo: envio de correo (SMTP).

En CU-05 el correo de bienvenida se envia de forma asincrona (-)) porque
depende de un servidor externo con latencia impredecible: si el SMTP se cae,
la creacion del usuario no debe fallar.

Por defecto opera en modo simulado y escribe el correo en el log, para que el
sistema arranque sin configurar un servidor real. Configura las variables SMTP_*
en el .env para enviar de verdad.
"""
import logging

logger = logging.getLogger(__name__)


class SMTPService:
    """Cliente de correo. Modo simulado mientras no haya credenciales."""

    @staticmethod
    def enviarBienvenida(email: str, passwordTemporal: str, nombre: str = "") -> bool:
        """`enviarBienvenida(email, passwordTemporal)` de CU-05.

        Devuelve True/False en vez de lanzar excepcion: quien la invoca lo hace
        en segundo plano y un fallo aqui no debe afectar al 201 Created ya
        entregado al administrador.
        """
        try:
            logger.info(
                "[SMTP simulado] Bienvenida a %s <%s> | contrasena temporal: %s",
                nombre or email,
                email,
                passwordTemporal,
            )
            # Envio real: descomentar y configurar SMTP_HOST/USER/PASSWORD.
            #
            # import smtplib
            # from email.message import EmailMessage
            # mensaje = EmailMessage()
            # mensaje["Subject"] = "Bienvenido a Cattleya-Flow"
            # mensaje["To"] = email
            # mensaje.set_content(
            #     f"Hola {nombre}, tu contrasena temporal es: {passwordTemporal}"
            # )
            # with smtplib.SMTP(host, port) as servidor:
            #     servidor.starttls()
            #     servidor.login(usuario, clave)
            #     servidor.send_message(mensaje)
            return True
        except Exception as exc:
            logger.error("Fallo el envio de correo a %s: %s", email, exc)
            return False
