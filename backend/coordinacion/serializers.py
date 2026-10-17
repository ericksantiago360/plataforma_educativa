from rest_framework import serializers
from .models import Tarea, Comunicado

class TareaSerializer(serializers.ModelSerializer):
    curso_nombre = serializers.CharField(source='curso.nombre', read_only=True)
    estado_nombre = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = Tarea
        fields = ['id', 'titulo', 'descripcion', 'curso', 'curso_nombre', 'fecha_vencimiento', 'estado', 'estado_nombre', 'creado']

class ComunicadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comunicado
        fields = ['id', 'titulo', 'contenido', 'curso', 'fecha_creacion', 'activo']
