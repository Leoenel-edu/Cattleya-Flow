/* =============================================================
   reportes.js - CU-04: Generar Reportes de Productividad.

   Las metricas se calculan en el backend a partir de los registros
   reales; esta pantalla solo las dibuja.
   ============================================================= */

const Reportes = (() => {
  let periodoActual = 'hoy';

  async function cargar() {
    try {
      const m = await API.metricas(periodoActual);
      document.getElementById('reporte-periodo').textContent = m.periodo;
      pintarTarjetas(m);
      pintarGrafico(m.empleados);
      pintarTabla(m.empleados);
    } catch (error) {
      UI.toast(error.message, 'danger');
    }
  }

  function pintarTarjetas(m) {
    const tarjetas = [
      { icon: '✅', title: 'Limpias hoy',     value: m.limpiasAhora,                        sub: 'habitaciones' },
      { icon: '⏱', title: 'Tiempo promedio', value: m.tiempoPromedio || '—',               sub: 'minutos por hab.' },
      { icon: '👥', title: 'Personal activo', value: m.personalActivo,                      sub: 'empleados en turno' },
      { icon: '📈', title: 'Eficiencia',      value: m.eficienciaGlobal ? m.eficienciaGlobal + '%' : '—', sub: 'del equipo' },
    ];

    document.getElementById('report-metrics').innerHTML = tarjetas
      .map(
        (t) => `<div class="report-card">
        <div class="report-card-icon">${t.icon}</div>
        <div class="report-card-title">${t.title}</div>
        <div class="report-card-value">${t.value}</div>
        <div class="report-card-sub">${t.sub}</div>
      </div>`
      )
      .join('');
  }

  function pintarGrafico(empleados) {
    const barras = document.getElementById('mini-bars');
    const etiquetas = document.getElementById('bar-labels');

    if (empleados.length === 0) {
      barras.innerHTML = '';
      etiquetas.innerHTML =
        '<div style="font-size:12px;color:var(--muted);padding:10px;">' +
        'Aún no hay habitaciones completadas en este período.</div>';
      return;
    }

    const maximo = Math.max(...empleados.map((e) => e.rooms));
    barras.innerHTML = empleados
      .map(
        (e) => `<div class="mini-bar" style="height:${(e.rooms / maximo) * 100}%;background:var(--accent)">
                  <div class="bar-tip">${e.rooms}</div>
                </div>`
      )
      .join('');
    etiquetas.innerHTML = empleados
      .map(
        (e) => `<div style="flex:1;text-align:center;font-size:10px;color:var(--muted);">
                  ${UI.escapar(e.name.split(' ')[0])}</div>`
      )
      .join('');
  }

  function pintarTabla(empleados) {
    const tbody = document.getElementById('employees-body');

    if (empleados.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="5" style="text-align:center;color:var(--muted);padding:20px;">' +
        'Sin datos todavía. Marca habitaciones como "Lista" para generar el reporte.</td></tr>';
      return;
    }

    tbody.innerHTML = empleados
      .map((e) => {
        const color = e.eff >= 94 ? 'var(--clean)' : e.eff >= 90 ? 'var(--warn)' : 'var(--danger)';
        return `<tr>
          <td><strong>${UI.escapar(e.name)}</strong></td>
          <td>${e.rooms} hab.</td>
          <td><span class="duration-pill">${e.avgMin} min</span></td>
          <td style="color:${color};font-weight:600;">${e.eff}%</td>
          <td>
            <div class="bar-track" style="width:100px;display:inline-block">
              <div class="bar-fill" style="width:${e.eff}%;background:${color}"></div>
            </div>
          </td>
        </tr>`;
      })
      .join('');
  }

  /**
   * Solicita el reporte y espera a que el backend lo termine.
   * El POST responde 202 Accepted sin el archivo (el diagrama lo modela
   * asincrono), asi que hay que consultar el estado hasta que este listo.
   */
  async function exportar(formato) {
    const boton = formato === 'pdf'
      ? document.getElementById('btn-export-pdf')
      : document.getElementById('btn-export-excel');
    const textoOriginal = boton.textContent;
    boton.disabled = true;
    boton.textContent = 'Generando...';

    try {
      const { reporteId } = await API.solicitarReporte(periodoActual, formato);

      // Polling con tope: sin limite, un reporte fallido dejaria el boton
      // bloqueado para siempre.
      const MAX_INTENTOS = 20;
      let listo = false;
      for (let i = 0; i < MAX_INTENTOS; i++) {
        const estado = await API.estadoReporte(reporteId);
        if (estado.listo) { listo = true; break; }
        if (estado.estado === 'error') throw new Error('El reporte falló al generarse');
        await new Promise((r) => setTimeout(r, 400));
      }

      if (!listo) throw new Error('El reporte está tardando demasiado. Intenta de nuevo.');

      await API.descargarReporte(reporteId, formato);
      UI.toast(`Reporte ${formato === 'pdf' ? 'PDF' : 'Excel'} descargado ✓`, 'success');
    } catch (error) {
      UI.toast(error.message, 'danger');
    } finally {
      boton.disabled = false;
      boton.textContent = textoOriginal;
    }
  }

  function inicializar() {
    document.querySelectorAll('#reporte-filters .filter-btn').forEach((boton) => {
      boton.addEventListener('click', () => {
        document.querySelectorAll('#reporte-filters .filter-btn')
          .forEach((b) => b.classList.remove('active'));
        boton.classList.add('active');
        periodoActual = boton.dataset.periodo;
        cargar();
      });
    });

    document.getElementById('btn-export-excel').addEventListener('click', () => exportar('excel'));
    document.getElementById('btn-export-pdf').addEventListener('click', () => exportar('pdf'));
  }

  return { cargar, inicializar };
})();
