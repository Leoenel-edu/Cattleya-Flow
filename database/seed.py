"""Carga los datos iniciales del sistema.

    python -m database.seed          crea la BD si no existe y la puebla
    python -m database.seed --reset  borra todo y vuelve a empezar

Genera las 24 habitaciones del Hotel Cattleya Real, los usuarios del equipo y
un historial de limpiezas del dia para que los reportes tengan algo que medir
desde el primer arranque.
"""
import argparse
import random
from datetime import datetime, time, timedelta

from backend.core.database import Base, SessionLocal, crear_tablas, engine
from backend.core.security import hashear_password
from backend.core.tiempo import ahora
from backend.models import (
    EstadoHabitacion,
    Habitacion,
    HistorialAccion,
    RegistroLimpieza,
    Rol,
    Usuario,
)

# --- Usuarios del equipo (contrasenas de demostracion) ---
USUARIOS = [
    ("Melanie", "Bolanos", "admin@hotel.com", Rol.ADMIN, "admin123"),
    ("Ana", "Recepcion", "recepcion@hotel.com", Rol.RECEPCION, "recep123"),
    ("Emily", "Damian", "emily@hotel.com", Rol.LIMPIEZA, "emily123"),
    ("Jostin", "Martinez", "jostin@hotel.com", Rol.LIMPIEZA, "jostin123"),
    ("Leonel", "Onate", "leonel@hotel.com", Rol.LIMPIEZA, "leonel123"),
    ("Carmen", "Auxiliar", "carmen@hotel.com", Rol.LIMPIEZA, "carmen123"),
]

# Habitaciones: 4 pisos x 6 habitaciones, igual que el demo original.
TIPOS_POR_PISO = {
    1: ["Doble", "Individual", "Matrimonial", "Doble", "Individual", "Matrimonial"],
    2: ["Triple", "Triple", "Matrimonial", "Doble", "Individual", "Matrimonial"],
    3: ["Triple", "Triple", "Matrimonial", "Doble", "Individual", "Matrimonial"],
    4: ["Cuadruple", "Triple", "Doble", "Doble", "Individual", "Matrimonial"],
}

# Estado inicial por habitacion, replicando la distribucion del demo.
ESTADOS_INICIALES = {
    "101": "dirty",   "102": "clean",   "103": "cleaning", "104": "clean",   "105": "dirty",   "106": "clean",
    "201": "cleaning","202": "dirty",   "203": "clean",    "204": "dirty",   "205": "clean",   "206": "clean",
    "301": "dirty",   "302": "clean",   "303": "cleaning", "304": "clean",   "305": "dirty",   "306": "clean",
    "401": "clean",   "402": "dirty",   "403": "cleaning", "404": "clean",   "405": "dirty",   "406": "clean",
}


def reset() -> None:
    print("Borrando el esquema anterior...")
    Base.metadata.drop_all(bind=engine)


def poblar() -> None:
    crear_tablas()
    db = SessionLocal()

    try:
        if db.query(Usuario).count() > 0:
            print("La base de datos ya tiene datos. Usa --reset para regenerarla.")
            return

        # ------------------------------------------------------- usuarios
        usuarios: dict[str, Usuario] = {}
        for nombre, apellido, email, rol, password in USUARIOS:
            usuario = Usuario(
                nombre=nombre,
                apellido=apellido,
                email=email,
                passwordHash=hashear_password(password),
                rol=rol.value,
                activo=email != "carmen@hotel.com",  # Carmen inactiva, como en el demo
            )
            db.add(usuario)
            usuarios[email] = usuario
        db.flush()
        print(f"  {len(usuarios)} usuarios creados")

        # --------------------------------------------------- habitaciones
        habitaciones: dict[str, Habitacion] = {}
        for piso, tipos in TIPOS_POR_PISO.items():
            for indice, tipo in enumerate(tipos, start=1):
                numero = f"{piso}0{indice}"
                habitacion = Habitacion(
                    numero=numero,
                    piso=piso,
                    tipo=tipo,
                    estado=ESTADOS_INICIALES.get(numero, EstadoHabitacion.SUCIA.value),
                )
                db.add(habitacion)
                habitaciones[numero] = habitacion
        db.flush()
        print(f"  {len(habitaciones)} habitaciones creadas")

        # ------------------------------------------- registros de limpieza
        # Historial del dia: alimenta los reportes de productividad para que la
        # pantalla no aparezca vacia en la primera demostracion.
        personal = [
            usuarios["emily@hotel.com"],
            usuarios["jostin@hotel.com"],
            usuarios["leonel@hotel.com"],
        ]
        hoy = ahora().date()
        aleatorio = random.Random(42)  # semilla fija: datos reproducibles
        registros = 0

        for numero, habitacion in habitaciones.items():
            if habitacion.estado == EstadoHabitacion.LISTA.value:
                # Limpieza completada: registro cerrado con duracion realista.
                empleado = personal[aleatorio.randrange(len(personal))]
                inicio = datetime.combine(hoy, time(7, 20)) + timedelta(
                    minutes=aleatorio.randrange(0, 90)
                )
                duracion = aleatorio.randrange(32, 52)
                db.add(
                    RegistroLimpieza(
                        horaInicio=inicio,
                        horaFin=inicio + timedelta(minutes=duracion),
                        estadoFinal=EstadoHabitacion.LISTA.value,
                        observaciones="",
                        usuario_id=empleado.id,
                        habitacion_id=habitacion.id,
                    )
                )
                registros += 1

            elif habitacion.estado == EstadoHabitacion.EN_LIMPIEZA.value:
                # Limpieza en curso: registro abierto, sin horaFin.
                # Es lo que permite que marcarla como "Lista" cierre el registro
                # existente en vez de crear uno nuevo.
                empleado = personal[aleatorio.randrange(len(personal))]
                inicio = ahora() - timedelta(minutes=aleatorio.randrange(5, 25))
                db.add(
                    RegistroLimpieza(
                        horaInicio=inicio,
                        horaFin=None,
                        estadoFinal=EstadoHabitacion.EN_LIMPIEZA.value,
                        observaciones="",
                        usuario_id=empleado.id,
                        habitacion_id=habitacion.id,
                    )
                )
                registros += 1

        db.flush()
        print(f"  {registros} registros de limpieza creados")

        # ------------------------------------------------------ auditoria
        db.add(
            HistorialAccion(
                accion="seed",
                entidadAfectada="Sistema",
                entidadId=0,
                usuario_id=usuarios["admin@hotel.com"].id,
                detalle="Carga inicial de datos del Hotel Cattleya Real",
            )
        )

        db.commit()

        print("\nBase de datos lista.\n")
        print("  Credenciales de acceso")
        print("  " + "-" * 52)
        for nombre, apellido, email, rol, password in USUARIOS:
            estado = "" if email != "carmen@hotel.com" else "  (cuenta desactivada)"
            print(f"  {rol.value:11} {email:24} {password}{estado}")
        print()

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carga los datos iniciales de Cattleya-Flow")
    parser.add_argument("--reset", action="store_true", help="Borra la base de datos y la recrea")
    args = parser.parse_args()

    if args.reset:
        reset()
    poblar()
