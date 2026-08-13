# Trazabilidad: del requisito al código

Este documento conecta cada requisito de la matriz ISO/IEC/IEEE 29148 y cada
flujo de los diagramas de secuencia con el archivo que lo implementa.

---

## 1. Requisitos Funcionales

| ID | Requisito | Implementación | Cómo verificarlo |
|---|---|---|---|
| RF-01 | Login con contraseña encriptada antes de entrar | `core/security.py` (bcrypt) · `api/deps.py` (`usuario_actual`) | Llamar a `GET /api/habitaciones` sin token → 401 |
| RF-02 | Panel de recepción con estados en tiempo real | `services/habitacion_service.py:listar` · `frontend/js/panel.js` · `realtime/websocket_manager.py` | Dos navegadores: cambiar estado en uno, ver el otro actualizarse |
| RF-03 | Personal de limpieza cambia estado desde el móvil | `services/habitacion_service.py:cambiarEstado` · `frontend/js/cambiar.js` | CSS responsive; entrar con `emily@hotel.com` |
| RF-04 | Guardar quién limpió y a qué hora empezó/terminó | `models/registro_limpieza.py` · `habitacion_service.cambiarEstado` | Marcar una habitación como Lista y revisar Historial |
| RF-05 | Reportes PDF y Excel con métricas | `services/generador_archivo.py` · `services/reporte_service.py` | Botones "Exportar Excel/PDF" en Reportes |
| RF-06 | Roles con permisos diferenciados | `models/enums.py:NAVEGACION_POR_ROL` · `api/deps.py:requiere_roles` | Entrar como limpieza: no aparece Reportes ni Usuarios |
| RF-07 | Admin crea, modifica y desactiva usuarios | `services/usuario_service.py` · `frontend/js/usuarios.js` | Pantalla "Gestionar Usuarios" |

## 2. Requisitos No Funcionales

| ID | Requisito | Implementación | Cómo verificarlo |
|---|---|---|---|
| RNF-01 | Funciona en móviles y tablets sin zoom | `frontend/css/styles.css` (media queries, sidebar plegable) | Reducir la ventana a 375 px |
| RNF-02 | Contraseñas con bcrypt **y** datos sensibles con AES-256 | `core/security.py:hashear_password` (contraseñas) · `core/crypto.py` (email) | Abrir la BD: `passwordHash` empieza por `$2b$`; `emailCifrado` es ilegible, no aparece ningún `@hotel.com` en la tabla `usuarios` |
| RNF-03 | Disponibilidad del 99% | Manejo de errores por capas; los fallos de un módulo no tumban el servidor | Los errores de negocio devuelven HTTP, no excepciones sin capturar |
| RNF-04 | Propagación en menos de 5 segundos | `realtime/websocket_manager.py` | Log: `Broadcast 'habitacionActualizada' a N cliente(s)` |
| RNF-05 | 50 usuarios concurrentes, respuesta ≤ 2 s | Consultas indexadas; `joinedload` evita el problema N+1 | `repositories/registro_repository.py:_consultaBase` |
| RNF-06 | Historial de 12 meses para auditoría | `models/historial_accion.py` · `config.py:RETENCION_HISTORIAL_MESES` | Tabla `historial_acciones` |
| RNF-07 | Arquitectura Frontend / Backend / BD separada | Estructura de carpetas + separación real de capas | Ver README sección 4 |

## 3. Requisitos de Negocio y de Stakeholder

| ID | Requisito | Implementación |
|---|---|---|
| RB-01 | Asignar habitaciones 40% más rápido | Panel en tiempo real: recepción ve la disponibilidad sin llamar por teléfono |
| RB-02 | Reportes de productividad | `services/reporte_service.py:calcularMetricas` |
| RS-01 | Recepción ve en tiempo real cuándo está lista | WebSocket + `panel.js` |
| RS-02 | Admin descarga Excel mensual | `GET /api/reportes/metricas?periodo=mes` + exportar |
| RS-03 | Supervisor sabe quién limpió y a qué hora | `services/historial_service.py` (CU-06) |

---

## 4. Diagramas de secuencia: flujos alternativos

Cada `alt` y `opt` de los diagramas está implementado y devuelve su código HTTP.

### CU-01 · Autenticarse — Bolaños Melanie

| Flujo | Código | Implementación |
|---|---|---|
| Principal | 200 | `auth_service.py:login` |
| alt [credenciales inválidas] | 401 | `errors.py:CredencialesInvalidas` |
| alt [cuenta desactivada] | 403 | `errors.py:CuentaDesactivada` |
| opt [primer login] | flag | `login()` devuelve `primerLogin` |

**Decisión:** la cuenta desactivada se comprueba *después* de la contraseña. Si
fuera antes, cualquiera podría descubrir qué correos existen probando al azar.

### CU-02 · Cambiar Estado — Damian Emily

| Flujo | Código | Implementación |
|---|---|---|
| **escanearQR(codigoHabitacion)** | 200 | `qr_service.py` + `GET /api/habitaciones/numero/{numero}` · `frontend/js/qr.js` |
| Principal | 200 | `habitacion_service.py:cambiarEstado` |
| alt [transición inválida] | 422 | `errors.py:TransicionInvalida` (incluye `estadosValidos`) |
| alt [habitación no encontrada] | 404 | `errors.py:NoEncontrado` |
| opt [estado = Lista] | — | `registro.registrarFin()` + `Notificacion` |
| broadcast asíncrono | — | `notificar_cambio_estado()` |

**Sobre el QR:** el diagrama modela `escanearQR` como una acción del actor sobre
la AppMovil. Se implementó con la cámara nativa del celular en vez de un escáner
propio: el QR codifica la URL `http://servidor:8000/?hab=101`, que el teléfono
abre directamente. Un escáner dentro de la app requeriría `getUserMedia`, que los
navegadores solo habilitan sobre HTTPS, y desde un celular apuntando a una IP
local por HTTP quedaría bloqueado. Ver README sección 3.

### CU-03 · Panel de Disponibilidad — Guaraca Dayana

| Flujo | Implementación |
|---|---|
| Principal | `habitacion_service.py:listar` |
| opt [filtrar por piso o tipo] | `habitacion_repository.py:obtenerTodas(filtros)` — filtra en la capa de datos |
| alt [sin resultados] | `panel.js` muestra "No hay habitaciones con ese filtro" |
| loop [actualización en tiempo real] | `realtime.js:onmessage` |
| loop [máx 3 intentos de reconexión] | `realtime.js:reconectar` |

### CU-04 · Reportes — Martinez Jostin

| Flujo | Código | Implementación |
|---|---|---|
| Principal | 202 | `reporte_controller.py:solicitar` |
| alt [sin registros en el período] | — | `calcularMetricas` devuelve ceros; la pantalla muestra "Sin datos" |
| alt [formato inválido] | 400 | `errors.py:FormatoInvalido` |
| opt [filtrar por empleado] | — | parámetro `usuarioId` |
| exportar asíncrono (-)) | — | `BackgroundTasks` + polling |

**Decisión:** el diagrama devuelve 404 cuando no hay registros. Aquí se devuelven
métricas en cero, porque un período sin limpiezas es un resultado legítimo, no un
error; la pantalla lo indica con un mensaje.

### CU-05 · Gestionar Usuarios — Oñate Leonel

| Flujo | Código | Implementación |
|---|---|---|
| Principal (crear) | 201 | `usuario_service.py:crear` |
| alt [email duplicado] | 409 | `errors.py:EmailDuplicado` — validación *fail-fast* antes de escribir en BD |
| alt [modificar rol] | 200 | `usuario_service.py:cambiarRol` |
| alt [desactivar cuenta] | 200 | `usuario_service.py:cambiarActivo` (borrado lógico) |
| SMTP asíncrono (-)) | — | `BackgroundTasks` + `smtp_service.py` |

**Protecciones añadidas:** un administrador no puede desactivarse a sí mismo ni
quitarse el rol de admin. Ambas acciones lo dejarían fuera del sistema sin forma
de revertirlo desde la interfaz.

### CU-06 · Historial — Oñate Leonel

| Flujo | Implementación |
|---|---|
| Principal | `historial_service.py:consultar` — consulta `RegistroLimpieza` **e** `HistorialAccion` |
| alt [historial vacío] | Tabla con mensaje "Sin registros para ese filtro" |
| opt [exportar registro] | `GET /api/historial/exportar?formato=pdf` |
| opt [ver detalle de registro] | `GET /api/historial/registro/{id}` → modal |

---

## 5. Diagrama de clases → código

| Clase | Archivo | Métodos implementados |
|---|---|---|
| `Usuario` | `models/usuario.py` | `validarCredenciales()`, `cambiarRol()` |
| `Habitacion` | `models/habitacion.py` | `validarTransicion()`, `cambiarEstado()`, `obtenerHistorial()` |
| `RegistroLimpieza` | `models/registro_limpieza.py` | `calcularDuracion()`, `registrarFin()` |
| `HistorialAccion` | `models/historial_accion.py` | `registrar()`, `buscarPorEntidad()` |
| `Reporte` | `models/reporte.py` | `generar()`, `calcularMetricas()`, `exportar()` (en `reporte_service.py`) |
| `Notificacion` | `models/notificacion.py` | `createNotificacion()`, `enviar()`, `marcarLeida()` |

`login()` y `logout()` figuran en la clase `Usuario` del diagrama, pero se
implementan en `AuthService`: generar un JWT y escribir en la auditoría son
responsabilidades de un servicio, no de una entidad de datos. La entidad conserva
`validarCredenciales()`, que sí es suya.

### Relaciones

| Relación | Tipo | Implementación |
|---|---|---|
| Usuario → RegistroLimpieza | Asociación 1..0..* | `usuario.registros` |
| Habitacion → RegistroLimpieza | Composición 1..0..* | `habitacion.registros` con `cascade="all, delete-orphan"` |
| Usuario → HistorialAccion | Asociación 1..0..* | `usuario.acciones` |
| RegistroLimpieza → Notificacion | Dependencia | `NotificacionService.crear()` desde `cambiarEstado` |
| Reporte → RegistroLimpieza | Dependencia | `reporte_service.calcularMetricas()` |
