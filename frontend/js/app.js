const API_BASE = '/api';

let currentStudent = null;
let courses = [];
let tasks = [];

async function init() {
    await loadStudentData();
    await loadCourses();
    await loadTasks();
    updateDashboard();
}

async function loadStudentData() {
    try {
        const response = await fetch(`${API_BASE}/estudiantes/`);
        const data = await response.json();
        const students = data.results || data;
        
        if (students.length > 0) {
            currentStudent = students[0];
            updateStudentProfile(currentStudent);
        }
    } catch (error) {
        console.error('Error cargando estudiante:', error);
    }
}

async function loadCourses() {
    try {
        const response = await fetch(`${API_BASE}/cursos/`);
        const data = await response.json();
        courses = data.results || data;
    } catch (error) {
        console.error('Error cargando cursos:', error);
    }
}

async function loadTasks() {
    try {
        const response = await fetch(`${API_BASE}/tareas/`);
        const data = await response.json();
        tasks = data.results || data;
    } catch (error) {
        console.error('Error cargando tareas:', error);
    }
}

function updateStudentProfile(student) {
    const studentNameElement = document.querySelector('.student-name');
    if (studentNameElement) {
        studentNameElement.textContent = `${student.nombre} ${student.apellido}`;
    }
    
    const studentIdElement = document.querySelector('.student-id');
    if (studentIdElement) {
        studentIdElement.textContent = `Matrícula: ${student.matricula}`;
    }
    
    const headerName = document.querySelector('.user-profile div div:first-child');
    if (headerName) {
        headerName.textContent = `${student.nombre} ${student.apellido}`;
    }
    
    const initials = `${student.nombre.charAt(0)}${student.apellido.charAt(0)}`;
    document.querySelectorAll('.user-avatar').forEach(avatar => {
        if (!avatar.querySelector('img')) {
            avatar.textContent = initials;
        }
    });
}

function updateDashboard() {
    const totalCoursesElement = document.querySelector('.stat-card:nth-child(2) .stat-value');
    if (totalCoursesElement) {
        totalCoursesElement.textContent = courses.length;
    }
    
    const pendingTasks = tasks.filter(t => t.estado === 'pendiente').length;
    const pendingTasksElement = document.querySelector('.stat-card:nth-child(3) .stat-value');
    if (pendingTasksElement) {
        pendingTasksElement.textContent = pendingTasks;
    }
    
    if (currentStudent) {
        const bannerTitle = document.querySelector('.banner-text h2');
        if (bannerTitle && bannerTitle.textContent.includes('Próximo')) {
            bannerTitle.textContent = `¡Bienvenido/a ${currentStudent.nombre}!`;
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

async function loadControlEscolar() {
    const container = document.querySelector('#control .clases-list');
    if (!container || courses.length === 0) return;
    
    let html = '<h3 style="margin-bottom: 1rem;">Mis Cursos</h3>';
    
    courses.forEach(course => {
        html += `
            <div class="clase-item">
                <div class="clase-header">
                    <div class="clase-title">${course.nombre}</div>
                    <div class="clase-badge badge-live">Cursando</div>
                </div>
                <div style="margin-top: 0.5rem;">
                    <p><strong>Código:</strong> ${course.codigo}</p>
                    <p><strong>Profesor:</strong> ${course.profesor}</p>
                    <p><strong>Créditos:</strong> ${course.creditos}</p>
                    <p><strong>Estudiantes:</strong> ${course.cantidad_estudiantes || 0}</p>
                </div>
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
        console.log('Cargando clases Zoom...');
        const response = await fetch(`${API_BASE}/clases-zoom/`);
        const data = await response.json();
        const clases = data.results || data;
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
                
                const btnElement = document.createElement('button');
                btnElement.className = 'btn btn-primary';
                btnElement.style.marginTop = '1rem';
                btnElement.textContent = clase.estado === 'en_vivo' ? '🎥 Unirse Ahora' : '📋 Ver Detalles';
                btnElement.setAttribute('data-clase-id', clase.id);
                
                html += `
                    <div class="clase-item">
                        <div class="clase-header">
                            <div class="clase-title">${clase.titulo}</div>
                            <div class="clase-badge ${badgeClass}">${estadoTexto}</div>
                        </div>
                        <div style="margin-top: 0.5rem;">
                            <p><strong>📚 Curso:</strong> ${clase.curso_nombre}</p>
                            <p><strong>👨‍🏫 Profesor:</strong> ${clase.profesor}</p>
                            <p><strong>⏱️ Duración:</strong> ${clase.duracion_minutos} minutos</p>
                            <p><strong>👥 Participantes:</strong> ${clase.total_participantes} / ${clase.max_participantes}</p>
                            <p><strong>📅 Fecha:</strong> ${new Date(clase.fecha_hora_inicio).toLocaleString('es-MX')}</p>
                            <button class="btn btn-primary zoom-btn" data-clase-id="${clase.id}" style="margin-top: 1rem;">
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

async function loadForo() {
    const container = document.querySelector('#foro .clases-list');
    if (!container || courses.length === 0) return;
    
    const firstCourse = courses[0];
    
    let html = `<h3 style="margin-bottom: 1rem;">${firstCourse.nombre} - Discusiones</h3>`;
    
    html += `
        <div class="card" style="margin-bottom: 1rem;">
            <div style="display: flex; gap: 1rem;">
                <div class="user-avatar" style="width: 40px; height: 40px;">PR</div>
                <div style="flex: 1;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <strong>${firstCourse.profesor} (Profesor)</strong>
                        <span style="color: var(--gray-700); font-size: 0.85rem;">Hace 2 horas</span>
                    </div>
                    <p style="color: var(--gray-700);">Bienvenidos al foro de ${firstCourse.nombre}.</p>
                    <div style="margin-top: 1rem; display: flex; gap: 1rem; font-size: 0.85rem; color: var(--gray-700);">
                        <span>👍 12 Me gusta</span>
                        <span>💬 8 Respuestas</span>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    if (currentStudent) {
        html += `
            <div class="card" style="margin-bottom: 1rem;">
                <div style="display: flex; gap: 1rem;">
                    <div class="user-avatar" style="width: 40px; height: 40px;">${currentStudent.nombre.charAt(0)}${currentStudent.apellido.charAt(0)}</div>
                    <div style="flex: 1;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <strong>${currentStudent.nombre} ${currentStudent.apellido}</strong>
                            <span style="color: var(--gray-700); font-size: 0.85rem;">Hace 5 horas</span>
                        </div>
                        <p style="color: var(--gray-700);">Excelente clase.</p>
                        <div style="margin-top: 1rem; display: flex; gap: 1rem; font-size: 0.85rem; color: var(--gray-700);">
                            <span>👍 5 Me gusta</span>
                            <span>💬 3 Respuestas</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    html += `
        <div class="card">
            <h4 style="margin-bottom: 1rem;">Nueva Publicación</h4>
            <textarea rows="3" placeholder="Escribe aquí..." style="width: 100%; padding: 0.75rem; border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 1rem;"></textarea>
            <button class="btn btn-primary" onclick="publicarEnForo()">Publicar</button>
        </div>
    `;
    
    container.innerHTML = html;
}

function publicarEnForo() {
    const textarea = document.querySelector('#foro textarea');
    if (textarea && textarea.value.trim()) {
        alert('Publicación enviada: ' + textarea.value);
        textarea.value = '';
        loadForo();
    } else {
        alert('Escribe algo antes de publicar');
    }
}

window.addEventListener('DOMContentLoaded', () => {
    init();
});

window.showSection = showSection;
window.publicarEnForo = publicarEnForo;
window.cargarClasesZoom = cargarClasesZoom;
window.abrirClaseZoom = abrirClaseZoom;
