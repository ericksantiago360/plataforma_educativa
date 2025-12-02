from rest_framework import viewsets
from .models import BibliotecaDigital, MesaAyuda, EventoCalendario, CentroIdiomas
from .serializers import BibliotecaDigitalSerializer, MesaAyudaSerializer, EventoCalendarioSerializer, CentroIdiomasSerializer

class BibliotecaDigitalViewSet(viewsets.ModelViewSet):
    queryset = BibliotecaDigital.objects.all()
    serializer_class = BibliotecaDigitalSerializer

class MesaAyudaViewSet(viewsets.ModelViewSet):
    queryset = MesaAyuda.objects.all()
    serializer_class = MesaAyudaSerializer

class EventoCalendarioViewSet(viewsets.ModelViewSet):
    queryset = EventoCalendario.objects.all()
    serializer_class = EventoCalendarioSerializer

class CentroIdiomasViewSet(viewsets.ModelViewSet):
    queryset = CentroIdiomas.objects.all()
    serializer_class = CentroIdiomasSerializer
