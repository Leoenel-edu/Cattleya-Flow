# Guion de Exposición — Cattleya-Flow

**Equipo:** Bolaños Melanie · Damian Emily · Martinez Jostin · Oñate Leonel
**Duración total:** 12 minutos · 4 partes de 3 min c/u

Notas concretas, no un texto para leer. Cada punto es una idea, no un párrafo.

| Parte | Tema | Min |
|---|---|---|
| 1 | Problema y objetivo | 3 |
| 2 | Requisitos, diseño y arquitectura | 3 |
| 3 | Demo en vivo | 3 |
| 4 | Seguridad, pruebas y cierre | 3 |

---

## PARTE 1 — Problema y objetivo

**Mostrar:** login de Cattleya-Flow.

**Problema (3 datos, no historia):**
- Hotel Cattleya Real controla la limpieza en **hojas físicas**
- Sin registro digital → recepción no sabe qué habitación está libre → demoras en check-in
- Sin datos → administración no puede medir tiempo de limpieza por empleado

**Objetivo general:**
> "Automatizar el control del ciclo de limpieza con actualización en tiempo real y trazabilidad completa de cada acción."

**Alcance del proyecto (decirlo así, con números):**
- 18 requisitos documentados bajo ISO/IEC/IEEE 29148
- 6 casos de uso
- 1 sistema funcional, no un prototipo de pantallas sueltas

**Frase de cierre de esta parte:**
> "Todo lo que van a ver corre con datos reales, guardados en una base de datos, no simulados."

---

## PARTE 2 — Requisitos, diseño y arquitectura

**Mostrar:** diagrama de clases + gráfico de arquitectura.

**Cómo se obtuvieron los requisitos:**
- Entrevistas → personal administrativo y recepción
- Encuestas → personal de limpieza
- Hallazgo clave: el personal prefiere el celular, no una computadora → definió que el sistema debe usarse sin hacer zoom

**Diseño (antes de programar):**
- 1 diagrama de clases, 6 entidades: Usuario, Habitación, RegistroLimpieza, HistorialAccion, Reporte, Notificación
- 6 diagramas de secuencia, uno por caso de uso, con flujos alternativos (errores incluidos)
- Regla: cada método del código ya estaba en el diagrama antes de escribirse

**Arquitectura — 3 capas:**
1. Presentación (lo que se ve)
2. Lógica de negocio (las reglas)
3. Acceso a datos + base de datos

> "Cada capa solo depende de la de abajo. Se puede cambiar la base de datos sin tocar el resto del sistema."

**Estimación de esfuerzo:**
- Técnica: descomposición del trabajo (WBS) por fase y módulo
- Total: ~70 horas de equipo

---

## PARTE 3 — Demo en vivo

**Antes:** `INICIAR-SERVIDOR.bat` corriendo, `http://127.0.0.1:8000` abierto, segunda sesión lista (otra pestaña o celular).

**5 pantallas + 4 modales. Recorrido en 6 pasos:**

| Paso | Acción | Qué decir |
|---|---|---|
| 1 | Login admin | "El rol lo decide el servidor, no un menú." |
| 2 | Panel de Habitaciones | "24 habitaciones, se actualiza sola, sin recargar." |
| 3 | Cambiar sesión → Personal de Limpieza → Cambiar Estado | "Solo aparecen los botones que su rol puede usar." |
| 4 | Escanear QR (o escribir número) → cambiar estado | "El QR es un enlace real, no una imagen decorativa." |
| 5 | **Volver a sesión admin** → mostrar Panel actualizado solo | **Momento clave: tiempo real en menos de 5 segundos.** |
| 6 | Reportes → exportar Excel → abrir archivo | "Los números vienen de registros reales, no de una plantilla." |

**Si sobra tiempo:** Usuarios → crear uno → repetir el correo → mostrar que lo rechaza.

**No decir "yo hice esto".** Decir: "el sistema hace esto".

---

## PARTE 4 — Seguridad, pruebas y cierre

**Seguridad — 3 mecanismos, cada uno con su propósito:**

| Mecanismo | Protege | Cómo |
|---|---|---|
| bcrypt | Contraseñas | Hash irreversible, ni el equipo puede leerlas |
| AES-256 | Correo electrónico | Cifrado reversible, estándar bancario |
| JWT | Sesiones | Token firmado, expira en 8 horas |

**Verificación:**
- Suite de 53 pruebas automáticas
- Cubre los 6 casos de uso **y** sus errores (401, 403, 404, 409, 422)
- Resultado: 53/53

**Mostrar:** terminal con `python -m tests.verificar_sistema`, o la captura ya lista.

**Cierre (una sola idea, no discurso):**
> "Cattleya-Flow cubre el ciclo completo: del problema real del hotel, a un sistema verificado con pruebas. Gracias."

---

## Preguntas esperadas — respuesta en una frase

| Pregunta | Respuesta |
|---|---|
| ¿Por qué SQLite y no PostgreSQL? | "No requiere instalación; migrar es cambiar una línea de configuración." |
| ¿El QR funciona de verdad? | "Codifica una URL real; la cámara del celular la abre directo." |
| ¿Qué pasa si dos cambian el mismo estado a la vez? | "El servidor valida contra el estado actual antes de guardar; no hay condiciones de carrera." |
| ¿Cuánto tiempo tomó? | "~70 horas de equipo, estimadas por descomposición del trabajo." |
| ¿Funciona sin internet? | "Corre en la red local del hotel; solo necesita la misma WiFi." |

---

## Checklist antes de exponer

- [ ] `INICIAR-SERVIDOR.bat` corriendo
- [ ] `http://127.0.0.1:8000` carga el login
- [ ] Segunda sesión lista (pestaña/incógnito/celular) para el paso 5 de la demo
- [ ] Terminal lista para `python -m tests.verificar_sistema`
