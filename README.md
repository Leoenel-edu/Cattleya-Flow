# Cattleya-Flow

**Sistema de Gestión de Limpieza Hotelera — Hotel Cattleya Real**

Plataforma web para la gestión de estados de habitaciones y optimización del
ciclo de limpieza en tiempo real.

| | |
|---|---|
| **Carrera** | Ciencia de Datos e Inteligencia Artificial (CDIA) — Quinto "A" |
| **Período** | P-2026S1 |
| **Asignatura** | Ingeniería de Software |
| **Integrantes** | Bolaños Melanie · Damian Emily · Guaraca Dayana · Martinez Jostin · Oñate Leonel |

---

## 1. Cómo ejecutarlo

Requisitos: **Python 3.11 o superior**. No hace falta instalar base de datos:
SQLite viene incluido en Python.

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Crear la base de datos con los datos iniciales
python -m database.seed

# 3. Arrancar el servidor
python run.py
```

Abre **http://127.0.0.1:8000** en el navegador.

La documentación interactiva del API (generada automáticamente) está en
**http://127.0.0.1:8000/docs**.

### Credenciales de prueba

| Rol | Correo | Contraseña |
|---|---|---|
| Administrador | `admin@hotel.com` | `admin123` |
| Supervisor | `supervisor@hotel.com` | `super123` |
| Recepción | `recepcion@hotel.com` | `recep123` |
| Personal de Limpieza | `emily@hotel.com` | `emily123` |
| Personal de Limpieza | `jostin@hotel.com` | `jostin123` |
| Personal de Limpieza | `leonel@hotel.com` | `leonel123` |
| Personal de Limpieza | `carmen@hotel.com` | `carmen123` (cuenta desactivada) |

La cuenta de Carmen está desactivada a propósito: sirve para demostrar el flujo
alternativo *[cuenta desactivada]* de CU-01, que responde 403.

### Comandos útiles

```bash
python -m database.seed --reset      # borra la BD y la vuelve a crear
python -m tests.verificar_sistema    # verifica los 6 casos de uso automáticamente
```

La verificación ejercita cada caso de uso con todos sus flujos alternativos
(401, 403, 404, 409, 422) y comprueba que los reportes PDF/Excel se generan de
verdad. Es la evidencia del método **[P] Prueba** de la matriz de requisitos.
Al terminar, ejecuta `python -m database.seed --reset` para restaurar los datos.

---

## 2. Demostrar el tiempo real (RNF-04)

El requisito exige que un cambio de estado se vea en todos los clientes en
menos de 5 segundos. Para mostrarlo:

1. Abre **dos navegadores distintos** (por ejemplo Chrome y Firefox), o una
   ventana normal y otra de incógnito.
2. En uno entra como **Recepción**; en el otro como **Personal de Limpieza**.
3. Desde limpieza, cambia el estado de una habitación.
4. El panel de recepción se actualiza **solo**, sin recargar la página.

> **Importante:** dos pestañas del *mismo* navegador comparten `localStorage`,
> así que comparten la sesión. Para ver dos roles a la vez hacen falta dos
> navegadores o una ventana de incógnito.

La propagación es por WebSocket: el servidor empuja el evento en cuanto ocurre,
por lo que la latencia real es de milisegundos.

---

## 3. Códigos QR por habitación (CU-02)

El personal escanea el QR pegado en la puerta y la aplicación abre **esa**
habitación con sus botones de estado listos. Es el mensaje `escanearQR(codigoHabitacion)`
con el que arranca el diagrama de secuencia de CU-02.

### Cómo usarlo

1. Entra como **Administrador** o **Supervisor**.
2. En el Panel, pulsa **📱 Imprimir códigos QR** → descarga un PDF con los 24
   códigos, uno por habitación.
3. Imprime y pega cada código en su puerta.
4. El personal lo escanea **con la cámara normal del celular** (la que ya trae
   el teléfono). Se abre la app en esa habitación.

> No hace falta pulsar nada dentro de la app para escanear: el QR es la
> *entrada* a la aplicación, no una función interna. El botón **📷 Escanear** de
> la barra superior solo explica el procedimiento y ofrece el respaldo manual.

### El botón "📷 Escanear"

Está en la barra superior y lo ven **todos los roles**. Al pulsarlo muestra:

- Las instrucciones para escanear con la cámara del celular.
- Un campo para **escribir el número de habitación** (ej. `203`) y abrir la
  misma pantalla.

El respaldo manual existe por tres razones concretas: un QR puede despegarse o
mancharse, el celular puede quedarse sin batería en plena jornada, y **Recepción
no tiene la pantalla "Cambiar Estado"** en su menú — sin este botón, su única vía
para registrar un check-out sería el QR.

### Por qué no hay un escáner dentro de la app

El QR no guarda un número suelto: guarda una URL
(`http://192.168.x.x:8000/?hab=101`). Así la lee la cámara nativa de cualquier
teléfono, sin instalar nada.

Un escáner propio necesitaría `getUserMedia`, que los navegadores **solo
permiten sobre HTTPS o localhost**. Desde un celular real apuntando a
`http://192.168.x.x:8000` la cámara quedaría bloqueada y el flujo no
funcionaría en la demostración. Esta solución cumple lo mismo y no depende de
certificados.

### Detalles

- La dirección de los QR se detecta sola: el sistema busca su **IP en la red
  local**, así que los códigos funcionan desde cualquier celular conectado a la
  misma WiFi, aunque el administrador haya abierto la app en `localhost`.
- Los botones que aparecen al escanear son **solo las transiciones válidas para
  ese rol**. Si la habitación está *Sucia*, sale únicamente *Limpiando*. Si el
  personal de limpieza escanea una habitación *Lista*, se le avisa que su rol no
  puede cambiarla (el check-out es de recepción).
- Para publicarlo en un dominio real, fija `CATTLEYA_BASE_URL` en el `.env`.

### Requisito: abrir el puerto en el firewall (una sola vez)

Para que el celular alcance el servidor hacen falta **dos** cosas. La primera ya
viene resuelta: `run.py` publica el servidor en `0.0.0.0`, es decir, en todas las
interfaces de red. Atado a `127.0.0.1` solo respondería a la propia computadora y
los QR no abrirían nada.

La segunda hay que hacerla a mano: **Windows Defender bloquea el puerto 8000**.
Sin una regla que lo permita, el teléfono se queda cargando indefinidamente.

Abre **PowerShell como Administrador** (clic derecho → *Ejecutar como
administrador*) y ejecuta:

```powershell
New-NetFirewallRule -DisplayName "Cattleya-Flow (puerto 8000)" `
  -Direction Inbound -Protocol TCP -LocalPort 8000 `
  -Action Allow -Profile Any -RemoteAddress LocalSubnet
```

`-RemoteAddress LocalSubnet` limita el acceso a los dispositivos de la misma red
local. Sin esa restricción, el puerto quedaría abierto a cualquier red a la que
te conectes después.

Para quitar la regla cuando ya no la necesites:

```powershell
Remove-NetFirewallRule -DisplayName "Cattleya-Flow (puerto 8000)"
```

### Si aun así el celular no abre nada

| Síntoma | Causa probable | Solución |
|---|---|---|
| Safari se queda cargando | Falta la regla del firewall | Ejecutar el comando de arriba |
| "No se puede conectar al servidor" | El celular está en otra red (datos móviles, WiFi de invitados) | Misma WiFi, y desactivar datos móviles |
| Funciona en la laptop pero no en el celular | La red aísla los dispositivos entre sí (*AP isolation*, común en WiFi de universidades y de invitados) | Usar un punto de acceso móvil: comparte internet desde el celular y conecta la laptop a él |
| El QR apunta a `127.0.0.1` | El sistema no detectó la IP de red | Fijar `CATTLEYA_BASE_URL` en el `.env` |

Comprueba la dirección desde el propio celular abriendo
`http://<ip-que-imprime-run.py>:8000` en Safari. Si esa página carga, los QR
funcionarán.

> **Para la demostración en clase:** la WiFi de una universidad casi siempre
> aísla los dispositivos entre sí. Lo más seguro es llevar tu propio punto de
> acceso: activa el hotspot del celular, conecta la laptop a ese hotspot, y
> vuelve a generar la hoja de QR (la IP cambia con la red).

---

## 4. Arquitectura

Estilo arquitectónico: **por capas (Layered / N-Tier)**, tal como se definió en
el taller de arquitectura. Cada capa solo conoce la inmediatamente inferior.

```
┌──────────────────────────────────────────────────┐
│  PRESENTACIÓN                                    │
│  frontend/            interfaz (HTML/CSS/JS)     │
│  backend/api/         controladores REST         │
│  backend/realtime/    WebSocket (tiempo real)    │
├──────────────────────────────────────────────────┤
│  LÓGICA DE NEGOCIO                               │
│  backend/services/    reglas del dominio         │
├──────────────────────────────────────────────────┤
│  ACCESO A DATOS                                  │
│  backend/repositories/  consultas                │
│  backend/models/        entidades                │
├──────────────────────────────────────────────────┤
│  PERSISTENCIA                                    │
│  database/            SQLite                     │
└──────────────────────────────────────────────────┘
```

La separación es real, no solo de carpetas:

- Los **servicios** no importan nada de FastAPI. Lanzan excepciones de negocio
  (`TransicionInvalida`, `EmailDuplicado`) y es la capa de presentación la que
  las traduce a códigos HTTP. Por eso la lógica podría reutilizarse desde un
  script o una tarea programada sin cambiar una línea.
- Los servicios **no escriben consultas**: piden datos a un repositorio.
- Las **reglas del dominio viven en las entidades**. `validarTransicion()` está
  en la clase `Habitacion`, no en el controlador, tal como impone el diagrama
  de clases.

### Estructura de carpetas

```
Cattleya-Flow/
├── backend/
│   ├── main.py                  ensamblaje de la aplicación
│   ├── core/                    configuración, BD, seguridad, tiempo
│   ├── models/                  las 6 entidades del diagrama de clases
│   ├── schemas/                 contratos de entrada/salida (Pydantic)
│   ├── repositories/            acceso a datos
│   ├── services/                lógica de negocio (un módulo por caso de uso)
│   ├── api/routes/              controladores REST
│   └── realtime/                gestor de WebSocket
├── frontend/
│   ├── index.html
│   ├── css/styles.css
│   ├── js/                      un módulo por pantalla
│   └── assets/                  imágenes
├── database/
│   ├── seed.py                  datos iniciales
│   └── cattleya.db              (se genera al ejecutar el seed)
├── storage/reportes/            reportes PDF/Excel generados
├── docs/                        documentación técnica
├── requirements.txt
└── run.py                       punto de arranque
```

---

## 5. Los 6 casos de uso

| CU | Nombre | Responsable | Backend | Frontend |
|---|---|---|---|---|
| CU-01 | Autenticarse | Bolaños Melanie | `auth_service.py` | `auth.js` |
| CU-02 | Cambiar estado de habitación | Damian Emily | `habitacion_service.py` | `cambiar.js` |
| CU-03 | Consultar panel de disponibilidad | Guaraca Dayana | `habitacion_service.py` | `panel.js` |
| CU-04 | Generar reportes de productividad | Martinez Jostin | `reporte_service.py` | `reportes.js` |
| CU-05 | Gestionar usuarios | Oñate Leonel | `usuario_service.py` | `usuarios.js` |
| CU-06 | Consultar historial de limpieza | Oñate Leonel | `historial_service.py` | `historial.js` |

Cada flujo alternativo de los diagramas de secuencia está implementado y
devuelve el código HTTP correspondiente. Ver [docs/trazabilidad.md](docs/trazabilidad.md).

---

## 6. La máquina de estados

`Habitacion.validarTransicion()` implementa el ciclo de limpieza:

```
   ┌──────────────────────────────────────┐
   │                                      │
   ▼                                      │
 SUCIA ──────► EN LIMPIEZA ──────► LISTA ─┘
                    │                  (check-out: solo
                    │                   recepción/supervisor/admin)
                    ▼
                  SUCIA
            (limpieza interrumpida)
```

Reglas y su porqué:

| Transición | ¿Permitida? | Motivo |
|---|---|---|
| Sucia → En Limpieza | Sí | Inicio normal del ciclo. Abre un `RegistroLimpieza`. |
| En Limpieza → Lista | Sí | Fin del ciclo. Cierra el registro y calcula la duración. |
| En Limpieza → Sucia | Sí | La limpieza puede interrumpirse. |
| **Sucia → Lista** | **No** | Es el caso que el documento cita como transición inválida. Sin pasar por *En Limpieza* no habría `horaInicio`, y el reporte de productividad no podría calcular la duración. |
| **Lista → Sucia** | **Solo recepción / supervisor / admin** | Representa el *check-out* del huésped, no un paso del ciclo de limpieza. El personal de limpieza no decide cuándo se ensucia una habitación: eso lo sabe recepción. |

> **Nota sobre una decisión de diseño:** el documento presenta *Lista → Sucia*
> como ejemplo de transición inválida. Interpretarlo de forma literal y
> absoluta dejaría al sistema sin ninguna forma de devolver una habitación al
> ciclo tras un check-out. Por eso se permite, pero restringida por rol. La
> restricción que el documento describe (que limpieza no salte pasos) se
> mantiene intacta.

---

## 7. Seguridad

- **Contraseñas con bcrypt** (RNF-02). En la base de datos no hay ni una
  contraseña en texto plano; bcrypt incluye un salt aleatorio en cada hash.
- **Email cifrado con AES-256-GCM** (RNF-02, "datos sensibles"). El correo se
  guarda cifrado en la columna `emailCifrado`; en la BD no aparece ningún email
  legible. Como AES-GCM usa un nonce aleatorio, el mismo correo produce un
  cifrado distinto cada vez — por eso el login y la detección de duplicados
  buscan por `emailIndice`, un HMAC-SHA256 determinista del correo (un "índice
  ciego": permite localizar la fila sin poder revertirse para recuperar el
  email). Ver `backend/core/crypto.py`.
- **Sesiones con JWT** firmado (CU-01). Todo endpoint exige token válido
  (RF-01), salvo el propio login.
- **Permisos por rol** (RF-06) verificados **en el servidor**. El prototipo
  original tenía un desplegable de rol en el login; se eliminó porque permitía
  entrar como Administrador con solo elegirlo en el navegador. Ahora el rol lo
  determina la cuenta.
- **Auditoría** (RNF-06): cada acción que modifica datos escribe en
  `HistorialAccion` con marca de tiempo y autor.
- El menú lateral lo construye el backend según el rol; el frontend solo dibuja
  lo que recibe.

### Antes de usarlo en producción

1. Cambia `CATTLEYA_SECRET_KEY` en el `.env` por una clave larga y aleatoria.
2. Quita `passwordTemporal` de la respuesta de `POST /api/usuarios`
   (`backend/api/routes/usuario_controller.py`). Hoy se devuelve solo porque el
   envío de correo está en modo simulado.
3. Configura un servidor SMTP real en `backend/services/smtp_service.py`.
4. Restringe `allow_origins` del CORS en `backend/main.py`.

---

## 8. Migrar a PostgreSQL

El documento especifica PostgreSQL. El proyecto usa SQLite para que arranque sin
instalar nada, pero el cambio no toca el diseño por capas:

```bash
pip install psycopg[binary]
```

En el `.env`:

```
CATTLEYA_DATABASE_URL=postgresql+psycopg://usuario:clave@localhost:5432/cattleya
```

Y ejecutar `python -m database.seed`. Nada más: los repositorios usan SQLAlchemy,
que abstrae el motor. Esa es precisamente la ventaja de la arquitectura por capas
que se argumentó en el taller.

---

## 9. Notas técnicas

**Manejo del tiempo.** Todo el sistema usa hora local del hotel sin zona horaria
(`backend/core/tiempo.py`). Las columnas `DateTime` de SQLite no guardan zona, y
mezclar fechas con y sin zona provoca el error
*"can't subtract offset-naive and offset-aware datetimes"*. Ningún módulo llama
a `datetime.now()` directamente; todos usan `ahora()`.

**El WebSocket y los hilos.** FastAPI ejecuta los endpoints declarados `def` en
un hilo del threadpool, donde no existe un bucle de eventos. Por eso el bucle
principal se registra al arrancar (`manager.registrar_loop`) y el broadcast se
publica con `run_coroutine_threadsafe`. Sin esto, los cambios se guardaban en la
base de datos pero no llegaban a ningún cliente.

**Reconexión.** Si se pierde la conexión en tiempo real, el cliente reintenta
3 veces con espera creciente (2s, 4s, 6s) y luego avisa al usuario, tal como
modela el `loop [max 3 intentos]` del diagrama de CU-03.
