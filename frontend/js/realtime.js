/* =============================================================
   realtime.js - Suscripcion a los cambios de "habitaciones" (CU-03).

   Antes esto era un WebSocket propio (/ws/habitaciones); ahora se
   suscribe directo a Supabase Realtime, que empuja cada UPDATE de la
   tabla "habitaciones" apenas el backend lo confirma en la base de
   datos (RNF-04: propagacion en menos de 5 segundos).

   Implementa el mismo loop de reconexion del diagrama original:
   maximo 3 intentos y, si fallan, se pasa a "modo sin tiempo real"
   en lugar de reintentar para siempre.
   ============================================================= */

const Realtime = (() => {
  const MAX_INTENTOS = 3;
  const ESPERA_MS = 2000;
  const CDN_SUPABASE = 'https://esm.sh/@supabase/supabase-js@2';

  let cliente = null;
  let canal = null;
  let intentos = 0;
  let cerradoAdrede = false;
  let segundosDesdeCambio = 0;
  let cronometro = null;

  /** Crea (una sola vez) el cliente de Supabase con la config publica que
   *  expone el backend. Si no hay credenciales configuradas, el sistema
   *  sigue funcionando sin tiempo real (solo hay que recargar a mano). */
  async function obtenerCliente() {
    if (cliente) return cliente;

    const config = await fetch('/api/config').then((r) => r.json());
    if (!config.supabaseUrl || !config.supabaseAnonKey) return null;

    const { createClient } = await import(CDN_SUPABASE);
    cliente = createClient(config.supabaseUrl, config.supabaseAnonKey);
    return cliente;
  }

  async function conectar() {
    cerradoAdrede = false;

    const sb = await obtenerCliente();
    if (!sb) {
      marcarEnVivo(false);
      return;
    }

    canal = sb
      .channel('habitaciones-cambios')
      .on(
        'postgres_changes',
        { event: 'UPDATE', schema: 'public', table: 'habitaciones' },
        (payload) => alRecibirCambio(payload.new)
      )
      .subscribe((status) => {
        if (status === 'SUBSCRIBED') {
          intentos = 0;
          marcarEnVivo(true);
        } else if (status === 'CHANNEL_ERROR' || status === 'TIMED_OUT' || status === 'CLOSED') {
          marcarEnVivo(false);
          if (!cerradoAdrede) reconectar();
        }
      });
  }

  /* loop [max 3 intentos de reconexion] */
  function reconectar() {
    if (intentos >= MAX_INTENTOS) {
      UI.toast('Sin conexión en tiempo real. Recarga la página.', 'warn');
      return;
    }
    intentos++;
    setTimeout(() => {
      if (!cerradoAdrede) {
        canal?.unsubscribe();
        conectar();
      }
    }, ESPERA_MS * intentos); // espera creciente: 2s, 4s, 6s
  }

  /** Llega un cambio de estado: se refresca lo que el usuario esta viendo.
   *  `habitacion` es la fila cruda de Postgres (id, numero, piso, tipo,
   *  estado...); las pantallas que necesitan el detalle completo (nombres
   *  de estado, empleado) vuelven a pedirlo al backend en vez de duplicar
   *  esa logica de serializacion aqui. */
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
    canal?.unsubscribe();
    canal = null;
  }

  return { iniciar, detener, reiniciarContador: () => (segundosDesdeCambio = 0) };
})();
