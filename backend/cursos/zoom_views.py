from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from .models import ClaseZoom, ParticipanteClase
from .zoom_serializers import ClaseZoomSerializer, ParticipanteClaseSerializer
from .zoom_service import ZoomService

class ClaseZoomViewSet(viewsets.ModelViewSet):
    queryset = ClaseZoom.objects.all()
    serializer_class = ClaseZoomSerializer
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        clase = self.get_object()
        user_name = request.data.get('user_name', 'Usuario')
        is_host = request.data.get('is_host', False)
        
        config = ZoomService.create_session_config(clase, user_name, is_host)
        
        if clase.estado == 'programada':
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
        clases = ClaseZoom.objects.filter(
            fecha_hora_inicio__gte=now,
            estado='programada'
        ).order_by('fecha_hora_inicio')[:5]
        
        serializer = self.get_serializer(clases, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def live(self, request):
        clases = ClaseZoom.objects.filter(estado='en_vivo')
        serializer = self.get_serializer(clases, many=True)
        return Response(serializer.data)

class ParticipanteClaseViewSet(viewsets.ModelViewSet):
    queryset = ParticipanteClase.objects.all()
    serializer_class = ParticipanteClaseSerializer
