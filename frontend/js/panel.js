/* =============================================================
   panel.js - CU-03: Consultar Panel de Disponibilidad.
   ============================================================= */

const Panel = (() => {
  let habitaciones = [];
  let filtroActual = 'all';

  /** Traduce el filtro visible a los parametros que entiende el API.
   *  El filtrado se hace en el servidor (capa de datos), no aqui. */
  function filtrosDelBoton(filtro) {
    if (filtro === 'all') return {};
    if (['clean', 'cleaning', 'dirty'].includes(filtro)) return { estado: filtro };
    return { piso: filtro };
  }

  async function cargar() {
    try {
      const datos = await API.habitaciones(filtrosDelBoton(filtroActual));
      habitaciones = datos.habitaciones;
      pintarEstadisticas(datos.estadisticas);
      pintarGrid(habitaciones);
      UI.construirNav(datos.estadisticas.dirty);
      // construirNav redibuja el menu y pierde la marca de pantalla activa.
      document.getElementById('nav-panel')?.classList.add('active');
    } catch (error) {
      UI.toast(error.message, 'danger');
    }
  }

  function pintarEstadisticas(stats) {
    document.getElementById('stat-total').textContent = stats.total;
    document.getElementById('stat-clean').textContent = stats.clean;
    document.getElementById('stat-cleaning').textContent = stats.cleaning;
    document.getElementById('stat-dirty').textContent = stats.dirty;
  }

  function pintarGrid(lista) {
    const grid = document.getElementById('rooms-grid');

    if (lista.length === 0) {
      // alt [sin habitaciones disponibles]
      grid.innerHTML =
        '<div style="grid-column:1/-1;text-align:center;color:var(--muted);padding:30px;">' +
        'No hay habitaciones con ese filtro</div>';
      return;
    }

    grid.innerHTML = lista.map(tarjeta).join('');
    grid.querySelectorAll('.room-card').forEach((card) => {
      card.addEventListener('click', () => abrirDetalle(Number(card.dataset.id)));
    });
  }

  function tarjeta(hab) {
    const clase = { clean: 'badge-clean', cleaning: 'badge-cleaning', dirty: 'badge-dirty' }[hab.status];
    const punto = hab.status === 'cleaning' ? '<div class="pulse-dot"></div>' : '';
    const empleado = hab.employee ? `<div class="room-employee">👤 ${UI.escapar(hab.employee)}</div>` : '';
    const tiempo = hab.timeEnd
      ? `<div class="room-time">✓ Fin: ${hab.timeEnd}</div>`
      : hab.timeStart
      ? `<div class="room-time">⏱ Inicio: ${hab.timeStart}</div>`
      : '';

    return `<div class="room-card ${hab.status}" id="room-card-${hab.id}" data-id="${hab.id}">
      <div class="room-number">${UI.escapar(hab.numero)}</div>
      <div class="room-floor">Piso ${hab.floor} · ${UI.escapar(hab.type)}</div>
      <div class="room-status-badge ${clase}">${punto}${UI.escapar(hab.statusLabel)}</div>
      ${empleado}${tiempo}
    </div>`;
  }

  /** Un cambio llego por Supabase Realtime: se refresca el panel completo.
   *  Recargar es mas simple que parchear la tarjeta y garantiza que las
   *  estadisticas y el badge del menu queden coherentes. */
  async function aplicarCambio(habitacion) {
    await cargar();
    const tarjetaCambiada = document.getElementById(`room-card-${habitacion.id}`);
    if (tarjetaCambiada) {
      tarjetaCambiada.classList.add('just-changed');
      setTimeout(() => tarjetaCambiada.classList.remove('just-changed'), 1200);
    }
    Realtime.reiniciarContador();
  }

  function abrirDetalle(id) {
    const hab = habitaciones.find((h) => h.id === id);
    if (!hab) return;

    document.getElementById('modal-room-title').textContent = `Habitación ${hab.numero}`;
    document.getElementById('modal-room-sub').textContent = `Piso ${hab.floor} · ${hab.type}`;
    document.getElementById('modal-room-body').innerHTML = `
      <div class="divider"></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
        <div><div class="form-label" style="margin-bottom:4px;">Estado actual</div>
          <span class="room-status-badge badge-${hab.status}">${UI.ICONOS_ESTADO[hab.status]} ${UI.escapar(hab.statusLabel)}</span></div>
        <div><div class="form-label" style="margin-bottom:4px;">Último empleado</div>
          <div style="font-size:13px;font-weight:500;">${UI.escapar(hab.employee || '—')}</div></div>
        <div><div class="form-label" style="margin-bottom:4px;">Hora inicio</div>
          <div style="font-size:13px;">${hab.timeStart || '—'}</div></div>
        <div><div class="form-label" style="margin-bottom:4px;">Hora fin</div>
          <div style="font-size:13px;">${hab.timeEnd || '—'}</div></div>
      </div>`;
    UI.abrirModal('modal-room');
  }

  function inicializar() {
    document.querySelectorAll('#panel-filters .filter-btn').forEach((boton) => {
      boton.addEventListener('click', () => {
        document.querySelectorAll('#panel-filters .filter-btn')
          .forEach((b) => b.classList.remove('active'));
        boton.classList.add('active');
        filtroActual = boton.dataset.filter;
        cargar();
      });
    });
  }

  return { cargar, aplicarCambio, inicializar };
})();
