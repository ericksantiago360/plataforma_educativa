from django.db.models import ProtectedError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from academico.reportes import datos_kardex, pdf_kardex, respuesta_pdf
from cuentas.permisos import AlcancePorRolMixin, SoloStaffEscribe
from cuentas.roles import ESTUDIANTE, STAFF, rol_de
from .models import Estudiante
from .serializers import AltaEstudianteSerializer, EstudianteSerializer

class EstudianteViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = Estudiante.objects.all()
    serializer_class = EstudianteSerializer
    permission_classes = [IsAuthenticated, SoloStaffEscribe]
    ruta_estudiante = ''
    ruta_curso = 'cursos'

    def destroy(self, request, *args, **kwargs):
        try:
            return super().destroy(request, *args, **kwargs)
        except ProtectedError:
            # Sus cargos y pagos deben conservarse
            return Response({'detail': 'El estudiante tiene cargos o pagos registrados: dalo de baja en lugar de borrarlo.'},
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def alta(self, request):
        """Crea estudiante + cuenta + perfil. La contraseña temporal solo se devuelve aquí, una vez."""
        serializer = AltaEstudianteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        estudiante = serializer.save()
        return Response({
            'estudiante': EstudianteSerializer(estudiante).data,
            'usuario': estudiante.usuario.username,
            'password_temporal': serializer.password_temporal,
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def kardex(self, request, pk=None):
        """PDF con el historial completo. Lo descarga el propio alumno o el staff; el profesor solo ve sus cursos."""
        if rol_de(request.user) not in (STAFF, ESTUDIANTE):
            raise PermissionDenied('El kardex completo solo lo descargan el alumno y Control Escolar.')
        estudiante = self.get_object()  # para el alumno, solo él mismo
        return respuesta_pdf(pdf_kardex(datos_kardex(estudiante)), f'kardex-{estudiante.matricula}.pdf')
