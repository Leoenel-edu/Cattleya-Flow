"""Verificacion automatica de los 6 casos de uso.

    python -m tests.verificar_sistema

Levanta la aplicacion en memoria (sin abrir un puerto) y ejercita cada caso de
uso con sus flujos alternativos. Sirve como evidencia del metodo [P] Prueba de
la matriz de requisitos.

AVISO: escribe sobre la base de datos configurada. Ejecuta despues
`python -m database.seed --reset` para dejarla en su estado inicial.
"""
import sys

from fastapi.testclient import TestClient

from backend.main import app

cliente = TestClient(app)
fallos: list[str] = []


def check(nombre: str, condicion: bool, detalle="") -> None:
    marca = "OK   " if condicion else "FALLA"
    extra = f"  -> {detalle}" if not condicion and detalle else ""
    print(f"  {marca}  {nombre}{extra}")
    if not condicion:
        fallos.append(nombre)


def seccion(titulo: str) -> None:
    print(f"\n--- {titulo} ---")


def main() -> int:
    # -------------------------------------------------- RNF-02 (AES-256)
    seccion("RNF-02 Cifrado de datos sensibles")
    import sqlite3

    from backend.core.config import settings

    ruta_db = settings.DATABASE_URL.replace("sqlite:///", "")
    con = sqlite3.connect(ruta_db)
    filas = con.execute("SELECT emailCifrado, emailIndice FROM usuarios").fetchall()
    con.close()

    check("hay usuarios para verificar", len(filas) > 0, len(filas))
    check(
        "ningun email aparece en claro en la BD",
        all("@" not in cifrado for cifrado, _ in filas),
        "se encontro un '@' en emailCifrado",
    )
    check(
        "el indice de busqueda no es el email (es un hash)",
        all("@" not in indice and len(indice) == 64 for _, indice in filas),
        "emailIndice deberia ser un hash hex de 64 caracteres",
    )

    from backend.core.crypto import cifrar, descifrar, indice_busqueda

    c1, c2 = cifrar("prueba@hotel.com"), cifrar("prueba@hotel.com")
    check("AES-256: el mismo texto cifra distinto cada vez (nonce)", c1 != c2, f"{c1[:20]} == {c2[:20]}")
    check("AES-256: ambos cifrados descifran al original", descifrar(c1) == descifrar(c2) == "prueba@hotel.com")
    check(
        "indice ciego: mismo email (normalizado) -> mismo hash",
        indice_busqueda("Admin@Hotel.com") == indice_busqueda(" admin@hotel.com "),
    )

    # ---------------------------------------------------------- CU-01
    seccion("CU-01 Autenticacion")
    r = cliente.post("/api/auth/login", json={"email": "admin@hotel.com", "password": "admin123"})
    check("login correcto -> 200", r.status_code == 200, r.text[:120])
    if r.status_code != 200:
        print("\nNo se pudo iniciar sesion. Ejecuta: python -m database.seed")
        return 1

    token = r.json()["token"]
    check("devuelve token JWT", len(token) > 20)
    check(
        "navegacion segun rol (RF-06)",
        r.json()["navegacion"] == ["panel", "cambiar", "historial", "reportes", "usuarios"],
        r.json()["navegacion"],
    )

    r = cliente.post("/api/auth/login", json={"email": "admin@hotel.com", "password": "incorrecta"})
    check("alt [credenciales invalidas] -> 401", r.status_code == 401, r.status_code)

    r = cliente.post("/api/auth/login", json={"email": "carmen@hotel.com", "password": "carmen123"})
    check("alt [cuenta desactivada] -> 403", r.status_code == 403, r.status_code)

    check("sin token no hay acceso (RF-01)", cliente.get("/api/habitaciones").status_code == 401)

    admin = {"Authorization": f"Bearer {token}"}

    # ---------------------------------------------------------- CU-03
    seccion("CU-03 Panel de Disponibilidad")
    r = cliente.get("/api/habitaciones", headers=admin)
    check("lista habitaciones -> 200", r.status_code == 200)
    datos = r.json()
    check("24 habitaciones", len(datos["habitaciones"]) == 24, len(datos["habitaciones"]))
    check("estadisticas coherentes", datos["estadisticas"]["total"] == 24, datos["estadisticas"])
    r = cliente.get("/api/habitaciones?piso=2", headers=admin)
    check("opt [filtrar por piso] -> 6", len(r.json()["habitaciones"]) == 6)

    # ---------------------------------------------------------- CU-02
    seccion("CU-02 Cambiar Estado (validarTransicion)")
    sucia = next(h for h in datos["habitaciones"] if h["status"] == "dirty")

    r = cliente.patch(f"/api/habitaciones/{sucia['id']}/estado", json={"estado": "clean"}, headers=admin)
    check("Sucia -> Lista prohibida -> 422", r.status_code == 422, r.status_code)
    check("422 informa estados validos", "estadosValidos" in r.json())

    r = cliente.patch(f"/api/habitaciones/{sucia['id']}/estado", json={"estado": "cleaning"}, headers=admin)
    check("Sucia -> En Limpieza -> 200", r.status_code == 200, r.text[:120])

    r = cliente.patch(f"/api/habitaciones/{sucia['id']}/estado", json={"estado": "clean"}, headers=admin)
    check("En Limpieza -> Lista -> 200", r.status_code == 200, r.text[:120])
    if r.status_code == 200:
        hab = r.json()["habitacion"]
        check("registra empleado y horas (RF-04)", bool(hab["employee"] and hab["timeStart"] and hab["timeEnd"]), hab)

    r = cliente.patch("/api/habitaciones/99999/estado", json={"estado": "cleaning"}, headers=admin)
    check("alt [habitacion no encontrada] -> 404", r.status_code == 404, r.status_code)

    # Restriccion de check-out por rol
    r = cliente.post("/api/auth/login", json={"email": "emily@hotel.com", "password": "emily123"})
    limpieza = {"Authorization": f"Bearer {r.json()['token']}"}
    lista = next(h for h in cliente.get("/api/habitaciones", headers=admin).json()["habitaciones"] if h["status"] == "clean")
    r = cliente.patch(f"/api/habitaciones/{lista['id']}/estado", json={"estado": "dirty"}, headers=limpieza)
    check("limpieza no hace check-out -> 422", r.status_code == 422, r.status_code)
    r = cliente.patch(f"/api/habitaciones/{lista['id']}/estado", json={"estado": "dirty"}, headers=admin)
    check("admin si hace check-out -> 200", r.status_code == 200, r.status_code)

    # ------------------------------------------------- CU-02 escanearQR
    seccion("CU-02 Codigos QR (escanearQR)")
    from backend.services.qr_service import generar_qr_png, url_habitacion

    enlace = url_habitacion("101")
    check("el QR codifica una URL abrible", enlace.startswith("http") and "?hab=101" in enlace, enlace)
    check("no apunta a localhost (funciona desde el celular)", "127.0.0.1" not in enlace, enlace)
    check("genera imagen PNG", generar_qr_png(enlace)[:4] == b"\x89PNG")

    r = cliente.get("/api/habitaciones/numero/101", headers=limpieza)
    check("resolver habitacion escaneada -> 200", r.status_code == 200, r.text[:120])
    if r.status_code == 200:
        escaneada = r.json()
        check("devuelve la habitacion correcta", escaneada["numero"] == "101", escaneada.get("numero"))
        check("indica los estados validos para el rol", "estadosValidos" in escaneada)
        check(
            "solo ofrece transiciones aplicables",
            all(e in ("dirty", "cleaning", "clean") for e in escaneada["estadosValidos"]),
            escaneada["estadosValidos"],
        )

    check(
        "QR de habitacion inexistente -> 404",
        cliente.get("/api/habitaciones/numero/999", headers=limpieza).status_code == 404,
    )

    r = cliente.get("/api/habitaciones/qr/hoja", headers=admin)
    check("hoja PDF imprimible", r.status_code == 200 and r.content[:4] == b"%PDF", f"{r.status_code} {len(r.content)}b")
    check(
        "limpieza no imprime la hoja -> 403",
        cliente.get("/api/habitaciones/qr/hoja", headers=limpieza).status_code == 403,
    )

    # ---------------------------------------------------------- CU-06
    seccion("CU-06 Historial")
    r = cliente.get("/api/historial", headers=admin)
    check("consulta historial -> 200", r.status_code == 200)
    check("devuelve registros e historial", "registros" in r.json() and "historial" in r.json())
    check("hay registros", r.json()["total"] > 0, r.json()["total"])

    # ---------------------------------------------------------- CU-04
    seccion("CU-04 Reportes")
    r = cliente.get("/api/reportes/metricas?periodo=hoy", headers=admin)
    check("metricas -> 200", r.status_code == 200)
    metricas = r.json()
    check("calcula tiempo promedio", metricas["tiempoPromedio"] > 0, metricas["tiempoPromedio"])
    check("eficiencia en rango 50-100", 50 <= metricas["eficienciaGlobal"] <= 100, metricas["eficienciaGlobal"])

    r = cliente.get("/api/reportes/exportar?periodo=hoy&formato=excel", headers=admin)
    check("descarga Excel real", r.status_code == 200 and len(r.content) > 3000, f"{r.status_code} {len(r.content)}b")

    r = cliente.get("/api/reportes/exportar?periodo=hoy&formato=pdf", headers=admin)
    check("descarga PDF real", r.status_code == 200 and r.content[:4] == b"%PDF", r.content[:8])

    r = cliente.get("/api/reportes/exportar?periodo=hoy&formato=word", headers=admin)
    check("alt [formato invalido] -> 400", r.status_code == 400, r.status_code)

    # ---------------------------------------------------------- CU-05
    seccion("CU-05 Gestionar Usuarios")
    check("admin lista usuarios", cliente.get("/api/usuarios", headers=admin).status_code == 200)
    check("limpieza no accede (RF-06) -> 403", cliente.get("/api/usuarios", headers=limpieza).status_code == 403)

    import uuid

    correo = f"prueba-{uuid.uuid4().hex[:8]}@hotel.com"
    r = cliente.post(
        "/api/usuarios",
        json={"nombre": "Prueba", "apellido": "Automatica", "email": correo, "rol": "limpieza"},
        headers=admin,
    )
    check("crear usuario -> 201", r.status_code == 201, r.text[:120])
    nuevo_id = r.json()["usuario"]["id"] if r.status_code == 201 else None

    r = cliente.post(
        "/api/usuarios",
        json={"nombre": "Otro", "apellido": "X", "email": correo, "rol": "limpieza"},
        headers=admin,
    )
    check("alt [email duplicado] -> 409", r.status_code == 409, r.status_code)

    if nuevo_id:
        check(
            "alt [modificar rol] -> 200",
            cliente.patch(f"/api/usuarios/{nuevo_id}/rol", json={"rol": "supervisor"}, headers=admin).status_code == 200,
        )
        r = cliente.patch(f"/api/usuarios/{nuevo_id}", json={"activo": False}, headers=admin)
        check("alt [desactivar cuenta] -> 200", r.status_code == 200 and r.json()["usuario"]["active"] is False)

    check(
        "admin no puede autodesactivarse",
        cliente.patch("/api/usuarios/1", json={"activo": False}, headers=admin).status_code == 400,
    )

    # ---------------------------------------------- Tiempo real (RNF-04)
    seccion("Configuracion de tiempo real (RNF-04)")
    config = cliente.get("/api/config").json()
    check("expone supabaseUrl", "supabaseUrl" in config)
    check("expone supabaseAnonKey", "supabaseAnonKey" in config)

    # ------------------------------------------------------- resumen
    print("\n" + "=" * 56)
    if fallos:
        print(f"FALLARON {len(fallos)} verificacion(es):")
        for f in fallos:
            print(f"   - {f}")
        return 1

    print("TODAS LAS VERIFICACIONES PASARON")
    print("\nRecuerda: python -m database.seed --reset  para restaurar los datos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
