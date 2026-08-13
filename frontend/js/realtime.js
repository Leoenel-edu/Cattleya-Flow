/* =============================================================
   realtime.js - Suscripcion al canal "habitaciones" (CU-03).

   Implementa el loop de reconexion del diagrama de secuencia:
   maximo 3 intentos y, si fallan, se pasa a "modo sin tiempo real"
   en lugar de reintentar para siempre.
   ============================================================= */

const Realtime = (() => {
  const MAX_INTENTOS = 3;
  const ESPERA_MS = 2000;

  let socket = null;
  let intentos = 0;
  let cerradoAdrede = false;
  let segundosDesdeCambio = 0;
  let cronometro = null;

  function urlCanal() {
    const protocolo = location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocolo}//${location.host}/ws/habitaciones`;
  }

  function conectar() {
    cerradoAdrede = false;
    socket = new WebSocket(urlCanal());

    socket.onopen = () => {
      intentos = 0;
      marcarEnVivo(true);
    };

    socket.onmessage = (evento) => {
      let mensaje;
      try {
        mensaje = JSON.parse(evento.data);
      } catch {
        return; // mensaje ilegible: se ignora en vez de romper el canal
      }

      if (mensaje.evento === 'habitacionActualizada') {
        alRecibirCambio(mensaje.datos);
      }
    };

    socket.onclose = () => {
      marcarEnVivo(false);
      if (!cerradoAdrede) reconectar();
    };

    // No hace falta actuar aqui: a un onerror siempre le sigue un onclose,
    // que es donde vive la logica de reconexion.
    socket.onerror = () => {};
  }

  /* loop [max 3 intentos de reconexion] */
  function reconectar() {
    if (intentos >= MAX_INTENTOS) {
      UI.toast('Sin conexión en tiempo real. Recarga la página.', 'warn');
      return;
    }
    intentos++;
    setTimeout(() => {
      if (!cerradoAdrede) conectar();
    }, ESPERA_MS * intentos); // espera creciente: 2s, 4s, 6s
  }

  /** Llega un cambio de estado: se refresca lo que el usuario esta viendo. */
  function alRecibirCambio(habitacion) {
    segundosDesdeCambio = 0;

    if (UI.pantallaActual === 'panel')     Panel.aplicarCambio(habitacion);
    if (UI.pantallaActual === 'cambiar')   Cambiar.cargar();
    if (UI.pantallaActual === 'historial') Historial.cargar();
    if (UI.pantallaActual === 'reportes')  Reportes.cargar();
  }

  function marcarEnVivo(activo) {
    const insignia = document.getElementById('live-badge');
    if (!insignia) return;
    insignia.style.opacity = activo ? '1' : '0.4';
    insignia.title = activo ? 'Conectado en tiempo real' : 'Sin conexión en tiempo real';
  }

  function iniciar() {
    conectar();
    segundosDesdeCambio = 0;
    cronometro = setInterval(() => {
      segundosDesdeCambio++;
      const el = document.getElementById('last-update');
      if (el) el.textContent = segundosDesdeCambio;
    }, 1000);
  }

  function detener() {
    cerradoAdrede = true;
    clearInterval(cronometro);
    socket?.close();
    socket = null;
  }

  return { iniciar, detener, reiniciarContador: () => (segundosDesdeCambio = 0) };
})();
