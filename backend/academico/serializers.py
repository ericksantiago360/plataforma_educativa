from rest_framework import serializers
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
    
    def get_total_mensajes(self, obj):
        return obj.mensajes.count()
    
    class Meta:
        model = ForoClase
        fields = '__all__'

class MensajeForoSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='estudiante.nombre', read_only=True)
    
    class Meta:
        model = MensajeForo
        fields = '__all__'

class ControlEscolarSerializer(serializers.ModelSerializer):
    materia_nombre = serializers.CharField(source='materia.nombre', read_only=True)
    
    class Meta:
        model = ControlEscolar
        fields = '__all__'
