from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from cuentas.permisos import AlcancePorRolMixin, ProfesorEscribe
from .models import Curso
from .serializers import CursoSerializer

class CursoViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = Curso.objects.all()
    serializer_class = CursoSerializer
    permission_classes = [IsAuthenticated, ProfesorEscribe]
    acciones_profesor = ('update', 'partial_update')
    ruta_curso = ''
