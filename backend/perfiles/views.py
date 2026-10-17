from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from cuentas.permisos import AlcancePorRolMixin, SoloStaffEscribe
from .models import PerfilEstudiante, Tutor, AsignacionTutor
from .serializers import PerfilEstudianteSerializer, TutorSerializer, AsignacionTutorSerializer

class PerfilEstudianteViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = PerfilEstudiante.objects.all()
    serializer_class = PerfilEstudianteSerializer
    permission_classes = [IsAuthenticated, SoloStaffEscribe]
    ruta_estudiante = 'estudiante'
    ruta_curso = 'estudiante__cursos'

class TutorViewSet(viewsets.ModelViewSet):
    queryset = Tutor.objects.all()
    serializer_class = TutorSerializer
    permission_classes = [IsAuthenticated, SoloStaffEscribe]

class AsignacionTutorViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = AsignacionTutor.objects.all()
    serializer_class = AsignacionTutorSerializer
    permission_classes = [IsAuthenticated, SoloStaffEscribe]
    ruta_estudiante = 'estudiante'
    ruta_curso = 'estudiante__cursos'
