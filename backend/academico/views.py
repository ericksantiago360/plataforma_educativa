from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from cuentas.permisos import AlcancePorRolMixin, AutorDelMensaje, ProfesorEscribe, SoloStaffEscribe
from cuentas.roles import es_profesor, estudiante_de
from .models import Materia, ClaseEnLinea, ForoClase, MensajeForo, ControlEscolar
from .serializers import MateriaSerializer, ClaseEnLineaSerializer, ForoClaseSerializer, MensajeForoSerializer, ControlEscolarSerializer

class MateriaViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = Materia.objects.all()
    serializer_class = MateriaSerializer
    permission_classes = [IsAuthenticated, SoloStaffEscribe]
    ruta_curso = 'curso'

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
