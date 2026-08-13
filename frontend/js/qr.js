/* =============================================================
   qr.js - CU-02: escanearQR(codigoHabitacion)

   El personal escanea el QR pegado en la puerta con la camara de
   su celular. El QR contiene la URL http://servidor:8000/?hab=101,
   asi que el telefono abre la aplicacion directamente en esa
   habitacion, con sus botones de estado listos.
   ============================================================= */

const QR = (() => {
  /** Lee el parametro ?hab= de la URL. Devuelve null si no viene de un QR. */
  function habitacionEnURL() {
    return new URLSearchParams(location.search).get('hab');
  }

  /** Borra ?hab= de la barra de direcciones sin recargar.
   *  El QR es una entrada de un solo uso: si no se limpiara, recargar la
   *  pagina o cerrar el modal dejaria la habitacion "pegada" en la URL. */
  function limpiarURL() {
    history.replaceState({}, '', location.pathname);
  }

  /** Abre la pantalla de una habitacion.
   *  `origen` solo cambia el mensaje de error: un 404 desde un QR significa
   *  que el codigo esta mal pegado; escrito a mano, que el numero no existe. */
  async function abrirHabitacion(numero, origen = 'qr') {
    let hab;
    try {
      hab = await API.habitacionPorNumero(numero);
    } catch (error) {
      // alt [habitacion no encontrada] -> 404
      UI.toast(
        origen === 'qr'
          ? `Código QR inválido: ${error.message}`
          : error.message,
        'danger'
      );
      limpiarURL();
      return;
    }

    // Si se llego escribiendo el numero, hay que cerrar ese modal antes de
    // abrir el de la habitacion: dos superpuestos dejarian el de atras
    // atrapado al cerrar el de arriba.
    UI.cerrarModal('modal-escanear');

    document.getElementById('qr-room-number').textContent = hab.numero;
    document.getElementById('qr-room-info').textContent = `Piso ${hab.floor} · ${hab.type}`;
    document.getElementById('qr-room-current').innerHTML =
      `<span class="room-status-badge badge-${hab.status}">
         ${UI.ICONOS_ESTADO[hab.status]} ${UI.escapar(hab.statusLabel)}
       </span>`;

    const empleado = document.getElementById('qr-room-employee');
    empleado.innerHTML = hab.employee
      ? `<div class="form-label" style="margin-bottom:4px;">Último empleado</div>
         <div style="font-size:13px;font-weight:500;">${UI.escapar(hab.employee)}
         ${hab.timeStart ? ` · desde ${hab.timeStart}` : ''}</div>`
      : '';

    pintarBotones(hab);
    UI.abrirModal('modal-qr');
    limpiarURL();
  }

  /** Dibuja solo las transiciones que este rol puede aplicar.
   *  Ofrecer botones que el backend va a rechazar con un 422 seria enseñarle
   *  al personal a chocar contra el error. */
  function pintarBotones(hab) {
    const contenedor = document.getElementById('qr-room-buttons');

    if (!hab.estadosValidos.length) {
      contenedor.innerHTML =
        `<div style="font-size:13px;color:var(--muted);text-align:center;padding:14px;">
           No hay cambios disponibles para esta habitación con tu rol.
         </div>`;
      return;
    }

    const estilos = {
      dirty:    { icono: '🔴', texto: 'Sucia',     clase: 'dirty-btn' },
      cleaning: { icono: '🧹', texto: 'Limpiando', clase: 'cleaning-btn' },
      clean:    { icono: '✅', texto: 'Lista',     clase: 'clean-btn' },
    };

    contenedor.innerHTML = hab.estadosValidos
      .map((estado) => {
        const e = estilos[estado];
        return `<button class="status-btn ${e.clase}" data-estado="${estado}"
                  style="padding:16px 10px;font-size:14px;">
                  <span>${e.icono}</span>${e.texto}
                </button>`;
      })
      .join('');

    contenedor.querySelectorAll('button').forEach((boton) => {
      boton.addEventListener('click', () => aplicar(hab, boton.dataset.estado));
    });
  }

  async function aplicar(hab, nuevoEstado) {
    const contenedor = document.getElementById('qr-room-buttons');
    contenedor.querySelectorAll('button').forEach((b) => (b.disabled = true));

    try {
      const respuesta = await API.cambiarEstado(hab.id, nuevoEstado);
      UI.toast(
        `Hab. ${respuesta.habitacion.numero}: ${respuesta.habitacion.statusLabel}`,
        nuevoEstado === 'clean' ? 'success' : nuevoEstado === 'dirty' ? 'danger' : 'warn'
      );
      UI.cerrarModal('modal-qr');
    } catch (error) {
      UI.toast(error.message, 'danger');
      // Reabrir con el estado fresco: si otra persona ya cambio la habitacion,
      // los botones que se estaban mostrando ya no son los correctos.
      abrirHabitacion(hab.numero);
    }
  }

  /** Descarga la hoja imprimible con los 24 QR (solo admin/supervisor). */
  async function imprimirHoja() {
    const boton = document.getElementById('btn-qr-hoja');
    const texto = boton.textContent;
    boton.disabled = true;
    boton.textContent = 'Generando...';

    try {
      const info = await API.infoQR();
      await API.descargarHojaQR();
      UI.toast('Hoja de códigos QR descargada ✓', 'success');

      // Un QR que apunta a localhost solo funciona en esta computadora: desde
      // un celular no abriria nada. Mejor avisarlo ahora que en la demo.
      if (info.esLocalhost) {
        setTimeout(
          () => UI.toast('Aviso: los QR apuntan a localhost y no funcionarán desde un celular.', 'warn'),
          800
        );
      }
    } catch (error) {
      UI.toast(error.message, 'danger');
    } finally {
      boton.disabled = false;
      boton.textContent = texto;
    }
  }

  /** Si la app se abrio desde un QR, muestra esa habitacion. */
  async function procesarEntradaPorQR() {
    const numero = habitacionEnURL();
    if (numero) await abrirHabitacion(numero);
  }

  // ------------------------------------------------- entrada manual
  function abrirModalEscanear() {
    const campo = document.getElementById('escanear-numero');
    campo.value = '';
    UI.abrirModal('modal-escanear');
    // En el celular esto levanta el teclado numerico de una vez.
    setTimeout(() => campo.focus(), 100);
  }

  async function abrirPorNumeroEscrito() {
    const numero = document.getElementById('escanear-numero').value.trim();
    if (!numero) {
      UI.toast('Escribe el número de habitación', 'danger');
      return;
    }
    await abrirHabitacion(numero, 'manual');
  }

  function inicializar() {
    document.getElementById('btn-qr-hoja')?.addEventListener('click', imprimirHoja);
    document.getElementById('btn-escanear')?.addEventListener('click', abrirModalEscanear);
    document.getElementById('btn-abrir-habitacion')?.addEventListener('click', abrirPorNumeroEscrito);

    // Enter en el campo abre la habitación, sin obligar a buscar el botón.
    document.getElementById('escanear-numero')?.addEventListener('keydown', (evento) => {
      if (evento.key === 'Enter') {
        evento.preventDefault();
        abrirPorNumeroEscrito();
      }
    });
  }

  return { inicializar, procesarEntradaPorQR, abrirHabitacion, habitacionEnURL };
})();
