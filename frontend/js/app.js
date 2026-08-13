/* =============================================================
   app.js - Arranque de la aplicacion.

   Conecta los listeners globales e inicializa cada pantalla.
   Se carga al final, cuando el resto de modulos ya existe.
   ============================================================= */

document.addEventListener('DOMContentLoaded', async () => {
  /* ---------------------------------------------- login (CU-01) */
  document.getElementById('login-form').addEventListener('submit', (evento) => {
    evento.preventDefault(); // sin esto el formulario recarga la pagina
    Auth.entrar(
      document.getElementById('login-email').value,
      document.getElementById('login-pass').value
    );
  });

  document.getElementById('btn-logout').addEventListener('click', Auth.salir);

  /* ---------------------------------------------------- sidebar */
  document.getElementById('btn-hamburger').addEventListener('click', UI.toggleSidebar);
  document.getElementById('overlay-bg').addEventListener('click', UI.cerrarSidebar);

  /* ----------------------------------------------------- modales */
  document.querySelectorAll('[data-close]').forEach((boton) => {
    boton.addEventListener('click', () => UI.cerrarModal(boton.dataset.close));
  });

  // Clic fuera de la caja: cierra el modal.
  document.querySelectorAll('.modal-overlay').forEach((overlay) => {
    overlay.addEventListener('click', (evento) => {
      if (evento.target === overlay) overlay.classList.remove('open');
    });
  });

  document.addEventListener('keydown', (evento) => {
    if (evento.key === 'Escape') {
      document.querySelectorAll('.modal-overlay').forEach((m) => m.classList.remove('open'));
    }
  });

  /* -------------------------------------- listeners de pantallas */
  Panel.inicializar();
  Historial.inicializar();
  Reportes.inicializar();
  Usuarios.inicializar();
  QR.inicializar();

  /* --------------------------------------------- sesion expirada */
  // La dispara api.js cuando el backend responde 401 con un token guardado.
  window.addEventListener('sesion-expirada', () => {
    Realtime.detener();
    document.getElementById('app-shell').style.display = 'none';
    document.getElementById('login-screen').style.display = 'flex';
    UI.toast('Tu sesión expiró. Inicia sesión de nuevo.', 'warn');
  });

  /* ------------------------------------- restaurar sesion previa */
  // Si hay un token valido en localStorage, se entra directo sin volver a
  // pedir credenciales tras un F5.
  const restaurada = await Auth.restaurar();
  if (!restaurada) {
    document.getElementById('login-screen').style.display = 'flex';
  }
});
