from rest_framework import viewsets
from .models import PerfilEstudiante, Tutor, AsignacionTutor
from .serializers import PerfilEstudianteSerializer, TutorSerializer, AsignacionTutorSerializer

class PerfilEstudianteViewSet(viewsets.ModelViewSet):
    queryset = PerfilEstudiante.objects.all()
    serializer_class = PerfilEstudianteSerializer

class TutorViewSet(viewsets.ModelViewSet):
    queryset = Tutor.objects.all()
    serializer_class = TutorSerializer

class AsignacionTutorViewSet(viewsets.ModelViewSet):
    queryset = AsignacionTutor.objects.all()
    serializer_class = AsignacionTutorSerializer
