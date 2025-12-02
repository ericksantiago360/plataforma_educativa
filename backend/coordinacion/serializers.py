from rest_framework import serializers
from .models import Tarea, Comunicado

class TareaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tarea
        fields = ['id', 'titulo', 'descripcion', 'curso', 'fecha_vencimiento', 'estado', 'creado']

class ComunicadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comunicado
        fields = ['id', 'titulo', 'contenido', 'curso', 'fecha_creacion', 'activo']
