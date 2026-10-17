from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from cuentas.permisos import AlcancePorRolMixin, SoloStaffEscribe
from .models import Estudiante
from .serializers import EstudianteSerializer

class EstudianteViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = Estudiante.objects.all()
    serializer_class = EstudianteSerializer
    permission_classes = [IsAuthenticated, SoloStaffEscribe]
    ruta_estudiante = ''
    ruta_curso = 'cursos'
