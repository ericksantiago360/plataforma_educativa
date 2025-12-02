from rest_framework import viewsets
from .models import Materia, ClaseEnLinea, ForoClase, MensajeForo, ControlEscolar
from .serializers import MateriaSerializer, ClaseEnLineaSerializer, ForoClaseSerializer, MensajeForoSerializer, ControlEscolarSerializer

class MateriaViewSet(viewsets.ModelViewSet):
    queryset = Materia.objects.all()
    serializer_class = MateriaSerializer

class ClaseEnLineaViewSet(viewsets.ModelViewSet):
    queryset = ClaseEnLinea.objects.all()
    serializer_class = ClaseEnLineaSerializer

class ForoClaseViewSet(viewsets.ModelViewSet):
    queryset = ForoClase.objects.all()
    serializer_class = ForoClaseSerializer

class MensajeForoViewSet(viewsets.ModelViewSet):
    queryset = MensajeForo.objects.all()
    serializer_class = MensajeForoSerializer

class ControlEscolarViewSet(viewsets.ModelViewSet):
    queryset = ControlEscolar.objects.all()
    serializer_class = ControlEscolarSerializer
