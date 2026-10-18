from decimal import Decimal

from rest_framework import serializers
from estudiantes.models import Estudiante
from .models import ConceptoPago, Cargo, Pago

MINIMO = Decimal('0.01')

class ConceptoPagoSerializer(serializers.ModelSerializer):
    tipo_nombre = serializers.CharField(source='get_tipo_display', read_only=True)

    class Meta:
        model = ConceptoPago
        fields = ['id', 'nombre', 'tipo', 'tipo_nombre', 'monto', 'activo']
        extra_kwargs = {'monto': {'min_value': MINIMO}}

class PagoSerializer(serializers.ModelSerializer):
    folio = serializers.ReadOnlyField()
    metodo_nombre = serializers.CharField(source='get_metodo_display', read_only=True)
    registrado_por_nombre = serializers.SerializerMethodField()
    recibo_url = serializers.SerializerMethodField()

    def get_registrado_por_nombre(self, obj):
        usuario = obj.registrado_por
        return (usuario.get_full_name() or usuario.username) if usuario else None

    def get_recibo_url(self, obj):
        return f'/api/pagos/{obj.id}/recibo/'

    class Meta:
        model = Pago
        fields = ['id', 'folio', 'cargo', 'monto', 'metodo', 'metodo_nombre', 'referencia', 'fecha',
                  'registrado_por_nombre', 'anulado', 'motivo_anulacion', 'recibo_url']
        read_only_fields = fields

class CargoSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.SerializerMethodField()
    matricula = serializers.CharField(source='estudiante.matricula', read_only=True)
    tipo_nombre = serializers.CharField(source='get_tipo_display', read_only=True)
    pagado = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    saldo = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    estado = serializers.ReadOnlyField()
    vencido = serializers.ReadOnlyField()
    pagos = PagoSerializer(many=True, read_only=True)

    def get_estudiante_nombre(self, obj):
        return f'{obj.estudiante.nombre} {obj.estudiante.apellido}'

    class Meta:
        model = Cargo
        fields = ['id', 'estudiante', 'estudiante_nombre', 'matricula', 'concepto', 'descripcion', 'tipo', 'tipo_nombre',
                  'periodo', 'monto', 'pagado', 'saldo', 'estado', 'fecha_limite', 'vencido', 'cancelado', 'creado', 'pagos']
        read_only_fields = fields

class CrearCargoSerializer(serializers.Serializer):
    """Cargo a un alumno a partir del catálogo: la descripción, el tipo y el monto salen del concepto."""
    estudiante = serializers.PrimaryKeyRelatedField(queryset=Estudiante.objects.filter(activo=True))
    concepto = serializers.PrimaryKeyRelatedField(queryset=ConceptoPago.objects.filter(activo=True))
    periodo = serializers.RegexField(r'^\d{4}-\d{1,2}$', required=False, allow_blank=True,
                                     error_messages={'invalid': 'Usa el formato AAAA-N, por ejemplo 2026-2.'})
    fecha_limite = serializers.DateField(required=False, allow_null=True)

class CargoMasivoSerializer(serializers.Serializer):
    """Colegiatura o inscripción de un periodo para todos los alumnos activos."""
    concepto = serializers.PrimaryKeyRelatedField(
        queryset=ConceptoPago.objects.filter(activo=True, tipo__in=('colegiatura', 'inscripcion')),
        error_messages={'does_not_exist': 'El cargo masivo es para colegiaturas e inscripciones activas.'},
    )
    periodo = serializers.RegexField(r'^\d{4}-\d{1,2}$',
                                     error_messages={'invalid': 'Usa el formato AAAA-N, por ejemplo 2026-2.'})
    fecha_limite = serializers.DateField(required=False, allow_null=True)

class RegistrarPagoSerializer(serializers.Serializer):
    monto = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=MINIMO)
    metodo = serializers.ChoiceField(choices=Pago.METODOS)
    referencia = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
