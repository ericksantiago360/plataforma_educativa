from rest_framework import serializers
from cuentas.roles import estudiante_de
from .models import BibliotecaDigital, MesaAyuda, EventoCalendario, CentroIdiomas

class BibliotecaDigitalSerializer(serializers.ModelSerializer):
    tipo_recurso_nombre = serializers.CharField(source='get_tipo_recurso_display', read_only=True)

    class Meta:
        model = BibliotecaDigital
        fields = '__all__'

class MesaAyudaSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='estudiante.nombre', read_only=True)
    estudiante_apellido = serializers.CharField(source='estudiante.apellido', read_only=True)
    categoria_nombre = serializers.CharField(source='get_categoria_display', read_only=True)
    estado_nombre = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = MesaAyuda
        fields = '__all__'
        read_only_fields = ['estudiante']

class EventoCalendarioSerializer(serializers.ModelSerializer):
    tipo_evento_nombre = serializers.CharField(source='get_tipo_evento_display', read_only=True)

    class Meta:
        model = EventoCalendario
        fields = '__all__'

class CentroIdiomasSerializer(serializers.ModelSerializer):
    cupos_disponibles = serializers.ReadOnlyField()
    idioma_nombre = serializers.CharField(source='get_idioma_display', read_only=True)
    nivel_nombre = serializers.CharField(source='get_nivel_display', read_only=True)
    inscrito = serializers.SerializerMethodField()

    def get_inscrito(self, obj):
        request = self.context.get('request')
        estudiante = estudiante_de(request.user) if request else None
        return estudiante is not None and obj.estudiantes_inscritos.filter(pk=estudiante.pk).exists()

    def to_representation(self, instance):
        datos = super().to_representation(instance)
        # La lista de inscritos solo la ve el staff; los demás ven "inscrito" y los cupos
        request = self.context.get('request')
        if not (request and request.user.is_staff):
            datos.pop('estudiantes_inscritos', None)
        return datos

    class Meta:
        model = CentroIdiomas
        fields = '__all__'
