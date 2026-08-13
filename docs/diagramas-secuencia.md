# Diagramas de Secuencia — Cattleya-Flow

Los seis casos de uso, con los nombres de los participantes tal como se
implementaron. En el documento original varios bloques Mermaid estaban
incompletos (cortados a media línea); aquí están completos y renderizables.

---

## CU-01 · Autenticarse en el Sistema — Bolaños Melanie

```mermaid
sequenceDiagram
    actor Usuario
    participant Frontend
    participant AuthController
    participant AuthService
    participant UsuarioBD as Usuario (BD)
    participant HistorialAccion

    Usuario ->> Frontend: ingresarCredenciales(email, password)
    Frontend ->> AuthController: POST /api/auth/login
    AuthController ->> AuthService: login(email, password)
    AuthService ->> UsuarioBD: buscarPorEmail(email)
    UsuarioBD -->> AuthService: Usuario | null

    alt credenciales inválidas
        AuthService -->> Frontend: 401 Credenciales incorrectas
        Frontend -->> Usuario: Mostrar error
    else cuenta desactivada
        AuthService -->> Frontend: 403 Cuenta desactivada
        Frontend -->> Usuario: Contactar administrador
    else credenciales válidas
        AuthService ->> AuthService: bcrypt.compare(password, passwordHash)
        AuthService ->> AuthService: generarJWT(id, rol)
        AuthService ->> HistorialAccion: registrar("login", "Usuario", id)
        AuthService -->> Frontend: { token, rol, nombre, navegacion }
        opt primer login
            Frontend -->> Usuario: Avisar cambio de contraseña
        end
        Frontend -->> Usuario: Redirigir a panel según rol
    end
```

> **Nota:** la verificación de `activo` ocurre después de comprobar la
> contraseña. Al revés, permitiría averiguar qué correos están registrados.

---

## CU-02 · Cambiar Estado de Habitación — Damian Emily

```mermaid
sequenceDiagram
    actor Personal
    participant Camara as Cámara del celular
    participant Frontend
    participant HabitacionController
    participant HabitacionService
    participant Habitacion
    participant RegistroLimpieza
    participant HistorialAccion
    participant WebSocket
    participant Recepcion

    Personal ->> Camara: escanearQR(codigoHabitacion)
    Camara -->> Frontend: abrir http://servidor:8000/?hab=101
    Frontend ->> HabitacionController: GET /api/habitaciones/numero/101
    HabitacionController ->> HabitacionService: obtenerPorNumero(numero, rol)
    HabitacionService -->> Frontend: Habitacion + estadosValidos para ese rol
    Frontend -->> Personal: Mostrar habitación y botones aplicables

    Personal ->> Frontend: seleccionarNuevoEstado(estado)
    Frontend ->> HabitacionController: PATCH /api/habitaciones/{id}/estado
    HabitacionController ->> HabitacionService: cambiarEstado(id, estado, usuario)
    HabitacionService ->> Habitacion: buscarPorId(id)

    alt habitación no encontrada
        HabitacionService -->> Frontend: 404 Habitación no existe
        Frontend -->> Personal: Mostrar error
    else habitación encontrada
        HabitacionService ->> Habitacion: validarTransicion(actual, nuevo, rol)
        Habitacion -->> HabitacionService: Boolean

        alt transición inválida
            HabitacionService -->> Frontend: 422 + estadosValidos
            Frontend -->> Personal: Mostrar estados válidos
        else transición válida
            opt estado = En Limpieza
                HabitacionService ->> RegistroLimpieza: crear(horaInicio, usuario, habitacion)
            end
            opt estado = Lista
                HabitacionService ->> RegistroLimpieza: registrarFin(horaFin, "Lista")
                RegistroLimpieza -->> HabitacionService: calcularDuracion()
            end
            HabitacionService ->> Habitacion: cambiarEstado(nuevoEstado, usuario)
            HabitacionService ->> HistorialAccion: registrar("cambiarEstado", "Habitacion", id)
            HabitacionService -)WebSocket: broadcast(habitacionId, nuevoEstado)
            HabitacionService -->> Frontend: 200 OK, estado actualizado
            Frontend -->> Personal: Confirmar cambio
            WebSocket -->> Recepcion: actualizar panel (< 5 seg)
        end
    end
```

El `broadcast` es asíncrono (`-)`): el personal recibe su confirmación sin
esperar a que todos los clientes conectados acusen recibo.

---

## CU-03 · Consultar Panel de Disponibilidad — Guaraca Dayana

```mermaid
sequenceDiagram
    actor Recepcionista
    participant Frontend
    participant HabitacionController
    participant HabitacionRepository
    participant WebSocket

    Recepcionista ->> Frontend: acceder a Panel de Disponibilidad
    Frontend ->> HabitacionController: GET /api/habitaciones
    HabitacionController ->> HabitacionRepository: obtenerTodas(filtros)
    HabitacionRepository -->> HabitacionController: List~Habitacion~
    HabitacionController -->> Frontend: [{id, numero, piso, tipo, estado}]
    Frontend -->> Recepcionista: Renderizar grid con colores

    opt filtrar por piso o tipo
        Recepcionista ->> Frontend: aplicarFiltro(piso, tipo)
        Frontend ->> HabitacionController: GET /api/habitaciones?piso=X&tipo=Y
        alt sin resultados
            Frontend -->> Recepcionista: No hay habitaciones con ese filtro
        else con resultados
            Frontend -->> Recepcionista: Actualizar grid filtrado
        end
    end

    Frontend ->> WebSocket: suscribirse("habitaciones")
    WebSocket -->> Frontend: conexión establecida

    loop actualización en tiempo real
        WebSocket -)Frontend: habitacionActualizada(id, nuevoEstado)
        Frontend -->> Recepcionista: Actualizar color en grid
    end

    alt pérdida de conexión WS
        loop máx 3 intentos de reconexión
            Frontend ->> WebSocket: reconectar()
        end
        Frontend -->> Recepcionista: Modo sin tiempo real
    end
```

---

## CU-04 · Generar Reportes de Productividad — Martinez Jostin

```mermaid
sequenceDiagram
    actor Admin
    participant Frontend
    participant ReporteController
    participant ReporteService
    participant RegistroLimpieza
    participant GeneradorArchivo

    Admin ->> Frontend: seleccionar(periodo, tipo, formato)
    Frontend ->> ReporteController: POST /api/reportes

    alt formato inválido
        ReporteController -->> Frontend: 400 Formato no soportado
        Frontend -->> Admin: Mostrar opciones válidas
    else formato válido
        ReporteController ->> ReporteService: solicitar(periodo, tipo, formato)
        ReporteController -->> Frontend: 202 Accepted, reporteId

        ReporteController -)ReporteService: generarArchivo(reporteId) [ASYNC]
        ReporteService ->> RegistroLimpieza: buscarPorPeriodo(fechaInicio, fechaFin)
        RegistroLimpieza -->> ReporteService: List~RegistroLimpieza~
        ReporteService ->> ReporteService: calcularMetricas(registros)
        ReporteService ->> GeneradorArchivo: exportar(metricas, formato)
        GeneradorArchivo -->> ReporteService: archivo generado

        loop hasta que esté listo
            Frontend ->> ReporteController: GET /api/reportes/{id}
            ReporteController -->> Frontend: { estado, listo }
        end

        Frontend ->> ReporteController: GET /api/reportes/{id}/descargar
        ReporteController -->> Frontend: archivo PDF/Excel
        Frontend -->> Admin: Iniciar descarga
    end
```

---

## CU-05 · Gestionar Usuarios — Oñate Leonel

```mermaid
sequenceDiagram
    actor Admin
    participant Frontend
    participant UsuarioController
    participant UsuarioService
    participant Usuario
    participant HistorialAccion
    participant SMTP

    Admin ->> Frontend: completar formulario(nombre, email, rol)
    Frontend ->> UsuarioController: POST /api/usuarios
    UsuarioController ->> UsuarioService: crear(nombre, email, rol, autor)
    UsuarioService ->> Usuario: buscarPorEmail(email)

    alt email duplicado
        Usuario -->> UsuarioService: Usuario (existente)
        UsuarioService -->> Frontend: 409 Email ya registrado
        Frontend -->> Admin: Mostrar error
    else email disponible
        Usuario -->> UsuarioService: null
        UsuarioService ->> UsuarioService: bcrypt.hash(passwordTemporal)
        UsuarioService ->> Usuario: crear(nombre, email, hash, rol)
        UsuarioService ->> HistorialAccion: registrar("crear", "Usuario", id)
        UsuarioController -)SMTP: enviarBienvenida(email, passwordTemporal) [ASYNC]
        UsuarioController -->> Frontend: 201 Created
        Frontend -->> Admin: Usuario creado exitosamente
    end

    alt modificar rol
        Admin ->> Frontend: cambiarRol(nuevoRol)
        Frontend ->> UsuarioController: PATCH /api/usuarios/{id}/rol
        UsuarioController ->> Usuario: cambiarRol(nuevoRol)
        UsuarioController ->> HistorialAccion: registrar("modificar", "Usuario", id)
        UsuarioController -->> Frontend: 200 OK
    end

    alt desactivar cuenta
        Admin ->> Frontend: desactivar(usuarioId)
        Frontend ->> UsuarioController: PATCH /api/usuarios/{id} {activo: false}
        UsuarioController ->> Usuario: activo = false
        UsuarioController ->> HistorialAccion: registrar("desactivar", "Usuario", id)
        UsuarioController -->> Frontend: 200 OK
    end
```

El envío del correo es asíncrono (`-)`): si el servidor SMTP está caído, el
usuario igual se crea. De lo contrario, el SMTP sería un punto único de fallo
para dar de alta personal.

---

## CU-06 · Consultar Historial de Limpieza — Oñate Leonel

```mermaid
sequenceDiagram
    actor Supervisor
    participant Frontend
    participant HistorialController
    participant HistorialService
    participant RegistroLimpieza
    participant HistorialAccion

    Supervisor ->> Frontend: ingresar filtros(habitacion, desde, hasta)
    Frontend ->> HistorialController: GET /api/historial?habitacion=X&desde=Y&hasta=Z
    HistorialController ->> HistorialService: consultar(habitacion, desde, hasta)
    HistorialService ->> RegistroLimpieza: buscarPorHabitacion(id, fechaInicio, fechaFin)

    alt historial vacío
        RegistroLimpieza -->> HistorialService: []
        HistorialService -->> Frontend: { registros: [], total: 0 }
        Frontend -->> Supervisor: Sin registros. Ampliar rango de fechas
    else registros encontrados
        RegistroLimpieza -->> HistorialService: List~RegistroLimpieza~
        HistorialService ->> HistorialAccion: buscarPorEntidad("Habitacion", id)
        HistorialAccion -->> HistorialService: List~HistorialAccion~
        HistorialService -->> Frontend: { registros, historial }
        Frontend -->> Supervisor: Tabla con personal, horas, duración

        opt ver detalle de registro
            Supervisor ->> Frontend: clickRegistro(id)
            Frontend ->> HistorialController: GET /api/historial/registro/{id}
            HistorialController -->> Frontend: registro + observaciones
            Frontend -->> Supervisor: Modal con detalles completos
        end

        opt exportar registro
            Supervisor ->> Frontend: exportar(formato)
            Frontend ->> HistorialController: GET /api/historial/exportar?formato=PDF
            HistorialController ->> RegistroLimpieza: exportar()
            HistorialController -->> Frontend: archivo
            Frontend -->> Supervisor: Descargar archivo
        end
    end
```
