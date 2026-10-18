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
- ✅ 12 secciones principales:
  - 🏠 Inicio
  - 📚 Biblioteca Digital
  - 📋 Control Escolar
  - 📝 Tareas
  - 📖 Contenido de Materias
  - 👨‍🏫 Mi Tutor
  - 🆘 Mesa de Ayuda
  - 📅 Calendario
  - 🌎 Centro de Idiomas
  - 🎥 Clases en Línea
  - 💬 Foro de Clase
  - ⚙️ Administración (solo staff)

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
| **Mailpit** | http://localhost:8025 | Bandeja de prueba con los correos que envía la plataforma |

> 🔒 Toda la API exige sesión. Para explorarla desde el navegador, inicia sesión primero en http://localhost:8000/admin/ y luego abre http://localhost:8000/api/estudiantes/ (la sesión se comparte en el mismo puerto).

### Endpoints de autenticación (`/api/auth/`)

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/auth/csrf/` | GET | Entrega la cookie `csrftoken` |
| `/api/auth/login/` | POST | `{usuario, password}` → inicia sesión (máx. 5 intentos por minuto por IP) |
| `/api/auth/logout/` | POST | Cierra la sesión |
| `/api/auth/me/` | GET | Usuario actual: `{id, usuario, nombre, rol, estudiante, debe_cambiar_password}` |
| `/api/auth/cambiar-password/` | POST | `{password_actual, password_nueva}` → cambia la contraseña con las reglas de Django (máx. 5 intentos por minuto); conserva la sesión actual y cierra las demás |

Las peticiones `POST`, `PUT`, `PATCH` y `DELETE` deben enviar el header `X-CSRFToken` con el valor de la cookie `csrftoken` (`frontend/js/auth.js` lo hace con la función `api()`).

### Endpoints de datos (`/api/`)

| App | Endpoints |
|-----|-----------|
| estudiantes | `estudiantes/` |
| cursos | `cursos/`, `clases-zoom/`, `participantes-clase/` |
| coordinacion | `tareas/`, `archivos-entrega/`, `comunicados/` |
| perfiles | `perfiles/`, `tutores/`, `asignaciones-tutor/` |
| servicios | `biblioteca/`, `mesa-ayuda/`, `calendario/`, `idiomas/` |
| academico | `materias/`, `clases/`, `foros/`, `mensajes-foro/`, `control-escolar/` |
| pagos | `conceptos-pago/`, `cargos/`, `pagos/` |

Filtros y acciones extra:
- `mensajes-foro/?foro=<id>` trae solo los mensajes de un foro.
- `calendario/?proximos=1` omite los eventos que ya terminaron.
- `POST idiomas/<id>/inscribir/` y `POST idiomas/<id>/cancelar/` inscriben o dan de baja al estudiante de la sesión (respetando el cupo).
- `GET estudiantes/<id>/kardex/` descarga en PDF el historial completo con promedio y créditos aprobados (el propio estudiante o el staff).
- `GET materias/<id>/reporte_grupo/?periodo=AAAA-N` descarga en PDF las calificaciones del grupo en ese periodo (el profesor de la materia o el staff).
- Pagos (registro interno; el staff funciona como caja):
  - `POST cargos/` (staff) crea un cargo a un alumno desde el catálogo; `POST cargos/masivo/` con `{concepto, periodo, fecha_limite}` lo genera a todos los activos que aún no lo tengan.
  - `POST cargos/<id>/pagar/` (staff) con `{monto, metodo, referencia}` registra un pago (parcial o total, nunca más que el saldo); `POST cargos/<id>/cancelar/` cancela un cargo sin pagos.
  - `POST cargos/solicitar_tramite/` con `{concepto}`: el estudiante pide un trámite del catálogo y se le genera el cargo.
  - `POST pagos/<id>/anular/` (staff) con `{motivo}` anula un pago (no se borran); `GET pagos/<id>/recibo/` descarga el recibo en PDF.
  - Inscribirse a un curso de idiomas con costo genera su cargo; cancelar la inscripción lo cancela si aún no tiene pagos.
- `POST tareas/<id>/entregar/` (multipart, campo `archivo`) sube un archivo a la entrega del estudiante de la sesión y la marca completada. Se acepta después del vencimiento, marcada como tarde.
- `GET tareas/<id>/entregas/` (profesor del curso y staff) lista a cada alumno inscrito con su estado y sus archivos.
- `GET archivos-entrega/<id>/descargar/` descarga un archivo de entrega (el alumno, el profesor del curso o el staff); `DELETE archivos-entrega/<id>/` lo quita (solo el alumno o el staff).
- `POST tareas/<id>/estado/` con `{"estado": "completada"}` marca el avance del estudiante de la sesión. Al listar tareas, el estudiante recibe su `estado` y profesor/staff un `resumen` del grupo.
- `POST estudiantes/alta/` (staff) crea estudiante + cuenta (usuario = matrícula) + perfil y devuelve **una sola vez** la contraseña temporal.
- `GET cursos/<id>/inscritos/` (profesor y staff), `POST cursos/<id>/inscribir/` y `POST cursos/<id>/quitar/` (staff) con `{estudiante}`.
- `POST materias/<id>/inscribir_grupo/` (staff) con `{periodo}` crea el historial "cursando" de cada alumno activo del curso que aún no lo tenga.
- `contenidos/?materia=<id>` lista el contenido de una materia. `POST contenidos/<id>/subir_archivo/` (multipart, campo `archivo`) agrega un adjunto.
- `GET archivos-contenido/<id>/descargar/` entrega un adjunto **revisando permisos** (no hay URL pública de los archivos); `DELETE archivos-contenido/<id>/` lo quita.

---

## ✉️ Avisos por correo

La plataforma avisa por correo a los alumnos activos (al email de su registro de Estudiante) cuando:

| Evento | Destinatarios |
|--------|---------------|
| El profesor crea una tarea | Alumnos del curso |
| Se captura o cambia una calificación final (aprobado/reprobado) | El alumno |
| El staff genera un cargo (individual o masivo) | Cada alumno con el cargo |
| Se registra un pago (con el **recibo PDF adjunto**) o se anula | El alumno |
| El staff responde o cambia el estado de un ticket de la Mesa de Ayuda | El alumno |
| Se publica un comunicado activo por la API | Alumnos del curso, o todos si es general |

Los correos salen cuando la operación ya se guardó; si el servidor de correo falla, solo queda en el log del backend y la operación no se pierde. Lo que se hace desde el admin de Django no envía avisos.

**En desarrollo** los atrapa **Mailpit**: no salen a internet y se ven en http://localhost:8025.

**En producción** configura un proveedor SMTP en `backend/.env` (ver `backend/.env.example`) y quita de `docker-compose.yml` las variables `EMAIL_*` que apuntan a Mailpit:
```
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.tu-proveedor.com
EMAIL_PORT=587
EMAIL_HOST_USER=usuario
EMAIL_HOST_PASSWORD=contraseña
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=Campus Virtual <no-responder@tu-universidad.mx>
URL_PLATAFORMA=https://campus.tu-universidad.mx
```
Sin configuración, los correos se imprimen en la consola del backend.

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
| Cursos | Los que cursa (lectura) | Los suyos (edita, no crea ni borra) | Todo, incluida la inscripción de alumnos |
| Materias | Las de sus cursos (lectura) | Las de sus cursos (lectura) | Todo, incluida la inscripción del grupo |
| Contenido de materias | Lo **publicado** de sus materias activas | Crea, edita, publica y elimina en sus materias (incluye borradores y adjuntos) | Todo |
| Tareas | Las de sus cursos (lectura) | Crea y elimina en sus cursos | Todo |
| Clases, foros | Los de sus cursos (lectura) | Los de sus cursos (edita) | Todo |
| Control escolar | Su historial (lectura) | Captura calificaciones de sus materias | Todo |
| Alta de estudiantes | — | — | Sí |
| Mensajes de foro | Publica, edita y borra los suyos | Publica y edita los suyos; borra cualquiera de sus cursos (moderar) | Todo |
| Mesa de ayuda | Abre y ve sus tickets | — | Todo (responde y cambia el estado) |
| Calendario | Eventos generales y de sus cursos | Eventos generales y de sus cursos | Todo |
| Centro de idiomas | Ve los cursos activos; se inscribe y cancela | Ve los cursos activos | Todo (incluida la lista de inscritos) |
| Mi tutor | Sus tutores asignados | Tutores de sus alumnos | Todo |
| Biblioteca, comunicados | Lectura (biblioteca: solo recursos activos) | Lectura | Todo |

**Adjuntos permitidos en el contenido de materias:** PDF, Word, PowerPoint y Excel (hasta 25 MB); JPG, PNG, GIF y WebP (hasta 10 MB); MP4 y WebM (hasta 200 MB). El servidor valida la extensión, el tamaño y que el contenido real del archivo corresponda (un HTML renombrado a `.pdf` se rechaza). El texto del editor se sanea: solo se conservan formato, enlaces y tablas.

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
- creado
```
La tarea es de todo el curso, también para quien se inscriba después.

### Tabla: **EntregaTarea**
```
- id (PK)
- tarea (FK)
- estudiante (FK)
- estado (pendiente/en_progreso/completada)
- entregado (fecha del último archivo subido; se marca "tarde" si pasa del vencimiento)
- actualizado
```
El avance de cada alumno en una tarea. Se crea la primera vez que el alumno cambia su estado o entrega; sin registro, la tarea está pendiente para él.

### Tabla: **ArchivoEntrega**
```
- id (PK)
- entrega (FK a EntregaTarea)
- archivo (en media/entregas/, con nombre aleatorio)
- nombre (original)
- tipo (documento/imagen/video)
- tamano
- subido
```
Mismos formatos y límites que los adjuntos de materias, hasta 10 archivos por entrega.

### Tabla: **ConceptoPago**
```
- id (PK)
- nombre
- tipo (colegiatura/inscripcion/tramite)
- monto
- activo
```

### Tabla: **Cargo**
```
- id (PK)
- estudiante (FK, protegido: un alumno con cargos no se borra)
- concepto (FK, opcional) / curso_idiomas (FK, opcional)
- descripcion, tipo, periodo, monto, fecha_limite
- cancelado
- creado, creado_por
```
Lo pagado, el saldo y el estado (pendiente/parcial/pagado/cancelado) se calculan de sus pagos no anulados.

### Tabla: **Pago**
```
- id (PK) → folio R-000001
- cargo (FK)
- monto, metodo (efectivo/transferencia/deposito/tarjeta), referencia
- fecha, registrado_por
- anulado, motivo_anulacion, anulado_por
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

### Tabla: **Materia**
```
- id (PK)
- curso (FK)
- nombre
- codigo (unique, se guarda en mayúsculas)
- creditos (≥ 0)
- nivel (semestre, ≥ 1)
- descripcion
- activo (inactiva = no admite inscripciones)
```

### Tabla: **ContenidoMateria** / **ArchivoContenido**
```
ContenidoMateria                       ArchivoContenido
- id (PK)                              - id (PK)
- materia (FK)                         - contenido (FK)
- titulo                               - archivo (ruta con nombre aleatorio en media/)
- cuerpo (HTML saneado: texto,         - nombre (original, para mostrar)
  enlaces y tablas)                    - tipo (documento/imagen/video)
- video_youtube (id del video)         - tamano
- publicado (borrador = solo profesor) - subido
- orden, autor, creado, actualizado
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
docker-compose exec backend python manage.py test
```

Son 185 pruebas, en el `tests.py` de cada app: autenticación y permisos (`cuentas`, incluidos el bloqueo de estudiantes dados de baja y el cambio de contraseña), servicios, alta de estudiantes, inscripción a cursos, clases de Zoom y asistencia, tareas, avance y entrega de archivos por alumno, comunicados, materias, calificaciones y promedio, reportes en PDF, pagos (cargos, pagos parciales, anulaciones y recibos), avisos por correo, perfiles, y contenido de materias (saneamiento de HTML, validación y descarga protegida de archivos).

Django crea una base temporal `test_plataforma_universitaria`. Si falla con *Access denied*, dale permiso al usuario de MySQL una sola vez:
```bash
docker-compose exec db mysql -uroot -proot_password \
  -e "GRANT ALL PRIVILEGES ON test_plataforma_universitaria.* TO 'admin_user'@'%';"
```

### Solución de Problemas

| Síntoma (en `docker-compose logs backend`) | Causa | Solución |
|---|---|---|
| `SECRET_KEY not found` | Falta `SECRET_KEY` en `backend/.env` | Agrégala (ver Puesta en Marcha, paso 1) y `docker-compose up -d backend` |
| `No module named 'jwt'` u otro `ModuleNotFoundError` | La imagen se construyó antes de cambiar `requirements.txt` | `docker-compose up -d --build` |
| `no such table` / `Unknown column` | Faltan migraciones | `docker-compose exec backend python manage.py migrate` |
| El seed falla con `Duplicate entry` | El seed ya se había ejecutado | `docker-compose down -v` (⚠️ borra los datos) y repetir la Puesta en Marcha |
| Los estudiantes no pueden iniciar sesión | Su registro no tiene `usuario` enlazado | Crear el usuario en el admin y enlazarlo al estudiante |
| Un adjunto da error 413 al subirlo | Supera `client_max_body_size` de nginx (210 MB) | Usa un archivo más pequeño o un enlace de YouTube para videos largos |
| Los adjuntos responden en blanco al abrirlos por el puerto 8000 | Con `SERVIR_ARCHIVOS_CON_NGINX=True` el archivo lo envía nginx | Entra siempre por http://localhost (puerto 80) |
| El editor de texto aparece como un cuadro simple | No cargó TinyMCE desde el CDN (sin internet) | Revisa la conexión; mientras tanto se puede escribir texto simple |
| "Tu inscripción está dada de baja" al iniciar sesión | El estudiante tiene `activo` desmarcado (también corta las sesiones abiertas) | Si debe volver a entrar, marca `activo` en su registro de Estudiante desde el admin |
| "Usuario o contraseña incorrectos" con una cuenta que antes funcionaba | La contraseña se cambió (por ejemplo, con "Cambiar contraseña" del campus o del admin, que no quedan en el historial) | Asigna una nueva: `docker-compose exec backend python manage.py changepassword <usuario>` |
| "Demasiados intentos. Espera un minuto…" | Límite de 5 intentos de login por minuto **por equipo** (todas las cuentas desde la misma IP cuentan juntas) | Espera un minuto y vuelve a intentar |
| El login falla con `CSRF cookie not set` en los logs | La página de login llevaba mucho tiempo abierta o se borraron las cookies | Recarga `login.html` antes de iniciar sesión |
| http://localhost/admin/ muestra el campus y no el panel de Django | nginx solo reenvía `/api` al backend | Usa http://localhost:8000/admin/ |

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
│   ├── academico/             # Materias, contenido, clases, foros, control escolar, reportes PDF
│   ├── pagos/                 # Conceptos, cargos, pagos y recibos
│   ├── notificaciones/        # Avisos por correo a los alumnos
│   │   └── archivos.py        # Validación de adjuntos, saneamiento de HTML y YouTube
│   └── media/                 # Adjuntos subidos (no se versiona; lo sirve nginx tras revisar permisos)
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
- ✅ **Inicio:** banner con el periodo y la fecha límite del perfil (o la próxima entrega del calendario)
- ✅ **Control Escolar:** historial con calificaciones (estudiante); el profesor captura calificaciones y el perfil del alumno se recalcula solo
- ✅ **Tareas:** el profesor crea tareas para sus cursos (se asignan a todo el grupo); el estudiante ve las suyas y cuáles están vencidas
- ✅ **Administración (staff):** alta de estudiantes con cuenta y perfil, inscripción a cursos, materias e inscripción del grupo a una materia
- ✅ **Contenido de Materias:** el profesor crea lecciones con texto enriquecido y **tablas** (editor TinyMCE), adjunta **PDF, Word, PowerPoint, Excel, imágenes y videos** (con barra de progreso) o un **video de YouTube**, y decide si se publican; el estudiante ve lo publicado con reproductor, galería y descargas
- ✅ **Foro de Clase:** foros de tus cursos; publicar, editar y eliminar mensajes; los mensajes de profesores llevan etiqueta
- ✅ **Clases en Línea:** lista de clases de Zoom
- ✅ **Biblioteca Digital:** recursos con buscador y filtro por tipo
- ✅ **Mi Tutor:** datos del tutor asignado y botón para solicitar cita por correo
- ✅ **Mesa de Ayuda:** el estudiante abre tickets y ve las respuestas; el staff responde y cambia el estado
- ✅ **Calendario:** próximos eventos generales y de tus cursos
- ✅ **Centro de Idiomas:** cursos con cupos; inscribirse y cancelar la inscripción

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
1. **Entregas de tareas**
   - Que el profesor califique y comente cada entrega

2. **Gestión de cuentas**
   - Editar materias e inscribir a un alumno individual en una materia desde la página

3. **Corregir la integración con Zoom**
   - Firma del Meeting SDK
   - No exponer la contraseña de la clase en la API

4. **Notificaciones**
   - Envío de correos en segundo plano (cola) para grupos muy grandes
   - Que cada alumno elija qué avisos recibir
   - Notificaciones push
   - Alertas de tareas

5. **Reportes y Exportación**
   - Exportar datos a Excel
   - Certificados digitales

### Funcionalidades Secundarias
- Chat en tiempo real (WebSockets)
- Pago en línea (Stripe o Mercado Pago) sobre el registro interno de pagos
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
- **TinyMCE 6** (MIT, desde CDN) - Editor de texto enriquecido con tablas

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
- [x] Biblioteca, Tutor, Mesa de Ayuda, Calendario e Idiomas conectados a la API
- [x] Inscripción a cursos de idiomas con control de cupo
- [x] Banner de período dinámico
- [x] Alta de estudiantes con cuenta y perfil
- [x] Inscripción de alumnos a cursos
- [x] Creación de tareas por el profesor
- [x] Captura de calificaciones con recálculo del perfil
- [x] Materias e inscripción del grupo por periodo
- [x] Contenido de materias con texto, tablas, adjuntos, imágenes y videos
- [x] Entregas de tareas con archivos
- [x] Cambio de contraseña (obligatorio para la contraseña temporal del alta)
- [x] Permisos por rol en las clases de Zoom
- [x] Reportes en PDF (kardex y reporte de grupo)
- [x] Sistema de pagos (cargos, pagos en caja y recibos en PDF)
- [x] Avisos por correo (tareas, calificaciones, cargos, pagos, mesa de ayuda, comunicados)

### Pendientes 🔄
- [ ] Corregir integración con Zoom
- [ ] Chat en tiempo real
- [ ] App móvil

---

## 💡 Consejos de Uso

### Para Desarrollo
1. Siempre usa `docker-compose logs` para depurar
2. Guarda backups de la base de datos regularmente
3. Prueba en el panel de admin antes del frontend
4. Usa Postman para probar la API (inicia sesión con `/api/auth/login/` y envía el header `X-CSRFToken`)
5. Corre `python manage.py test` después de cambiar permisos
6. Si cambias `requirements.txt`, reconstruye la imagen con `docker-compose up -d --build`

### Para Producción
1. Pon `DEBUG=False` en `backend/.env` (activa cookies solo por HTTPS)
2. Usa un `SECRET_KEY` largo y aleatorio, distinto al de desarrollo
3. Ajusta `ALLOWED_HOSTS` y, si el frontend está en otro dominio, `CSRF_TRUSTED_ORIGINS`
4. Configura HTTPS con certificados SSL
5. Usa Gunicorn en lugar de runserver
6. No publiques los puertos 8000 (Django) ni 3306 (MySQL): todo el tráfico debe pasar por Nginx
7. Cambia las contraseñas de MySQL de `docker-compose.yml`
8. Respalda `backend/media/` junto con la base de datos: ahí están los adjuntos de las materias
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
