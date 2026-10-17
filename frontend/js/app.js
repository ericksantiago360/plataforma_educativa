let usuarioActual = null;
let currentStudent = null;
let courses = [];
let tasks = [];

// Escapa texto de la API antes de insertarlo con innerHTML (evita XSS)
function escapeHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

// Pide una lista a la API con api() de auth.js (cookie de sesión + CSRF)
async function getLista(ruta) {
    const response = await api(ruta);
    if (!response.ok) {
        throw new Error(`${ruta} respondió ${response.status}`);
    }
    const data = await response.json();
    return data.results || data;
}

// Como getLista, pero recorre todas las páginas (la API pagina de 10 en 10)
async function getTodas(ruta) {
    const todas = [];
    let siguiente = ruta;
    while (siguiente) {
        const response = await api(siguiente);
        if (!response.ok) {
            throw new Error(`${siguiente} respondió ${response.status}`);
        }
        const data = await response.json();
        if (!data.results) return data;  // respuesta sin paginar
        todas.push(...data.results);
        // "next" viene como URL absoluta; api() espera la ruta sin el prefijo /api
        siguiente = data.next ? new URL(data.next).pathname.replace(/^\/api/, '') + new URL(data.next).search : null;
    }
    return todas;
}

async function init() {
    // verificarSesion() ya pinta nombre y rol; si no hay sesión redirige al login
    const usuario = await verificarSesion();
    if (!usuario) return;
    usuarioActual = usuario;
    currentStudent = usuario.estudiante;

    const [, , perfil] = await Promise.all([loadCourses(), loadTasks(), loadPerfil()]);
    updatePerfil(perfil);
    updateDashboard(usuario);
}

async function loadCourses() {
    try {
        courses = await getLista('/cursos/');
    } catch (error) {
        console.error('Error cargando cursos:', error);
    }
}

async function loadTasks() {
    try {
        tasks = await getLista('/tareas/');
    } catch (error) {
        console.error('Error cargando tareas:', error);
    }
}

// Solo los estudiantes tienen perfil académico; la API ya devuelve únicamente el propio
async function loadPerfil() {
    if (!currentStudent) return null;
    try {
        const perfiles = await getLista('/perfiles/');
        return perfiles[0] || null;
    } catch (error) {
        console.error('Error cargando perfil:', error);
        return null;
    }
}

function updatePerfil(perfil) {
    const asignar = (selector, texto) => {
        const el = document.querySelector(selector);
        if (el) el.textContent = texto;
    };

    if (!perfil) {
        asignar('.student-program', 'Sin perfil académico');
        return;
    }

    const progreso = Math.max(0, Math.min(100, perfil.progreso_academico));
    asignar('#stat-cursadas', perfil.materias_cursadas);
    asignar('#stat-totales', perfil.materias_totales);
    asignar('#stat-progreso', `${progreso}%`);
    asignar('#stat-promedio', Number(perfil.promedio).toFixed(1));

    asignar('.student-program', perfil.programa);
    asignar('.progress-text', `${progreso}%`);
    asignar('#progress-materias', `${perfil.materias_cursadas} de ${perfil.materias_totales} Materias`);

    // El arco mide 251 (≈ 2π·40); el offset es la parte sin completar
    const arco = document.getElementById('progress-arc');
    if (arco) arco.setAttribute('stroke-dashoffset', String(251 * (1 - progreso / 100)));
}

function updateDashboard(usuario) {
    const nombre = currentStudent ? currentStudent.nombre : usuario.nombre;
    const bannerTitle = document.querySelector('#inicio .banner-text h2');
    if (bannerTitle) {
        bannerTitle.textContent = `¡Bienvenido/a ${nombre}!`;
    }

    if (currentStudent) {
        const pendientes = tasks.filter(t => t.estado === 'pendiente').length;
        const bannerText = document.querySelector('#inicio .banner-text p');
        if (bannerText) {
            bannerText.textContent = pendientes === 1
                ? 'Tienes 1 tarea pendiente'
                : `Tienes ${pendientes} tareas pendientes`;
        }
    }
}

function showSection(sectionId) {
    document.querySelectorAll('.section').forEach(section => {
        section.classList.remove('active');
    });
    
    const selectedSection = document.getElementById(sectionId);
    if (selectedSection) {
        selectedSection.classList.add('active');
    }
    
    document.querySelectorAll('.menu-item').forEach(item => {
        item.classList.remove('active');
    });
    
    const menuItems = document.querySelectorAll('.menu-item');
    menuItems.forEach(item => {
        if (item.getAttribute('onclick') && item.getAttribute('onclick').includes(sectionId)) {
            item.classList.add('active');
        }
    });
    
    switch(sectionId) {
        case 'control':
            loadControlEscolar();
            break;
        case 'clases':
            cargarClasesZoom();
            break;
        case 'foro':
            loadForo();
            break;
    }
}

// Badge según el estado del registro en Control Escolar
const ESTADOS_ESCOLARES = {
    aprobado: { clase: 'badge-completed', texto: 'Aprobado' },
    cursando: { clase: 'badge-scheduled', texto: 'Cursando' },
    reprobado: { clase: 'badge-live', texto: 'Reprobado' },
    baja: { clase: 'badge-neutral', texto: 'Baja' },
};

async function loadControlEscolar() {
    const container = document.querySelector('#control .clases-list');
    if (!container) return;

    // El estudiante ve su historial; profesor y staff, los registros de sus grupos
    const titulo = currentStudent ? 'Historial Académico' : 'Calificaciones de mis grupos';
    container.innerHTML = `<h3 style="margin-bottom: 1rem;">${titulo}</h3><p>Cargando…</p>`;

    let registros;
    try {
        registros = await getTodas('/control-escolar/');
    } catch (error) {
        console.error('Error cargando control escolar:', error);
        container.innerHTML = `<h3 style="margin-bottom: 1rem;">${titulo}</h3>`
            + '<div class="card"><p style="color: red;">No se pudo cargar el historial.</p></div>';
        return;
    }

    let html = `<h3 style="margin-bottom: 1rem;">${titulo}</h3>`;

    if (registros.length === 0) {
        html += '<div class="card"><p>Aún no hay materias registradas.</p></div>';
    }

    registros.forEach(registro => {
        const estado = ESTADOS_ESCOLARES[registro.estado] || { clase: 'badge-neutral', texto: registro.estado };
        const badge = registro.calificacion !== null
            ? `${estado.texto} - ${Number(registro.calificacion).toFixed(1)}`
            : estado.texto;
        const alumno = currentStudent
            ? ''
            : `<div>Estudiante: ${escapeHtml(registro.estudiante_nombre)} ${escapeHtml(registro.estudiante_apellido)}</div>`;

        html += `
            <div class="clase-item">
                <div class="clase-header">
                    <div class="clase-title">${escapeHtml(registro.materia_nombre)}</div>
                    <div class="clase-badge ${estado.clase}">${escapeHtml(badge)}</div>
                </div>
                ${alumno}
                <div>Período: ${escapeHtml(registro.periodo)}</div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// Función auxiliar para abrir Zoom
function abrirClaseZoom(claseId) {
    window.open('zoom-config.html?id=' + claseId, '_blank');
}

async function cargarClasesZoom() {
    try {
        const clases = await getLista('/clases-zoom/');
        const container = document.querySelector('#clases .clases-list');
        
        if (!container) {
            console.error('Container no encontrado');
            return;
        }
        
        let html = '<h3 style="margin-bottom: 1rem;">🎥 Mis Clases en Línea con Zoom</h3>';
        
        if (clases.length === 0) {
            html += '<div class="card"><p>No hay clases disponibles</p></div>';
        } else {
            clases.forEach(clase => {
                const badgeClass = clase.estado === 'en_vivo' ? 'badge-live' : 
                                 clase.estado === 'programada' ? 'badge-scheduled' : 'badge-completed';
                const estadoTexto = clase.estado === 'en_vivo' ? '🔴 EN VIVO' :
                                  clase.estado === 'programada' ? '📅 PROGRAMADA' : '✅ FINALIZADA';

                html += `
                    <div class="clase-item">
                        <div class="clase-header">
                            <div class="clase-title">${escapeHtml(clase.titulo)}</div>
                            <div class="clase-badge ${badgeClass}">${estadoTexto}</div>
                        </div>
                        <div style="margin-top: 0.5rem;">
                            <p><strong>📚 Curso:</strong> ${escapeHtml(clase.curso_nombre)}</p>
                            <p><strong>👨‍🏫 Profesor:</strong> ${escapeHtml(clase.profesor)}</p>
                            <p><strong>⏱️ Duración:</strong> ${escapeHtml(clase.duracion_minutos)} minutos</p>
                            <p><strong>👥 Participantes:</strong> ${escapeHtml(clase.total_participantes)} / ${escapeHtml(clase.max_participantes)}</p>
                            <p><strong>📅 Fecha:</strong> ${escapeHtml(new Date(clase.fecha_hora_inicio).toLocaleString('es-MX'))}</p>
                            <button class="btn btn-primary zoom-btn" data-clase-id="${escapeHtml(clase.id)}" style="margin-top: 1rem;">
                                ${clase.estado === 'en_vivo' ? '🎥 Unirse Ahora' : '📋 Ver Detalles'}
                            </button>
                        </div>
                    </div>
                `;
            });
        }
        
        container.innerHTML = html;
        
        // Agregar event listeners a los botones
        document.querySelectorAll('.zoom-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                const claseId = this.getAttribute('data-clase-id');
                abrirClaseZoom(claseId);
            });
        });
        
        console.log('✅ Clases Zoom cargadas');
        
    } catch (error) {
        console.error('❌ Error:', error);
        const container = document.querySelector('#clases .clases-list');
        if (container) {
            container.innerHTML = '<div class="card"><p style="color: red;">Error al cargar clases</p></div>';
        }
    }
}

// ---------- Foro de clase ----------

let foroActual = null;

const ESTILO_ACCION = 'background: none; border: none; cursor: pointer; font-size: 0.85rem; padding: 0;';

const FORO_TITULO = '<h3 style="margin-bottom: 1rem;">Foros de mis clases</h3>';

function formatearFecha(iso) {
    return new Date(iso).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' });
}

// Etiqueta junto al nombre para distinguir a profesores y staff en la conversación
const ETIQUETAS_AUTOR = {
    profesor: 'Profesor',
    staff: 'Administración',
};

function esMensajeMio(mensaje) {
    return Boolean(usuarioActual) && mensaje.autor === usuarioActual.id;
}

function puedeEliminar(mensaje) {
    const rol = usuarioActual && usuarioActual.rol;
    if (rol === 'staff' || rol === 'profesor') return true;  // el profesor modera sus cursos (la API lo limita)
    return esMensajeMio(mensaje);
}

async function loadForo() {
    const container = document.querySelector('#foro .clases-list');
    if (!container) return;
    foroActual = null;
    container.innerHTML = FORO_TITULO + '<p>Cargando…</p>';

    let foros;
    try {
        foros = await getTodas('/foros/');
    } catch (error) {
        console.error('Error cargando foros:', error);
        container.innerHTML = FORO_TITULO
            + '<div class="card"><p style="color: red;">No se pudieron cargar los foros.</p></div>';
        return;
    }

    let html = FORO_TITULO;
    if (foros.length === 0) {
        html += '<div class="card"><p>No hay foros en tus cursos.</p></div>';
    }

    foros.forEach(foro => {
        const total = foro.total_mensajes;
        html += `
            <div class="clase-item foro-item" data-foro-id="${escapeHtml(foro.id)}" style="cursor: pointer;">
                <div class="clase-header">
                    <div class="clase-title">${escapeHtml(foro.titulo)}</div>
                    <div class="clase-badge ${foro.activo ? 'badge-completed' : 'badge-neutral'}">${foro.activo ? 'Abierto' : 'Cerrado'}</div>
                </div>
                <div>${escapeHtml(foro.materia_nombre)} · ${escapeHtml(foro.clase_titulo)}</div>
                <div style="color: var(--gray-700); font-size: 0.85rem; margin-top: 0.25rem;">
                    💬 ${total === 1 ? '1 mensaje' : `${escapeHtml(total)} mensajes`}
                </div>
            </div>
        `;
    });

    container.innerHTML = html;
    container.querySelectorAll('.foro-item').forEach(item => {
        item.addEventListener('click', () => {
            const foro = foros.find(f => String(f.id) === item.dataset.foroId);
            abrirForo(foro);
        });
    });
}

async function abrirForo(foro) {
    const container = document.querySelector('#foro .clases-list');
    if (!container) return;
    foroActual = foro;

    const encabezado = `
        <button type="button" class="btn btn-primary" id="foro-volver" style="margin-bottom: 1rem;">← Volver a los foros</button>
        <h3 style="margin-bottom: 0.25rem;">${escapeHtml(foro.titulo)}</h3>
        <p style="color: var(--gray-700); font-size: 0.9rem;">${escapeHtml(foro.materia_nombre)} · ${escapeHtml(foro.clase_titulo)}</p>
        <p style="margin: 0.75rem 0 1.5rem;">${escapeHtml(foro.descripcion)}</p>
    `;
    container.innerHTML = encabezado + '<p>Cargando mensajes…</p>';
    document.getElementById('foro-volver').addEventListener('click', loadForo);

    let mensajes;
    try {
        mensajes = await getTodas(`/mensajes-foro/?foro=${encodeURIComponent(foro.id)}`);
    } catch (error) {
        console.error('Error cargando mensajes:', error);
        container.innerHTML = encabezado
            + '<div class="card"><p style="color: red;">No se pudieron cargar los mensajes.</p></div>';
        document.getElementById('foro-volver').addEventListener('click', loadForo);
        return;
    }

    let html = encabezado;
    if (mensajes.length === 0) {
        html += '<div class="card" style="margin-bottom: 1rem;"><p>Todavía no hay mensajes. ¡Sé el primero en participar!</p></div>';
    }

    mensajes.forEach(mensaje => {
        const esMio = esMensajeMio(mensaje);
        const iniciales = mensaje.autor_nombre.split(/\s+/).slice(0, 2).map(p => p.charAt(0)).join('').toUpperCase();
        const etiqueta = ETIQUETAS_AUTOR[mensaje.autor_rol]
            ? `<span class="clase-badge" style="background: var(--primary); color: white; margin-left: 0.5rem;">${ETIQUETAS_AUTOR[mensaje.autor_rol]}</span>`
            : '';
        html += `
            <div class="card" style="margin-bottom: 1rem;">
                <div style="display: flex; gap: 1rem;">
                    <div class="user-avatar" style="width: 40px; height: 40px; flex-shrink: 0;">${escapeHtml(iniciales)}</div>
                    <div style="flex: 1; min-width: 0;">
                        <div style="display: flex; justify-content: space-between; gap: 1rem; margin-bottom: 0.5rem;">
                            <span><strong>${escapeHtml(mensaje.autor_nombre)}${esMio ? ' (tú)' : ''}</strong>${etiqueta}</span>
                            <span style="color: var(--gray-700); font-size: 0.85rem;">
                                ${escapeHtml(formatearFecha(mensaje.fecha_publicacion))}${mensaje.editado ? ' · editado' : ''}
                            </span>
                        </div>
                        <div class="foro-vista">
                            <p style="color: var(--gray-700); white-space: pre-wrap; overflow-wrap: anywhere;">${escapeHtml(mensaje.contenido)}</p>
                            <div style="display: flex; gap: 1rem; margin-top: 0.75rem;">
                                ${esMio && foro.activo ? `
                                    <button type="button" class="foro-editar" data-mensaje-id="${escapeHtml(mensaje.id)}"
                                            style="${ESTILO_ACCION} color: var(--primary);">Editar</button>` : ''}
                                ${puedeEliminar(mensaje) ? `
                                    <button type="button" class="foro-eliminar" data-mensaje-id="${escapeHtml(mensaje.id)}"
                                            style="${ESTILO_ACCION} color: var(--danger);">Eliminar</button>` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });

    if (!foro.activo) {
        html += '<div class="card"><p>🔒 Este foro está cerrado y ya no recibe mensajes.</p></div>';
    } else {
        html += `
            <div class="card">
                <h4 style="margin-bottom: 1rem;">Nueva publicación</h4>
                <textarea id="foro-texto" rows="3" maxlength="5000" placeholder="Escribe aquí..."
                          style="width: 100%; padding: 0.75rem; border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 0.5rem; font-family: inherit;"></textarea>
                <p id="foro-error" role="alert" style="color: var(--danger); font-size: 0.85rem; min-height: 1.2em; margin-bottom: 0.5rem;"></p>
                <button type="button" class="btn btn-primary" id="foro-publicar">Publicar</button>
            </div>
        `;
    }

    container.innerHTML = html;
    document.getElementById('foro-volver').addEventListener('click', loadForo);
    const publicar = document.getElementById('foro-publicar');
    if (publicar) publicar.addEventListener('click', publicarEnForo);
    container.querySelectorAll('.foro-eliminar').forEach(boton => {
        boton.addEventListener('click', () => eliminarMensaje(boton.dataset.mensajeId));
    });
    container.querySelectorAll('.foro-editar').forEach(boton => {
        const mensaje = mensajes.find(m => String(m.id) === boton.dataset.mensajeId);
        boton.addEventListener('click', () => editarMensaje(mensaje, boton.closest('.foro-vista')));
    });
}

// Cambia el mensaje por un editor en su lugar; Cancelar lo restaura sin recargar
function editarMensaje(mensaje, vista) {
    const editor = document.createElement('div');
    editor.innerHTML = `
        <textarea rows="3" maxlength="5000"
                  style="width: 100%; padding: 0.75rem; border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 0.5rem; font-family: inherit;"></textarea>
        <p role="alert" style="color: var(--danger); font-size: 0.85rem; min-height: 1.2em; margin-bottom: 0.5rem;"></p>
        <div style="display: flex; gap: 0.5rem;">
            <button type="button" class="btn btn-primary" data-accion="guardar">Guardar</button>
            <button type="button" class="btn-salir" data-accion="cancelar">Cancelar</button>
        </div>
    `;
    const textarea = editor.querySelector('textarea');
    const error = editor.querySelector('[role="alert"]');
    const guardar = editor.querySelector('[data-accion="guardar"]');
    textarea.value = mensaje.contenido;  // .value, no innerHTML: el texto nunca se interpreta como HTML

    const cerrar = () => {
        editor.remove();
        vista.style.display = '';
    };

    editor.querySelector('[data-accion="cancelar"]').addEventListener('click', cerrar);
    guardar.addEventListener('click', async () => {
        const contenido = textarea.value.trim();
        if (!contenido) {
            error.textContent = 'El mensaje no puede quedar vacío.';
            return;
        }
        if (contenido === mensaje.contenido) {
            cerrar();
            return;
        }

        error.textContent = '';
        guardar.disabled = true;
        try {
            const response = await api(`/mensajes-foro/${encodeURIComponent(mensaje.id)}/`, {
                method: 'PATCH',
                body: JSON.stringify({ contenido }),
            });
            if (response.ok) {
                await abrirForo(foroActual);
                return;
            }
            const datos = await response.json().catch(() => ({}));
            error.textContent = datos.detail || 'No se pudo guardar el cambio.';
        } catch {
            error.textContent = 'No hay conexión con el servidor.';
        }
        guardar.disabled = false;
    });

    vista.style.display = 'none';
    vista.after(editor);
    textarea.focus();
}

async function publicarEnForo() {
    const textarea = document.getElementById('foro-texto');
    const error = document.getElementById('foro-error');
    const boton = document.getElementById('foro-publicar');
    const contenido = textarea.value.trim();

    if (!contenido) {
        error.textContent = 'Escribe algo antes de publicar.';
        return;
    }

    error.textContent = '';
    boton.disabled = true;
    try {
        const response = await api('/mensajes-foro/', {
            method: 'POST',
            body: JSON.stringify({ foro: foroActual.id, contenido }),
        });
        if (response.ok) {
            await abrirForo(foroActual);
            return;
        }
        const datos = await response.json().catch(() => ({}));
        error.textContent = datos.detail || 'No se pudo publicar el mensaje.';
    } catch {
        error.textContent = 'No hay conexión con el servidor.';
    }
    boton.disabled = false;
}

async function eliminarMensaje(mensajeId) {
    if (!confirm('¿Eliminar este mensaje? No se puede deshacer.')) return;
    try {
        const response = await api(`/mensajes-foro/${encodeURIComponent(mensajeId)}/`, { method: 'DELETE' });
        if (!response.ok) {
            const datos = await response.json().catch(() => ({}));
            alert(datos.detail || 'No se pudo eliminar el mensaje.');
            return;
        }
    } catch {
        alert('No hay conexión con el servidor.');
        return;
    }
    await abrirForo(foroActual);
}

window.addEventListener('DOMContentLoaded', () => {
    init();
});

window.showSection = showSection;
window.cargarClasesZoom = cargarClasesZoom;
window.abrirClaseZoom = abrirClaseZoom;
