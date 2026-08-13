/* =============================================================
   cambiar.js - CU-02: Cambiar Estado de Habitacion.
   ============================================================= */

const Cambiar = (() => {
  let habitaciones = [];

  async function cargar() {
    try {
      const datos = await API.habitaciones();
      habitaciones = datos.habitaciones;
      pintar();
    } catch (error) {
      UI.toast(error.message, 'danger');
    }
  }

  function pintar() {
    const grid = document.getElementById('change-grid');
    grid.innerHTML = habitaciones.map(tarjeta).join('');

    grid.querySelectorAll('.status-btn').forEach((boton) => {
      boton.addEventListener('click', () =>
        cambiar(Number(boton.dataset.id), boton.dataset.estado)
      );
    });
  }

  function tarjeta(hab) {
    const botones = [
      { estado: 'dirty',    icono: '🔴', texto: 'Sucia',     clase: 'dirty-btn' },
      { estado: 'cleaning', icono: '🧹', texto: 'Limpiando', clase: 'cleaning-btn' },
      { estado: 'clean',    icono: '✅', texto: 'Lista',     clase: 'clean-btn' },
    ]
      .map(
        (b) => `<button class="status-btn ${b.clase} ${hab.status === b.estado ? 'current-status' : ''}"
                  data-id="${hab.id}" data-estado="${b.estado}">
                  <span>${b.icono}</span>${b.texto}
                </button>`
      )
      .join('');

    return `<div class="change-card">
      <div class="change-card-header">
        <div>
          <div class="change-room-num">${UI.escapar(hab.numero)}</div>
          <div class="change-room-info">Piso ${hab.floor} · ${UI.escapar(hab.type)}</div>
        </div>
        <span class="room-status-badge badge-${hab.status}">${UI.escapar(hab.statusLabel)}</span>
      </div>
      <div class="status-buttons">${botones}</div>
    </div>`;
  }

  async function cambiar(id, nuevoEstado) {
    const hab = habitaciones.find((h) => h.id === id);
    if (!hab || hab.status === nuevoEstado) return;

    try {
      const respuesta = await API.cambiarEstado(id, nuevoEstado);
      const actualizada = respuesta.habitacion;

      UI.toast(
        `Hab. ${actualizada.numero}: ${UI.ETIQUETAS_ESTADO[hab.status]} → ${actualizada.statusLabel}`,
        nuevoEstado === 'clean' ? 'success' : nuevoEstado === 'dirty' ? 'danger' : 'warn'
      );

      // No se recarga la lista: el broadcast del WebSocket llega enseguida
      // y dispara el refresco. Recargar aqui duplicaria la peticion.
    } catch (error) {
      // alt [transicion invalida] -> 422 con los estados validos
      if (error.status === 422 && error.datos.estadosValidosEtiquetas) {
        const validos = error.datos.estadosValidosEtiquetas;
        // La lista llega vacia cuando el rol no puede hacer ningun cambio
        // desde ese estado (limpieza sobre una habitacion ya Lista). Anunciar
        // "Estados válidos:" sin nada detras confundiria mas que ayudar.
        UI.toast(
          validos.length
            ? `${error.message}. Estados válidos: ${validos.join(' o ')}`
            : `${error.message}. Tu rol no puede cambiar esta habitación.`,
          'danger'
        );
      } else {
        UI.toast(error.message, 'danger');
      }
      cargar(); // resincroniza por si el estado local quedo desfasado
    }
  }

  return { cargar };
})();
