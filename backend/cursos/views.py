from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from cuentas.permisos import AlcancePorRolMixin, ProfesorEscribe
from cuentas.roles import PROFESOR, STAFF, rol_de
from estudiantes.models import Estudiante
from estudiantes.serializers import EstudianteSerializer
from .models import Curso
from .serializers import CursoSerializer

class CursoViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = Curso.objects.all()
    serializer_class = CursoSerializer
    permission_classes = [IsAuthenticated, ProfesorEscribe]
    acciones_profesor = ('update', 'partial_update')  # inscribir/quitar quedan solo para staff
    ruta_curso = ''

    @action(detail=True, methods=['get'])
    def inscritos(self, request, pk=None):
        # Un estudiante no debe ver los datos de contacto de sus compañeros
        if rol_de(request.user) not in (STAFF, PROFESOR):
            raise PermissionDenied('Solo profesores y staff pueden ver la lista de inscritos.')
        curso = self.get_object()
        return Response(EstudianteSerializer(curso.estudiantes.order_by('apellido', 'nombre'), many=True).data)

    @action(detail=True, methods=['post'])
    def inscribir(self, request, pk=None):
        curso = self.get_object()
        curso.estudiantes.add(self._estudiante(request))
        return Response(self.get_serializer(curso).data)

    @action(detail=True, methods=['post'])
    def quitar(self, request, pk=None):
        curso = self.get_object()
        curso.estudiantes.remove(self._estudiante(request))
        return Response(self.get_serializer(curso).data)

    def _estudiante(self, request):
        try:
            return Estudiante.objects.get(pk=int(request.data.get('estudiante')))
        except (TypeError, ValueError, Estudiante.DoesNotExist):
            raise ValidationError({'estudiante': 'Estudiante no válido.'})
