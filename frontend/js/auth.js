// Sesión del usuario y llamadas a la API con cookie de sesión + token CSRF.
// La cookie de sesión es HttpOnly: este archivo nunca la ve, solo lee "csrftoken".

const ROLES = {
    staff: 'Administración',
    profesor: 'Profesor',
    estudiante: 'Estudiante',
};

function getCookie(nombre) {
    const par = document.cookie.split('; ').find(c => c.startsWith(nombre + '='));
    return par ? decodeURIComponent(par.split('=')[1]) : '';
}

async function api(ruta, opciones = {}) {
    const metodo = (opciones.method || 'GET').toUpperCase();
    const headers = { ...opciones.headers };
    if (metodo !== 'GET' && metodo !== 'HEAD') {
        headers['X-CSRFToken'] = getCookie('csrftoken');
    }
    if (opciones.body) {
        headers['Content-Type'] = 'application/json';
    }
    return fetch('/api' + ruta, { ...opciones, headers, credentials: 'same-origin' });
}

async function cerrarSesion() {
    await api('/auth/logout/', { method: 'POST' });
    window.location.replace('login.html');
}

// Llamar al cargar una página protegida: si no hay sesión, manda al login.
async function verificarSesion() {
    let respuesta;
    try {
        respuesta = await api('/auth/me/');
    } catch {
        // Sin red o servidor caído: en lugar de dejar la página en blanco, la pantalla "Sin conexión"
        window.location.replace('offline.html');
        return null;
    }
    if (!respuesta.ok) {
        window.location.replace('login.html');
        return null;
    }
    const usuario = await respuesta.json();
    // Con la contraseña temporal del alta no se entra al campus hasta cambiarla
    if (usuario.debe_cambiar_password) {
        window.location.replace('cambiar-password.html');
        return null;
    }
    mostrarUsuario(usuario);
    aplicarRol(usuario.rol);
    document.body.classList.remove('cargando');
    return usuario;
}

function mostrarUsuario(usuario) {
    const est = usuario.estudiante;
    const nombre = est ? `${est.nombre} ${est.apellido}` : usuario.nombre;
    const iniciales = nombre.split(/\s+/).slice(0, 2).map(p => p.charAt(0)).join('').toUpperCase();

    const asignar = (selector, texto) => {
        const el = document.querySelector(selector);
        if (el) el.textContent = texto;
    };
    asignar('#header-nombre', nombre);
    asignar('#header-rol', ROLES[usuario.rol] || 'Sin rol asignado');
    asignar('#header-avatar', iniciales);

    const infoEstudiante = document.querySelector('.student-info');
    if (est) {
        asignar('.student-name', nombre);
        asignar('.student-id', `Matrícula: ${est.matricula}`);
        const avatar = document.querySelector('.student-avatar img');
        if (avatar) {
            avatar.src = avatarSvg(iniciales);
            avatar.alt = nombre;
        }
    } else if (infoEstudiante) {
        // Sin estudiante no hay tarjeta de perfil: se oculta todo el encabezado para no dejar la franja vacía
        (infoEstudiante.closest('.sidebar-header') || infoEstudiante).style.display = 'none';
    }
}

// Círculo con iniciales, como el avatar original de la barra lateral
function avatarSvg(iniciales) {
    const texto = iniciales.replace(/[^\p{L}\p{N}]/gu, '');
    const svg = `<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>`
        + `<circle cx='50' cy='50' r='45' fill='#667eea'/>`
        + `<text x='50' y='50' text-anchor='middle' dy='.3em' fill='white' font-size='40' font-family='Arial'>${texto}</text>`
        + `</svg>`;
    return 'data:image/svg+xml,' + encodeURIComponent(svg);
}

// Oculta los elementos con data-roles="rol1,rol2" que no corresponden al usuario
function aplicarRol(rol) {
    document.querySelectorAll('[data-roles]').forEach(el => {
        const permitidos = el.dataset.roles.split(',').map(r => r.trim());
        if (!permitidos.includes(rol)) {
            el.style.display = 'none';
        }
    });
}

window.api = api;
window.getCookie = getCookie;
window.cerrarSesion = cerrarSesion;
window.verificarSesion = verificarSesion;
