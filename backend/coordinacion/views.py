from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from cuentas.permisos import AlcancePorRolMixin, ProfesorEscribe, SoloStaffEscribe
from .models import Tarea, Comunicado
from .serializers import TareaSerializer, ComunicadoSerializer

class TareaViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = Tarea.objects.all()
    serializer_class = TareaSerializer
    permission_classes = [IsAuthenticated, ProfesorEscribe]
    ruta_curso = 'curso'

class ComunicadoViewSet(viewsets.ModelViewSet):
    queryset = Comunicado.objects.all()
    serializer_class = ComunicadoSerializer
    permission_classes = [IsAuthenticated, SoloStaffEscribe]
