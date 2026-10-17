from rest_framework import serializers
from cuentas.roles import GRUPO_PROFESOR
from .models import Materia, ClaseEnLinea, ForoClase, MensajeForo, ControlEscolar

class MateriaSerializer(serializers.ModelSerializer):
    curso_nombre = serializers.CharField(source='curso.nombre', read_only=True)
    
    class Meta:
        model = Materia
        fields = '__all__'

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
    
    class Meta:
        model = ControlEscolar
        fields = '__all__'
