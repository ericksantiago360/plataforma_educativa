from django.db import models
from estudiantes.models import Estudiante
from cursos.models import Curso

class Tarea(models.Model):
    # La tarea es de todo el curso (también para quien se inscriba después);
    # el avance de cada alumno vive en EntregaTarea
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='tareas')
    fecha_vencimiento = models.DateTimeField()
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_vencimiento']

    def __str__(self):
        return self.titulo

class EntregaTarea(models.Model):
    ESTADOS = [
        ('pendiente', 'Pendiente'),
        ('en_progreso', 'En Progreso'),
        ('completada', 'Completada'),
    ]

    # Se crea la primera vez que el alumno cambia su estado; sin registro, la tarea está pendiente para él
    tarea = models.ForeignKey(Tarea, on_delete=models.CASCADE, related_name='entregas')
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='entregas_tareas')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['tarea', 'estudiante']
        verbose_name = 'Entrega de tarea'
        verbose_name_plural = 'Entregas de tareas'

    def __str__(self):
        return f"{self.estudiante.nombre} - {self.tarea.titulo} ({self.get_estado_display()})"

class Comunicado(models.Model):
    titulo = models.CharField(max_length=200)
    contenido = models.TextField()
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='comunicados', null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return self.titulo
