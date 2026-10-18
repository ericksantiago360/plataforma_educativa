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

    const [, , perfil, eventos] = await Promise.all([loadCourses(), loadTasks(), loadPerfil(), loadProximosEventos()]);
    updatePerfil(perfil);
    updateBanner(perfil, eventos);
    updateDashboard(usuario);
}

async function loadProximosEventos() {
    try {
        return await getLista('/calendario/?proximos=1');
    } catch (error) {
        console.error('Error cargando próximos eventos:', error);
        return [];
    }
}

// Banner del inicio. Prioridad: periodo y fecha límite del perfil; si el perfil no tiene
// fecha límite, la próxima entrega del calendario; sin perfil (profesor/staff), el próximo evento.
function updateBanner(perfil, eventos) {
    const banner = document.getElementById('period-info');
    if (!banner) return;

    const partes = [];
    if (perfil && perfil.periodo_actual) {
        partes.push(['Período', perfil.periodo_actual]);
    }

    if (perfil && perfil.fecha_limite_actividades) {
        partes.push(['Fecha Límite de Entrega', formatearDia(perfil.fecha_limite_actividades)]);
    } else {
        // El calendario ya viene ordenado por fecha de inicio
        const entrega = eventos.find(e => e.tipo_evento === 'entrega');
        const evento = entrega || (perfil ? null : eventos[0]);
        if (evento) {
            const fecha = new Date(evento.fecha_inicio).toLocaleDateString('es-MX', { day: 'numeric', month: 'long', year: 'numeric' });
            partes.push([entrega ? 'Próxima entrega' : 'Próximo evento', `${evento.titulo} · ${fecha}`]);
        }
    }

    if (partes.length === 0) {
        banner.style.display = 'none';
        return;
    }
    banner.innerHTML = partes.map(([etiqueta, valor]) => `<strong>${escapeHtml(etiqueta)}:</strong> ${escapeHtml(valor)}`).join(' | ');
    banner.style.display = '';
}

async function loadCourses() {
    try {
        courses = await getTodas('/cursos/');
    } catch (error) {
        console.error('Error cargando cursos:', error);
    }
}

async function loadTasks() {
    try {
        tasks = await getTodas('/tareas/');
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
        case 'biblioteca':
            loadBiblioteca();
            break;
        case 'tutor':
            loadTutor();
            break;
        case 'ayuda':
            loadMesaAyuda();
            break;
        case 'calendario':
            loadCalendario();
            break;
        case 'idiomas':
            loadIdiomas();
            break;
        case 'tareas':
            loadTareas();
            break;
        case 'contenido':
            loadContenido();
            break;
        case 'administracion':
            loadAdministracion();
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
                ${currentStudent ? '' : editorDeCalificacion(registro)}
            </div>
        `;
    });

    container.innerHTML = html;
    container.querySelectorAll('.calificacion-guardar').forEach(boton => {
        boton.addEventListener('click', () => guardarCalificacion(boton.dataset.registroId, boton.closest('.calificacion-editor')));
    });
}

// Captura de calificación en línea para profesor y staff (la API limita al profesor a sus materias)
function editorDeCalificacion(registro) {
    const opciones = Object.entries(ESTADOS_ESCOLARES).map(([valor, { texto }]) =>
        `<option value="${valor}"${valor === registro.estado ? ' selected' : ''}>${texto}</option>`
    ).join('');
    const valor = registro.calificacion !== null ? Number(registro.calificacion) : '';
    return `
        <div class="calificacion-editor" style="display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; margin-top: 0.75rem;">
            <input type="number" class="calificacion-valor" min="0" max="10" step="0.1" value="${escapeHtml(valor)}"
                   placeholder="0 – 10" aria-label="Calificación" style="${ESTILO_CAMPO} width: 6.5rem;">
            <select class="calificacion-estado" aria-label="Estado" style="${ESTILO_CAMPO} width: auto;">${opciones}</select>
            <button type="button" class="btn btn-primary calificacion-guardar" data-registro-id="${escapeHtml(registro.id)}">Guardar</button>
            <span class="calificacion-mensaje" role="status" style="font-size: 0.85rem;"></span>
        </div>
    `;
}

async function guardarCalificacion(registroId, editor) {
    const mensaje = editor.querySelector('.calificacion-mensaje');
    const boton = editor.querySelector('.calificacion-guardar');
    const valor = editor.querySelector('.calificacion-valor').value.trim();

    mensaje.textContent = '';
    boton.disabled = true;
    try {
        const response = await api(`/control-escolar/${encodeURIComponent(registroId)}/`, {
            method: 'PATCH',
            body: JSON.stringify({
                calificacion: valor === '' ? null : valor,
                estado: editor.querySelector('.calificacion-estado').value,
            }),
        });
        if (response.ok) {
            await loadControlEscolar();
            return;
        }
        mensaje.style.color = 'var(--danger)';
        mensaje.textContent = mensajeDeError(await response.json().catch(() => ({})), 'No se pudo guardar.');
    } catch {
        mensaje.style.color = 'var(--danger)';
        mensaje.textContent = 'No hay conexión con el servidor.';
    }
    boton.disabled = false;
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

// ---------- Utilidades compartidas por las secciones de servicios ----------

const ESTILO_CAMPO = 'width: 100%; padding: 0.75rem; border: 1px solid var(--gray-200); border-radius: 8px; font-family: inherit;';

// "2026-11-01" → "1 de noviembre de 2026". Se arma con la fecha local:
// new Date('2026-11-01') la toma como UTC y en México mostraría el día anterior.
function formatearDia(fechaISO) {
    const [anio, mes, dia] = fechaISO.split('-').map(Number);
    return new Date(anio, mes - 1, dia).toLocaleDateString('es-MX', { day: 'numeric', month: 'long', year: 'numeric' });
}

// Solo enlaces http(s): evita que un "javascript:..." guardado en la base se vuelva clicable
function urlSegura(url) {
    return /^https?:\/\//i.test(url || '') ? url : null;
}

// Mensaje legible a partir de una respuesta de error de DRF ({detail} o errores por campo)
function mensajeDeError(datos, porDefecto) {
    if (datos && datos.detail) return datos.detail;
    const primero = datos && Object.values(datos)[0];
    if (Array.isArray(primero) && primero.length) return primero[0];
    return porDefecto;
}

function errorDeCarga(container, que) {
    container.innerHTML = `<div class="card"><p style="color: red;">No se pudo cargar ${que}.</p></div>`;
}

// ---------- Biblioteca Digital ----------

let recursosBiblioteca = [];

const ICONOS_RECURSO = { libro: '📘', revista: '📰', articulo: '📄', video: '🎬' };

async function loadBiblioteca() {
    const container = document.getElementById('biblioteca-contenido');
    if (!container) return;
    container.innerHTML = '<p>Cargando…</p>';

    try {
        recursosBiblioteca = await getTodas('/biblioteca/');
    } catch (error) {
        console.error('Error cargando biblioteca:', error);
        errorDeCarga(container, 'la biblioteca');
        return;
    }

    container.innerHTML = `
        <div style="display: flex; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 1rem;">
            <input id="biblioteca-buscar" type="search" placeholder="Buscar por título, autor o categoría"
                   aria-label="Buscar en la biblioteca" style="${ESTILO_CAMPO} flex: 1; min-width: 200px; width: auto;">
            <select id="biblioteca-tipo" aria-label="Tipo de recurso" style="${ESTILO_CAMPO} width: auto;">
                <option value="">Todos los tipos</option>
                <option value="libro">Libros</option>
                <option value="revista">Revistas</option>
                <option value="articulo">Artículos</option>
                <option value="video">Videos</option>
            </select>
        </div>
        <div id="biblioteca-resultados"></div>
    `;
    document.getElementById('biblioteca-buscar').addEventListener('input', renderBiblioteca);
    document.getElementById('biblioteca-tipo').addEventListener('change', renderBiblioteca);
    renderBiblioteca();
}

function renderBiblioteca() {
    const texto = document.getElementById('biblioteca-buscar').value.trim().toLowerCase();
    const tipo = document.getElementById('biblioteca-tipo').value;
    const resultados = document.getElementById('biblioteca-resultados');

    const filtrados = recursosBiblioteca.filter(r =>
        (!tipo || r.tipo_recurso === tipo) &&
        (!texto || [r.titulo, r.autor, r.categoria].some(campo => campo.toLowerCase().includes(texto)))
    );

    if (filtrados.length === 0) {
        resultados.innerHTML = recursosBiblioteca.length === 0
            ? '<p>La biblioteca aún no tiene recursos.</p>'
            : '<p>No se encontraron recursos con esos filtros.</p>';
        return;
    }

    resultados.innerHTML = filtrados.map(recurso => {
        const url = urlSegura(recurso.url_recurso);
        return `
            <div class="clase-item">
                <div class="clase-header">
                    <div class="clase-title">${escapeHtml(recurso.titulo)}</div>
                    <div class="clase-badge badge-neutral">${ICONOS_RECURSO[recurso.tipo_recurso] || ''} ${escapeHtml(recurso.tipo_recurso_nombre)}</div>
                </div>
                <div style="color: var(--gray-700); font-size: 0.9rem;">
                    ${escapeHtml(recurso.autor)} · ${escapeHtml(recurso.categoria)} · ${escapeHtml(recurso.fecha_publicacion.slice(0, 4))}
                </div>
                <p style="margin-top: 0.5rem;">${escapeHtml(recurso.descripcion)}</p>
                ${url ? `<a class="btn btn-primary" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer"
                            style="display: inline-block; margin-top: 0.75rem; text-decoration: none;">Abrir recurso ↗</a>` : ''}
            </div>
        `;
    }).join('');
}

// ---------- Mi Tutor ----------

async function loadTutor() {
    const container = document.getElementById('tutor-contenido');
    if (!container) return;
    container.innerHTML = '<div class="card"><p>Cargando…</p></div>';

    let asignaciones;
    try {
        asignaciones = (await getTodas('/asignaciones-tutor/')).filter(a => a.activo);
    } catch (error) {
        console.error('Error cargando tutor:', error);
        errorDeCarga(container, 'la información de tu tutor');
        return;
    }

    if (asignaciones.length === 0) {
        container.innerHTML = '<div class="card"><p>Aún no tienes un tutor asignado. Comunícate con Control Escolar.</p></div>';
        return;
    }

    container.innerHTML = asignaciones.map(asignacion => {
        const iniciales = asignacion.tutor_nombre.split(/\s+/).slice(0, 2).map(p => p.charAt(0)).join('').toUpperCase();
        const cita = `mailto:${encodeURIComponent(asignacion.tutor_email)}?subject=${encodeURIComponent('Solicitud de cita de tutoría')}`;
        return `
            <div class="card" style="margin-bottom: 1rem;">
                <div class="card-header">
                    <div class="user-avatar" style="width: 60px; height: 60px; font-size: 1.5rem;">${escapeHtml(iniciales)}</div>
                    <div>
                        <h3>${escapeHtml(asignacion.tutor_nombre)}</h3>
                        <p style="color: var(--gray-700);">Tutor Académico</p>
                    </div>
                </div>
                <div style="margin-top: 1.5rem;">
                    <p><strong>Email:</strong> <a href="mailto:${escapeHtml(encodeURIComponent(asignacion.tutor_email))}">${escapeHtml(asignacion.tutor_email)}</a></p>
                    <p><strong>Teléfono:</strong> ${escapeHtml(asignacion.tutor_telefono)}</p>
                    <p><strong>Especialidad:</strong> ${escapeHtml(asignacion.tutor_especialidad)}</p>
                </div>
                <a class="btn btn-primary" href="${escapeHtml(cita)}"
                   style="display: inline-block; margin-top: 1.5rem; text-decoration: none;">Solicitar cita por correo</a>
            </div>
        `;
    }).join('');
}

// ---------- Mesa de Ayuda ----------

const BADGES_TICKET = {
    abierto: 'badge-scheduled',
    en_proceso: 'badge-scheduled',
    resuelto: 'badge-completed',
    cerrado: 'badge-neutral',
};

const ESTADOS_TICKET = [
    ['abierto', 'Abierto'],
    ['en_proceso', 'En Proceso'],
    ['resuelto', 'Resuelto'],
    ['cerrado', 'Cerrado'],
];

async function loadMesaAyuda() {
    const container = document.getElementById('ayuda-contenido');
    if (!container) return;
    container.innerHTML = '<div class="card"><p>Cargando…</p></div>';

    let tickets;
    try {
        tickets = await getTodas('/mesa-ayuda/');
    } catch (error) {
        console.error('Error cargando tickets:', error);
        errorDeCarga(container, 'la mesa de ayuda');
        return;
    }

    const esStaff = usuarioActual && usuarioActual.rol === 'staff';
    let html = '';

    if (currentStudent) {
        html += `
            <div class="card" style="margin-bottom: 1.5rem;">
                <h3>Crear Nuevo Ticket</h3>
                <form id="ticket-form" style="margin-top: 1rem;">
                    <div style="margin-bottom: 1rem;">
                        <label for="ticket-categoria" style="display: block; margin-bottom: 0.5rem;">Categoría</label>
                        <select id="ticket-categoria" style="${ESTILO_CAMPO}">
                            <option value="tecnico">Soporte Técnico</option>
                            <option value="academico">Académico</option>
                            <option value="administrativo">Administrativo</option>
                            <option value="otro">Otro</option>
                        </select>
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <label for="ticket-asunto" style="display: block; margin-bottom: 0.5rem;">Asunto</label>
                        <input id="ticket-asunto" type="text" maxlength="200" required
                               placeholder="Describe tu problema brevemente" style="${ESTILO_CAMPO}">
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <label for="ticket-descripcion" style="display: block; margin-bottom: 0.5rem;">Descripción</label>
                        <textarea id="ticket-descripcion" rows="4" required
                                  placeholder="Describe tu problema en detalle" style="${ESTILO_CAMPO}"></textarea>
                    </div>
                    <p id="ticket-error" role="alert" style="color: var(--danger); font-size: 0.85rem; min-height: 1.2em; margin-bottom: 0.5rem;"></p>
                    <button class="btn btn-primary" type="submit" id="ticket-enviar">Enviar Ticket</button>
                </form>
            </div>
        `;
    }

    html += `<div class="clases-list"><h3 style="margin-bottom: 1rem;">${esStaff ? 'Tickets de los estudiantes' : 'Mis tickets'}</h3>`;
    if (tickets.length === 0) {
        html += '<p>No hay tickets.</p>';
    }

    tickets.forEach(ticket => {
        const fecha = new Date(ticket.fecha_creacion).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' });
        html += `
            <div class="clase-item">
                <div class="clase-header">
                    <div class="clase-title">${escapeHtml(ticket.asunto)}</div>
                    <div class="clase-badge ${BADGES_TICKET[ticket.estado] || 'badge-neutral'}">${escapeHtml(ticket.estado_nombre)}</div>
                </div>
                <div style="color: var(--gray-700); font-size: 0.85rem;">
                    ${escapeHtml(ticket.categoria_nombre)} · ${escapeHtml(fecha)}
                    ${esStaff ? ` · ${escapeHtml(ticket.estudiante_nombre)} ${escapeHtml(ticket.estudiante_apellido)}` : ''}
                </div>
                <p style="margin-top: 0.5rem; white-space: pre-wrap; overflow-wrap: anywhere;">${escapeHtml(ticket.descripcion)}</p>
                ${esStaff ? editorDeTicket(ticket) : (ticket.respuesta ? `
                    <div style="margin-top: 0.75rem; padding: 0.75rem; background: var(--gray-100); border-radius: 8px;">
                        <strong>Respuesta de soporte:</strong>
                        <p style="margin-top: 0.25rem; white-space: pre-wrap; overflow-wrap: anywhere;">${escapeHtml(ticket.respuesta)}</p>
                    </div>` : '')}
            </div>
        `;
    });
    html += '</div>';

    container.innerHTML = html;

    const form = document.getElementById('ticket-form');
    if (form) form.addEventListener('submit', enviarTicket);
    container.querySelectorAll('.ticket-guardar').forEach(boton => {
        boton.addEventListener('click', () => responderTicket(boton.dataset.ticketId, boton.closest('.ticket-editor')));
    });
}

function editorDeTicket(ticket) {
    const opciones = ESTADOS_TICKET.map(([valor, nombre]) =>
        `<option value="${valor}"${valor === ticket.estado ? ' selected' : ''}>${nombre}</option>`
    ).join('');
    return `
        <div class="ticket-editor" style="margin-top: 0.75rem; padding: 0.75rem; background: var(--gray-100); border-radius: 8px;">
            <label style="display: block; margin-bottom: 0.25rem; font-size: 0.85rem;">Estado</label>
            <select class="ticket-estado" style="${ESTILO_CAMPO} margin-bottom: 0.5rem; background: white;">${opciones}</select>
            <label style="display: block; margin-bottom: 0.25rem; font-size: 0.85rem;">Respuesta al estudiante</label>
            <textarea class="ticket-respuesta" rows="2" style="${ESTILO_CAMPO} background: white;">${escapeHtml(ticket.respuesta)}</textarea>
            <p class="ticket-error" role="alert" style="color: var(--danger); font-size: 0.85rem; min-height: 1.2em; margin: 0.25rem 0;"></p>
            <button type="button" class="btn btn-primary ticket-guardar" data-ticket-id="${escapeHtml(ticket.id)}">Guardar</button>
        </div>
    `;
}

async function enviarTicket(evento) {
    evento.preventDefault();
    const error = document.getElementById('ticket-error');
    const boton = document.getElementById('ticket-enviar');
    const datos = {
        categoria: document.getElementById('ticket-categoria').value,
        asunto: document.getElementById('ticket-asunto').value.trim(),
        descripcion: document.getElementById('ticket-descripcion').value.trim(),
    };

    if (!datos.asunto || !datos.descripcion) {
        error.textContent = 'Escribe el asunto y la descripción.';
        return;
    }

    error.textContent = '';
    boton.disabled = true;
    try {
        const response = await api('/mesa-ayuda/', { method: 'POST', body: JSON.stringify(datos) });
        if (response.ok) {
            await loadMesaAyuda();
            return;
        }
        error.textContent = mensajeDeError(await response.json().catch(() => ({})), 'No se pudo enviar el ticket.');
    } catch {
        error.textContent = 'No hay conexión con el servidor.';
    }
    boton.disabled = false;
}

async function responderTicket(ticketId, editor) {
    const error = editor.querySelector('.ticket-error');
    const boton = editor.querySelector('.ticket-guardar');
    error.textContent = '';
    boton.disabled = true;
    try {
        const response = await api(`/mesa-ayuda/${encodeURIComponent(ticketId)}/`, {
            method: 'PATCH',
            body: JSON.stringify({
                estado: editor.querySelector('.ticket-estado').value,
                respuesta: editor.querySelector('.ticket-respuesta').value.trim(),
            }),
        });
        if (response.ok) {
            await loadMesaAyuda();
            return;
        }
        error.textContent = mensajeDeError(await response.json().catch(() => ({})), 'No se pudo guardar.');
    } catch {
        error.textContent = 'No hay conexión con el servidor.';
    }
    boton.disabled = false;
}

// ---------- Calendario ----------

const BADGES_EVENTO = {
    examen: 'badge-live',
    entrega: 'badge-scheduled',
    clase: 'badge-completed',
    evento: 'badge-completed',
};

async function loadCalendario() {
    const container = document.getElementById('calendario-contenido');
    if (!container) return;
    container.innerHTML = '<p>Cargando…</p>';

    let eventos;
    try {
        eventos = await getTodas('/calendario/?proximos=1');
    } catch (error) {
        console.error('Error cargando calendario:', error);
        errorDeCarga(container, 'el calendario');
        return;
    }

    let html = '<h3 style="margin-bottom: 1rem;">Próximos Eventos</h3>';
    if (eventos.length === 0) {
        html += '<p>No hay eventos próximos.</p>';
    }

    eventos.forEach(evento => {
        const inicio = new Date(evento.fecha_inicio);
        const fin = new Date(evento.fecha_fin);
        const hora = { hour: '2-digit', minute: '2-digit' };
        const horario = inicio.toDateString() === fin.toDateString()
            ? `${inicio.toLocaleTimeString('es-MX', hora)} – ${fin.toLocaleTimeString('es-MX', hora)}`
            : `hasta el ${fin.toLocaleDateString('es-MX', { day: 'numeric', month: 'short' })}`;
        html += `
            <div class="clase-item">
                <div class="clase-header">
                    <div class="clase-title">${escapeHtml(evento.titulo)}</div>
                    <div class="clase-badge ${BADGES_EVENTO[evento.tipo_evento] || 'badge-completed'}">
                        ${escapeHtml(inicio.toLocaleDateString('es-MX', { day: 'numeric', month: 'short', year: 'numeric' }))}
                    </div>
                </div>
                <div style="color: var(--gray-700); font-size: 0.85rem;">${escapeHtml(evento.tipo_evento_nombre)} · ${escapeHtml(horario)}</div>
                <div style="margin-top: 0.25rem;">${escapeHtml(evento.descripcion)}</div>
            </div>
        `;
    });

    container.innerHTML = html;
}

// ---------- Centro de Idiomas ----------

let cursosIdiomas = [];

const ESTILO_IDIOMA = {
    ingles: { bandera: '🇬🇧', fondo: '#dbeafe' },
    frances: { bandera: '🇫🇷', fondo: '#fef3c7' },
    aleman: { bandera: '🇩🇪', fondo: '#fce7f3' },
    italiano: { bandera: '🇮🇹', fondo: '#dcfce7' },
    japones: { bandera: '🇯🇵', fondo: '#fee2e2' },
    mandarin: { bandera: '🇨🇳', fondo: '#fef9c3' },
};

const formatoPrecio = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN' });

async function loadIdiomas() {
    const container = document.getElementById('idiomas-contenido');
    if (!container) return;
    container.innerHTML = '<div class="card"><p>Cargando…</p></div>';

    try {
        cursosIdiomas = await getTodas('/idiomas/');
    } catch (error) {
        console.error('Error cargando idiomas:', error);
        errorDeCarga(container, 'el centro de idiomas');
        return;
    }
    renderIdiomas();
}

function renderIdiomas() {
    const container = document.getElementById('idiomas-contenido');
    if (cursosIdiomas.length === 0) {
        container.innerHTML = '<div class="card"><p>No hay cursos de idiomas disponibles por ahora.</p></div>';
        return;
    }

    container.innerHTML = '<div class="cards-grid">' + cursosIdiomas.map(curso => {
        const estilo = ESTILO_IDIOMA[curso.idioma] || { bandera: '🌎', fondo: '#e0e7ff' };
        const cupos = curso.cupos_disponibles;

        let accion = '';
        if (currentStudent) {
            if (curso.inscrito) {
                accion = `
                    <p style="margin-top: 1rem; color: var(--success); font-weight: 600;">✅ Estás inscrito</p>
                    <button type="button" class="btn-salir idioma-accion" data-accion="cancelar" data-curso-id="${escapeHtml(curso.id)}"
                            style="margin-top: 0.5rem; width: 100%;">Cancelar inscripción</button>`;
            } else if (cupos <= 0) {
                accion = '<button type="button" class="btn btn-primary" disabled style="margin-top: 1rem; width: 100%; opacity: 0.6;">Sin cupo</button>';
            } else {
                accion = `
                    <button type="button" class="btn btn-primary idioma-accion" data-accion="inscribir" data-curso-id="${escapeHtml(curso.id)}"
                            style="margin-top: 1rem; width: 100%;">Inscribirme</button>`;
            }
            accion += '<p class="idioma-error" role="alert" style="color: var(--danger); font-size: 0.85rem; margin-top: 0.5rem;"></p>';
        }

        return `
            <div class="card">
                <div class="card-header">
                    <div class="card-icon" style="background: ${estilo.fondo};">${estilo.bandera}</div>
                    <div class="card-title">${escapeHtml(curso.nombre_curso)}</div>
                </div>
                <div class="card-description">
                    <p>${escapeHtml(curso.idioma_nombre)} · Nivel ${escapeHtml(curso.nivel_nombre.toLowerCase())}</p>
                    <p style="margin-top: 0.5rem;">${escapeHtml(curso.descripcion)}</p>
                    <p style="margin-top: 0.5rem;"><strong>Instructor:</strong> ${escapeHtml(curso.instructor)}</p>
                    <p><strong>Inicio:</strong> ${escapeHtml(formatearDia(curso.fecha_inicio))} · ${escapeHtml(curso.duracion_semanas)} semanas</p>
                    <p><strong>Costo:</strong> ${escapeHtml(formatoPrecio.format(Number(curso.precio)))}</p>
                    <p><strong>Cupos disponibles:</strong> ${escapeHtml(Math.max(cupos, 0))} de ${escapeHtml(curso.cupo_maximo)}</p>
                    ${accion}
                </div>
            </div>
        `;
    }).join('') + '</div>';

    container.querySelectorAll('.idioma-accion').forEach(boton => {
        boton.addEventListener('click', () => cambiarInscripcion(boton));
    });
}

async function cambiarInscripcion(boton) {
    const { accion, cursoId } = boton.dataset;
    if (accion === 'cancelar' && !confirm('¿Cancelar tu inscripción a este curso?')) return;

    const error = boton.parentElement.querySelector('.idioma-error');
    error.textContent = '';
    boton.disabled = true;
    try {
        const response = await api(`/idiomas/${encodeURIComponent(cursoId)}/${accion}/`, { method: 'POST' });
        const datos = await response.json().catch(() => ({}));
        if (response.ok) {
            // La API devuelve el curso actualizado (cupos e "inscrito")
            cursosIdiomas = cursosIdiomas.map(c => (String(c.id) === cursoId ? datos : c));
            renderIdiomas();
            return;
        }
        error.textContent = mensajeDeError(datos, 'No se pudo completar la operación.');
    } catch {
        error.textContent = 'No hay conexión con el servidor.';
    }
    boton.disabled = false;
}

// ---------- Tareas ----------

const BADGES_TAREA = {
    pendiente: 'badge-scheduled',
    en_progreso: 'badge-scheduled',
    completada: 'badge-completed',
};

const ESTADOS_TAREA = [
    ['pendiente', 'Pendiente'],
    ['en_progreso', 'En progreso'],
    ['completada', 'Completada'],
];

function puedeGestionarTareas() {
    return Boolean(usuarioActual) && ['profesor', 'staff'].includes(usuarioActual.rol);
}

// Valor por defecto del campo de fecha: mañana a las 23:59, en hora local
function mananaAlFinalDelDia() {
    const fecha = new Date();
    fecha.setDate(fecha.getDate() + 1);
    fecha.setHours(23, 59, 0, 0);
    const dos = n => String(n).padStart(2, '0');
    return `${fecha.getFullYear()}-${dos(fecha.getMonth() + 1)}-${dos(fecha.getDate())}T23:59`;
}

async function loadTareas() {
    const container = document.getElementById('tareas-contenido');
    if (!container) return;
    container.innerHTML = '<div class="card"><p>Cargando…</p></div>';

    let lista;
    try {
        lista = await getTodas('/tareas/');
    } catch (error) {
        console.error('Error cargando tareas:', error);
        errorDeCarga(container, 'las tareas');
        return;
    }

    let html = '';
    if (puedeGestionarTareas()) {
        const opcionesCurso = courses.map(c => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.nombre)} (${escapeHtml(c.codigo)})</option>`).join('');
        html += courses.length === 0
            ? '<div class="card" style="margin-bottom: 1.5rem;"><p>No tienes cursos asignados para crear tareas.</p></div>'
            : `
            <div class="card" style="margin-bottom: 1.5rem;">
                <h3>Nueva tarea</h3>
                <form id="tarea-form" style="margin-top: 1rem;">
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 1rem;">
                        <div>
                            <label for="tarea-curso" style="display: block; margin-bottom: 0.5rem;">Curso</label>
                            <select id="tarea-curso" style="${ESTILO_CAMPO}">${opcionesCurso}</select>
                        </div>
                        <div>
                            <label for="tarea-vence" style="display: block; margin-bottom: 0.5rem;">Fecha de entrega</label>
                            <input id="tarea-vence" type="datetime-local" required value="${mananaAlFinalDelDia()}" style="${ESTILO_CAMPO}">
                        </div>
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <label for="tarea-titulo" style="display: block; margin-bottom: 0.5rem;">Título</label>
                        <input id="tarea-titulo" type="text" maxlength="200" required style="${ESTILO_CAMPO}">
                    </div>
                    <div style="margin-bottom: 1rem;">
                        <label for="tarea-descripcion" style="display: block; margin-bottom: 0.5rem;">Instrucciones</label>
                        <textarea id="tarea-descripcion" rows="3" required style="${ESTILO_CAMPO}"></textarea>
                    </div>
                    <p id="tarea-error" role="alert" style="color: var(--danger); font-size: 0.85rem; min-height: 1.2em; margin-bottom: 0.5rem;"></p>
                    <button class="btn btn-primary" type="submit" id="tarea-crear">Crear tarea</button>
                </form>
            </div>
        `;
    }

    html += `<div class="clases-list"><h3 style="margin-bottom: 1rem;">${puedeGestionarTareas() ? 'Tareas de mis cursos' : 'Mis tareas'}</h3>`;
    if (lista.length === 0) {
        html += '<p>No hay tareas.</p>';
    }

    const ahora = new Date();
    lista.forEach(tarea => {
        const vence = new Date(tarea.fecha_vencimiento);
        // El alumno ve su propio estado; profesor y staff, el avance del grupo
        let badge;
        if (tarea.resumen) {
            const { completadas, alumnos } = tarea.resumen;
            const clase = alumnos > 0 && completadas === alumnos ? 'badge-completed' : (vence < ahora ? 'badge-live' : 'badge-scheduled');
            badge = `<div class="clase-badge ${clase}">${escapeHtml(completadas)}/${escapeHtml(alumnos)} completadas</div>`;
        } else {
            const vencida = vence < ahora && tarea.estado !== 'completada';
            badge = `<div class="clase-badge ${vencida ? 'badge-live' : (BADGES_TAREA[tarea.estado] || 'badge-neutral')}">
                        ${vencida ? 'Vencida' : escapeHtml(tarea.estado_nombre)}
                    </div>`;
        }
        html += `
            <div class="clase-item">
                <div class="clase-header">
                    <div class="clase-title">${escapeHtml(tarea.titulo)}</div>
                    ${badge}
                </div>
                <div style="color: var(--gray-700); font-size: 0.85rem;">
                    ${escapeHtml(tarea.curso_nombre)} · Entrega: ${escapeHtml(vence.toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' }))}
                </div>
                <p style="margin-top: 0.5rem; white-space: pre-wrap; overflow-wrap: anywhere;">${escapeHtml(tarea.descripcion)}</p>
                ${puedeGestionarTareas() ? `
                    <div style="margin-top: 0.75rem; display: flex; gap: 1rem;">
                        <button type="button" class="tarea-ver-entregas" data-tarea-id="${escapeHtml(tarea.id)}"
                                style="${ESTILO_ACCION}">Ver entregas (${escapeHtml(tarea.resumen.con_archivos)} con archivos)</button>
                        <button type="button" class="tarea-eliminar" data-tarea-id="${escapeHtml(tarea.id)}"
                                style="${ESTILO_ACCION} color: var(--danger);">Eliminar</button>
                    </div>
                    <div class="tarea-entregas" id="entregas-${escapeHtml(tarea.id)}" hidden></div>` : ''}
                ${currentStudent ? `
                    <label style="display: block; margin-top: 0.75rem; font-size: 0.85rem;">Mi avance:
                        <select class="tarea-estado" data-tarea-id="${escapeHtml(tarea.id)}" style="${ESTILO_CAMPO} width: auto; margin-left: 0.5rem;">
                            ${ESTADOS_TAREA.map(([valor, nombre]) =>
                                `<option value="${valor}"${valor === tarea.estado ? ' selected' : ''}>${nombre}</option>`).join('')}
                        </select>
                    </label>
                    ${htmlMiEntrega(tarea)}` : ''}
            </div>
        `;
    });
    html += '</div>';

    container.innerHTML = html;
    const form = document.getElementById('tarea-form');
    if (form) form.addEventListener('submit', crearTarea);
    container.querySelectorAll('.tarea-eliminar').forEach(boton => {
        boton.addEventListener('click', () => eliminarTarea(boton.dataset.tareaId));
    });
    container.querySelectorAll('.tarea-estado').forEach(selector => {
        selector.addEventListener('change', () => cambiarEstadoTarea(selector));
    });
    container.querySelectorAll('.tarea-archivo').forEach(entrada => {
        entrada.addEventListener('change', () => entregarArchivos(entrada));
    });
    container.querySelectorAll('.entrega-quitar').forEach(boton => {
        boton.addEventListener('click', () => quitarArchivoEntrega(boton.dataset.archivoId));
    });
    container.querySelectorAll('.tarea-ver-entregas').forEach(boton => {
        boton.addEventListener('click', () => verEntregas(boton.dataset.tareaId));
    });
}

function fechaCorta(iso) {
    return new Date(iso).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' });
}

function htmlArchivosEntrega(archivos, conQuitar) {
    return archivos.map(archivo => `
        <div style="display: flex; justify-content: space-between; gap: 1rem; padding: 0.25rem 0; font-size: 0.85rem;">
            <a href="${escapeHtml(archivo.url)}" target="_blank" rel="noopener" style="overflow-wrap: anywhere;">
                ${ICONOS_DOCUMENTO[extensionDe(archivo.nombre)] || (archivo.tipo === 'imagen' ? '🖼️' : archivo.tipo === 'video' ? '🎬' : '📄')}
                ${escapeHtml(archivo.nombre)}
            </a>
            <span style="color: var(--gray-700); white-space: nowrap;">${escapeHtml(formatoTamano(archivo.tamano))}
                ${conQuitar ? `<button type="button" class="entrega-quitar" data-archivo-id="${escapeHtml(archivo.id)}"
                        style="${ESTILO_ACCION} color: var(--danger); margin-left: 0.5rem;">Quitar</button>` : ''}
            </span>
        </div>
    `).join('');
}

function etiquetaEntrega(entrega) {
    if (!entrega.entregado) return '';
    return `Entregada el ${escapeHtml(fechaCorta(entrega.entregado))}`
        + (entrega.tarde ? ' · <strong style="color: var(--danger);">tarde</strong>' : '');
}

// Bloque de entrega del alumno: lo que ya subió y el selector para subir más
function htmlMiEntrega(tarea) {
    const aceptados = Object.keys(FORMATOS_ADJUNTO).map(e => `.${e}`).join(',');
    return `
        <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid var(--gray-200);">
            <div style="font-size: 0.85rem; font-weight: 600; margin-bottom: 0.25rem;">Mi entrega</div>
            ${tarea.entregado ? `<p style="font-size: 0.85rem; margin-bottom: 0.25rem;">${etiquetaEntrega(tarea)}</p>` : ''}
            ${htmlArchivosEntrega(tarea.archivos, true)}
            <label style="display: block; margin-top: 0.5rem; font-size: 0.85rem;">
                ${tarea.archivos.length ? 'Agregar archivos' : 'Subir archivos para entregar'}
                <input type="file" multiple class="tarea-archivo" data-tarea-id="${escapeHtml(tarea.id)}" accept="${aceptados}"
                       style="${ESTILO_CAMPO} margin-top: 0.25rem;">
            </label>
            <div style="color: var(--gray-700); font-size: 0.75rem; margin-top: 0.25rem;">
                PDF y Office (hasta ${LIMITE_ADJUNTO_MB.documento} MB) · imágenes (hasta ${LIMITE_ADJUNTO_MB.imagen} MB) · MP4 y WebM (hasta ${LIMITE_ADJUNTO_MB.video} MB)
            </div>
            <p class="tarea-subida" role="status" style="font-size: 0.85rem; margin-top: 0.25rem; white-space: pre-line;"></p>
        </div>
    `;
}

async function entregarArchivos(entrada) {
    const archivos = Array.from(entrada.files);
    const aviso = entrada.closest('div').querySelector('.tarea-subida');
    const invalidos = archivos.map(a => [a, problemaDeAdjunto(a)]).filter(([, problema]) => problema);
    if (invalidos.length) {
        aviso.style.color = 'var(--danger)';
        aviso.textContent = invalidos.map(([a, problema]) => `${a.name}: ${problema}`).join('\n');
        entrada.value = '';
        return;
    }

    entrada.disabled = true;
    aviso.style.color = '';
    const fallidos = [];
    for (const [indice, archivo] of archivos.entries()) {
        const prefijo = `Subiendo ${indice + 1} de ${archivos.length}: ${archivo.name}`;
        aviso.textContent = prefijo + '…';
        const resultado = await subirAdjunto(`/tareas/${encodeURIComponent(entrada.dataset.tareaId)}/entregar/`, archivo,
            fraccion => { aviso.textContent = `${prefijo} (${Math.round(fraccion * 100)}%)`; });
        if (!resultado.ok) fallidos.push(`${archivo.name}: ${mensajeDeError(resultado.datos, 'Error al subir')}`);
    }

    await loadTasks();
    updateDashboard(usuarioActual);
    await loadTareas();
    if (fallidos.length) {
        alert('Algunos archivos no se subieron:\n' + fallidos.join('\n'));
    }
}

async function quitarArchivoEntrega(archivoId) {
    if (!confirm('¿Quitar este archivo de tu entrega?')) return;
    try {
        const response = await api(`/archivos-entrega/${encodeURIComponent(archivoId)}/`, { method: 'DELETE' });
        if (!response.ok) {
            alert(mensajeDeError(await response.json().catch(() => ({})), 'No se pudo quitar el archivo.'));
            return;
        }
    } catch {
        alert('No hay conexión con el servidor.');
        return;
    }
    await loadTareas();
}

// Profesor y staff: lista de alumnos inscritos con su avance y archivos (se abre y cierra con el mismo botón)
async function verEntregas(tareaId) {
    const panel = document.getElementById(`entregas-${tareaId}`);
    if (!panel.hidden) {
        panel.hidden = true;
        return;
    }
    panel.hidden = false;
    panel.innerHTML = '<p style="margin-top: 0.75rem;">Cargando…</p>';

    let filas;
    try {
        const response = await api(`/tareas/${encodeURIComponent(tareaId)}/entregas/`);
        if (!response.ok) throw new Error(response.status);
        filas = await response.json();
    } catch (error) {
        console.error('Error cargando entregas:', error);
        panel.innerHTML = '<p style="margin-top: 0.75rem; color: var(--danger);">No se pudieron cargar las entregas.</p>';
        return;
    }

    panel.innerHTML = filas.length === 0
        ? '<p style="margin-top: 0.75rem;">No hay alumnos inscritos.</p>'
        : filas.map(fila => `
            <div style="margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid var(--gray-200);">
                <div style="display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap;">
                    <strong>${escapeHtml(fila.nombre)} <span style="font-weight: normal; color: var(--gray-700); font-size: 0.85rem;">${escapeHtml(fila.matricula)}</span></strong>
                    <span class="clase-badge ${BADGES_TAREA[fila.estado] || 'badge-neutral'}">${escapeHtml(fila.estado_nombre)}</span>
                </div>
                ${fila.entregado ? `<p style="font-size: 0.85rem;">${etiquetaEntrega(fila)}</p>` : ''}
                ${fila.archivos.length ? htmlArchivosEntrega(fila.archivos, false)
                                       : '<p style="font-size: 0.85rem; color: var(--gray-700);">Sin archivos.</p>'}
            </div>
        `).join('');
}

async function cambiarEstadoTarea(selector) {
    selector.disabled = true;
    try {
        const response = await api(`/tareas/${encodeURIComponent(selector.dataset.tareaId)}/estado/`, {
            method: 'POST',
            body: JSON.stringify({ estado: selector.value }),
        });
        if (!response.ok) {
            alert(mensajeDeError(await response.json().catch(() => ({})), 'No se pudo guardar tu avance.'));
        }
    } catch {
        alert('No hay conexión con el servidor.');
    }
    // Se recarga para reflejar el badge y el contador de pendientes del inicio
    await loadTasks();
    updateDashboard(usuarioActual);
    await loadTareas();
}

async function crearTarea(evento) {
    evento.preventDefault();
    const error = document.getElementById('tarea-error');
    const boton = document.getElementById('tarea-crear');
    const datos = {
        curso: document.getElementById('tarea-curso').value,
        titulo: document.getElementById('tarea-titulo').value.trim(),
        descripcion: document.getElementById('tarea-descripcion').value.trim(),
        // datetime-local viene en hora local; se envía en ISO (UTC) para que el servidor no la reinterprete
        fecha_vencimiento: new Date(document.getElementById('tarea-vence').value).toISOString(),
    };

    if (!datos.titulo || !datos.descripcion) {
        error.textContent = 'Escribe el título y las instrucciones.';
        return;
    }

    error.textContent = '';
    boton.disabled = true;
    try {
        const response = await api('/tareas/', { method: 'POST', body: JSON.stringify(datos) });
        if (response.ok) {
            await loadTareas();
            return;
        }
        error.textContent = mensajeDeError(await response.json().catch(() => ({})), 'No se pudo crear la tarea.');
    } catch {
        error.textContent = 'No hay conexión con el servidor.';
    }
    boton.disabled = false;
}

async function eliminarTarea(tareaId) {
    if (!confirm('¿Eliminar esta tarea? No se puede deshacer.')) return;
    try {
        const response = await api(`/tareas/${encodeURIComponent(tareaId)}/`, { method: 'DELETE' });
        if (!response.ok) {
            alert(mensajeDeError(await response.json().catch(() => ({})), 'No se pudo eliminar la tarea.'));
            return;
        }
    } catch {
        alert('No hay conexión con el servidor.');
        return;
    }
    await loadTareas();
}

// ---------- Administración (solo staff) ----------

const NIVELES_EDUCATIVOS = [
    ['preparatoria', 'Preparatoria'],
    ['tsu', 'Técnico Superior Universitario'],
    ['licenciatura', 'Carrera Profesional'],
    ['maestria', 'Maestría'],
    ['doctorado', 'Doctorado'],
];

function campoAlta(id, etiqueta, atributos = '') {
    return `
        <div>
            <label for="alta-${id}" style="display: block; margin-bottom: 0.5rem;">${etiqueta}</label>
            <input id="alta-${id}" name="${id}" ${atributos} style="${ESTILO_CAMPO}">
        </div>
    `;
}

async function loadAdministracion() {
    const container = document.getElementById('administracion-contenido');
    if (!container) return;

    const opcionesNivel = NIVELES_EDUCATIVOS.map(([valor, nombre]) =>
        `<option value="${valor}"${valor === 'licenciatura' ? ' selected' : ''}>${nombre}</option>`).join('');
    const opcionesCurso = courses.map(c => `<option value="${escapeHtml(c.id)}">${escapeHtml(c.nombre)} (${escapeHtml(c.codigo)})</option>`).join('');

    container.innerHTML = `
        <div class="card" style="margin-bottom: 1.5rem;">
            <h3>Alta de estudiante</h3>
            <p style="color: var(--gray-700); font-size: 0.9rem; margin-top: 0.25rem;">
                Crea el expediente, la cuenta de acceso (usuario = matrícula) y el perfil académico.
            </p>
            <form id="alta-form" style="margin-top: 1rem;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1rem; margin-bottom: 1rem;">
                    ${campoAlta('nombre', 'Nombre', 'required maxlength="100"')}
                    ${campoAlta('apellido', 'Apellido', 'required maxlength="100"')}
                    ${campoAlta('matricula', 'Matrícula', 'required maxlength="50"')}
                    ${campoAlta('email', 'Correo', 'type="email" required')}
                    ${campoAlta('telefono', 'Teléfono (opcional)', 'type="tel" maxlength="20"')}
                    <div>
                        <label for="alta-nivel_educativo" style="display: block; margin-bottom: 0.5rem;">Nivel</label>
                        <select id="alta-nivel_educativo" name="nivel_educativo" style="${ESTILO_CAMPO}">${opcionesNivel}</select>
                    </div>
                    ${campoAlta('programa', 'Programa', 'required maxlength="200" placeholder="Licenciatura en …"')}
                    ${campoAlta('periodo_actual', 'Periodo', 'required maxlength="50" placeholder="2026-2"')}
                    ${campoAlta('materias_totales', 'Materias del plan', 'type="number" min="0" value="40"')}
                </div>
                <p id="alta-error" role="alert" style="color: var(--danger); font-size: 0.85rem; min-height: 1.2em; margin-bottom: 0.5rem;"></p>
                <button class="btn btn-primary" type="submit" id="alta-enviar">Dar de alta</button>
            </form>
            <div id="alta-resultado"></div>
        </div>

        <div class="card">
            <h3>Inscripción a cursos</h3>
            ${courses.length === 0 ? '<p style="margin-top: 1rem;">No hay cursos registrados.</p>' : `
                <div style="margin-top: 1rem;">
                    <label for="inscripcion-curso" style="display: block; margin-bottom: 0.5rem;">Curso</label>
                    <select id="inscripcion-curso" style="${ESTILO_CAMPO}">${opcionesCurso}</select>
                </div>
                <div id="inscripcion-detalle" style="margin-top: 1rem;"></div>
            `}
        </div>

        ${tarjetaMaterias(opcionesCurso)}
    `;

    document.getElementById('alta-form').addEventListener('submit', darDeAlta);
    const selectCurso = document.getElementById('inscripcion-curso');
    if (selectCurso) {
        selectCurso.addEventListener('change', cargarInscripcion);
        await cargarInscripcion();
    }
    const selectMaterias = document.getElementById('materias-curso');
    if (selectMaterias) {
        selectMaterias.addEventListener('change', renderMaterias);
        document.getElementById('materia-form').addEventListener('submit', crearMateria);
        await cargarMaterias();
    }
}

// ---------- Materias (dentro de Administración) ----------

let materiasAdmin = [];

// Periodo en curso con el formato AAAA-N: enero-junio = 1, julio-diciembre = 2
function periodoActual() {
    const hoy = new Date();
    return `${hoy.getFullYear()}-${hoy.getMonth() < 6 ? 1 : 2}`;
}

function tarjetaMaterias(opcionesCurso) {
    if (courses.length === 0) return '';
    const etiqueta = 'display: block; margin-bottom: 0.5rem;';
    return `
        <div class="card" style="margin-top: 1.5rem;">
            <h3>Materias</h3>
            <p style="color: var(--gray-700); font-size: 0.9rem; margin-top: 0.25rem;">
                Crea las materias de cada curso e inscribe al grupo en un periodo; así aparecen en Control Escolar para calificarlas.
            </p>
            <div style="margin-top: 1rem;">
                <label for="materias-curso" style="${etiqueta}">Curso</label>
                <select id="materias-curso" style="${ESTILO_CAMPO}">${opcionesCurso}</select>
            </div>

            <form id="materia-form" style="margin-top: 1rem; padding: 1rem; background: var(--gray-100); border-radius: 8px;">
                <h4 style="margin-bottom: 0.75rem;">Nueva materia</h4>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; margin-bottom: 1rem;">
                    <div style="grid-column: span 2;">
                        <label for="materia-nombre" style="${etiqueta}">Nombre</label>
                        <input id="materia-nombre" required maxlength="200" style="${ESTILO_CAMPO} background: white;">
                    </div>
                    <div>
                        <label for="materia-codigo" style="${etiqueta}">Código</label>
                        <input id="materia-codigo" required maxlength="50" placeholder="ADM101-3" style="${ESTILO_CAMPO} background: white;">
                    </div>
                    <div>
                        <label for="materia-creditos" style="${etiqueta}">Créditos</label>
                        <input id="materia-creditos" type="number" min="0" required value="6" style="${ESTILO_CAMPO} background: white;">
                    </div>
                    <div>
                        <label for="materia-nivel" style="${etiqueta}">Nivel (semestre)</label>
                        <input id="materia-nivel" type="number" min="1" required value="1" style="${ESTILO_CAMPO} background: white;">
                    </div>
                </div>
                <div style="margin-bottom: 1rem;">
                    <label for="materia-descripcion" style="${etiqueta}">Descripción</label>
                    <textarea id="materia-descripcion" rows="2" required style="${ESTILO_CAMPO} background: white;"></textarea>
                </div>
                <p id="materia-error" role="alert" style="color: var(--danger); font-size: 0.85rem; min-height: 1.2em; margin-bottom: 0.5rem;"></p>
                <button class="btn btn-primary" type="submit" id="materia-crear">Crear materia</button>
            </form>

            <div style="display: flex; gap: 0.75rem; align-items: center; flex-wrap: wrap; margin-top: 1.5rem;">
                <label for="materias-periodo">Periodo para inscribir al grupo:</label>
                <input id="materias-periodo" value="${periodoActual()}" placeholder="AAAA-N" maxlength="7"
                       style="${ESTILO_CAMPO} width: 7rem;">
            </div>
            <div id="materias-lista" style="margin-top: 1rem;"><p>Cargando…</p></div>
        </div>
    `;
}

async function cargarMaterias() {
    try {
        materiasAdmin = await getTodas('/materias/');
    } catch (error) {
        console.error('Error cargando materias:', error);
        document.getElementById('materias-lista').innerHTML = '<p style="color: red;">No se pudieron cargar las materias.</p>';
        return;
    }
    renderMaterias();
}

function renderMaterias() {
    const lista = document.getElementById('materias-lista');
    const cursoId = document.getElementById('materias-curso').value;
    const delCurso = materiasAdmin.filter(m => String(m.curso) === cursoId);

    if (delCurso.length === 0) {
        lista.innerHTML = '<p>Este curso aún no tiene materias.</p>';
        return;
    }

    lista.innerHTML = delCurso.map(materia => `
        <div class="clase-item" data-materia-id="${escapeHtml(materia.id)}">
            <div class="clase-header">
                <div class="clase-title">${escapeHtml(materia.codigo)} · ${escapeHtml(materia.nombre)}</div>
                <div class="clase-badge ${materia.activo ? 'badge-completed' : 'badge-neutral'}">${materia.activo ? 'Activa' : 'Inactiva'}</div>
            </div>
            <div style="color: var(--gray-700); font-size: 0.85rem;">Nivel ${escapeHtml(materia.nivel)} · ${escapeHtml(materia.creditos)} créditos</div>
            <p style="margin-top: 0.25rem;">${escapeHtml(materia.descripcion)}</p>
            <div style="display: flex; gap: 1rem; align-items: center; flex-wrap: wrap; margin-top: 0.75rem;">
                ${materia.activo ? `<button type="button" class="btn btn-primary materia-inscribir">Inscribir al grupo</button>` : ''}
                <button type="button" class="materia-activo" style="${ESTILO_ACCION} color: ${materia.activo ? 'var(--danger)' : 'var(--primary)'};">
                    ${materia.activo ? 'Desactivar' : 'Activar'}
                </button>
                <span class="materia-mensaje" role="status" style="font-size: 0.85rem;"></span>
            </div>
        </div>
    `).join('');

    lista.querySelectorAll('.clase-item').forEach(item => {
        const materia = delCurso.find(m => String(m.id) === item.dataset.materiaId);
        const inscribir = item.querySelector('.materia-inscribir');
        if (inscribir) inscribir.addEventListener('click', () => inscribirGrupo(materia, item));
        item.querySelector('.materia-activo').addEventListener('click', () => cambiarActivoMateria(materia));
    });
}

async function crearMateria(evento) {
    evento.preventDefault();
    const error = document.getElementById('materia-error');
    const boton = document.getElementById('materia-crear');
    const valor = id => document.getElementById(id).value.trim();
    const datos = {
        curso: document.getElementById('materias-curso').value,
        nombre: valor('materia-nombre'),
        codigo: valor('materia-codigo'),
        creditos: Number(valor('materia-creditos')),
        nivel: Number(valor('materia-nivel')),
        descripcion: valor('materia-descripcion'),
    };

    if (!datos.nombre || !datos.codigo || !datos.descripcion) {
        error.textContent = 'Completa el nombre, el código y la descripción.';
        return;
    }

    error.textContent = '';
    boton.disabled = true;
    try {
        const response = await api('/materias/', { method: 'POST', body: JSON.stringify(datos) });
        if (response.ok) {
            ['materia-nombre', 'materia-codigo', 'materia-descripcion'].forEach(id => { document.getElementById(id).value = ''; });
            await cargarMaterias();
        } else {
            error.textContent = mensajeDeError(await response.json().catch(() => ({})), 'No se pudo crear la materia.');
        }
    } catch {
        error.textContent = 'No hay conexión con el servidor.';
    }
    boton.disabled = false;
}

async function cambiarActivoMateria(materia) {
    const desactivar = materia.activo;
    if (desactivar && !confirm(`¿Desactivar ${materia.codigo}? Ya no se podrá inscribir a grupos en ella.`)) return;
    try {
        const response = await api(`/materias/${encodeURIComponent(materia.id)}/`, {
            method: 'PATCH',
            body: JSON.stringify({ activo: !desactivar }),
        });
        if (!response.ok) {
            alert(mensajeDeError(await response.json().catch(() => ({})), 'No se pudo actualizar la materia.'));
            return;
        }
    } catch {
        alert('No hay conexión con el servidor.');
        return;
    }
    await cargarMaterias();
}

async function inscribirGrupo(materia, item) {
    const mensaje = item.querySelector('.materia-mensaje');
    const boton = item.querySelector('.materia-inscribir');
    const periodo = document.getElementById('materias-periodo').value.trim();

    mensaje.style.color = 'var(--danger)';
    mensaje.textContent = '';
    boton.disabled = true;
    try {
        const response = await api(`/materias/${encodeURIComponent(materia.id)}/inscribir_grupo/`, {
            method: 'POST',
            body: JSON.stringify({ periodo }),
        });
        const datos = await response.json().catch(() => ({}));
        if (response.ok) {
            mensaje.style.color = 'var(--success)';
            const inscritos = datos.inscritos === 1 ? '1 alumno inscrito' : `${datos.inscritos} alumnos inscritos`;
            const previos = datos.ya_inscritos === 1 ? '1 ya lo estaba' : `${datos.ya_inscritos} ya lo estaban`;
            mensaje.textContent = datos.inscritos === 0
                ? `Todo el grupo ya estaba inscrito en ${periodo}.`
                : `✅ ${inscritos} en ${periodo}` + (datos.ya_inscritos ? ` (${previos}).` : '.');
        } else {
            mensaje.textContent = mensajeDeError(datos, 'No se pudo inscribir al grupo.');
        }
    } catch {
        mensaje.textContent = 'No hay conexión con el servidor.';
    }
    boton.disabled = false;
}

async function darDeAlta(evento) {
    evento.preventDefault();
    const form = evento.target;
    const error = document.getElementById('alta-error');
    const resultado = document.getElementById('alta-resultado');
    const boton = document.getElementById('alta-enviar');

    const datos = Object.fromEntries(new FormData(form).entries());
    Object.keys(datos).forEach(campo => { datos[campo] = datos[campo].trim(); });
    datos.materias_totales = Number(datos.materias_totales || 0);

    error.textContent = '';
    resultado.innerHTML = '';
    boton.disabled = true;
    try {
        const response = await api('/estudiantes/alta/', { method: 'POST', body: JSON.stringify(datos) });
        const respuesta = await response.json().catch(() => ({}));
        if (response.ok) {
            form.reset();
            // La contraseña temporal solo existe en esta respuesta: se muestra una vez
            resultado.innerHTML = `
                <div style="margin-top: 1rem; padding: 1rem; background: #dcfce7; border-radius: 8px;">
                    <strong>✅ ${escapeHtml(respuesta.estudiante.nombre)} ${escapeHtml(respuesta.estudiante.apellido)} quedó registrado.</strong>
                    <p style="margin-top: 0.5rem;">Usuario: <code>${escapeHtml(respuesta.usuario)}</code></p>
                    <p>Contraseña temporal: <code>${escapeHtml(respuesta.password_temporal)}</code></p>
                    <p style="margin-top: 0.5rem; font-size: 0.85rem;">Anótala y entrégala al estudiante: no se volverá a mostrar.</p>
                </div>
            `;
            await cargarInscripcion();  // el nuevo estudiante ya aparece para inscribirlo
        } else {
            error.textContent = mensajeDeError(respuesta, 'No se pudo dar de alta.');
        }
    } catch {
        error.textContent = 'No hay conexión con el servidor.';
    }
    boton.disabled = false;
}

async function cargarInscripcion() {
    const selectCurso = document.getElementById('inscripcion-curso');
    const detalle = document.getElementById('inscripcion-detalle');
    if (!selectCurso || !detalle) return;
    const cursoId = selectCurso.value;
    detalle.innerHTML = '<p>Cargando…</p>';

    let inscritos, estudiantes;
    try {
        [inscritos, estudiantes] = await Promise.all([
            getTodas(`/cursos/${encodeURIComponent(cursoId)}/inscritos/`),
            getTodas('/estudiantes/'),
        ]);
    } catch (error) {
        console.error('Error cargando inscripciones:', error);
        detalle.innerHTML = '<p style="color: red;">No se pudo cargar la inscripción.</p>';
        return;
    }

    const idsInscritos = new Set(inscritos.map(e => e.id));
    const disponibles = estudiantes.filter(e => !idsInscritos.has(e.id) && e.activo);

    detalle.innerHTML = `
        <h4 style="margin-bottom: 0.5rem;">Inscritos (${inscritos.length})</h4>
        ${inscritos.length === 0 ? '<p>Nadie inscrito todavía.</p>' : inscritos.map(e => `
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.5rem 0; border-bottom: 1px solid var(--gray-200);">
                <span>${escapeHtml(e.nombre)} ${escapeHtml(e.apellido)} <span style="color: var(--gray-700); font-size: 0.85rem;">· ${escapeHtml(e.matricula)}</span></span>
                <button type="button" class="inscripcion-quitar" data-estudiante-id="${escapeHtml(e.id)}"
                        style="${ESTILO_ACCION} color: var(--danger);">Quitar</button>
            </div>`).join('')}
        ${disponibles.length === 0 ? '<p style="margin-top: 1rem; color: var(--gray-700);">Todos los estudiantes activos ya están inscritos.</p>' : `
            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 1rem;">
                <select id="inscripcion-estudiante" aria-label="Estudiante a inscribir" style="${ESTILO_CAMPO} flex: 1; width: auto; min-width: 200px;">
                    ${disponibles.map(e => `<option value="${escapeHtml(e.id)}">${escapeHtml(e.apellido)}, ${escapeHtml(e.nombre)} · ${escapeHtml(e.matricula)}</option>`).join('')}
                </select>
                <button type="button" class="btn btn-primary" id="inscripcion-agregar">Inscribir</button>
            </div>`}
        <p id="inscripcion-error" role="alert" style="color: var(--danger); font-size: 0.85rem; margin-top: 0.5rem;"></p>
    `;

    const agregar = document.getElementById('inscripcion-agregar');
    if (agregar) {
        agregar.addEventListener('click', () =>
            cambiarInscripcionCurso(cursoId, 'inscribir', document.getElementById('inscripcion-estudiante').value));
    }
    detalle.querySelectorAll('.inscripcion-quitar').forEach(boton => {
        boton.addEventListener('click', () => cambiarInscripcionCurso(cursoId, 'quitar', boton.dataset.estudianteId));
    });
}

async function cambiarInscripcionCurso(cursoId, accion, estudianteId) {
    if (accion === 'quitar' && !confirm('¿Quitar a este estudiante del curso?')) return;
    const error = document.getElementById('inscripcion-error');
    try {
        const response = await api(`/cursos/${encodeURIComponent(cursoId)}/${accion}/`, {
            method: 'POST',
            body: JSON.stringify({ estudiante: estudianteId }),
        });
        if (!response.ok) {
            error.textContent = mensajeDeError(await response.json().catch(() => ({})), 'No se pudo completar la operación.');
            return;
        }
    } catch {
        error.textContent = 'No hay conexión con el servidor.';
        return;
    }
    await cargarInscripcion();
}

// ---------- Contenido de Materias ----------

let materiasContenido = [];
let materiaContenidoId = null;

// Igual que en el backend (academico/archivos.py): el servidor vuelve a validar todo
const FORMATOS_ADJUNTO = {
    pdf: 'documento', doc: 'documento', docx: 'documento', ppt: 'documento', pptx: 'documento',
    xls: 'documento', xlsx: 'documento',
    jpg: 'imagen', jpeg: 'imagen', png: 'imagen', gif: 'imagen', webp: 'imagen',
    mp4: 'video', webm: 'video',
};
const LIMITE_ADJUNTO_MB = { documento: 25, imagen: 10, video: 200 };
const ICONOS_DOCUMENTO = { pdf: '📕', doc: '📘', docx: '📘', ppt: '📙', pptx: '📙', xls: '📗', xlsx: '📗' };

const TINYMCE_BASE = 'https://cdn.jsdelivr.net/npm/tinymce@6.8.5';
const TINYMCE_IDIOMA = 'https://cdn.jsdelivr.net/npm/tinymce-i18n@24.7.29/langs6/es_MX.js';
let promesaTinyMCE = null;

function extensionDe(nombre) {
    const partes = nombre.toLowerCase().split('.');
    return partes.length > 1 ? partes.pop() : '';
}

function formatoTamano(bytes) {
    if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function puedeEditarContenido() {
    return Boolean(usuarioActual) && ['profesor', 'staff'].includes(usuarioActual.rol);
}

function cargarTinyMCE() {
    if (window.tinymce) return Promise.resolve(window.tinymce);
    if (!promesaTinyMCE) {
        promesaTinyMCE = new Promise((resolve, reject) => {
            const script = document.createElement('script');
            script.src = `${TINYMCE_BASE}/tinymce.min.js`;
            script.referrerPolicy = 'origin';
            script.onload = () => resolve(window.tinymce);
            script.onerror = () => {
                promesaTinyMCE = null;
                reject(new Error('No se pudo cargar el editor'));
            };
            document.head.appendChild(script);
        });
    }
    return promesaTinyMCE;
}

function cerrarEditorContenido() {
    if (window.tinymce) window.tinymce.remove('#contenido-cuerpo');
}

async function loadContenido() {
    const container = document.getElementById('contenido-contenido');
    if (!container) return;
    cerrarEditorContenido();
    container.innerHTML = '<div class="card"><p>Cargando…</p></div>';

    try {
        const materias = await getTodas('/materias/');
        // Para el estudiante, las materias inactivas no tienen contenido visible
        materiasContenido = puedeEditarContenido() ? materias : materias.filter(m => m.activo);
    } catch (error) {
        console.error('Error cargando materias:', error);
        errorDeCarga(container, 'las materias');
        return;
    }

    if (materiasContenido.length === 0) {
        container.innerHTML = '<div class="card"><p>No tienes materias con contenido disponible.</p></div>';
        return;
    }
    if (!materiasContenido.some(m => String(m.id) === String(materiaContenidoId))) {
        materiaContenidoId = materiasContenido[0].id;
    }

    const opciones = materiasContenido.map(m => `
        <option value="${escapeHtml(m.id)}"${String(m.id) === String(materiaContenidoId) ? ' selected' : ''}>
            ${escapeHtml(m.curso_nombre)} · ${escapeHtml(m.codigo)} ${escapeHtml(m.nombre)}${m.activo ? '' : ' (inactiva)'}
        </option>`).join('');

    container.innerHTML = `
        <div class="card" style="margin-bottom: 1.5rem; display: flex; gap: 1rem; align-items: end; flex-wrap: wrap;">
            <div style="flex: 1; min-width: 240px;">
                <label for="contenido-materia" style="display: block; margin-bottom: 0.5rem;">Materia</label>
                <select id="contenido-materia" style="${ESTILO_CAMPO}">${opciones}</select>
            </div>
            ${puedeEditarContenido() ? '<button type="button" class="btn btn-primary" id="contenido-nuevo">+ Nuevo contenido</button>' : ''}
        </div>
        <div id="contenido-area"></div>
    `;

    document.getElementById('contenido-materia').addEventListener('change', evento => {
        materiaContenidoId = evento.target.value;
        listarContenidos();
    });
    const nuevo = document.getElementById('contenido-nuevo');
    if (nuevo) nuevo.addEventListener('click', () => editarContenido(null));
    await listarContenidos();
}

async function listarContenidos() {
    const area = document.getElementById('contenido-area');
    cerrarEditorContenido();
    area.innerHTML = '<div class="card"><p>Cargando…</p></div>';

    let contenidos;
    try {
        contenidos = await getTodas(`/contenidos/?materia=${encodeURIComponent(materiaContenidoId)}`);
    } catch (error) {
        console.error('Error cargando contenidos:', error);
        errorDeCarga(area, 'el contenido');
        return;
    }

    if (contenidos.length === 0) {
        area.innerHTML = `<div class="card"><p>${puedeEditarContenido()
            ? 'Esta materia aún no tiene contenido. Usa "+ Nuevo contenido" para crear el primero.'
            : 'Tu profesor aún no ha publicado contenido en esta materia.'}</p></div>`;
        return;
    }

    area.innerHTML = '<div class="clases-list">' + contenidos.map(contenido => {
        const cuenta = tipo => contenido.archivos.filter(a => a.tipo === tipo).length;
        const resumen = [
            cuenta('documento') && `📄 ${cuenta('documento')}`,
            cuenta('imagen') && `🖼️ ${cuenta('imagen')}`,
            (cuenta('video') + (contenido.video_youtube ? 1 : 0)) && `🎬 ${cuenta('video') + (contenido.video_youtube ? 1 : 0)}`,
        ].filter(Boolean).join(' · ');
        const fecha = new Date(contenido.actualizado).toLocaleDateString('es-MX', { dateStyle: 'medium' });
        return `
            <div class="clase-item contenido-item" data-contenido-id="${escapeHtml(contenido.id)}" style="cursor: pointer;">
                <div class="clase-header">
                    <div class="clase-title">${escapeHtml(contenido.titulo)}</div>
                    ${puedeEditarContenido()
                        ? `<div class="clase-badge ${contenido.publicado ? 'badge-completed' : 'badge-neutral'}">${contenido.publicado ? 'Publicado' : 'Borrador'}</div>`
                        : ''}
                </div>
                <div style="color: var(--gray-700); font-size: 0.85rem;">
                    Actualizado el ${escapeHtml(fecha)}${resumen ? ` · ${resumen}` : ''}
                </div>
            </div>
        `;
    }).join('') + '</div>';

    area.querySelectorAll('.contenido-item').forEach(item => {
        item.addEventListener('click', () => verContenido(contenidos.find(c => String(c.id) === item.dataset.contenidoId)));
    });
}

function verContenido(contenido) {
    const area = document.getElementById('contenido-area');
    cerrarEditorContenido();

    const imagenes = contenido.archivos.filter(a => a.tipo === 'imagen');
    const videos = contenido.archivos.filter(a => a.tipo === 'video');
    const documentos = contenido.archivos.filter(a => a.tipo === 'documento');
    const fecha = new Date(contenido.actualizado).toLocaleString('es-MX', { dateStyle: 'medium', timeStyle: 'short' });
    // El id viene validado del servidor; se revisa otra vez antes de armar la URL del reproductor
    const youtube = /^[A-Za-z0-9_-]{11}$/.test(contenido.video_youtube || '') ? contenido.video_youtube : null;

    area.innerHTML = `
        <div class="card">
            <div style="display: flex; justify-content: space-between; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem;">
                <button type="button" class="btn btn-primary" id="contenido-volver">← Volver</button>
                ${puedeEditarContenido() ? `
                    <div style="display: flex; gap: 1rem; align-items: center;">
                        <button type="button" class="btn-salir" id="contenido-editar">Editar</button>
                        <button type="button" id="contenido-eliminar" style="${ESTILO_ACCION} color: var(--danger);">Eliminar</button>
                    </div>` : ''}
            </div>
            <h3 style="margin-bottom: 0.25rem;">${escapeHtml(contenido.titulo)}
                ${puedeEditarContenido() && !contenido.publicado ? '<span class="clase-badge badge-neutral" style="margin-left: 0.5rem;">Borrador</span>' : ''}
            </h3>
            <p style="color: var(--gray-700); font-size: 0.85rem; margin-bottom: 1.25rem;">
                ${escapeHtml(contenido.materia_nombre)} · ${contenido.autor_nombre ? `${escapeHtml(contenido.autor_nombre)} · ` : ''}${escapeHtml(fecha)}
            </p>

            <div class="contenido-cuerpo" id="contenido-cuerpo-vista"></div>

            ${youtube ? `
                <div class="contenido-video" style="margin-top: 1.25rem;">
                    <iframe src="https://www.youtube-nocookie.com/embed/${youtube}" title="Video de YouTube"
                            allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; fullscreen"
                            referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>
                </div>` : ''}

            ${videos.map(video => `
                <div style="margin-top: 1.25rem;">
                    <div class="contenido-video"><video controls preload="metadata" src="${escapeHtml(video.url)}"></video></div>
                    <div style="color: var(--gray-700); font-size: 0.85rem; margin-top: 0.25rem;">🎬 ${escapeHtml(video.nombre)}</div>
                </div>`).join('')}

            ${imagenes.length ? `
                <h4 style="margin: 1.5rem 0 0.75rem;">Imágenes</h4>
                <div class="contenido-galeria">
                    ${imagenes.map(imagen => `
                        <a href="${escapeHtml(imagen.url)}" target="_blank" rel="noopener" title="${escapeHtml(imagen.nombre)}">
                            <img src="${escapeHtml(imagen.url)}" alt="${escapeHtml(imagen.nombre)}" loading="lazy">
                        </a>`).join('')}
                </div>` : ''}

            ${documentos.length ? `
                <h4 style="margin: 1.5rem 0 0.75rem;">Documentos</h4>
                ${documentos.map(documento => `
                    <a class="clase-item" href="${escapeHtml(documento.url)}" target="_blank" rel="noopener"
                       style="display: flex; justify-content: space-between; align-items: center; text-decoration: none; color: inherit;">
                        <span>${ICONOS_DOCUMENTO[extensionDe(documento.nombre)] || '📄'} ${escapeHtml(documento.nombre)}</span>
                        <span style="color: var(--gray-700); font-size: 0.85rem; white-space: nowrap;">
                            ${escapeHtml(formatoTamano(documento.tamano))} · ${extensionDe(documento.nombre) === 'pdf' ? 'Abrir' : 'Descargar'}
                        </span>
                    </a>`).join('')}` : ''}
        </div>
    `;

    // HTML saneado por el servidor (solo formato, enlaces y tablas); las tablas se envuelven para desplazarse en móvil
    const cuerpo = document.getElementById('contenido-cuerpo-vista');
    cuerpo.innerHTML = contenido.cuerpo || '';
    cuerpo.querySelectorAll('table').forEach(tabla => {
        const envoltura = document.createElement('div');
        envoltura.className = 'tabla-desplazable';
        tabla.replaceWith(envoltura);
        envoltura.appendChild(tabla);
    });
    cuerpo.querySelectorAll('a').forEach(enlace => {
        enlace.target = '_blank';
        enlace.rel = 'noopener noreferrer';
    });

    document.getElementById('contenido-volver').addEventListener('click', listarContenidos);
    if (puedeEditarContenido()) {
        document.getElementById('contenido-editar').addEventListener('click', () => editarContenido(contenido));
        document.getElementById('contenido-eliminar').addEventListener('click', () => eliminarContenido(contenido));
    }
}

async function eliminarContenido(contenido) {
    if (!confirm(`¿Eliminar "${contenido.titulo}" y todos sus archivos? No se puede deshacer.`)) return;
    try {
        const response = await api(`/contenidos/${encodeURIComponent(contenido.id)}/`, { method: 'DELETE' });
        if (!response.ok) {
            alert(mensajeDeError(await response.json().catch(() => ({})), 'No se pudo eliminar.'));
            return;
        }
    } catch {
        alert('No hay conexión con el servidor.');
        return;
    }
    await listarContenidos();
}

// Editor para crear (contenido = null) o editar
async function editarContenido(contenido) {
    const area = document.getElementById('contenido-area');
    cerrarEditorContenido();
    const aceptados = Object.keys(FORMATOS_ADJUNTO).map(e => `.${e}`).join(',');

    area.innerHTML = `
        <div class="card">
            <h3 style="margin-bottom: 1rem;">${contenido ? 'Editar contenido' : 'Nuevo contenido'}</h3>
            <form id="contenido-form">
                <div style="margin-bottom: 1rem;">
                    <label for="contenido-titulo" style="display: block; margin-bottom: 0.5rem;">Título</label>
                    <input id="contenido-titulo" required maxlength="200" style="${ESTILO_CAMPO}"
                           placeholder="Unidad 1: Introducción" value="${escapeHtml(contenido ? contenido.titulo : '')}">
                </div>
                <div style="margin-bottom: 1rem;">
                    <label for="contenido-cuerpo" style="display: block; margin-bottom: 0.5rem;">Texto (puedes insertar tablas)</label>
                    <textarea id="contenido-cuerpo" rows="12" style="${ESTILO_CAMPO}">${escapeHtml(contenido ? contenido.cuerpo : '')}</textarea>
                    <p id="contenido-aviso-editor" style="color: var(--gray-700); font-size: 0.85rem; margin-top: 0.25rem;"></p>
                </div>
                <div style="margin-bottom: 1rem;">
                    <label for="contenido-youtube" style="display: block; margin-bottom: 0.5rem;">Video de YouTube (opcional)</label>
                    <input id="contenido-youtube" type="url" maxlength="300" style="${ESTILO_CAMPO}"
                           placeholder="https://www.youtube.com/watch?v=…" value="${escapeHtml(contenido ? contenido.video_url : '')}">
                </div>

                <div style="margin-bottom: 1rem;">
                    <label for="contenido-archivos" style="display: block; margin-bottom: 0.5rem;">Adjuntos</label>
                    ${contenido && contenido.archivos.length ? `
                        <div id="contenido-adjuntos-actuales" style="margin-bottom: 0.75rem;">
                            ${contenido.archivos.map(archivo => `
                                <div style="display: flex; justify-content: space-between; align-items: center; padding: 0.4rem 0; border-bottom: 1px solid var(--gray-200);">
                                    <span>${archivo.tipo === 'imagen' ? '🖼️' : archivo.tipo === 'video' ? '🎬' : '📄'} ${escapeHtml(archivo.nombre)}
                                        <span style="color: var(--gray-700); font-size: 0.85rem;">· ${escapeHtml(formatoTamano(archivo.tamano))}</span></span>
                                    <button type="button" class="adjunto-quitar" data-archivo-id="${escapeHtml(archivo.id)}"
                                            style="${ESTILO_ACCION} color: var(--danger);">Quitar</button>
                                </div>`).join('')}
                        </div>` : ''}
                    <input id="contenido-archivos" type="file" multiple accept="${aceptados}" style="${ESTILO_CAMPO}">
                    <p style="color: var(--gray-700); font-size: 0.8rem; margin-top: 0.25rem;">
                        PDF, Word, PowerPoint y Excel (hasta ${LIMITE_ADJUNTO_MB.documento} MB) · JPG, PNG, GIF y WebP
                        (hasta ${LIMITE_ADJUNTO_MB.imagen} MB) · MP4 y WebM (hasta ${LIMITE_ADJUNTO_MB.video} MB)
                    </p>
                    <div id="contenido-seleccion" style="margin-top: 0.5rem;"></div>
                </div>

                <label style="display: flex; gap: 0.5rem; align-items: center; margin-bottom: 1rem; cursor: pointer;">
                    <input type="checkbox" id="contenido-publicado" ${!contenido || contenido.publicado ? 'checked' : ''}>
                    Publicado (visible para los alumnos)
                </label>

                <p id="contenido-error" role="alert" style="color: var(--danger); font-size: 0.85rem; min-height: 1.2em; margin-bottom: 0.5rem; white-space: pre-line;"></p>
                <div style="display: flex; gap: 0.5rem;">
                    <button class="btn btn-primary" type="submit" id="contenido-guardar">Guardar</button>
                    <button class="btn-salir" type="button" id="contenido-cancelar">Cancelar</button>
                </div>
            </form>
        </div>
    `;

    document.getElementById('contenido-cancelar').addEventListener('click', () =>
        (contenido ? verContenido(contenido) : listarContenidos()));
    document.getElementById('contenido-archivos').addEventListener('change', mostrarSeleccionAdjuntos);
    document.getElementById('contenido-form').addEventListener('submit', evento => guardarContenido(evento, contenido));
    area.querySelectorAll('.adjunto-quitar').forEach(boton => {
        boton.addEventListener('click', () => quitarAdjunto(contenido, boton.dataset.archivoId));
    });

    try {
        const tinymce = await cargarTinyMCE();
        await tinymce.init({
            selector: '#contenido-cuerpo',
            language: 'es_MX',
            language_url: TINYMCE_IDIOMA,
            base_url: TINYMCE_BASE,
            suffix: '.min',
            height: 380,
            menubar: false,
            branding: false,
            promotion: false,
            plugins: 'lists link autolink table',
            toolbar: 'undo redo | blocks | bold italic underline strikethrough | bullist numlist blockquote | link table | removeformat',
            block_formats: 'Párrafo=p; Título=h2; Subtítulo=h3; Sección=h4',
            table_default_styles: {},
            // Imágenes y videos van como adjuntos, no incrustados en el texto
            paste_data_images: false,
            invalid_elements: 'img,video,iframe,script,style,object,embed',
            link_default_target: '_blank',
            content_style: 'body { font-family: Segoe UI, Tahoma, sans-serif; font-size: 15px; } table td, table th { border: 1px solid #ccc; padding: 4px 8px; }',
        });
    } catch (error) {
        console.error(error);
        document.getElementById('contenido-aviso-editor').textContent =
            'No se pudo cargar el editor enriquecido (¿sin internet?). Escribe texto simple: cada línea en blanco separa un párrafo.';
    }
}

function mostrarSeleccionAdjuntos() {
    const archivos = Array.from(document.getElementById('contenido-archivos').files);
    document.getElementById('contenido-seleccion').innerHTML = archivos.map((archivo, i) => {
        const problema = problemaDeAdjunto(archivo);
        return `
            <div style="padding: 0.4rem 0;" data-indice="${i}">
                <div style="display: flex; justify-content: space-between; gap: 1rem;">
                    <span>${escapeHtml(archivo.name)} <span style="color: var(--gray-700); font-size: 0.85rem;">· ${escapeHtml(formatoTamano(archivo.size))}</span></span>
                    <span class="adjunto-estado" style="font-size: 0.85rem; color: ${problema ? 'var(--danger)' : 'var(--gray-700)'};">${escapeHtml(problema || 'Listo para subir')}</span>
                </div>
                <div class="barra-progreso"><div></div></div>
            </div>
        `;
    }).join('');
}

function problemaDeAdjunto(archivo) {
    const tipo = FORMATOS_ADJUNTO[extensionDe(archivo.name)];
    if (!tipo) return 'Formato no permitido';
    if (archivo.size > LIMITE_ADJUNTO_MB[tipo] * 1024 * 1024) return `Supera ${LIMITE_ADJUNTO_MB[tipo]} MB`;
    return null;
}

function obtenerCuerpo() {
    const editor = window.tinymce && window.tinymce.get('contenido-cuerpo');
    if (editor) return editor.getContent();
    // Sin editor: texto simple → párrafos (escapado; el servidor además sanea)
    return document.getElementById('contenido-cuerpo').value
        .split(/\n\s*\n/)
        .map(parrafo => parrafo.trim())
        .filter(Boolean)
        .map(parrafo => `<p>${escapeHtml(parrafo).replace(/\n/g, '<br>')}</p>`)
        .join('');
}

// Subida con XMLHttpRequest para poder mostrar el progreso (fetch no lo informa)
// ruta: endpoint de la API que recibe el campo "archivo" (adjunto de contenido o entrega de tarea)
function subirAdjunto(ruta, archivo, alProgresar) {
    return new Promise(resolve => {
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api' + ruta);
        xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
        xhr.upload.onprogress = evento => {
            if (evento.lengthComputable) alProgresar(evento.loaded / evento.total);
        };
        xhr.onload = () => {
            let datos = {};
            try { datos = JSON.parse(xhr.responseText); } catch { /* respuesta sin JSON */ }
            if (xhr.status === 413) datos = { detail: 'El archivo supera el tamaño que acepta el servidor.' };
            resolve({ ok: xhr.status >= 200 && xhr.status < 300, datos });
        };
        xhr.onerror = () => resolve({ ok: false, datos: { detail: 'No hay conexión con el servidor.' } });
        const formulario = new FormData();
        formulario.append('archivo', archivo);
        xhr.send(formulario);
    });
}

async function guardarContenido(evento, contenido) {
    evento.preventDefault();
    const error = document.getElementById('contenido-error');
    const boton = document.getElementById('contenido-guardar');
    const archivos = Array.from(document.getElementById('contenido-archivos').files);

    const titulo = document.getElementById('contenido-titulo').value.trim();
    if (!titulo) {
        error.textContent = 'Escribe un título.';
        return;
    }
    const invalidos = archivos.filter(problemaDeAdjunto);
    if (invalidos.length) {
        error.textContent = 'Quita los archivos marcados en rojo antes de guardar.';
        return;
    }

    error.textContent = '';
    boton.disabled = true;
    boton.textContent = 'Guardando…';

    let guardado;
    try {
        const response = await api(contenido ? `/contenidos/${encodeURIComponent(contenido.id)}/` : '/contenidos/', {
            method: contenido ? 'PATCH' : 'POST',
            body: JSON.stringify({
                materia: materiaContenidoId,
                titulo,
                cuerpo: obtenerCuerpo(),
                video_url: document.getElementById('contenido-youtube').value.trim(),
                publicado: document.getElementById('contenido-publicado').checked,
            }),
        });
        guardado = await response.json().catch(() => ({}));
        if (!response.ok) {
            error.textContent = mensajeDeError(guardado, 'No se pudo guardar el contenido.');
            boton.disabled = false;
            boton.textContent = 'Guardar';
            return;
        }
    } catch {
        error.textContent = 'No hay conexión con el servidor.';
        boton.disabled = false;
        boton.textContent = 'Guardar';
        return;
    }

    // Adjuntos uno por uno, con su barra de progreso
    const fallidos = [];
    for (const [indice, archivo] of archivos.entries()) {
        const fila = document.querySelector(`#contenido-seleccion [data-indice="${indice}"]`);
        const barra = fila.querySelector('.barra-progreso > div');
        const estado = fila.querySelector('.adjunto-estado');
        estado.textContent = 'Subiendo…';
        boton.textContent = `Subiendo ${indice + 1} de ${archivos.length}…`;
        const resultado = await subirAdjunto(`/contenidos/${encodeURIComponent(guardado.id)}/subir_archivo/`, archivo, fraccion => { barra.style.width = `${Math.round(fraccion * 100)}%`; });
        if (resultado.ok) {
            barra.style.width = '100%';
            estado.textContent = '✅ Subido';
        } else {
            const motivo = mensajeDeError(resultado.datos, 'Error al subir');
            estado.style.color = 'var(--danger)';
            estado.textContent = motivo;
            fallidos.push(`${archivo.name}: ${motivo}`);
        }
    }

    // Se recarga el contenido para mostrar los adjuntos que sí se guardaron
    const actualizado = await api(`/contenidos/${encodeURIComponent(guardado.id)}/`).then(r => r.json()).catch(() => guardado);
    if (fallidos.length) {
        await editarContenido(actualizado);
        document.getElementById('contenido-error').textContent =
            'El contenido se guardó, pero algunos archivos no se subieron:\n' + fallidos.join('\n');
        return;
    }
    verContenido(actualizado);
}

async function quitarAdjunto(contenido, archivoId) {
    if (!confirm('¿Quitar este archivo? Se borrará definitivamente.')) return;
    try {
        const response = await api(`/archivos-contenido/${encodeURIComponent(archivoId)}/`, { method: 'DELETE' });
        if (!response.ok) {
            alert(mensajeDeError(await response.json().catch(() => ({})), 'No se pudo quitar el archivo.'));
            return;
        }
    } catch {
        alert('No hay conexión con el servidor.');
        return;
    }
    // Conserva lo que se haya escrito en el formulario al volver a dibujarlo
    const borrador = {
        ...contenido,
        titulo: document.getElementById('contenido-titulo').value,
        cuerpo: obtenerCuerpo(),
        video_url: document.getElementById('contenido-youtube').value,
        publicado: document.getElementById('contenido-publicado').checked,
        archivos: contenido.archivos.filter(a => String(a.id) !== String(archivoId)),
    };
    await editarContenido(borrador);
}

window.addEventListener('DOMContentLoaded', () => {
    init();
});

window.showSection = showSection;
window.cargarClasesZoom = cargarClasesZoom;
window.abrirClaseZoom = abrirClaseZoom;
