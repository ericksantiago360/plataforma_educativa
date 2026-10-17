from rest_framework import serializers
from cuentas.roles import GRUPO_PROFESOR
from .models import Materia, ClaseEnLinea, ForoClase, MensajeForo, ControlEscolar

class MateriaSerializer(serializers.ModelSerializer):
    curso_nombre = serializers.CharField(source='curso.nombre', read_only=True)

    def validate_codigo(self, valor):
        valor = valor.strip().upper()
        otras = Materia.objects.filter(codigo__iexact=valor)
        if self.instance:
            otras = otras.exclude(pk=self.instance.pk)
        if otras.exists():
            raise serializers.ValidationError('Ya existe una materia con este código.')
        return valor

    class Meta:
        model = Materia
        fields = '__all__'
        # El validador automático da un mensaje genérico ("un/a materia con este/a codigo"); lo reemplaza validate_codigo
        extra_kwargs = {
            'codigo': {'validators': []},
            'creditos': {'min_value': 0},
            'nivel': {'min_value': 1},
        }

class ClaseEnLineaSerializer(serializers.ModelSerializer):
    materia_nombre = serializers.CharField(source='materia.nombre', read_only=True)
    
    class Meta:
        model = ClaseEnLinea
        fields = '__all__'

class ForoClaseSerializer(serializers.ModelSerializer):
    total_mensajes = serializers.SerializerMethodField()
    clase_titulo = serializers.CharField(source='clase.titulo', read_only=True)
    materia_nombre = serializers.CharField(source='clase.materia.nombre', read_only=True)
    
    def get_total_mensajes(self, obj):
        return obj.mensajes.count()
    
    class Meta:
        model = ForoClase
        fields = '__all__'

class MensajeForoSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.ReadOnlyField()
    autor_rol = serializers.SerializerMethodField()

    def get_autor_rol(self, obj):
        # Usa autor.groups precargado por la vista (evita una consulta por mensaje)
        if obj.estudiante_id:
            return 'estudiante'
        if obj.autor is None:
            return None
        if obj.autor.is_staff:
            return 'staff'
        if any(g.name == GRUPO_PROFESOR for g in obj.autor.groups.all()):
            return 'profesor'
        return None

    class Meta:
        model = MensajeForo
        fields = '__all__'
        read_only_fields = ['autor', 'estudiante', 'editado']

class ControlEscolarSerializer(serializers.ModelSerializer):
    materia_nombre = serializers.CharField(source='materia.nombre', read_only=True)
    estudiante_nombre = serializers.CharField(source='estudiante.nombre', read_only=True)
    estudiante_apellido = serializers.CharField(source='estudiante.apellido', read_only=True)

    def validate_calificacion(self, valor):
        if valor is not None and not 0 <= valor <= 10:
            raise serializers.ValidationError('La calificación debe estar entre 0 y 10.')
        return valor

    def validate(self, datos):
        # Al crear un registro (o cambiar alumno/materia), el alumno debe estar inscrito en el curso.
        # Solo se revisa si vienen esos campos: capturar la calificación de un alumno que después
        # dejó el curso debe seguir siendo posible.
        if 'estudiante' in datos or 'materia' in datos:
            estudiante = datos.get('estudiante', getattr(self.instance, 'estudiante', None))
            materia = datos.get('materia', getattr(self.instance, 'materia', None))
            if not materia.curso.estudiantes.filter(pk=estudiante.pk).exists():
                raise serializers.ValidationError({'estudiante': 'El estudiante no está inscrito en el curso de esta materia.'})

        # En una edición parcial, lo que no viene se toma del registro actual
        estado = datos.get('estado', getattr(self.instance, 'estado', None))
        calificacion = datos.get('calificacion', getattr(self.instance, 'calificacion', None))
        if estado in ('aprobado', 'reprobado') and calificacion is None:
            raise serializers.ValidationError({'calificacion': 'Captura la calificación para marcar la materia como aprobada o reprobada.'})
        return datos

    class Meta:
        model = ControlEscolar
        fields = '__all__'
