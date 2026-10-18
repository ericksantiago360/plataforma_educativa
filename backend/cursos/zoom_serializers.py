from rest_framework import serializers
from .models import ClaseZoom, ParticipanteClase

class ClaseZoomSerializer(serializers.ModelSerializer):
    curso_nombre = serializers.CharField(source='curso.nombre', read_only=True)
    profesor = serializers.CharField(source='curso.profesor', read_only=True)
    total_participantes = serializers.SerializerMethodField()
    
    class Meta:
        model = ClaseZoom
        fields = '__all__'
    
    def get_total_participantes(self, obj):
        return obj.participantes.filter(asistio=True).count()

class ParticipanteClaseSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='estudiante.nombre', read_only=True)
    estudiante_apellido = serializers.CharField(source='estudiante.apellido', read_only=True)

    def validate(self, datos):
        # Solo al crear o cambiar alumno/clase: marcar la asistencia de quien después dejó el curso sigue siendo posible
        if 'clase' in datos or 'estudiante' in datos:
            clase = datos.get('clase', getattr(self.instance, 'clase', None))
            estudiante = datos.get('estudiante', getattr(self.instance, 'estudiante', None))
            if not clase.curso.estudiantes.filter(pk=estudiante.pk).exists():
                raise serializers.ValidationError({'estudiante': 'El estudiante no está inscrito en el curso de esta clase.'})
        return datos

    class Meta:
        model = ParticipanteClase
        fields = '__all__'
