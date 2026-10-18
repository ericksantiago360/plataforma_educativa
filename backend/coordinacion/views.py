import os

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from academico.archivos import respuesta_de_descarga, validar_archivo
from cuentas.permisos import AlcancePorRolMixin, ProfesorEscribe, SoloStaffEscribe
from cuentas.roles import ESTUDIANTE, PROFESOR, STAFF, estudiante_de, rol_de
from .models import Tarea, EntregaTarea, ArchivoEntrega, Comunicado
from .serializers import ArchivoEntregaSerializer, TareaSerializer, ComunicadoSerializer, datos_de_entrega

MAXIMO_ARCHIVOS_POR_ENTREGA = 10

class TareaViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = Tarea.objects.select_related('curso').order_by('fecha_vencimiento')
    serializer_class = TareaSerializer
    permission_classes = [IsAuthenticated, ProfesorEscribe]
    ruta_curso = 'curso'

    def get_permissions(self):
        # Marcar el propio avance o entregar no es editar la tarea: basta con verla (el queryset la limita a sus cursos)
        if self.action in ('estado', 'entregar'):
            return [IsAuthenticated()]
        return super().get_permissions()

    def _estudiante(self):
        estudiante = estudiante_de(self.request.user)
        if estudiante is None:
            raise PermissionDenied('Solo los estudiantes entregan o marcan su avance en una tarea.')
        return estudiante

    @action(detail=True, methods=['post'])
    def estado(self, request, pk=None):
        """El alumno marca su avance: pendiente, en_progreso o completada."""
        tarea = self.get_object()
        estudiante = self._estudiante()
        estado = request.data.get('estado')
        if estado not in dict(EntregaTarea.ESTADOS):
            return Response({'estado': ['Usa pendiente, en_progreso o completada.']}, status=status.HTTP_400_BAD_REQUEST)

        EntregaTarea.objects.update_or_create(tarea=tarea, estudiante=estudiante, defaults={'estado': estado})
        return Response(self.get_serializer(tarea).data)

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser])
    def entregar(self, request, pk=None):
        """El alumno sube un archivo a su entrega; la tarea queda completada. Entregar tarde se permite y se marca."""
        tarea = self.get_object()
        estudiante = self._estudiante()
        archivo = request.FILES.get('archivo')
        if archivo is None:
            return Response({'archivo': ['Adjunta un archivo.']}, status=status.HTTP_400_BAD_REQUEST)
        try:
            tipo = validar_archivo(archivo)
        except DjangoValidationError as error:
            return Response({'archivo': error.messages}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            EntregaTarea.objects.get_or_create(tarea=tarea, estudiante=estudiante)
            # Bloquea la entrega para que dos subidas simultáneas no rebasen el máximo de archivos
            entrega = EntregaTarea.objects.select_for_update().get(tarea=tarea, estudiante=estudiante)
            if entrega.archivos.count() >= MAXIMO_ARCHIVOS_POR_ENTREGA:
                return Response({'archivo': [f'Máximo {MAXIMO_ARCHIVOS_POR_ENTREGA} archivos por entrega.']},
                                status=status.HTTP_400_BAD_REQUEST)
            ArchivoEntrega.objects.create(
                entrega=entrega,
                archivo=archivo,
                nombre=os.path.basename(archivo.name)[:255],
                tipo=tipo,
                tamano=archivo.size,
            )
            entrega.estado = 'completada'
            entrega.entregado = timezone.now()
            entrega.save()
        return Response(self.get_serializer(tarea).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def entregas(self, request, pk=None):
        """Profesor y staff: el avance y los archivos de cada alumno inscrito, haya entregado o no."""
        if rol_de(request.user) not in (STAFF, PROFESOR):
            raise PermissionDenied('Solo profesores y staff pueden ver las entregas del grupo.')
        tarea = self.get_object()
        por_alumno = {e.estudiante_id: e for e in tarea.entregas.select_related('tarea').prefetch_related('archivos')}
        return Response([
            {
                'estudiante': estudiante.id,
                'nombre': f'{estudiante.nombre} {estudiante.apellido}',
                'matricula': estudiante.matricula,
                **datos_de_entrega(por_alumno.get(estudiante.id)),
            }
            for estudiante in tarea.curso.estudiantes.order_by('apellido', 'nombre')
        ])

class ArchivoEntregaViewSet(AlcancePorRolMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin,
                            viewsets.GenericViewSet):
    """Cada alumno ve y quita sus archivos; el profesor ve los de sus cursos; el staff, todos."""
    queryset = ArchivoEntrega.objects.select_related('entrega__tarea__curso')
    serializer_class = ArchivoEntregaSerializer
    ruta_curso = 'entrega__tarea__curso'
    ruta_estudiante = 'entrega__estudiante'

    def perform_destroy(self, instance):
        # El trabajo de un alumno solo lo quita él (o el staff), no el profesor
        if not (self.request.user.is_staff or rol_de(self.request.user) == ESTUDIANTE):
            raise PermissionDenied('Solo el alumno que entregó puede quitar sus archivos.')
        entrega = instance.entrega
        super().perform_destroy(instance)
        # Sin archivos ya no hay entrega que fechar (el estado lo sigue decidiendo el alumno)
        if not entrega.archivos.exists():
            entrega.entregado = None
            entrega.save(update_fields=['entregado', 'actualizado'])

    @action(detail=True, methods=['get'])
    def descargar(self, request, pk=None):
        return respuesta_de_descarga(self.get_object())  # get_object aplica los permisos de arriba

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
