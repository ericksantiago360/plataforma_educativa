import secrets
from django.contrib.auth.models import Group, User
from estudiantes.models import Estudiante
from cursos.models import Curso
from coordinacion.models import Tarea, Comunicado
from academico.archivos import sanear_html
from academico.models import (Materia, ControlEscolar, ClaseEnLinea, ForoClase, MensajeForo,
                              ContenidoMateria, ArchivoContenido)
from perfiles.models import PerfilEstudiante, Tutor, AsignacionTutor
from servicios.models import BibliotecaDigital, MesaAyuda, EventoCalendario, CentroIdiomas
from django.utils import timezone
from datetime import datetime, timedelta

# Crear usuarios con contraseñas aleatorias (se imprimen al final; solo para desarrollo)
credenciales = []

def crear_usuario(username, first_name='', last_name='', **extra):
    password = secrets.token_urlsafe(9)
    user = User.objects.create_user(username, password=password, first_name=first_name, last_name=last_name, **extra)
    credenciales.append((username, password))
    return user

grupo_profesor = Group.objects.get(name='Profesor')

crear_usuario('admin', 'Control', 'Escolar', is_staff=True, is_superuser=True)

prof_alfonso = crear_usuario('alfonso', 'Alfonso', 'Ramírez')
prof_alfonso.groups.add(grupo_profesor)

prof_beatriz = crear_usuario('beatriz', 'Beatriz', 'Núñez')
prof_beatriz.groups.add(grupo_profesor)

# Crear estudiantes
est1 = Estudiante.objects.create(
    usuario=crear_usuario('2024001'),
    nombre='Juan',
    apellido='Pérez',
    email='juan@example.com',
    matricula='2024001',
    telefono='555-1234'
)

est2 = Estudiante.objects.create(
    usuario=crear_usuario('2024002'),
    nombre='María',
    apellido='García',
    email='maria@example.com',
    matricula='2024002',
    telefono='555-5678'
)

est3 = Estudiante.objects.create(
    usuario=crear_usuario('2024003'),
    nombre='Carlos',
    apellido='López',
    email='carlos@example.com',
    matricula='2024003',
    telefono='555-9012'
)

# Crear cursos
curso1 = Curso.objects.create(
    nombre='Administración de Empresas',
    codigo='ADM101',
    descripcion='Conceptos fundamentales de administración',
    profesor='Dr. Alfonso',
    titular=prof_alfonso,
    creditos=3,
    fecha_inicio='2024-01-15',
    fecha_fin='2024-05-15'
)

curso2 = Curso.objects.create(
    nombre='Contabilidad I',
    codigo='CON101',
    descripcion='Principios de contabilidad general',
    profesor='Dra. Beatriz',
    titular=prof_beatriz,
    creditos=4,
    fecha_inicio='2024-01-15',
    fecha_fin='2024-05-15'
)

# Agregar estudiantes a cursos
curso1.estudiantes.add(est1, est2)
curso2.estudiantes.add(est2, est3)

# Crear tareas
tarea1 = Tarea.objects.create(
    titulo='Análisis FODA',
    descripcion='Realizar análisis FODA de una empresa',
    curso=curso1,
    fecha_vencimiento=datetime.now() + timedelta(days=7),
)

tarea2 = Tarea.objects.create(
    titulo='Balance General',
    descripcion='Preparar balance general del mes',
    curso=curso2,
    fecha_vencimiento=datetime.now() + timedelta(days=3),
)

# Crear comunicados
com1 = Comunicado.objects.create(
    titulo='Cierre de semestre',
    contenido='El semestre finaliza el próximo viernes',
    curso=curso1
)

com2 = Comunicado.objects.create(
    titulo='Cambio de aula',
    contenido='La clase de contabilidad se trasladará al edificio B',
    curso=curso2
)

# Crear materias (periodos con formato AAAA-N para que se ordenen bien)
mat_fund = Materia.objects.create(nombre='Fundamentos de Administración', codigo='ADM101-1', creditos=6, nivel=1,
                                  descripcion='Proceso administrativo y teoría de la organización', curso=curso1)
mat_comp = Materia.objects.create(nombre='Comportamiento Organizacional', codigo='ADM101-2', creditos=6, nivel=2,
                                  descripcion='Individuos, grupos y cultura en la organización', curso=curso1)
mat_fin = Materia.objects.create(nombre='Contabilidad Financiera', codigo='CON101-1', creditos=8, nivel=1,
                                 descripcion='Registro contable y estados financieros', curso=curso2)
mat_cost = Materia.objects.create(nombre='Contabilidad de Costos', codigo='CON101-2', creditos=8, nivel=2,
                                  descripcion='Costeo por órdenes y por procesos', curso=curso2)

# Historial académico: (estudiante, materia, periodo, estado, calificación)
historial = [
    (est1, mat_fund, '2026-1', 'aprobado', 9.5),
    (est1, mat_comp, '2026-2', 'cursando', None),
    (est2, mat_fund, '2026-1', 'aprobado', 8.0),
    (est2, mat_fin, '2026-1', 'aprobado', 9.0),
    (est2, mat_comp, '2026-2', 'cursando', None),
    (est2, mat_cost, '2026-2', 'cursando', None),
    (est3, mat_fin, '2026-1', 'reprobado', 5.5),
    (est3, mat_fin, '2026-2', 'cursando', None),
    (est3, mat_cost, '2026-2', 'baja', None),
]
for estudiante, materia, periodo, estado, calificacion in historial:
    ControlEscolar.objects.create(estudiante=estudiante, materia=materia, periodo=periodo,
                                  estado=estado, calificacion=calificacion)

# Clases en línea, foros y mensajes
ahora = timezone.now()
clase_comp = ClaseEnLinea.objects.create(materia=mat_comp, titulo='Sesión 3: Motivación', descripcion='Teorías de la motivación',
                                         fecha_clase=ahora - timedelta(days=2), duracion_minutos=90, estado='finalizada')
clase_cost = ClaseEnLinea.objects.create(materia=mat_cost, titulo='Sesión 2: Costeo por órdenes', descripcion='Hoja de costos',
                                         fecha_clase=ahora - timedelta(days=1), duracion_minutos=90, estado='finalizada')

foro_mot = ForoClase.objects.create(clase=clase_comp, titulo='Dudas sobre la teoría de Herzberg',
                                    descripcion='Comparte ejemplos de factores higiénicos y motivadores en tu trabajo.')
foro_cost = ForoClase.objects.create(clase=clase_cost, titulo='Ejercicio de la hoja de costos',
                                     descripcion='Publica tus dudas sobre el ejercicio de la sesión 2.')
ForoClase.objects.create(clase=clase_cost, titulo='Avisos de la sesión 1', activo=False,
                         descripcion='Foro cerrado: ya no recibe mensajes.')

MensajeForo.objects.create(foro=foro_mot, autor=est1.usuario, estudiante=est1,
                           contenido='En mi trabajo el salario no me motiva tanto como poder proponer mejoras.')
MensajeForo.objects.create(foro=foro_mot, autor=est2.usuario, estudiante=est2,
                           contenido='Coincido; para mí el reconocimiento del equipo es un motivador claro.')
MensajeForo.objects.create(foro=foro_cost, autor=est3.usuario, estudiante=est3,
                           contenido='¿La mano de obra indirecta va en gastos indirectos de fabricación?')
MensajeForo.objects.create(foro=foro_cost, autor=prof_beatriz,
                           contenido='Sí: la mano de obra indirecta forma parte de los gastos indirectos de fabricación.')

# Perfiles académicos, con estadísticas calculadas a partir del historial
MATERIAS_DEL_PLAN = 40
programas = {
    est1: 'Licenciatura en Administración',
    est2: 'Licenciatura en Contaduría',
    est3: 'Licenciatura en Contaduría',
}
for estudiante, programa in programas.items():
    PerfilEstudiante.objects.create(
        estudiante=estudiante,
        nivel_educativo='licenciatura',
        programa=programa,
        periodo_actual='2026-2',
        fecha_limite_actividades=timezone.localdate(ahora + timedelta(days=20)),  # mismo día que el cierre del periodo
        materias_totales=MATERIAS_DEL_PLAN,
    ).recalcular()

# Tutores
tutor_lucia = Tutor.objects.create(nombre='Lucía Hernández Mora', email='lucia.hernandez@universidad.edu',
                                   telefono='555-201-3040', especialidad='Ciencias Económico-Administrativas')
tutor_raul = Tutor.objects.create(nombre='Raúl Domínguez Paz', email='raul.dominguez@universidad.edu',
                                  telefono='555-201-3055', especialidad='Contaduría y Finanzas')
AsignacionTutor.objects.create(estudiante=est1, tutor=tutor_lucia)
AsignacionTutor.objects.create(estudiante=est2, tutor=tutor_raul)
AsignacionTutor.objects.create(estudiante=est3, tutor=tutor_raul)

# Biblioteca digital
recursos = [
    ('Administración: una perspectiva global', 'Harold Koontz', 'Administración', 'libro',
     'Texto clásico sobre el proceso administrativo.', 'https://openlibrary.org/search?q=koontz+administracion', '2012-01-01'),
    ('Contabilidad Financiera', 'Gerardo Guajardo', 'Contabilidad', 'libro',
     'Fundamentos de contabilidad y estados financieros.', 'https://openlibrary.org/search?q=guajardo+contabilidad', '2014-06-01'),
    ('Revista de Contaduría y Administración', 'UNAM', 'Contabilidad', 'revista',
     'Publicación académica arbitrada de la FCA-UNAM.', 'https://www.cya.unam.mx', '2024-01-01'),
    ('La teoría de los dos factores de Herzberg', 'Varios autores', 'Administración', 'articulo',
     'Revisión de la teoría de motivación e higiene.', 'https://scholar.google.com/scholar?q=Herzberg+two+factor+theory', '2019-03-15'),
    ('Introducción al costeo por órdenes', 'Canal académico', 'Contabilidad', 'video',
     'Video explicativo del costeo por órdenes de producción.', 'https://www.youtube.com/results?search_query=costeo+por+ordenes', '2021-09-01'),
]
for titulo, autor, categoria, tipo, descripcion, url, fecha in recursos:
    BibliotecaDigital.objects.create(titulo=titulo, autor=autor, categoria=categoria, tipo_recurso=tipo,
                                     descripcion=descripcion, url_recurso=url, fecha_publicacion=fecha)

# Calendario: eventos generales y de cada curso
evento_general = EventoCalendario.objects.create(
    titulo='Cierre del periodo 2026-2', descripcion='Último día para entregar actividades del periodo.',
    tipo_evento='evento', todos_estudiantes=True,
    fecha_inicio=ahora + timedelta(days=20), fecha_fin=ahora + timedelta(days=20, hours=23))
examen_adm = EventoCalendario.objects.create(
    titulo='Examen parcial de Comportamiento Organizacional', descripcion='Unidades 1 a 3.',
    tipo_evento='examen', fecha_inicio=ahora + timedelta(days=6), fecha_fin=ahora + timedelta(days=6, hours=2))
examen_adm.cursos.add(curso1)
entrega_con = EventoCalendario.objects.create(
    titulo='Entrega: hoja de costos', descripcion='Subir el ejercicio de la sesión 2.',
    tipo_evento='entrega', fecha_inicio=ahora + timedelta(days=4), fecha_fin=ahora + timedelta(days=4, hours=23))
entrega_con.cursos.add(curso2)

# Centro de idiomas
hoy = timezone.localdate()
ingles = CentroIdiomas.objects.create(idioma='ingles', nivel='basico', nombre_curso='Inglés A1',
                                      descripcion='Comunicación básica: presentaciones, rutinas y descripciones.',
                                      duracion_semanas=12, precio=1500, instructor='Mtra. Laura Smith',
                                      cupo_maximo=25, fecha_inicio=hoy + timedelta(days=15))
CentroIdiomas.objects.create(idioma='frances', nivel='basico', nombre_curso='Francés A1',
                             descripcion='Primeros pasos en francés con enfoque conversacional.',
                             duracion_semanas=12, precio=1500, instructor='Mtro. Pierre Dubois',
                             cupo_maximo=20, fecha_inicio=hoy + timedelta(days=30))
aleman = CentroIdiomas.objects.create(idioma='aleman', nivel='intermedio', nombre_curso='Alemán B1',
                                      descripcion='Grupo reducido para nivel intermedio.',
                                      duracion_semanas=16, precio=1800, instructor='Mtra. Anna Becker',
                                      cupo_maximo=2, fecha_inicio=hoy + timedelta(days=45))
ingles.estudiantes_inscritos.add(est2)
aleman.estudiantes_inscritos.add(est1, est3)  # grupo lleno, para ver el "Sin cupo"

# Mesa de ayuda: un ticket respondido y uno abierto
MesaAyuda.objects.create(estudiante=est2, categoria='tecnico', asunto='No puedo ver la grabación de la sesión 2',
                         descripcion='Al abrir la grabación aparece un error de permisos.',
                         estado='resuelto', respuesta='Ya quedó corregido el permiso. Intenta de nuevo, por favor.')
MesaAyuda.objects.create(estudiante=est2, categoria='administrativo', asunto='Constancia de estudios',
                         descripcion='Necesito una constancia de estudios para mi trabajo.')

# Contenido de materias: texto con tabla, video de YouTube y adjuntos (PDF e imagen generados aquí mismo)
def pdf_de_ejemplo(texto):
    flujo = f'BT /F1 18 Tf 72 720 Td ({texto}) Tj ET'.encode('latin-1')
    objetos = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
        b'<< /Length ' + str(len(flujo)).encode() + b' >>\nstream\n' + flujo + b'\nendstream',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ]
    pdf, posiciones = b'%PDF-1.4\n', []
    for numero, objeto in enumerate(objetos, start=1):
        posiciones.append(len(pdf))
        pdf += f'{numero} 0 obj\n'.encode() + objeto + b'\nendobj\n'
    inicio_xref = len(pdf)
    pdf += f'xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n'.encode()
    pdf += b''.join(f'{p:010d} 00000 n \n'.encode() for p in posiciones)
    pdf += f'trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{inicio_xref}\n%%EOF\n'.encode()
    return pdf

def png_de_ejemplo(ancho=320, alto=180):
    import struct, zlib
    # cada fila: byte de filtro + RGB por pixel (degradado)
    filas = b''.join(b'\x00' + b''.join(bytes((40 + x * 180 // ancho, 90, 200 - y * 120 // alto)) for x in range(ancho))
                     for y in range(alto))
    def bloque(tipo, datos):
        return struct.pack('>I', len(datos)) + tipo + datos + struct.pack('>I', zlib.crc32(tipo + datos) & 0xffffffff)
    return (b'\x89PNG\r\n\x1a\n' + bloque(b'IHDR', struct.pack('>IIBBBBB', ancho, alto, 8, 2, 0, 0, 0))
            + bloque(b'IDAT', zlib.compress(filas)) + bloque(b'IEND', b''))

from django.core.files.base import ContentFile
leccion = ContenidoMateria.objects.create(
    materia=mat_comp, autor=prof_alfonso, publicado=True, orden=1,
    titulo='Unidad 3: Teorías de la motivación',
    cuerpo=sanear_html(
        '<h2>Objetivo</h2><p>Comparar las principales teorías de la motivación y aplicarlas a casos reales.</p>'
        '<h3>Resumen de teorías</h3>'
        '<table><thead><tr><th>Teoría</th><th>Autor</th><th>Idea central</th></tr></thead><tbody>'
        '<tr><td>Jerarquía de necesidades</td><td>Maslow</td><td>Las necesidades se satisfacen por niveles.</td></tr>'
        '<tr><td>Dos factores</td><td>Herzberg</td><td>Factores higiénicos vs. motivadores.</td></tr>'
        '<tr><td>Expectativas</td><td>Vroom</td><td>Esfuerzo → desempeño → recompensa.</td></tr>'
        '</tbody></table>'
        '<p><strong>Actividad:</strong> lee la guía en PDF y comenta un ejemplo en el foro.</p>'),
    video_youtube='Lp7E973zozc',
)
for nombre, datos, tipo in [('Guía de la unidad 3.pdf', pdf_de_ejemplo('Guia de la unidad 3 - Teorias de la motivacion'), 'documento'),
                            ('Diagrama de motivación.png', png_de_ejemplo(), 'imagen')]:
    adjunto = ArchivoContenido(contenido=leccion, nombre=nombre, tipo=tipo, tamano=len(datos))
    adjunto.archivo.save(nombre, ContentFile(datos), save=True)
ContenidoMateria.objects.create(materia=mat_comp, autor=prof_alfonso, publicado=False, orden=2,
                                titulo='Unidad 4: Liderazgo (borrador)', cuerpo='<p>En preparación.</p>')

print("✅ Datos de ejemplo creados exitosamente")
print("\nUsuarios de prueba (usuario / contraseña):")
for usuario, password in credenciales:
    print(f"  {usuario:10} {password}")
