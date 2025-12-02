from django.db import models
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
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='mensajes_foro')
    contenido = models.TextField()
    fecha_publicacion = models.DateTimeField(auto_now_add=True)
    editado = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['fecha_publicacion']
    
    def __str__(self):
        return f"{self.estudiante.nombre} - {self.foro.titulo}"

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
