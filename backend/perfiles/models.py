from django.db import models
from django.contrib.auth.models import User
from estudiantes.models import Estudiante

class PerfilEstudiante(models.Model):
    NIVELES_EDUCATIVOS = [
        ('preparatoria', 'Preparatoria'),
        ('tsu', 'Técnico Superior Universitario'),
        ('licenciatura', 'Carrera Profesional'),
        ('maestria', 'Maestría'),
        ('doctorado', 'Doctorado'),
    ]
    
    estudiante = models.OneToOneField(Estudiante, on_delete=models.CASCADE, related_name='perfil')
    foto = models.URLField(blank=True, null=True)
    nivel_educativo = models.CharField(max_length=20, choices=NIVELES_EDUCATIVOS)
    programa = models.CharField(max_length=200)
    periodo_actual = models.CharField(max_length=50)
    fecha_limite_actividades = models.DateField(null=True, blank=True)
    progreso_academico = models.IntegerField(default=0)  # Porcentaje 0-100
    materias_cursadas = models.IntegerField(default=0)
    materias_totales = models.IntegerField(default=0)
    promedio = models.DecimalField(max_digits=4, decimal_places=2, default=0.0)
    
    class Meta:
        verbose_name_plural = "Perfiles de Estudiantes"
    
    def __str__(self):
        return f"Perfil de {self.estudiante.nombre} {self.estudiante.apellido}"

class Tutor(models.Model):
    nombre = models.CharField(max_length=200)
    email = models.EmailField()
    telefono = models.CharField(max_length=20)
    especialidad = models.CharField(max_length=200)
    foto = models.URLField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    
    def __str__(self):
        return self.nombre

class AsignacionTutor(models.Model):
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='tutores')
    tutor = models.ForeignKey(Tutor, on_delete=models.CASCADE, related_name='estudiantes')
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    
    class Meta:
        unique_together = ['estudiante', 'tutor']
    
    def __str__(self):
        return f"{self.tutor.nombre} - {self.estudiante.nombre}"
