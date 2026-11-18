from django.db import models
from estudiantes.models import Estudiante

class BibliotecaDigital(models.Model):
    titulo = models.CharField(max_length=300)
    autor = models.CharField(max_length=200)
    categoria = models.CharField(max_length=100)
    descripcion = models.TextField()
    url_recurso = models.URLField()
    tipo_recurso = models.CharField(max_length=50, choices=[
        ('libro', 'Libro'),
        ('revista', 'Revista'),
        ('articulo', 'Artículo'),
        ('video', 'Video'),
    ])
    fecha_publicacion = models.DateField()
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Biblioteca Digital"
    
    def __str__(self):
        return self.titulo

class MesaAyuda(models.Model):
    ESTADOS = [
        ('abierto', 'Abierto'),
        ('en_proceso', 'En Proceso'),
        ('resuelto', 'Resuelto'),
        ('cerrado', 'Cerrado'),
    ]
    
    CATEGORIAS = [
        ('tecnico', 'Soporte Técnico'),
        ('academico', 'Académico'),
        ('administrativo', 'Administrativo'),
        ('otro', 'Otro'),
    ]
    
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='tickets')
    categoria = models.CharField(max_length=20, choices=CATEGORIAS)
    asunto = models.CharField(max_length=200)
    descripcion = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='abierto')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    respuesta = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Mesa de Ayuda"
        ordering = ['-fecha_creacion']
    
    def __str__(self):
        return f"{self.asunto} - {self.estudiante.nombre}"

class EventoCalendario(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField()
    fecha_inicio = models.DateTimeField()
    fecha_fin = models.DateTimeField()
    tipo_evento = models.CharField(max_length=50, choices=[
        ('clase', 'Clase'),
        ('examen', 'Examen'),
        ('entrega', 'Entrega de Actividad'),
        ('evento', 'Evento Institucional'),
    ])
    cursos = models.ManyToManyField('cursos.Curso', related_name='eventos', blank=True)
    todos_estudiantes = models.BooleanField(default=False)
    
    class Meta:
        verbose_name_plural = "Calendario"
        ordering = ['fecha_inicio']
    
    def __str__(self):
        return self.titulo

class CentroIdiomas(models.Model):
    IDIOMAS = [
        ('ingles', 'Inglés'),
        ('frances', 'Francés'),
        ('aleman', 'Alemán'),
        ('italiano', 'Italiano'),
        ('japones', 'Japonés'),
        ('mandarin', 'Mandarín'),
    ]
    
    NIVELES = [
        ('basico', 'Básico'),
        ('intermedio', 'Intermedio'),
        ('avanzado', 'Avanzado'),
    ]
    
    idioma = models.CharField(max_length=20, choices=IDIOMAS)
    nivel = models.CharField(max_length=20, choices=NIVELES)
    nombre_curso = models.CharField(max_length=200)
    descripcion = models.TextField()
    duracion_semanas = models.IntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    instructor = models.CharField(max_length=200)
    cupo_maximo = models.IntegerField(default=25)
    estudiantes_inscritos = models.ManyToManyField(Estudiante, related_name='cursos_idiomas', blank=True)
    fecha_inicio = models.DateField()
    horario = models.CharField(max_length=200, blank=True)  # texto libre: "Lunes y miércoles, 18:00 a 20:00"
    lugar = models.CharField(max_length=200, blank=True)    # salón o enlace de la sesión
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name_plural = "Centro de Idiomas"
    
    def __str__(self):
        return f"{self.idioma} - {self.nivel}"
    
    @property
    def cupos_disponibles(self):
        return self.cupo_maximo - self.estudiantes_inscritos.count()


class ClaseIdiomas(models.Model):
    """Una sesión programada de un curso de idiomas. La ven los alumnos inscritos; la administra el staff."""
    curso = models.ForeignKey(CentroIdiomas, on_delete=models.CASCADE, related_name='clases')
    titulo = models.CharField(max_length=200)
    fecha_hora = models.DateTimeField()
    duracion_minutos = models.PositiveIntegerField(default=60)
    enlace = models.URLField(blank=True)  # videollamada, si la sesión es en línea
    notas = models.TextField(blank=True)

    class Meta:
        ordering = ['fecha_hora']
        verbose_name = 'Clase de idiomas'
        verbose_name_plural = 'Clases de idiomas'

    def __str__(self):
        return f"{self.curso.nombre_curso} - {self.titulo}"


class MaterialIdiomas(models.Model):
    """Material de estudio de un curso de idiomas (lectura, audio, ejercicios): un enlace con su descripción."""
    curso = models.ForeignKey(CentroIdiomas, on_delete=models.CASCADE, related_name='materiales')
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    enlace = models.URLField(blank=True)
    publicado = models.BooleanField(default=True)  # un borrador solo lo ve el staff
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'id']
        verbose_name = 'Material de idiomas'
        verbose_name_plural = 'Materiales de idiomas'

    def __str__(self):
        return f"{self.curso.nombre_curso} - {self.titulo}"
