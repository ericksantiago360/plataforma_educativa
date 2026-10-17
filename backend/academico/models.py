import os
import uuid

from django.conf import settings
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from estudiantes.models import Estudiante
from cursos.models import Curso

class Materia(models.Model):
    nombre = models.CharField(max_length=200)
    codigo = models.CharField(max_length=50, unique=True)
    creditos = models.IntegerField()
    nivel = models.IntegerField()
    descripcion = models.TextField()
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='materias')
    activo = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

class ClaseEnLinea(models.Model):
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='clases')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    url_clase = models.URLField(blank=True)
    url_grabacion = models.URLField(blank=True)
    fecha_clase = models.DateTimeField()
    duracion_minutos = models.IntegerField()
    estado = models.CharField(max_length=20, choices=[
        ('programada', 'Programada'),
        ('en_vivo', 'En Vivo'),
        ('finalizada', 'Finalizada'),
    ], default='programada')
    
    class Meta:
        verbose_name_plural = "Clases en Línea"
        ordering = ['-fecha_clase']
    
    def __str__(self):
        return f"{self.materia.nombre} - {self.titulo}"

class ForoClase(models.Model):
    clase = models.ForeignKey(ClaseEnLinea, on_delete=models.CASCADE, related_name='foros')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Foros de Clase"
    
    def __str__(self):
        return self.titulo

class MensajeForo(models.Model):
    foro = models.ForeignKey(ForoClase, on_delete=models.CASCADE, related_name='mensajes')
    # Quien publica: estudiante, profesor o staff. Define quién puede editar el mensaje.
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='mensajes_publicados')
    # Solo se llena cuando publica un estudiante (conserva el vínculo con su expediente)
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, null=True, blank=True, related_name='mensajes_foro')
    contenido = models.TextField()
    fecha_publicacion = models.DateTimeField(auto_now_add=True)
    editado = models.BooleanField(default=False)

    class Meta:
        ordering = ['fecha_publicacion']

    @property
    def autor_nombre(self):
        if self.estudiante:
            return f"{self.estudiante.nombre} {self.estudiante.apellido}"
        if self.autor:
            return self.autor.get_full_name() or self.autor.username
        return 'Usuario eliminado'

    def __str__(self):
        return f"{self.autor_nombre} - {self.foro.titulo}"

class ControlEscolar(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='historial_escolar')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE)
    calificacion = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    periodo = models.CharField(max_length=50)
    fecha_inscripcion = models.DateField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=[
        ('cursando', 'Cursando'),
        ('aprobado', 'Aprobado'),
        ('reprobado', 'Reprobado'),
        ('baja', 'Baja'),
    ], default='cursando')
    
    class Meta:
        unique_together = ['estudiante', 'materia', 'periodo']
        verbose_name_plural = "Control Escolar"
    
    def __str__(self):
        return f"{self.estudiante.nombre} - {self.materia.nombre}"


def ruta_archivo_contenido(instancia, nombre_original):
    # Nombre aleatorio: evita choques y que la ruta revele o permita adivinar el nombre original
    extension = os.path.splitext(nombre_original)[1].lower()
    return f'contenidos/materia_{instancia.contenido.materia_id}/{uuid.uuid4().hex}{extension}'

class ContenidoMateria(models.Model):
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='contenidos')
    titulo = models.CharField(max_length=200)
    cuerpo = models.TextField(blank=True)  # HTML ya saneado (ver archivos.sanear_html)
    video_youtube = models.CharField(max_length=11, blank=True)  # solo el id del video
    publicado = models.BooleanField(default=False)
    orden = models.PositiveIntegerField(default=0)
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='contenidos_creados')
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['orden', 'creado']
        verbose_name = 'Contenido de materia'
        verbose_name_plural = 'Contenidos de materias'

    def __str__(self):
        return f"{self.materia.codigo} - {self.titulo}"

class ArchivoContenido(models.Model):
    TIPOS = [
        ('documento', 'Documento'),
        ('imagen', 'Imagen'),
        ('video', 'Video'),
    ]

    contenido = models.ForeignKey(ContenidoMateria, on_delete=models.CASCADE, related_name='archivos')
    archivo = models.FileField(upload_to=ruta_archivo_contenido)
    nombre = models.CharField(max_length=255)  # nombre original, para mostrarlo y descargarlo
    tipo = models.CharField(max_length=10, choices=TIPOS)
    tamano = models.PositiveBigIntegerField()
    subido = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['tipo', 'subido']
        verbose_name = 'Archivo de contenido'
        verbose_name_plural = 'Archivos de contenido'

    def __str__(self):
        return self.nombre

@receiver(post_delete, sender=ArchivoContenido)
def borrar_archivo_del_disco(sender, instance, **kwargs):
    # También se ejecuta al borrar el contenido o la materia (borrado en cascada)
    instance.archivo.delete(save=False)
