from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from cuentas.permisos import AlcancePorRolMixin, SoloStaffEscribe
from .models import Estudiante
from .serializers import AltaEstudianteSerializer, EstudianteSerializer

class EstudianteViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = Estudiante.objects.all()
    serializer_class = EstudianteSerializer
    permission_classes = [IsAuthenticated, SoloStaffEscribe]
    ruta_estudiante = ''
    ruta_curso = 'cursos'

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
