from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from cuentas.permisos import AlcancePorRolMixin, EstudianteAutor, SoloStaffEscribe
from cuentas.roles import ESTUDIANTE, PROFESOR, STAFF, estudiante_de, rol_de
from .models import BibliotecaDigital, MesaAyuda, EventoCalendario, CentroIdiomas
from .serializers import BibliotecaDigitalSerializer, MesaAyudaSerializer, EventoCalendarioSerializer, CentroIdiomasSerializer

class BibliotecaDigitalViewSet(viewsets.ModelViewSet):
    queryset = BibliotecaDigital.objects.order_by('titulo')
    serializer_class = BibliotecaDigitalSerializer
    permission_classes = [IsAuthenticated, SoloStaffEscribe]

    def get_queryset(self):
        qs = super().get_queryset()
        # Los recursos dados de baja solo los ve el staff
        return qs if self.request.user.is_staff else qs.filter(activo=True)

class MesaAyudaViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = MesaAyuda.objects.select_related('estudiante')
    serializer_class = MesaAyudaSerializer
    permission_classes = [IsAuthenticated, EstudianteAutor]
    ruta_estudiante = 'estudiante'

    def perform_create(self, serializer):
        estudiante = estudiante_de(self.request.user)
        if estudiante is None:
            raise PermissionDenied('Solo los estudiantes pueden abrir tickets.')
        # Estado y respuesta los gestiona el staff, no quien abre el ticket
        serializer.save(estudiante=estudiante, estado='abierto', respuesta='')

class EventoCalendarioViewSet(viewsets.ModelViewSet):
    queryset = EventoCalendario.objects.all()
    serializer_class = EventoCalendarioSerializer
    permission_classes = [IsAuthenticated, SoloStaffEscribe]

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        rol = rol_de(user)

        # Cada quien ve los eventos generales y los de sus cursos
        if rol == PROFESOR:
            qs = qs.filter(Q(todos_estudiantes=True) | Q(cursos__titular=user)).distinct()
        elif rol == ESTUDIANTE:
            qs = qs.filter(Q(todos_estudiantes=True) | Q(cursos__estudiantes=estudiante_de(user))).distinct()
        elif rol != STAFF:
            return qs.none()

        # ?proximos=1 para omitir los eventos que ya terminaron
        if self.request.query_params.get('proximos') == '1':
            qs = qs.filter(fecha_fin__gte=timezone.now())
        return qs

class CentroIdiomasViewSet(viewsets.ModelViewSet):
    queryset = CentroIdiomas.objects.order_by('fecha_inicio', 'idioma')
    serializer_class = CentroIdiomasSerializer
    permission_classes = [IsAuthenticated, SoloStaffEscribe]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs if self.request.user.is_staff else qs.filter(activo=True)

    def get_permissions(self):
        # Inscribirse no es editar el catálogo: basta con tener sesión (cada acción valida el rol)
        if self.action in ('inscribir', 'cancelar'):
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=True, methods=['post'])
    def inscribir(self, request, pk=None):
        estudiante = self._estudiante()
        with transaction.atomic():
            # Bloquea el curso para que dos inscripciones simultáneas no rebasen el cupo
            curso = CentroIdiomas.objects.select_for_update().get(pk=self.get_object().pk)
            if not curso.estudiantes_inscritos.filter(pk=estudiante.pk).exists():
                if curso.cupos_disponibles <= 0:
                    return Response({'detail': 'Ya no hay cupo en este curso.'}, status=status.HTTP_400_BAD_REQUEST)
                curso.estudiantes_inscritos.add(estudiante)
        return Response(self.get_serializer(curso).data)

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        estudiante = self._estudiante()
        curso = self.get_object()
        curso.estudiantes_inscritos.remove(estudiante)
        return Response(self.get_serializer(curso).data)

    def _estudiante(self):
        estudiante = estudiante_de(self.request.user)
        if estudiante is None:
            raise PermissionDenied('Solo los estudiantes pueden inscribirse a cursos de idiomas.')
        return estudiante
