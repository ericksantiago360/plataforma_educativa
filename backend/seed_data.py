from estudiantes.models import Estudiante
from cursos.models import Curso
from coordinacion.models import Tarea, Comunicado
from datetime import datetime, timedelta

# Crear estudiantes
est1 = Estudiante.objects.create(
    nombre='Juan',
    apellido='Pérez',
    email='juan@example.com',
    matricula='2024001',
    telefono='555-1234'
)

est2 = Estudiante.objects.create(
    nombre='María',
    apellido='García',
    email='maria@example.com',
    matricula='2024002',
    telefono='555-5678'
)

est3 = Estudiante.objects.create(
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
    creditos=3,
    fecha_inicio='2024-01-15',
    fecha_fin='2024-05-15'
)

curso2 = Curso.objects.create(
    nombre='Contabilidad I',
    codigo='CON101',
    descripcion='Principios de contabilidad general',
    profesor='Dra. Beatriz',
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
    estado='pendiente'
)
tarea1.estudiantes.add(est1, est2)

tarea2 = Tarea.objects.create(
    titulo='Balance General',
    descripcion='Preparar balance general del mes',
    curso=curso2,
    fecha_vencimiento=datetime.now() + timedelta(days=3),
    estado='pendiente'
)
tarea2.estudiantes.add(est2, est3)

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

print("✅ Datos de ejemplo creados exitosamente")
