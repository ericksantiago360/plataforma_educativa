from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from cuentas.permisos import AlcancePorRolMixin, ProfesorEscribe, SoloStaffEscribe
from .models import Tarea, Comunicado
from .serializers import TareaSerializer, ComunicadoSerializer

class TareaViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = Tarea.objects.select_related('curso').order_by('fecha_vencimiento')
    serializer_class = TareaSerializer
    permission_classes = [IsAuthenticated, ProfesorEscribe]
    ruta_curso = 'curso'

    def perform_create(self, serializer):
        super().perform_create(serializer)  # el mixin verifica que el curso sea del profesor
        # La tarea se asigna a todos los alumnos inscritos en el curso
        tarea = serializer.instance
        tarea.estudiantes.set(tarea.curso.estudiantes.all())

class ComunicadoViewSet(viewsets.ModelViewSet):
    queryset = Comunicado.objects.all()
    serializer_class = ComunicadoSerializer
    permission_classes = [IsAuthenticated, SoloStaffEscribe]
