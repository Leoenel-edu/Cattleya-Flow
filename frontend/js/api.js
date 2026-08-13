/* =============================================================
   api.js - Cliente HTTP: unico punto por el que el frontend habla
   con el backend.

   Guarda el token JWT y lo adjunta a cada peticion, de modo que
   ninguna pantalla tenga que preocuparse por la autenticacion.
   ============================================================= */

const API = (() => {
  const CLAVE_TOKEN = 'cattleya_token';

  let token = localStorage.getItem(CLAVE_TOKEN) || null;

  function guardarToken(nuevo) {
    token = nuevo;
    if (nuevo) localStorage.setItem(CLAVE_TOKEN, nuevo);
    else localStorage.removeItem(CLAVE_TOKEN);
  }

  /**
   * Error con el codigo HTTP y los datos extra que envia el backend.
   * Permite que cada pantalla reaccione al caso concreto (422 con
   * estados validos, 409 email duplicado) en vez de a un texto suelto.
   */
  class ErrorAPI extends Error {
    constructor(mensaje, status, datos) {
      super(mensaje);
      this.status = status;
      this.datos = datos || {};
    }
  }

  async function pedir(ruta, opciones = {}) {
    const cabeceras = { ...(opciones.headers || {}) };
    if (opciones.body) cabeceras['Content-Type'] = 'application/json';
    if (token) cabeceras['Authorization'] = `Bearer ${token}`;

    let respuesta;
    try {
      respuesta = await fetch(ruta, { ...opciones, headers: cabeceras });
    } catch (e) {
      // El servidor no respondio (caido, sin red). Sin este caso el
      // usuario solo veria un error de consola.
      throw new ErrorAPI('No se pudo conectar con el servidor', 0);
    }

    if (respuesta.status === 204) return null;

    const tipo = respuesta.headers.get('content-type') || '';
    const cuerpo = tipo.includes('application/json') ? await respuesta.json() : null;

    if (!respuesta.ok) {
      // El token caduco o la cuenta se desactivo: hay que volver al login.
      if (respuesta.status === 401 && token) {
        guardarToken(null);
        window.dispatchEvent(new CustomEvent('sesion-expirada'));
      }
      const mensaje = cuerpo?.detail || `Error ${respuesta.status}`;
      throw new ErrorAPI(
        typeof mensaje === 'string' ? mensaje : 'Datos invalidos',
        respuesta.status,
        cuerpo
      );
    }

    return cuerpo;
  }

  /** Descarga un archivo binario respetando el token de sesion.
   *  Un <a href> normal no puede enviar el header Authorization. */
  async function descargar(ruta, nombreSugerido) {
    const respuesta = await fetch(ruta, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!respuesta.ok) {
      const cuerpo = await respuesta.json().catch(() => ({}));
      throw new ErrorAPI(cuerpo.detail || 'No se pudo descargar', respuesta.status, cuerpo);
    }

    const blob = await respuesta.blob();
    const nombre =
      respuesta.headers
        .get('content-disposition')
        ?.match(/filename="?([^"]+)"?/)?.[1] || nombreSugerido;

    const url = URL.createObjectURL(blob);
    const enlace = document.createElement('a');
    enlace.href = url;
    enlace.download = nombre;
    document.body.appendChild(enlace);
    enlace.click();
    enlace.remove();
    URL.revokeObjectURL(url);
  }

  const json = (datos) => JSON.stringify(datos);

  return {
    ErrorAPI,
    get token() { return token; },
    guardarToken,
    descargar,

    // ------------------------------------------------- CU-01
    login: (email, password) =>
      pedir('/api/auth/login', { method: 'POST', body: json({ email, password }) }),
    logout: () => pedir('/api/auth/logout', { method: 'POST' }),
    perfil: () => pedir('/api/auth/yo'),

    // ------------------------------------------- CU-02 / CU-03
    habitaciones: (filtros = {}) => {
      const q = new URLSearchParams();
      if (filtros.piso) q.set('piso', filtros.piso);
      if (filtros.tipo) q.set('tipo', filtros.tipo);
      if (filtros.estado) q.set('estado', filtros.estado);
      const cadena = q.toString();
      return pedir(`/api/habitaciones${cadena ? '?' + cadena : ''}`);
    },
    cambiarEstado: (id, estado, observaciones = '') =>
      pedir(`/api/habitaciones/${id}/estado`, {
        method: 'PATCH',
        body: json({ estado, observaciones }),
      }),

    // ------------------------------- CU-02: escanearQR(codigoHabitacion)
    habitacionPorNumero: (numero) =>
      pedir(`/api/habitaciones/numero/${encodeURIComponent(numero)}`),
    infoQR: () => pedir('/api/habitaciones/qr/info'),
    descargarHojaQR: () =>
      descargar('/api/habitaciones/qr/hoja', 'codigos-qr-habitaciones.pdf'),

    // ------------------------------------------------- CU-06
    historial: (filtros = {}) => {
      const q = new URLSearchParams();
      if (filtros.habitacion) q.set('habitacion', filtros.habitacion);
      if (filtros.desde) q.set('desde', filtros.desde);
      if (filtros.hasta) q.set('hasta', filtros.hasta);
      const cadena = q.toString();
      return pedir(`/api/historial${cadena ? '?' + cadena : ''}`);
    },
    detalleRegistro: (id) => pedir(`/api/historial/registro/${id}`),
    exportarHistorial: (formato = 'pdf') =>
      descargar(`/api/historial/exportar?formato=${formato}`, `historial.${formato === 'pdf' ? 'pdf' : 'xlsx'}`),

    // ------------------------------------------------- CU-04
    metricas: (periodo = 'hoy') => pedir(`/api/reportes/metricas?periodo=${periodo}`),
    solicitarReporte: (periodo, formato) =>
      pedir('/api/reportes', { method: 'POST', body: json({ periodo, formato, tipo: 'productividad' }) }),
    estadoReporte: (id) => pedir(`/api/reportes/${id}`),
    descargarReporte: (id, formato) =>
      descargar(`/api/reportes/${id}/descargar`, `reporte.${formato === 'pdf' ? 'pdf' : 'xlsx'}`),

    // ------------------------------------------------- CU-05
    usuarios: () => pedir('/api/usuarios'),
    crearUsuario: (datos) => pedir('/api/usuarios', { method: 'POST', body: json(datos) }),
    cambiarRol: (id, rol) =>
      pedir(`/api/usuarios/${id}/rol`, { method: 'PATCH', body: json({ rol }) }),
    cambiarActivo: (id, activo) =>
      pedir(`/api/usuarios/${id}`, { method: 'PATCH', body: json({ activo }) }),
  };
})();
