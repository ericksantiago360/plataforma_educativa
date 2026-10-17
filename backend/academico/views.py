import re

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from cuentas.permisos import AlcancePorRolMixin, AutorDelMensaje, ProfesorEscribe, SoloStaffEscribe
from cuentas.roles import es_profesor, estudiante_de
from .models import Materia, ClaseEnLinea, ForoClase, MensajeForo, ControlEscolar
from .serializers import MateriaSerializer, ClaseEnLineaSerializer, ForoClaseSerializer, MensajeForoSerializer, ControlEscolarSerializer

PERIODO_VALIDO = re.compile(r'^\d{4}-\d{1,2}$')

class MateriaViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = Materia.objects.select_related('curso').order_by('curso__nombre', 'nivel', 'nombre')
    serializer_class = MateriaSerializer
    permission_classes = [IsAuthenticated, SoloStaffEscribe]
    ruta_curso = 'curso'

    @action(detail=True, methods=['post'])
    def inscribir_grupo(self, request, pk=None):
        """Crea el registro de historial (cursando) de cada alumno activo del curso que aún no lo tenga en ese periodo."""
        materia = self.get_object()
        periodo = str(request.data.get('periodo', '')).strip()
        if not PERIODO_VALIDO.match(periodo):
            return Response({'periodo': ['Usa el formato AAAA-N, por ejemplo 2026-2.']}, status=status.HTTP_400_BAD_REQUEST)
        if not materia.activo:
            return Response({'detail': 'La materia está inactiva.'}, status=status.HTTP_400_BAD_REQUEST)

        ya_inscritos = set(ControlEscolar.objects.filter(materia=materia, periodo=periodo).values_list('estudiante_id', flat=True))
        nuevos = [
            ControlEscolar(estudiante=estudiante, materia=materia, periodo=periodo)
            for estudiante in materia.curso.estudiantes.filter(activo=True)
            if estudiante.pk not in ya_inscritos
        ]
        ControlEscolar.objects.bulk_create(nuevos)
        return Response({'inscritos': len(nuevos), 'ya_inscritos': len(ya_inscritos)})

class ClaseEnLineaViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = ClaseEnLinea.objects.all()
    serializer_class = ClaseEnLineaSerializer
    permission_classes = [IsAuthenticated, ProfesorEscribe]
    ruta_curso = 'materia__curso'

class ForoClaseViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = ForoClase.objects.select_related('clase__materia').order_by('-fecha_creacion')
    serializer_class = ForoClaseSerializer
    permission_classes = [IsAuthenticated, ProfesorEscribe]
    ruta_curso = 'clase__materia__curso'

class MensajeForoViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = MensajeForo.objects.all()
    serializer_class = MensajeForoSerializer
    permission_classes = [IsAuthenticated, AutorDelMensaje]
    ruta_curso = 'foro__clase__materia__curso'

    def get_queryset(self):
        qs = super().get_queryset().select_related('estudiante', 'autor').prefetch_related('autor__groups')
        # ?foro=<id> para traer solo los mensajes de un foro
        foro = self.request.query_params.get('foro')
        if foro is not None:
            if not foro.isdigit():
                raise ValidationError({'foro': 'Debe ser un id numérico.'})
            qs = qs.filter(foro_id=foro)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        self._verificar_foro(serializer.validated_data['foro'], user)
        # El autor siempre sale de la sesión, nunca del cliente
        serializer.save(autor=user, estudiante=estudiante_de(user))

    def perform_update(self, serializer):
        foro = serializer.validated_data.get('foro', serializer.instance.foro)
        self._verificar_foro(foro, self.request.user)
        serializer.save(editado=True)

    def _verificar_foro(self, foro, user):
        if not foro.activo:
            raise PermissionDenied('Este foro está cerrado.')
        if user.is_staff:
            return
        curso = foro.clase.materia.curso
        if es_profesor(user):
            permitido = curso.titular_id == user.pk
        else:
            estudiante = estudiante_de(user)
            permitido = estudiante is not None and curso.estudiantes.filter(pk=estudiante.pk).exists()
        if not permitido:
            raise PermissionDenied('Solo puedes publicar en foros de tus cursos.')

class ControlEscolarViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = ControlEscolar.objects.select_related('materia', 'estudiante').order_by('-periodo', 'materia__nombre')
    serializer_class = ControlEscolarSerializer
    permission_classes = [IsAuthenticated, ProfesorEscribe]
    ruta_estudiante = 'estudiante'
    ruta_curso = 'materia__curso'

    # Tras capturar una calificación, el perfil (promedio, progreso) debe reflejarla
    def perform_create(self, serializer):
        super().perform_create(serializer)
        self._recalcular_perfil(serializer.instance.estudiante)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        self._recalcular_perfil(serializer.instance.estudiante)

    def _recalcular_perfil(self, estudiante):
        perfil = getattr(estudiante, 'perfil', None)
        if perfil:
            perfil.recalcular()
