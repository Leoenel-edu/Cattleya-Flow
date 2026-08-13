/* =============================================================
   ui.js - Elementos visuales compartidos: navegacion, toasts,
   modales, sidebar y estado de sesion en memoria.
   ============================================================= */

const UI = (() => {
  /* Estado de la sesion actual. Lo llena auth.js tras el login. */
  const sesion = {
    nombre: null,
    rol: null,
    rolEtiqueta: null,
    usuarioId: null,
    navegacion: [],
  };

  const NAV_ITEMS = {
    panel:     { icon: '🏨', label: 'Panel de Habitaciones' },
    cambiar:   { icon: '🔄', label: 'Cambiar Estado' },
    historial: { icon: '📋', label: 'Historial de Limpieza' },
    reportes:  { icon: '📊', label: 'Reportes' },
    usuarios:  { icon: '👥', label: 'Gestionar Usuarios' },
  };

  let pantallaActual = null;

  /* -------------------------------------------------- toasts */
  function toast(mensaje, tipo = 'success') {
    const contenedor = document.getElementById('toast-container');
    const elemento = document.createElement('div');
    elemento.className = `toast ${tipo}`;
    // textContent y no innerHTML: el mensaje puede incluir el nombre de un
    // usuario, y un nombre con < > romperia el marcado o inyectaria HTML.
    elemento.textContent = mensaje;
    contenedor.appendChild(elemento);
    setTimeout(() => {
      elemento.classList.add('hiding');
      setTimeout(() => elemento.remove(), 300);
    }, 3000);
  }

  /* -------------------------------------------------- modales */
  const abrirModal  = (id) => document.getElementById(id).classList.add('open');
  const cerrarModal = (id) => document.getElementById(id).classList.remove('open');

  /* -------------------------------------------------- sidebar */
  function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('open');
    document.getElementById('overlay-bg').classList.toggle('open');
  }
  function cerrarSidebar() {
    document.getElementById('sidebar').classList.remove('open');
    document.getElementById('overlay-bg').classList.remove('open');
  }

  /* ----------------------------------------------- navegacion */
  /** Dibuja el menu con las pantallas que el backend autorizo (RF-06). */
  function construirNav(dirtyCount = 0) {
    const nav = document.getElementById('sidebar-nav');
    nav.innerHTML = '';

    const seccion = document.createElement('div');
    seccion.className = 'nav-section';
    seccion.innerHTML = '<div class="nav-section-label">Menú</div>';

    sesion.navegacion.forEach((clave) => {
      const item = NAV_ITEMS[clave];
      if (!item) return;

      const div = document.createElement('div');
      div.className = 'nav-item';
      div.id = `nav-${clave}`;
      div.innerHTML =
        `<span class="nav-icon">${item.icon}</span>${item.label}` +
        (clave === 'panel' && dirtyCount > 0 ? `<span class="nav-badge">${dirtyCount}</span>` : '');
      div.addEventListener('click', () => navegarA(clave));
      seccion.appendChild(div);
    });

    nav.appendChild(seccion);
  }

  function navegarA(pantalla) {
    // Defensa por si se invoca con una pantalla que el rol no tiene.
    if (!sesion.navegacion.includes(pantalla)) return;

    pantallaActual = pantalla;

    document.querySelectorAll('.nav-item').forEach((el) => el.classList.remove('active'));
    document.getElementById(`nav-${pantalla}`)?.classList.add('active');

    document.querySelectorAll('.screen').forEach((s) => s.classList.remove('active'));
    document.getElementById(`screen-${pantalla}`)?.classList.add('active');

    document.getElementById('topbar-title').textContent = NAV_ITEMS[pantalla]?.label || '';
    cerrarSidebar();

    // Cada pantalla se recarga al entrar, para no mostrar datos viejos.
    if (pantalla === 'panel')     Panel.cargar();
    if (pantalla === 'cambiar')   Cambiar.cargar();
    if (pantalla === 'historial') Historial.cargar();
    if (pantalla === 'reportes')  Reportes.cargar();
    if (pantalla === 'usuarios')  Usuarios.cargar();
  }

  /* ------------------------------------------- utilidades */
  const ETIQUETAS_ESTADO = { clean: 'Lista', cleaning: 'En limpieza', dirty: 'Sucia' };
  const ICONOS_ESTADO    = { clean: '✅', cleaning: '🧹', dirty: '🔴' };

  /** Escapa texto que provenga de la base de datos antes de insertarlo
   *  con innerHTML (nombres de empleados, observaciones). */
  function escapar(texto) {
    const div = document.createElement('div');
    div.textContent = texto ?? '';
    return div.innerHTML;
  }

  return {
    sesion,
    NAV_ITEMS,
    ETIQUETAS_ESTADO,
    ICONOS_ESTADO,
    escapar,
    toast,
    abrirModal,
    cerrarModal,
    toggleSidebar,
    cerrarSidebar,
    construirNav,
    navegarA,
    get pantallaActual() { return pantallaActual; },
  };
})();
