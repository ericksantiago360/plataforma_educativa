from django.db import models
from .models import Curso
from estudiantes.models import Estudiante

class ClaseZoom(models.Model):
    ESTADOS = [
        ('programada', 'Programada'),
        ('en_vivo', 'En Vivo'),
        ('finalizada', 'Finalizada'),
        ('cancelada', 'Cancelada'),
    ]
    
    curso = models.ForeignKey(Curso, on_delete=models.CASCADE, related_name='clases_zoom')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    fecha_hora_inicio = models.DateTimeField()
    duracion_minutos = models.IntegerField(default=60)
    session_name = models.CharField(max_length=200, unique=True)  # Nombre único para Zoom
    password = models.CharField(max_length=50, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='programada')
    url_grabacion = models.URLField(blank=True, null=True)
    max_participantes = models.IntegerField(default=100)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-fecha_hora_inicio']
        verbose_name = 'Clase Zoom'
        verbose_name_plural = 'Clases Zoom'
    
    def __str__(self):
        return f"{self.titulo} - {self.curso.nombre}"

class ParticipanteClase(models.Model):
    clase = models.ForeignKey(ClaseZoom, on_delete=models.CASCADE, related_name='participantes')
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='clases_asistidas')
    fecha_ingreso = models.DateTimeField(null=True, blank=True)
    fecha_salida = models.DateTimeField(null=True, blank=True)
    asistio = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['clase', 'estudiante']
        verbose_name = 'Participante'
        verbose_name_plural = 'Participantes'
    
    def __str__(self):
        return f"{self.estudiante.nombre} - {self.clase.titulo}"
