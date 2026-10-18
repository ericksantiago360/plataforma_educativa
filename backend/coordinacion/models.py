import os
import uuid

from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from academico.models import ArchivoContenido
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
    entregado = models.DateTimeField(null=True, blank=True)  # último archivo subido
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['tarea', 'estudiante']
        verbose_name = 'Entrega de tarea'
        verbose_name_plural = 'Entregas de tareas'

    def __str__(self):
        return f"{self.estudiante.nombre} - {self.tarea.titulo} ({self.get_estado_display()})"

    @property
    def tarde(self):
        return self.entregado is not None and self.entregado > self.tarea.fecha_vencimiento

def ruta_archivo_entrega(instancia, nombre_original):
    # Nombre aleatorio, como en los adjuntos de materias: no revela ni permite adivinar el nombre original
    extension = os.path.splitext(nombre_original)[1].lower()
    return f'entregas/tarea_{instancia.entrega.tarea_id}/{uuid.uuid4().hex}{extension}'

class ArchivoEntrega(models.Model):
    entrega = models.ForeignKey(EntregaTarea, on_delete=models.CASCADE, related_name='archivos')
    archivo = models.FileField(upload_to=ruta_archivo_entrega)
    nombre = models.CharField(max_length=255)  # nombre original, para mostrarlo y descargarlo
    tipo = models.CharField(max_length=10, choices=ArchivoContenido.TIPOS)
    tamano = models.PositiveBigIntegerField()
    subido = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['subido']
        verbose_name = 'Archivo de entrega'
        verbose_name_plural = 'Archivos de entregas'

    def __str__(self):
        return self.nombre

@receiver(post_delete, sender=ArchivoEntrega)
def borrar_archivo_del_disco(sender, instance, **kwargs):
    # También se ejecuta al borrar la entrega, la tarea o el curso (borrado en cascada)
    instance.archivo.delete(save=False)

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
