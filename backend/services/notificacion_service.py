"""Servicio de notificaciones.

Cubre la dependencia RegistroLimpieza -> Notificacion del diagrama de clases:
"un registro produce notificaciones al completarse".
"""
from sqlalchemy.orm import Session

from backend.models.notificacion import Notificacion


class NotificacionService:
    def __init__(self, db: Session):
        self.db = db

    def crear(self, mensaje: str, tipo: str = "info", usuario_id: int | None = None) -> Notificacion:
        """Usa la fabrica `createNotificacion(msg, tipo)` de la entidad.

        No hace commit: la notificacion se confirma con la transaccion que la
        origino (el cambio de estado), no por separado.
        """
        notificacion = Notificacion.createNotificacion(mensaje, tipo)
        notificacion.usuario_id = usuario_id
        self.db.add(notificacion)
        return notificacion

    def enviar(self, usuario_id: int, mensaje: str, tipo: str = "info") -> Notificacion:
        """`enviar(usuario): void` del diagrama.

        Aqui la notificacion se persiste y el frontend la recoge; el envio por
        correo lo hace SMTPService.
        """
        notificacion = self.crear(mensaje, tipo, usuario_id)
        self.db.commit()
        return notificacion

    def listarNoLeidas(self, usuario_id: int) -> list[Notificacion]:
        return list(
            self.db.query(Notificacion)
            .filter(
                Notificacion.usuario_id == usuario_id,
                Notificacion.leida.is_(False),
            )
            .order_by(Notificacion.fecha.desc())
            .all()
        )

    def marcarLeida(self, notificacion_id: int) -> None:
        notificacion = self.db.get(Notificacion, notificacion_id)
        if notificacion is not None:
            notificacion.marcarLeida()
            self.db.commit()
