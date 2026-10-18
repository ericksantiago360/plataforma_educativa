from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone
from estudiantes.models import Estudiante

TIPOS = [
    ('colegiatura', 'Colegiatura'),
    ('inscripcion', 'Inscripción'),
    ('idiomas', 'Curso de idiomas'),
    ('tramite', 'Trámite'),
]

class ConceptoPago(models.Model):
    """Catálogo de precios que administra el staff. Los cursos de idiomas no usan catálogo: cobran su propio precio."""
    nombre = models.CharField(max_length=200)
    tipo = models.CharField(max_length=20, choices=[t for t in TIPOS if t[0] != 'idiomas'])
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['tipo', 'nombre']
        verbose_name = 'Concepto de pago'
        verbose_name_plural = 'Conceptos de pago'

    def __str__(self):
        return f"{self.nombre} (${self.monto})"

class Cargo(models.Model):
    """
    Lo que un alumno debe. No se edita ni se borra: si no procede, se cancela (solo sin pagos válidos).
    El saldo sale de sus pagos no anulados, así que admite pagos parciales.
    """
    # Un alumno con movimientos no se borra (se da de baja): el historial de pagos debe conservarse
    estudiante = models.ForeignKey(Estudiante, on_delete=models.PROTECT, related_name='cargos')
    # Si se borra el concepto o el curso, el cargo se conserva: ya guarda su descripción y su monto
    concepto = models.ForeignKey(ConceptoPago, on_delete=models.SET_NULL, null=True, blank=True, related_name='cargos')
    curso_idiomas = models.ForeignKey('servicios.CentroIdiomas', on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='cargos')
    descripcion = models.CharField(max_length=255)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    periodo = models.CharField(max_length=20, blank=True)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_limite = models.DateField(null=True, blank=True)
    cancelado = models.BooleanField(default=False)
    creado = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='cargos_creados')

    class Meta:
        ordering = ['-creado']

    def __str__(self):
        return f"{self.descripcion} - {self.estudiante} (${self.monto})"

    @property
    def pagado(self):
        # La vista lo anota (pagado_total) para no hacer una consulta por cargo
        if hasattr(self, 'pagado_total'):
            return self.pagado_total or Decimal('0')
        return self.pagos.filter(anulado=False).aggregate(t=Sum('monto'))['t'] or Decimal('0')

    @property
    def saldo(self):
        return Decimal('0') if self.cancelado else max(self.monto - self.pagado, Decimal('0'))

    @property
    def estado(self):
        if self.cancelado:
            return 'cancelado'
        if self.saldo == 0:
            return 'pagado'
        return 'parcial' if self.pagado > 0 else 'pendiente'

    @property
    def vencido(self):
        return self.saldo > 0 and self.fecha_limite is not None and self.fecha_limite < timezone.localdate()

def con_pagado(queryset):
    """Anota lo pagado (sin anulados) en cada cargo."""
    return queryset.annotate(pagado_total=Sum('pagos__monto', filter=Q(pagos__anulado=False)))

class Pago(models.Model):
    """Un pago registrado en caja. No se borra: si fue un error, se anula con motivo y el saldo vuelve al cargo."""
    METODOS = [
        ('efectivo', 'Efectivo'),
        ('transferencia', 'Transferencia'),
        ('deposito', 'Depósito bancario'),
        ('tarjeta', 'Tarjeta (terminal)'),
    ]

    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT, related_name='pagos')
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    metodo = models.CharField(max_length=20, choices=METODOS)
    referencia = models.CharField(max_length=100, blank=True)  # folio de transferencia, número de ficha, etc.
    fecha = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
                                       related_name='pagos_registrados')
    anulado = models.BooleanField(default=False)
    motivo_anulacion = models.CharField(max_length=255, blank=True)
    anulado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='pagos_anulados')

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"{self.folio} - ${self.monto}"

    @property
    def folio(self):
        return f'R-{self.pk:06d}'

def cargar_curso_idiomas(curso, estudiante):
    """Al inscribirse a un curso de idiomas con costo se genera su cargo (uno vigente por alumno y curso)."""
    if curso.precio > 0 and not Cargo.objects.filter(curso_idiomas=curso, estudiante=estudiante, cancelado=False).exists():
        Cargo.objects.create(estudiante=estudiante, curso_idiomas=curso, tipo='idiomas', monto=curso.precio,
                             descripcion=f'Curso de idiomas: {curso.nombre_curso}')

def cargo_vigente_de_idiomas(curso, estudiante):
    return con_pagado(Cargo.objects.filter(curso_idiomas=curso, estudiante=estudiante, cancelado=False)).first()
