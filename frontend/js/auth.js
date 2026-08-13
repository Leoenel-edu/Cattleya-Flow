/* =============================================================
   auth.js - CU-01: Autenticarse en el Sistema.

   A diferencia del prototipo, aqui no hay selector de rol: el rol
   lo determina el backend a partir de la cuenta. Elegirlo desde el
   navegador permitiria a cualquiera entrar como Administrador.
   ============================================================= */

const Auth = (() => {
  function mostrarError(mensaje) {
    const el = document.getElementById('login-error');
    el.textContent = mensaje;
    el.style.display = 'block';
  }

  function ocultarError() {
    document.getElementById('login-error').style.display = 'none';
  }

  async function entrar(email, password) {
    ocultarError();
    const boton = document.getElementById('login-btn');
    boton.disabled = true;
    boton.textContent = 'Verificando...';

    try {
      const datos = await API.login(email, password);
      API.guardarToken(datos.token);
      iniciarSesionEnUI(datos);

      // opt [primer login]
      if (datos.primerLogin) {
        UI.toast('Es tu primer acceso: cambia tu contraseña pronto.', 'warn');
      }
    } catch (error) {
      // alt [credenciales invalidas] 401 / alt [cuenta desactivada] 403
      mostrarError(error.message);
    } finally {
      boton.disabled = false;
      boton.textContent = 'Iniciar sesión';
    }
  }

  /** Pinta la aplicacion con la sesion ya validada. */
  function iniciarSesionEnUI(datos) {
    Object.assign(UI.sesion, {
      nombre: datos.nombre,
      rol: datos.rol,
      rolEtiqueta: datos.rolEtiqueta,
      usuarioId: datos.usuarioId,
      navegacion: datos.navegacion,
    });

    document.getElementById('user-name').textContent = datos.nombre;
    document.getElementById('user-role').textContent = datos.rolEtiqueta;
    document.getElementById('user-avatar').textContent = datos.nombre.charAt(0).toUpperCase();

    document.getElementById('login-screen').style.display = 'none';
    document.getElementById('app-shell').style.display = 'block';

    // Imprimir los códigos QR es tarea de administración: el backend lo
    // restringe a admin/supervisor, así que el botón tampoco se muestra al
    // resto en vez de dejar que descubran un 403.
    const botonQR = document.getElementById('btn-qr-hoja');
    if (botonQR) {
      botonQR.style.display = ['admin', 'supervisor'].includes(datos.rol) ? '' : 'none';
    }

    UI.construirNav();
    UI.navegarA(datos.navegacion[0]);
    Realtime.iniciar();

    UI.toast(`Bienvenido, ${datos.nombre}`, 'success');

    // Si se entró escaneando un QR (/?hab=101), abrir esa habitación.
    // Va aquí y no en app.js porque este es el único punto por el que pasan
    // tanto el login normal como la restauración de sesión.
    QR.procesarEntradaPorQR();
  }

  async function salir() {
    try {
      await API.logout();
    } catch {
      // Si la llamada falla (servidor caido, token vencido) igual hay que
      // cerrar sesion en el navegador: dejar al usuario dentro seria peor.
    }
    API.guardarToken(null);
    Realtime.detener();
    document.getElementById('app-shell').style.display = 'none';
    document.getElementById('login-screen').style.display = 'flex';
    document.getElementById('login-form').reset();
  }

  /** Restaura la sesion tras recargar la pagina (F5), si el token sigue vivo. */
  async function restaurar() {
    if (!API.token) return false;
    try {
      const perfil = await API.perfil();
      iniciarSesionEnUI({ ...perfil, primerLogin: false });
      return true;
    } catch {
      API.guardarToken(null);
      return false;
    }
  }

  return { entrar, salir, restaurar };
})();
