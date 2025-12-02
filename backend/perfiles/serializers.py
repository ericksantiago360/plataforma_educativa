from rest_framework import serializers
from .models import PerfilEstudiante, Tutor, AsignacionTutor

class PerfilEstudianteSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='estudiante.nombre', read_only=True)
    estudiante_apellido = serializers.CharField(source='estudiante.apellido', read_only=True)
    estudiante_email = serializers.CharField(source='estudiante.email', read_only=True)
    estudiante_matricula = serializers.CharField(source='estudiante.matricula', read_only=True)
    
    class Meta:
        model = PerfilEstudiante
        fields = '__all__'

class TutorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tutor
        fields = '__all__'

class AsignacionTutorSerializer(serializers.ModelSerializer):
    tutor_nombre = serializers.CharField(source='tutor.nombre', read_only=True)
    tutor_email = serializers.CharField(source='tutor.email', read_only=True)
    
    class Meta:
        model = AsignacionTutor
        fields = '__all__'
