from rest_framework import serializers
from .models import BibliotecaDigital, MesaAyuda, EventoCalendario, CentroIdiomas

class BibliotecaDigitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = BibliotecaDigital
        fields = '__all__'

class MesaAyudaSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='estudiante.nombre', read_only=True)
    
    class Meta:
        model = MesaAyuda
        fields = '__all__'

class EventoCalendarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventoCalendario
        fields = '__all__'

class CentroIdiomasSerializer(serializers.ModelSerializer):
    cupos_disponibles = serializers.ReadOnlyField()
    
    class Meta:
        model = CentroIdiomas
        fields = '__all__'
