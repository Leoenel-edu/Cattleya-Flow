/* =============================================================
   historial.js - CU-06: Consultar Historial de Limpieza.
   ============================================================= */

const Historial = (() => {
  let registros = [];

  async function cargar() {
    try {
      const datos = await API.historial();
      registros = datos.registros;
      pintar(registros);
    } catch (error) {
      UI.toast(error.message, 'danger');
    }
  }

  function pintar(lista) {
    const tbody = document.getElementById('historial-body');

    // alt [historial vacio]: se avisa en la tabla, sin tratarlo como error.
    if (lista.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:24px;">' +
        'Sin registros para ese filtro. Prueba ampliando el rango de fechas.</td></tr>';
      return;
    }

    tbody.innerHTML = lista
      .map(
        (h) => `<tr data-id="${h.id}" style="cursor:pointer">
        <td><strong>${UI.escapar(h.room)}</strong></td>
        <td>${UI.escapar(h.employee)}</td>
        <td style="font-family:monospace;font-size:12px;">${h.start}</td>
        <td style="font-family:monospace;font-size:12px;">${h.end}</td>
        <td><span class="duration-pill">${UI.escapar(h.duration)}</span></td>
        <td><span class="room-status-badge badge-${h.status}">
          ${UI.ICONOS_ESTADO[h.status] || ''} ${UI.ETIQUETAS_ESTADO[h.status] || h.status}
        </span></td>
      </tr>`
      )
      .join('');

    // opt [ver detalle de registro]
    tbody.querySelectorAll('tr[data-id]').forEach((fila) => {
      fila.addEventListener('click', () => verDetalle(Number(fila.dataset.id)));
    });
  }

  /** Filtro de texto en memoria: la lista ya esta cargada y filtrar en el
   *  cliente evita una peticion por cada tecla pulsada. */
  function filtrar(texto) {
    const q = texto.trim().toLowerCase();
    if (!q) return pintar(registros);
    pintar(
      registros.filter(
        (h) =>
          String(h.room).toLowerCase().includes(q) ||
          h.employee.toLowerCase().includes(q)
      )
    );
  }

  /** opt [ver detalle de registro]: modal con la informacion completa.
   *  Se pide al servidor porque las observaciones no viajan en el listado. */
  async function verDetalle(id) {
    let registro;
    try {
      registro = await API.detalleRegistro(id);
    } catch (error) {
      UI.toast(error.message, 'danger');
      return;
    }

    document.getElementById('modal-room-title').textContent = `Habitación ${registro.room}`;
    document.getElementById('modal-room-sub').textContent = `${registro.fecha} · ${registro.employee}`;
    document.getElementById('modal-room-body').innerHTML = `
      <div class="divider"></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
        <div><div class="form-label" style="margin-bottom:4px;">Hora inicio</div>
          <div style="font-size:13px;">${registro.start}</div></div>
        <div><div class="form-label" style="margin-bottom:4px;">Hora fin</div>
          <div style="font-size:13px;">${registro.end}</div></div>
        <div><div class="form-label" style="margin-bottom:4px;">Duración</div>
          <span class="duration-pill">${UI.escapar(registro.duration)}</span></div>
        <div><div class="form-label" style="margin-bottom:4px;">Estado final</div>
          <span class="room-status-badge badge-${registro.status}">
            ${UI.ETIQUETAS_ESTADO[registro.status] || registro.status}</span></div>
      </div>
      <div class="divider"></div>
      <div><div class="form-label" style="margin-bottom:4px;">Observaciones</div>
        <div style="font-size:13px;color:var(--muted);">${UI.escapar(registro.observaciones)}</div></div>`;
    UI.abrirModal('modal-room');
  }

  async function exportar() {
    try {
      UI.toast('Generando PDF...', 'warn');
      await API.exportarHistorial('pdf');
      UI.toast('Historial exportado ✓', 'success');
    } catch (error) {
      UI.toast(error.message, 'danger');
    }
  }

  function inicializar() {
    document.getElementById('historial-search')
      .addEventListener('input', (e) => filtrar(e.target.value));
    document.getElementById('btn-export-historial')
      .addEventListener('click', exportar);
  }

  return { cargar, inicializar };
})();
