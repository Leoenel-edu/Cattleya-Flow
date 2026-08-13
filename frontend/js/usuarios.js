/* =============================================================
   usuarios.js - CU-05: Gestionar Usuarios.
   ============================================================= */

const Usuarios = (() => {
  let usuarios = [];

  async function cargar() {
    try {
      const datos = await API.usuarios();
      usuarios = datos.usuarios;
      pintar(usuarios);
    } catch (error) {
      UI.toast(error.message, 'danger');
    }
  }

  function pintar(lista) {
    const tbody = document.getElementById('users-body');

    if (lista.length === 0) {
      tbody.innerHTML =
        '<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:24px;">' +
        'No se encontraron usuarios.</td></tr>';
      return;
    }

    tbody.innerHTML = lista
      .map(
        (u) => `<tr>
        <td>
          <div style="display:flex;align-items:center;gap:10px;">
            <div class="user-avatar" style="width:30px;height:30px;font-size:12px;">${UI.escapar(u.name.charAt(0))}</div>
            <strong>${UI.escapar(u.name)}</strong>
          </div>
        </td>
        <td><span class="role-badge role-${u.role}">${UI.escapar(u.roleLabel)}</span></td>
        <td style="color:var(--muted);font-size:12px;">${UI.escapar(u.email)}</td>
        <td>
          ${u.active
            ? '<div class="status-active"><div class="pulse-dot" style="background:var(--clean)"></div>Activo</div>'
            : '<div class="status-inactive">⬤ Inactivo</div>'}
        </td>
        <td style="font-size:12px;color:var(--muted);">${UI.escapar(u.last)}</td>
        <td>
          <div style="display:flex;gap:6px;">
            <button class="action-btn" data-accion="rol" data-id="${u.id}">Cambiar rol</button>
            <button class="action-btn danger" data-accion="activo" data-id="${u.id}">
              ${u.active ? 'Desactivar' : 'Activar'}
            </button>
          </div>
        </td>
      </tr>`
      )
      .join('');

    tbody.querySelectorAll('button[data-accion]').forEach((boton) => {
      const id = Number(boton.dataset.id);
      if (boton.dataset.accion === 'activo') {
        boton.addEventListener('click', () => alternarActivo(id));
      } else {
        boton.addEventListener('click', () => cambiarRol(id));
      }
    });
  }

  function filtrar(texto) {
    const q = texto.trim().toLowerCase();
    if (!q) return pintar(usuarios);
    pintar(
      usuarios.filter(
        (u) => u.name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q)
      )
    );
  }

  /* alt [desactivar cuenta] */
  async function alternarActivo(id) {
    const usuario = usuarios.find((u) => u.id === id);
    if (!usuario) return;

    try {
      const respuesta = await API.cambiarActivo(id, !usuario.active);
      UI.toast(
        `${respuesta.usuario.name}: ${respuesta.usuario.active ? 'activado' : 'desactivado'}`,
        respuesta.usuario.active ? 'success' : 'warn'
      );
      cargar();
    } catch (error) {
      UI.toast(error.message, 'danger');
    }
  }

  /* alt [modificar rol] */
  async function cambiarRol(id) {
    const usuario = usuarios.find((u) => u.id === id);
    if (!usuario) return;

    const roles = ['limpieza', 'recepcion', 'supervisor', 'admin'];
    const etiquetas = {
      limpieza: 'Personal de Limpieza',
      recepcion: 'Recepción',
      supervisor: 'Supervisor',
      admin: 'Administrador',
    };

    const opciones = roles.map((r, i) => `${i + 1}. ${etiquetas[r]}`).join('\n');
    const eleccion = prompt(
      `Nuevo rol para ${usuario.name} (actual: ${usuario.roleLabel})\n\n${opciones}\n\nEscribe el número:`
    );
    if (!eleccion) return;

    const indice = parseInt(eleccion, 10) - 1;
    if (isNaN(indice) || indice < 0 || indice >= roles.length) {
      UI.toast('Opción inválida', 'danger');
      return;
    }

    try {
      const respuesta = await API.cambiarRol(id, roles[indice]);
      UI.toast(`${respuesta.usuario.name} ahora es ${respuesta.usuario.roleLabel}`, 'success');
      cargar();
    } catch (error) {
      UI.toast(error.message, 'danger');
    }
  }

  function abrirModalNuevo() {
    ['new-user-name', 'new-user-lastname', 'new-user-email'].forEach(
      (id) => (document.getElementById(id).value = '')
    );
    UI.abrirModal('modal-user');
  }

  async function crear() {
    const nombre   = document.getElementById('new-user-name').value.trim();
    const apellido = document.getElementById('new-user-lastname').value.trim();
    const email    = document.getElementById('new-user-email').value.trim();
    const rol      = document.getElementById('new-user-role').value;

    if (!nombre || !email) {
      UI.toast('Completa nombre y correo', 'danger');
      return;
    }

    try {
      const respuesta = await API.crearUsuario({ nombre, apellido, email, rol });
      UI.cerrarModal('modal-user');
      UI.toast(`Usuario "${respuesta.usuario.name}" creado ✓`, 'success');

      // El SMTP corre en modo simulado, asi que la contrasena temporal se
      // muestra aqui para poder probar el acceso del nuevo usuario.
      if (respuesta.passwordTemporal) {
        setTimeout(
          () => UI.toast(`Contraseña temporal: ${respuesta.passwordTemporal}`, 'warn'),
          600
        );
      }
      cargar();
    } catch (error) {
      // alt [email duplicado] -> 409
      UI.toast(error.message, 'danger');
    }
  }

  function inicializar() {
    document.getElementById('usuarios-search')
      .addEventListener('input', (e) => filtrar(e.target.value));
    document.getElementById('btn-nuevo-usuario')
      .addEventListener('click', abrirModalNuevo);
    document.getElementById('btn-crear-usuario')
      .addEventListener('click', crear);
  }

  return { cargar, inicializar };
})();
