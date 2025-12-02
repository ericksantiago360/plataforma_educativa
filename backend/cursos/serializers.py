from rest_framework import serializers
from .models import Curso

class CursoSerializer(serializers.ModelSerializer):
    cantidad_estudiantes = serializers.ReadOnlyField()
    
    class Meta:
        model = Curso
        fields = ['id', 'nombre', 'codigo', 'descripcion', 'profesor', 'creditos', 'cantidad_estudiantes', 'fecha_inicio', 'fecha_fin', 'activo']
