from django.db import transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from academico.reportes import respuesta_pdf
from cuentas.permisos import SoloStaffEscribe
from cuentas.roles import STAFF, ESTUDIANTE, estudiante_de, rol_de
from estudiantes.models import Estudiante
from .models import ConceptoPago, Cargo, Pago, con_pagado
from .recibos import datos_recibo, pdf_recibo
from .serializers import (CargoMasivoSerializer, CargoSerializer, ConceptoPagoSerializer, CrearCargoSerializer,
                          PagoSerializer, RegistrarPagoSerializer)

class ConceptoPagoViewSet(viewsets.ModelViewSet):
    """Catálogo de precios: lo administra el staff; los demás ven los activos (para solicitar trámites)."""
    queryset = ConceptoPago.objects.all()
    serializer_class = ConceptoPagoSerializer
    permission_classes = [IsAuthenticated, SoloStaffEscribe]

    def get_queryset(self):
        qs = super().get_queryset()
        return qs if self.request.user.is_staff else qs.filter(activo=True)

def _cargos_de(user):
    """Cargos visibles: el staff ve todos, el alumno los suyos y nadie más ve dinero ajeno."""
    qs = con_pagado(Cargo.objects.select_related('estudiante')).prefetch_related('pagos__registrado_por')
    rol = rol_de(user)
    if rol == STAFF:
        return qs
    if rol == ESTUDIANTE:
        return qs.filter(estudiante=estudiante_de(user))
    return qs.none()

class CargoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    """Los cargos no se editan ni se borran: se cancelan. Así el estado de cuenta conserva su historia."""
    queryset = Cargo.objects.all()
    serializer_class = CargoSerializer

    def get_permissions(self):
        if self.action in ('create', 'masivo', 'cancelar', 'pagar'):
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = _cargos_de(self.request.user)
        # ?estudiante=<id> para el estado de cuenta de un alumno (útil para el staff)
        estudiante = self.request.query_params.get('estudiante')
        if estudiante is not None:
            if not estudiante.isdigit():
                raise ValidationError({'estudiante': 'Debe ser un id numérico.'})
            qs = qs.filter(estudiante_id=estudiante)
        return qs

    def _respuesta(self, cargo, codigo=status.HTTP_200_OK, **extra):
        # Se vuelve a leer con lo pagado anotado y los pagos al día
        cargo = self.get_queryset().get(pk=cargo.pk)
        return Response({**self.get_serializer(cargo).data, **extra}, status=codigo)

    def create(self, request):
        """Cargo individual desde el catálogo."""
        datos = CrearCargoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        concepto = datos.validated_data['concepto']
        cargo = Cargo.objects.create(
            estudiante=datos.validated_data['estudiante'], concepto=concepto, descripcion=concepto.nombre,
            tipo=concepto.tipo, monto=concepto.monto, periodo=datos.validated_data.get('periodo', ''),
            fecha_limite=datos.validated_data.get('fecha_limite'), creado_por=request.user,
        )
        return self._respuesta(cargo, status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'])
    def masivo(self, request):
        """Colegiatura o inscripción de un periodo para todos los alumnos activos que aún no la tengan."""
        datos = CargoMasivoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        concepto, periodo = datos.validated_data['concepto'], datos.validated_data['periodo']

        ya_tienen = set(Cargo.objects.filter(concepto=concepto, periodo=periodo, cancelado=False)
                        .values_list('estudiante_id', flat=True))
        activos = list(Estudiante.objects.filter(activo=True))
        nuevos = [
            Cargo(estudiante=estudiante, concepto=concepto, descripcion=concepto.nombre, tipo=concepto.tipo,
                  monto=concepto.monto, periodo=periodo, fecha_limite=datos.validated_data.get('fecha_limite'),
                  creado_por=request.user)
            for estudiante in activos
            if estudiante.pk not in ya_tienen
        ]
        Cargo.objects.bulk_create(nuevos)
        return Response({'creados': len(nuevos), 'ya_tenian': len(activos) - len(nuevos)}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        with transaction.atomic():
            cargo = Cargo.objects.select_for_update().get(pk=self.get_object().pk)
            if cargo.pagado > 0:
                return Response({'detail': 'El cargo tiene pagos: anúlalos antes de cancelarlo.'},
                                status=status.HTTP_400_BAD_REQUEST)
            cargo.cancelado = True
            cargo.save(update_fields=['cancelado'])
        return self._respuesta(cargo)

    @action(detail=True, methods=['post'])
    def pagar(self, request, pk=None):
        """Registra un pago en caja. Se aceptan pagos parciales, nunca más que el saldo."""
        datos = RegistrarPagoSerializer(data=request.data)
        datos.is_valid(raise_exception=True)
        with transaction.atomic():
            # Bloquea el cargo para que dos cajas a la vez no cobren de más
            cargo = Cargo.objects.select_for_update().get(pk=self.get_object().pk)
            if cargo.cancelado:
                return Response({'detail': 'El cargo está cancelado.'}, status=status.HTTP_400_BAD_REQUEST)
            if datos.validated_data['monto'] > cargo.saldo:
                return Response({'monto': [f'El saldo pendiente es ${cargo.saldo:,.2f}.']},
                                status=status.HTTP_400_BAD_REQUEST)
            pago = Pago.objects.create(cargo=cargo, registrado_por=request.user, **datos.validated_data)
        return self._respuesta(cargo, status.HTTP_201_CREATED, pago=PagoSerializer(pago).data)

    @action(detail=False, methods=['post'])
    def solicitar_tramite(self, request):
        """El alumno pide un trámite del catálogo (constancia, kardex oficial…) y se le genera el cargo."""
        estudiante = estudiante_de(request.user)
        if estudiante is None:
            raise PermissionDenied('Solo los estudiantes solicitan trámites.')
        try:
            concepto = ConceptoPago.objects.get(pk=int(request.data.get('concepto')), tipo='tramite', activo=True)
        except (TypeError, ValueError, ConceptoPago.DoesNotExist):
            raise ValidationError({'concepto': ['Elige un trámite del catálogo.']})
        cargo = Cargo.objects.create(estudiante=estudiante, concepto=concepto, descripcion=concepto.nombre,
                                     tipo='tramite', monto=concepto.monto, creado_por=request.user)
        return self._respuesta(cargo, status.HTTP_201_CREATED)

class PagoViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Los pagos no se borran: se anulan con motivo."""
    queryset = Pago.objects.all()
    serializer_class = PagoSerializer

    def get_permissions(self):
        if self.action == 'anular':
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        qs = Pago.objects.select_related('cargo__estudiante', 'registrado_por')
        rol = rol_de(self.request.user)
        if rol == STAFF:
            return qs
        if rol == ESTUDIANTE:
            return qs.filter(cargo__estudiante=estudiante_de(self.request.user))
        return qs.none()

    @action(detail=True, methods=['post'])
    def anular(self, request, pk=None):
        motivo = str(request.data.get('motivo', '')).strip()
        if not motivo:
            raise ValidationError({'motivo': ['Escribe el motivo de la anulación.']})
        with transaction.atomic():
            pago = Pago.objects.select_for_update().get(pk=self.get_object().pk)
            if pago.anulado:
                return Response({'detail': 'El pago ya estaba anulado.'}, status=status.HTTP_400_BAD_REQUEST)
            pago.anulado = True
            pago.motivo_anulacion = motivo[:255]
            pago.anulado_por = request.user
            pago.save(update_fields=['anulado', 'motivo_anulacion', 'anulado_por'])
        return Response(self.get_serializer(pago).data)

    @action(detail=True, methods=['get'])
    def recibo(self, request, pk=None):
        pago = self.get_object()  # el alumno, solo de sus pagos
        return respuesta_pdf(pdf_recibo(datos_recibo(pago)), f'recibo-{pago.folio}.pdf')
