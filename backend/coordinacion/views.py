from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from cuentas.permisos import AlcancePorRolMixin, ProfesorEscribe, SoloStaffEscribe
from cuentas.roles import ESTUDIANTE, PROFESOR, STAFF, estudiante_de, rol_de
from .models import Tarea, EntregaTarea, Comunicado
from .serializers import TareaSerializer, ComunicadoSerializer

class TareaViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = Tarea.objects.select_related('curso').order_by('fecha_vencimiento')
    serializer_class = TareaSerializer
    permission_classes = [IsAuthenticated, ProfesorEscribe]
    ruta_curso = 'curso'

    def get_permissions(self):
        # Marcar el propio avance no es editar la tarea: basta con verla (el queryset la limita a sus cursos)
        if self.action == 'estado':
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def estado(self, request, pk=None):
        """El alumno marca su avance: pendiente, en_progreso o completada."""
        tarea = self.get_object()
        estudiante = estudiante_de(request.user)
        if estudiante is None:
            raise PermissionDenied('Solo los estudiantes marcan su avance en una tarea.')
        estado = request.data.get('estado')
        if estado not in dict(EntregaTarea.ESTADOS):
            return Response({'estado': ['Usa pendiente, en_progreso o completada.']}, status=status.HTTP_400_BAD_REQUEST)

        EntregaTarea.objects.update_or_create(tarea=tarea, estudiante=estudiante, defaults={'estado': estado})
        return Response(self.get_serializer(tarea).data)

class ComunicadoViewSet(viewsets.ModelViewSet):
    queryset = Comunicado.objects.all()
    serializer_class = ComunicadoSerializer
    permission_classes = [IsAuthenticated, SoloStaffEscribe]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        rol = rol_de(user)

        # Cada quien ve los comunicados generales (sin curso) y los de sus cursos; los inactivos solo el staff
        if rol == STAFF:
            return qs
        if rol == PROFESOR:
            return qs.filter(Q(curso__isnull=True) | Q(curso__titular=user), activo=True).distinct()
        if rol == ESTUDIANTE:
            return qs.filter(Q(curso__isnull=True) | Q(curso__estudiantes=estudiante_de(user)), activo=True).distinct()
        return qs.none()
