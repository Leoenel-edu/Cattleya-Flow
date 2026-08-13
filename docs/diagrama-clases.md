# Diagrama de Clases — Cattleya-Flow

Diagrama de clases unificado del sistema. En el documento original el código
Mermaid quedó partido en varios bloques sueltos; aquí está completo y se
renderiza (GitHub, VS Code con extensión Mermaid, o https://mermaid.live).

```mermaid
classDiagram
    class Usuario {
        +int id
        +String nombre
        +String apellido
        +String email
        +String passwordHash
        +String rol
        +Boolean activo
        +DateTime fechaCreacion
        +login(email, password) Token
        +logout(token) void
        +validarCredenciales() Boolean
        +cambiarRol(nuevoRol) void
    }

    class Habitacion {
        +int id
        +String numero
        +int piso
        +String tipo
        +String estado
        +DateTime ultimaActualizacion
        +cambiarEstado(nuevoEstado, usuario) void
        +obtenerHistorial() List~RegistroLimpieza~
        +validarTransicion(estadoActual, estadoNuevo) Boolean
    }

    class RegistroLimpieza {
        +int id
        +DateTime horaInicio
        +DateTime horaFin
        +String estadoFinal
        +String observaciones
        +calcularDuracion() int
        +registrarFin(hora, estado) void
        +exportar() File
    }

    class HistorialAccion {
        +int id
        +String accion
        +DateTime fecha
        +String entidadAfectada
        +int entidadId
        +registrar(accion, entidad, id) void
        +buscarPorEntidad(id) List
        +exportar() File
    }

    class Reporte {
        +int id
        +String tipo
        +DateTime fechaGeneracion
        +String formato
        +String periodo
        +generar(periodo, tipo) Reporte
        +exportar(formato) File
        +calcularMetricas() Map
    }

    class Notificacion {
        +int id
        +String mensaje
        +String tipo
        +DateTime fecha
        +Boolean leida
        +enviar(usuario) void
        +marcarLeida() void
        +createNotificacion(msg, tipo) Notificacion
    }

    Usuario "1" --> "0..*" RegistroLimpieza : realiza
    Habitacion "1" *-- "0..*" RegistroLimpieza : tiene
    Usuario "1" --> "0..*" HistorialAccion : genera
    RegistroLimpieza "1" ..> "0..*" Notificacion : produce
    Reporte "1" ..> "0..*" RegistroLimpieza : consulta
```

## Relaciones

| Relación | Tipo | Multiplicidad | Descripción |
|---|---|---|---|
| Usuario → RegistroLimpieza | Asociación | 1 a 0..* | Un usuario realiza múltiples registros de limpieza |
| Habitacion → RegistroLimpieza | Composición | 1 a 0..* | Una habitación tiene múltiples registros de limpieza |
| Usuario → HistorialAccion | Asociación | 1 a 0..* | Un usuario genera múltiples entradas de historial |
| RegistroLimpieza → Notificacion | Dependencia | 1 a 0..* | Un registro produce notificaciones al completarse |
| Reporte → RegistroLimpieza | Dependencia | 1 a 0..* | Un reporte consulta múltiples registros de limpieza |

**Por qué composición y no agregación** entre `Habitacion` y `RegistroLimpieza`:
un registro de limpieza no tiene sentido sin la habitación a la que pertenece.
En el código esto se traduce en `cascade="all, delete-orphan"`.

---

## Máquina de estados de Habitacion

```mermaid
stateDiagram-v2
    [*] --> Sucia
    Sucia --> EnLimpieza : personal inicia limpieza<br/>(abre RegistroLimpieza)
    EnLimpieza --> Lista : personal termina<br/>(cierra registro, calcula duración)
    EnLimpieza --> Sucia : limpieza interrumpida
    Lista --> Sucia : check-out del huésped<br/>(solo recepción/supervisor/admin)

    note right of Sucia
        Sucia --> Lista está prohibida:
        sin pasar por En Limpieza no hay
        horaInicio y el reporte no podría
        calcular la duración.
    end note
```
