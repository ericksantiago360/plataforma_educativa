from django.db import models
from estudiantes.models import Estudiante

class Curso(models.Model):
    nombre = models.CharField(max_length=150)
    codigo = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField()
    profesor = models.CharField(max_length=100)
    creditos = models.IntegerField(default=3)
    estudiantes = models.ManyToManyField(Estudiante, related_name='cursos', blank=True)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"

    @property
    def cantidad_estudiantes(self):
        return self.estudiantes.count()

# Modelos de Zoom
from django.db import models as db_models
from estudiantes.models import Estudiante

class ClaseZoom(db_models.Model):
    ESTADOS = [
        ('programada', 'Programada'),
        ('en_vivo', 'En Vivo'),
        ('finalizada', 'Finalizada'),
        ('cancelada', 'Cancelada'),
    ]
    
    curso = db_models.ForeignKey(Curso, on_delete=db_models.CASCADE, related_name='clases_zoom')
    titulo = db_models.CharField(max_length=200)
    descripcion = db_models.TextField()
    fecha_hora_inicio = db_models.DateTimeField()
    duracion_minutos = db_models.IntegerField(default=60)
    session_name = db_models.CharField(max_length=200, unique=True)
    password = db_models.CharField(max_length=50, blank=True)
    estado = db_models.CharField(max_length=20, choices=ESTADOS, default='programada')
    url_grabacion = db_models.URLField(blank=True, null=True)
    max_participantes = db_models.IntegerField(default=100)
    creado = db_models.DateTimeField(auto_now_add=True)
    actualizado = db_models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-fecha_hora_inicio']
        verbose_name = 'Clase Zoom'
        verbose_name_plural = 'Clases Zoom'
    
    def __str__(self):
        return f"{self.titulo} - {self.curso.nombre}"

class ParticipanteClase(db_models.Model):
    clase = db_models.ForeignKey(ClaseZoom, on_delete=db_models.CASCADE, related_name='participantes')
    estudiante = db_models.ForeignKey(Estudiante, on_delete=db_models.CASCADE, related_name='clases_asistidas')
    fecha_ingreso = db_models.DateTimeField(null=True, blank=True)
    fecha_salida = db_models.DateTimeField(null=True, blank=True)
    asistio = db_models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['clase', 'estudiante']
        verbose_name = 'Participante'
        verbose_name_plural = 'Participantes'
    
    def __str__(self):
        return f"{self.estudiante.nombre} - {self.clase.titulo}"
