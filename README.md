# plataforma_educativa
# 🎓 Plataforma Universitaria - Resumen Final



### **Backend Django REST API**
- ✅ 7 aplicaciones Django (estudiantes, cursos, coordinación, perfiles, servicios, académico, cuentas)
- ✅ Base de datos MySQL con modelos relacionales
- ✅ API REST con 22 recursos, todos protegidos con inicio de sesión
- ✅ Autenticación por sesión con 3 roles: estudiante, profesor y staff
- ✅ Permisos por rol: cada usuario solo ve y modifica lo que le corresponde
- ✅ Panel administrativo de Django
- ✅ Pruebas automáticas de autenticación y permisos

### **Frontend Campus Virtual estilo UVEG**
- ✅ Interfaz moderna y responsive
- ✅ Página de inicio de sesión
- ✅ Sidebar con perfil del estudiante
- ✅ Dashboard con estadísticas del perfil académico
- ✅ Menús según el rol del usuario
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

## ⚡ Puesta en Marcha

### 1. Configurar variables de entorno
```bash
cp backend/.env.example backend/.env
```

Edita `backend/.env` y define `SECRET_KEY` (sin ella Django no arranca). Para generar una:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

> ⚠️ El archivo `.env` nunca se sube a git (está en `.gitignore`). Usa `.env.example` como plantilla.

### 2. Levantar los contenedores
```bash
docker-compose up -d --build
```

### 3. Crear las tablas
```bash
docker-compose exec backend python manage.py migrate
```

### 4. Cargar datos de prueba
```bash
docker-compose exec -T backend python manage.py shell < backend/seed_data.py
```

Al terminar imprime los **usuarios de prueba con sus contraseñas** (se generan al azar en cada ejecución):

| Usuario | Rol | Qué puedes probar |
|---------|-----|-------------------|
| `admin` | Staff | Ve y administra todo; entra al panel de Django |
| `alfonso` | Profesor | Curso de Administración (ADM101) |
| `beatriz` | Profesora | Curso de Contabilidad (CON101) |
| `2024001` | Estudiante (Juan) | Un curso, historial corto |
| `2024002` | Estudiante (María) | Dos cursos, más historial y foros |
| `2024003` | Estudiante (Carlos) | Materia reprobada y una baja |

> El seed no se puede ejecutar dos veces sobre la misma base. Para empezar de cero: `docker-compose down -v` (⚠️ borra todos los datos) y repite los pasos 2 a 4.

### 5. Entrar
Abre http://localhost: te llevará a la página de inicio de sesión.

---

## 🌐 URLs de Acceso

| Servicio | URL | Descripción |
|----------|-----|-------------|
| **Frontend** | http://localhost | Campus Virtual (Principal) |
| **Login** | http://localhost/login.html | Inicio de sesión |
| **API REST** | http://localhost/api/ | API a través de Nginx (la que usa el frontend) |
| **Admin Django** | http://localhost:8000/admin/ | Panel administrativo |

> 🔒 Toda la API exige sesión. Para explorarla desde el navegador, inicia sesión primero en http://localhost:8000/admin/ y luego abre http://localhost:8000/api/estudiantes/ (la sesión se comparte en el mismo puerto).

### Endpoints de autenticación (`/api/auth/`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/auth/csrf/` | GET | Entrega la cookie `csrftoken` |
| `/api/auth/login/` | POST | `{usuario, password}` → inicia sesión (máx. 5 intentos por minuto por IP) |
| `/api/auth/logout/` | POST | Cierra la sesión |
| `/api/auth/me/` | GET | Usuario actual: `{id, usuario, nombre, rol, estudiante}` |

Las peticiones `POST`, `PUT`, `PATCH` y `DELETE` deben enviar el header `X-CSRFToken` con el valor de la cookie `csrftoken` (`frontend/js/auth.js` lo hace con la función `api()`).

### Endpoints de datos (`/api/`)

| App | Endpoints |
|-----|-----------|
| estudiantes | `estudiantes/` |
| cursos | `cursos/`, `clases-zoom/`, `participantes-clase/` |
| coordinacion | `tareas/`, `comunicados/` |
| perfiles | `perfiles/`, `tutores/`, `asignaciones-tutor/` |
| servicios | `biblioteca/`, `mesa-ayuda/`, `calendario/`, `idiomas/` |
| academico | `materias/`, `clases/`, `foros/`, `mensajes-foro/`, `control-escolar/` |

`mensajes-foro/` acepta `?foro=<id>` para traer solo los mensajes de un foro.

---

## 🔐 Roles y Permisos

| Rol | Cómo se asigna |
|-----|----------------|
| **Staff** | Usuario con `is_staff` (casilla "Es staff" en el admin) |
| **Profesor** | Usuario en el grupo `Profesor` + asignado como `titular` de sus cursos |
| **Estudiante** | Usuario enlazado a un registro de `Estudiante` (campo `usuario`) |

Las cuentas las crea Control Escolar desde el panel de administración: primero el usuario y después se enlaza al estudiante o se agrega al grupo `Profesor`. No hay registro público.

| Recurso | Estudiante | Profesor | Staff |
|---------|------------|----------|-------|
| Estudiantes, perfiles | Solo el suyo (lectura) | Alumnos de sus cursos (lectura) | Todo |
| Cursos | Los que cursa (lectura) | Los suyos (edita, no crea ni borra) | Todo |
| Tareas, clases, foros | Los de sus cursos (lectura) | Los de sus cursos (edita) | Todo |
| Control escolar | Su historial (lectura) | Sus materias (edita calificaciones) | Todo |
| Mensajes de foro | Publica, edita y borra los suyos | Publica y edita los suyos; borra cualquiera de sus cursos (moderar) | Todo |
| Mesa de ayuda | Abre y ve sus tickets | — | Todo (responde y cambia el estado) |
| Biblioteca, calendario, idiomas, comunicados | Lectura | Lectura | Todo |

Si un usuario pide un registro que no le corresponde, la API responde **404** (no revela que existe). El autor de mensajes y tickets siempre se toma de la sesión, nunca de lo que envía el navegador.

---

## 📊 Estructura de la Base de Datos

### Tabla: **Estudiante**
```
- id (PK)
- usuario (FK a User, opcional) ← cuenta para iniciar sesión
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
- profesor (texto; se reemplazará por titular)
- titular (FK a User del grupo Profesor, opcional)
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

### Tabla: **PerfilEstudiante**
```
- id (PK)
- estudiante (OneToOne)
- nivel_educativo
- programa
- periodo_actual
- materias_cursadas
- materias_totales
- progreso_academico (0-100)
- promedio
```

### Tabla: **ControlEscolar** (historial académico)
```
- id (PK)
- estudiante (FK)
- materia (FK)
- periodo (formato AAAA-N, p. ej. 2026-1, para que se ordene bien)
- calificacion
- estado (cursando/aprobado/reprobado/baja)
- unique: estudiante + materia + periodo
```

### Tabla: **ForoClase** / **MensajeForo**
```
ForoClase                         MensajeForo
- id (PK)                         - id (PK)
- clase (FK a ClaseEnLinea)       - foro (FK)
- titulo                          - autor (FK a User) ← quien publica
- descripcion                     - estudiante (FK, solo si publica un estudiante)
- activo (cerrado = sin mensajes) - contenido
                                  - fecha_publicacion
                                  - editado
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
docker-compose exec -T backend python manage.py shell < backend/seed_data.py
```

### Pruebas Automáticas
```bash
docker-compose exec backend python manage.py test cuentas
```

Django crea una base temporal `test_plataforma_universitaria`. Si falla con *Access denied*, dale permiso al usuario de MySQL una sola vez:
```bash
docker-compose exec db mysql -uroot -proot_password \
  -e "GRANT ALL PRIVILEGES ON test_plataforma_universitaria.* TO 'admin_user'@'%';"
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
│   ├── .env.example           # Plantilla de variables de entorno
│   ├── seed_data.py           # Datos y usuarios de prueba
│   ├── config/                # Configuración del proyecto
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── cuentas/               # Login, roles y permisos
│   │   ├── views.py           # csrf / login / logout / me
│   │   ├── roles.py           # Detecta el rol de un usuario
│   │   ├── permisos.py        # Clases de permiso y filtro por rol
│   │   └── tests.py           # Pruebas de autenticación y permisos
│   ├── estudiantes/           # App Estudiantes
│   ├── cursos/                # App Cursos (incluye clases Zoom)
│   ├── coordinacion/          # App Coordinación (tareas, comunicados)
│   ├── perfiles/              # Perfil académico y tutores
│   ├── servicios/             # Biblioteca, mesa de ayuda, calendario, idiomas
│   └── academico/             # Materias, clases, foros, control escolar
└── frontend/
    ├── index.html             # Campus virtual (requiere sesión)
    ├── login.html             # Inicio de sesión
    ├── zoom-config.html       # Unirse a una clase de Zoom
    ├── css/
    │   └── styles.css
    └── js/
        ├── auth.js            # Sesión, CSRF y menús por rol
        └── app.js             # Lógica del campus virtual
```

Cada app de Django sigue la misma estructura: `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py` y `migrations/`.

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
- ✅ Menús según el rol ("Mi Tutor" solo para estudiantes)

### Sesión
- ✅ Redirige al login si no hay sesión
- ✅ Nombre y rol del usuario en el encabezado
- ✅ Botón "Cerrar sesión"

### Datos Reales desde la API
- ✅ **Inicio:** bienvenida, tareas pendientes y estadísticas del perfil académico
- ✅ **Control Escolar:** historial con calificaciones (estudiante) o calificaciones de sus grupos (profesor)
- ✅ **Foro de Clase:** foros de tus cursos; publicar, editar y eliminar mensajes; los mensajes de profesores llevan etiqueta
- ✅ **Clases en Línea:** lista de clases de Zoom
- 🔄 **Biblioteca, Mi Tutor, Mesa de Ayuda, Calendario e Idiomas:** todavía muestran contenido de ejemplo (sus endpoints ya existen)

### Perfil del Estudiante
- ✅ Avatar con iniciales
- ✅ Información académica
- ✅ Progreso visual (gráfica circular)
- ✅ Matrícula y programa

### Seguridad
- ✅ Todo dato de la API se escapa antes de mostrarse (previene XSS)
- ✅ Cookie de sesión `HttpOnly`: JavaScript no puede leerla

---

## 🔧 Próximas Mejoras Sugeridas

### Funcionalidades Prioritarias
1. **Conectar las secciones restantes**
   - Biblioteca, Mi Tutor, Mesa de Ayuda, Calendario e Idiomas
   - Abrir tickets de ayuda desde el frontend

2. **Formularios Completos**
   - Crear estudiantes desde frontend
   - Inscribir a cursos
   - Subir tareas
   - Captura de calificaciones por el profesor

3. **Corregir la integración con Zoom**
   - Firma del Meeting SDK
   - Que solo el profesor del curso pueda iniciar y terminar clases
   - No exponer la contraseña de la clase en la API

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
- [x] Sistema de autenticación (sesión + roles)
- [x] Permisos por rol en toda la API
- [x] Historial académico (Control Escolar)
- [x] Foro de clase funcional
- [x] Pruebas automáticas de permisos

### Pendientes 🔄
- [ ] Conectar Biblioteca, Tutor, Mesa de Ayuda, Calendario e Idiomas
- [ ] Formularios de creación
- [ ] Captura de calificaciones desde el frontend
- [ ] Corregir integración con Zoom
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
4. Usa Postman para probar la API (inicia sesión con `/api/auth/login/` y envía el header `X-CSRFToken`)
5. Corre `python manage.py test cuentas` después de cambiar permisos

### Para Producción
1. Pon `DEBUG=False` en `backend/.env` (activa cookies solo por HTTPS)
2. Usa un `SECRET_KEY` largo y aleatorio, distinto al de desarrollo
3. Ajusta `ALLOWED_HOSTS` y, si el frontend está en otro dominio, `CSRF_TRUSTED_ORIGINS`
4. Configura HTTPS con certificados SSL
5. Usa Gunicorn en lugar de runserver
6. No publiques los puertos 8000 (Django) ni 3306 (MySQL): todo el tráfico debe pasar por Nginx
7. Cambia las contraseñas de MySQL de `docker-compose.yml`
8. Agrega monitoreo con Sentry

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
- ✅ Autenticación y permisos por rol
- ✅ Frontend moderno estilo UVEG
- ✅ Infraestructura escalable con Docker
- ✅ Base de datos relacional
- ✅ Integración completa frontend-backend

**¡Felicidades! Tu plataforma está lista para ser expandida.** 🎉
