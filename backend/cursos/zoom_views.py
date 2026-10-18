from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from cuentas.permisos import ACCIONES_ESCRITURA, AlcancePorRolMixin, ProfesorEscribe
from .models import ClaseZoom, ParticipanteClase
from .zoom_serializers import ClaseZoomSerializer, ParticipanteClaseSerializer
from .zoom_service import ZoomService

class ClaseZoomViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = ClaseZoom.objects.select_related('curso')
    serializer_class = ClaseZoomSerializer
    permission_classes = [IsAuthenticated, ProfesorEscribe]
    acciones_profesor = ACCIONES_ESCRITURA + ('end',)
    ruta_curso = 'curso'

    def get_permissions(self):
        # Unirse no es editar la clase: basta con verla (el queryset ya la limita a los cursos de cada quien)
        if self.action == 'join':
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        clase = self.get_object()
        if clase.estado in ('finalizada', 'cancelada'):
            return Response({'detail': f'La clase está {clase.get_estado_display().lower()}.'},
                            status=status.HTTP_400_BAD_REQUEST)
        if not ZoomService.configurado():
            return Response({'detail': 'Zoom no está configurado en el servidor.'},
                            status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # El rol de anfitrión y el nombre salen de la sesión, nunca del cliente
        user = request.user
        is_host = user.is_staff or clase.curso.titular_id == user.pk
        user_name = user.get_full_name() or user.username

        config = ZoomService.create_session_config(clase, user_name, is_host)

        # La clase empieza cuando entra el anfitrión, no cuando llega el primer alumno
        if is_host and clase.estado == 'programada':
            clase.estado = 'en_vivo'
            clase.save()

        return Response(config)

    @action(detail=True, methods=['post'])
    def end(self, request, pk=None):
        clase = self.get_object()
        clase.estado = 'finalizada'
        clase.save()

        return Response({'message': 'Clase finalizada exitosamente'})

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        now = timezone.now()
        clases = self.get_queryset().filter(
            fecha_hora_inicio__gte=now,
            estado='programada'
        ).order_by('fecha_hora_inicio')[:5]

        serializer = self.get_serializer(clases, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def live(self, request):
        clases = self.get_queryset().filter(estado='en_vivo')
        serializer = self.get_serializer(clases, many=True)
        return Response(serializer.data)

class ParticipanteClaseViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = ParticipanteClase.objects.select_related('estudiante')
    serializer_class = ParticipanteClaseSerializer
    permission_classes = [IsAuthenticated, ProfesorEscribe]
    ruta_estudiante = 'estudiante'
    ruta_curso = 'clase__curso'
