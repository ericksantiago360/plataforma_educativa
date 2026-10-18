import re

from django.db import models
from django.contrib.auth.models import User
from estudiantes.models import Estudiante

PERIODO = re.compile(r'^(\d{4})-(\d{1,2})$')


def clave_periodo(periodo):
    """'2026-2' → (2026, 2), para ordenar periodos como números ('2026-10' va después de '2026-9')."""
    coincidencia = PERIODO.match(periodo or '')
    return tuple(int(parte) for parte in coincidencia.groups()) if coincidencia else (0, 0)

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

    def recalcular(self):
        """
        Actualiza materias aprobadas, progreso y promedio a partir del historial (ControlEscolar).
        Solo cuentan calificaciones finales (aprobado/reprobado) y, si una materia se cursó varias veces,
        solo el último intento: un parcial de una materia en curso o un reprobado ya recursado no bajan el promedio.
        """
        ultimos = {}
        for registro in self.estudiante.historial_escolar.filter(estado__in=('aprobado', 'reprobado')):
            clave = (clave_periodo(registro.periodo), registro.pk)
            if registro.materia_id not in ultimos or clave > ultimos[registro.materia_id][0]:
                ultimos[registro.materia_id] = (clave, registro)
        finales = [registro for _, registro in ultimos.values()]

        self.materias_cursadas = sum(1 for registro in finales if registro.estado == 'aprobado')
        calificaciones = [registro.calificacion for registro in finales if registro.calificacion is not None]
        self.promedio = round(sum(calificaciones) / len(calificaciones), 2) if calificaciones else 0
        if self.materias_totales:
            self.progreso_academico = min(100, round(self.materias_cursadas * 100 / self.materias_totales))
        self.save(update_fields=['materias_cursadas', 'promedio', 'progreso_academico'])

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
