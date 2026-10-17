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

window.addEventListener('DOMContentLoaded', () => {
    init();
});

window.showSection = showSection;
window.cargarClasesZoom = cargarClasesZoom;
window.abrirClaseZoom = abrirClaseZoom;
