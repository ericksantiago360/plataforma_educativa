from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from cuentas.permisos import AlcancePorRolMixin, EstudianteAutor, SoloStaffEscribe
from cuentas.roles import estudiante_de
from .models import BibliotecaDigital, MesaAyuda, EventoCalendario, CentroIdiomas
from .serializers import BibliotecaDigitalSerializer, MesaAyudaSerializer, EventoCalendarioSerializer, CentroIdiomasSerializer

class BibliotecaDigitalViewSet(viewsets.ModelViewSet):
    queryset = BibliotecaDigital.objects.all()
    serializer_class = BibliotecaDigitalSerializer
    permission_classes = [IsAuthenticated, SoloStaffEscribe]

class MesaAyudaViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = MesaAyuda.objects.all()
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

class CentroIdiomasViewSet(viewsets.ModelViewSet):
    queryset = CentroIdiomas.objects.all()
    serializer_class = CentroIdiomasSerializer
    permission_classes = [IsAuthenticated, SoloStaffEscribe]
