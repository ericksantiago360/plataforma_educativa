# plataforma_educativa
# 🎓 Plataforma Universitaria - Resumen Final



### **Backend Django REST API**
- ✅ 3 aplicaciones Django (estudiantes, cursos, coordinación)
- ✅ Base de datos MySQL con modelos relacionales
- ✅ API REST completa con 8 endpoints
- ✅ Panel administrativo de Django
- ✅ Serializers para transformación de datos
- ✅ CORS configurado para frontend

### **Frontend Campus Virtual estilo UVEG**
- ✅ Interfaz moderna y responsive
- ✅ Sidebar con perfil del estudiante
- ✅ Dashboard con estadísticas en tiempo real
- ✅ 9 secciones principales:
  - 🏠 Inicio
  - 📚 Biblioteca Digital
  - 📋 Control Escolar
  - 👨‍🏫 Mi Tutor
  - 🆘 Mesa de Ayuda
  - 📅 Calendario
  - 🌎 Centro de Idiomas
  - 🎥 Clases en Línea
  - 💬 Foro de Clase

### **Servicios Académicos**
- ✅ Preparatoria (Bachillerato General)
- ✅ Técnico Superior Universitario (TSU)
- ✅ Carreras Profesionales (Licenciaturas)
- ✅ Maestrías
- ✅ Doctorados
- ✅ Centro de Idiomas

### **Infraestructura Docker**
- ✅ 3 contenedores (MySQL, Django, Nginx)
- ✅ Configuración automática
- ✅ Volúmenes persistentes
- ✅ Red interna para comunicación

---

## 🌐 URLs de Acceso

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Frontend** | http://localhost | Campus Virtual (Principal) |
| **API REST** | http://localhost:8000/api/ | Documentación API |
| **Admin Django** | http://localhost:8000/admin/ | Panel administrativo |
| **Estudiantes API** | http://localhost:8000/api/estudiantes/ | CRUD Estudiantes |
| **Cursos API** | http://localhost:8000/api/cursos/ | CRUD Cursos |
| **Tareas API** | http://localhost:8000/api/tareas/ | CRUD Tareas |
| **Comunicados API** | http://localhost:8000/api/comunicados/ | CRUD Comunicados |

---

## 📊 Estructura de la Base de Datos

### Tabla: **Estudiante**
```
- id (PK)
- nombre
- apellido
- email (unique)
- matricula (unique)
- telefono
- fecha_inscripcion
- activo
```

### Tabla: **Curso**
```
- id (PK)
- nombre
- codigo (unique)
- descripcion
- profesor
- creditos
- fecha_inicio
- fecha_fin
- activo
- estudiantes (ManyToMany)
```

### Tabla: **Tarea**
```
- id (PK)
- titulo
- descripcion
- curso (FK)
- fecha_vencimiento
- estado (pendiente/en_progreso/completada)
- creado
- estudiantes (ManyToMany)
```

### Tabla: **Comunicado**
```
- id (PK)
- titulo
- contenido
- curso (FK)
- fecha_creacion
- activo
```

---

## 🚀 Comandos Útiles

### Iniciar la Plataforma
```bash
cd plataforma-universitaria
docker-compose up -d
```

### Detener la Plataforma
```bash
docker-compose down
```

### Ver Logs
```bash
# Todos los servicios
docker-compose logs -f

# Solo backend
docker-compose logs backend -f

# Solo frontend
docker-compose logs frontend -f
```

### Comandos Django
```bash
# Migraciones
docker-compose exec backend python manage.py makemigrations
docker-compose exec backend python manage.py migrate

# Shell de Django
docker-compose exec backend python manage.py shell

# Crear superusuario
docker-compose exec backend python manage.py createsuperuser

# Crear datos de prueba
docker-compose exec backend python manage.py shell
# Luego pega el código para crear estudiantes, cursos, etc.
```

### Reiniciar Servicios
```bash
# Reiniciar backend
docker-compose restart backend

# Reiniciar frontend
docker-compose restart frontend

# Reiniciar todo
docker-compose restart
```

---

## 📁 Estructura del Proyecto

```
plataforma-universitaria/
├── docker-compose.yml          # Orquestación de contenedores
├── nginx.conf                  # Configuración Nginx
├── backend/
│   ├── Dockerfile             # Imagen Docker del backend
│   ├── requirements.txt       # Dependencias Python
│   ├── manage.py              # Script de Django
│   ├── config/                # Configuración del proyecto
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── estudiantes/           # App Estudiantes
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── admin.py
│   ├── cursos/                # App Cursos
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── admin.py
│   └── coordinacion/          # App Coordinación
│       ├── models.py
│       ├── serializers.py
│       ├── views.py
│       ├── urls.py
│       └── admin.py
└── frontend/
    ├── index.html             # Página principal
    ├── css/
    │   └── styles.css
    └── js/
        └── app.js             # Lógica del frontend
```

---

## 🎨 Características del Frontend

### Diseño Responsive
- ✅ Adaptable a móviles, tablets y desktop
- ✅ Sidebar colapsable
- ✅ Cards con hover effects
- ✅ Colores inspirados en UVEG

### Navegación Dinámica
- ✅ Cambio de secciones sin recargar página
- ✅ Menú lateral con indicador activo
- ✅ Breadcrumbs visuales

### Datos en Tiempo Real
- ✅ Carga de estudiantes desde API
- ✅ Estadísticas dinámicas
- ✅ Cursos actualizados
- ✅ Tareas pendientes

### Perfil del Estudiante
- ✅ Avatar con iniciales
- ✅ Información académica
- ✅ Progreso visual (gráfica circular)
- ✅ Matrícula y programa

---

## 🔧 Próximas Mejoras Sugeridas

### Funcionalidades Prioritarias
1. **Autenticación JWT**
   - Login de estudiantes
   - Tokens de sesión
   - Roles y permisos

2. **Formularios Completos**
   - Crear estudiantes desde frontend
   - Inscribir a cursos
   - Subir tareas

3. **Sistema de Calificaciones**
   - Registro de notas
   - Historial académico
   - Promedios automáticos

4. **Notificaciones**
   - Email automático
   - Notificaciones push
   - Alertas de tareas

5. **Reportes y Exportación**
   - Generar PDF de boletas
   - Exportar datos a Excel
   - Certificados digitales

### Funcionalidades Secundarias
- Chat en tiempo real (WebSockets)
- Videollamadas integradas (Zoom/Meet)
- Sistema de pagos
- App móvil (React Native)
- Módulo de asistencia
- Gamificación (logros, badges)

---

## 📚 Tecnologías Utilizadas

### Backend
- **Django 4.2** - Framework web
- **Django REST Framework 3.14** - API REST
- **MySQL 8.0** - Base de datos
- **Python 3.10** - Lenguaje

### Frontend
- **HTML5** - Estructura
- **CSS3** - Estilos
- **JavaScript ES6+** - Interactividad
- **Fetch API** - Consumo de API

### DevOps
- **Docker** - Contenedores
- **Docker Compose** - Orquestación
- **Nginx** - Servidor web
- **Git** - Control de versiones

---

## 🎯 Checklist de Funcionalidades

### Completadas ✅
- [x] Estructura Docker completa
- [x] Backend Django con API REST
- [x] Base de datos MySQL
- [x] CRUD de Estudiantes
- [x] CRUD de Cursos
- [x] CRUD de Tareas
- [x] CRUD de Comunicados
- [x] Frontend campus virtual
- [x] Perfil de estudiante
- [x] Dashboard con estadísticas
- [x] Secciones académicas
- [x] Integración API-Frontend

### Pendientes 🔄
- [ ] Sistema de autenticación
- [ ] Formularios de creación
- [ ] Sistema de calificaciones
- [ ] Notificaciones por email
- [ ] Reportes en PDF
- [ ] Chat en tiempo real
- [ ] Sistema de pagos
- [ ] App móvil

---

## 💡 Consejos de Uso

### Para Desarrollo
1. Siempre usa `docker-compose logs` para depurar
2. Guarda backups de la base de datos regularmente
3. Prueba en el panel de admin antes del frontend
4. Usa Postman para probar la API

### Para Producción
1. Cambia `DEBUG = False` en settings.py
2. Genera un `SECRET_KEY` seguro
3. Configura HTTPS con certificados SSL
4. Usa Gunicorn en lugar de runserver
5. Implementa rate limiting
6. Agrega monitoreo con Sentry

---

## 📞 Recursos de Ayuda

### Documentación
- Django: https://docs.djangoproject.com/
- DRF: https://www.django-rest-framework.org/
- Docker: https://docs.docker.com/

### Comunidad
- Stack Overflow: https://stackoverflow.com/
- Django Forum: https://forum.djangoproject.com/
- Reddit r/django: https://reddit.com/r/django

---

## 🏆 Logros

Has creado exitosamente una **plataforma educativa completa** con:
- ✅ Backend profesional con API REST
- ✅ Frontend moderno estilo UVEG
- ✅ Infraestructura escalable con Docker
- ✅ Base de datos relacional
- ✅ Integración completa frontend-backend

**¡Felicidades! Tu plataforma está lista para ser expandida.** 🎉
