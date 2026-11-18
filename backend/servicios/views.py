from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from cuentas.permisos import AlcancePorRolMixin, EstudianteAutor, SoloStaffEscribe
from cuentas.roles import ESTUDIANTE, PROFESOR, STAFF, estudiante_de, rol_de
from notificaciones.correo import avisar_respuesta_ticket
from pagos.models import Cargo, cargar_curso_idiomas, cargo_vigente_de_idiomas, con_pagado
from .models import BibliotecaDigital, MesaAyuda, EventoCalendario, CentroIdiomas, ClaseIdiomas, MaterialIdiomas
from .serializers import (BibliotecaDigitalSerializer, MesaAyudaSerializer, EventoCalendarioSerializer,
                          CentroIdiomasSerializer, ClaseIdiomasSerializer, MaterialIdiomasSerializer)

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

    def perform_update(self, serializer):
        antes = (serializer.instance.estado, serializer.instance.respuesta)
        super().perform_update(serializer)
        ticket = serializer.instance
        if (ticket.estado, ticket.respuesta) != antes:
            avisar_respuesta_ticket(ticket)

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
                if curso.fecha_inicio < timezone.localdate():
                    return Response({'detail': 'Este curso ya inició: las inscripciones están cerradas.'},
                                    status=status.HTTP_400_BAD_REQUEST)
                if curso.cupos_disponibles <= 0:
                    return Response({'detail': 'Ya no hay cupo en este curso.'}, status=status.HTTP_400_BAD_REQUEST)
                curso.estudiantes_inscritos.add(estudiante)
                cargar_curso_idiomas(curso, estudiante)
        return Response(self.get_serializer(curso).data)

    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        estudiante = self._estudiante()
        curso = self.get_object()
        with transaction.atomic():
            cargo = cargo_vigente_de_idiomas(curso, estudiante)
            # Si ya pagó, la baja (y la devolución) las resuelve Control Escolar; si no, el cargo se cancela
            if cargo and cargo.pagado > 0:
                return Response({'detail': 'Ya tienes pagos en este curso: acude a Control Escolar para darte de baja.'},
                                status=status.HTTP_400_BAD_REQUEST)
            if cargo:
                cargo.cancelado = True
                cargo.save(update_fields=['cancelado'])
            curso.estudiantes_inscritos.remove(estudiante)
        return Response(self.get_serializer(curso).data)

    @action(detail=True, methods=['get'])
    def mi_curso(self, request, pk=None):
        """Lo que el alumno inscrito recibe del curso: horario, clases, materiales y el estado de su pago. El staff lo ve completo."""
        curso = self.get_object()
        estudiante = estudiante_de(request.user)
        inscrito = estudiante is not None and curso.estudiantes_inscritos.filter(pk=estudiante.pk).exists()
        if not (request.user.is_staff or inscrito):
            raise PermissionDenied('Inscríbete al curso para ver sus clases y materiales.')

        materiales = curso.materiales.all()
        if not request.user.is_staff:
            materiales = materiales.filter(publicado=True)
        cargo = cargo_vigente_de_idiomas(curso, estudiante) if inscrito else None
        return Response({
            'curso': self.get_serializer(curso).data,
            'clases': ClaseIdiomasSerializer(curso.clases.all(), many=True).data,
            'materiales': MaterialIdiomasSerializer(materiales, many=True).data,
            'cargo': datos_de_cargo(cargo),
        })

    @action(detail=True, methods=['get'])
    def inscritos(self, request, pk=None):
        """Solo staff: quién está inscrito y cómo va su pago."""
        if not request.user.is_staff:
            raise PermissionDenied('Solo el staff puede ver la lista de inscritos.')
        curso = self.get_object()
        cargos = {c.estudiante_id: c for c in con_pagado(Cargo.objects.filter(curso_idiomas=curso, cancelado=False))}
        return Response([
            {
                'estudiante': e.id,
                'nombre': f'{e.nombre} {e.apellido}',
                'matricula': e.matricula,
                'cargo': datos_de_cargo(cargos.get(e.id)),
            }
            for e in curso.estudiantes_inscritos.order_by('apellido', 'nombre')
        ])

    def _estudiante(self):
        estudiante = estudiante_de(self.request.user)
        if estudiante is None:
            raise PermissionDenied('Solo los estudiantes pueden inscribirse a cursos de idiomas.')
        return estudiante


def datos_de_cargo(cargo):
    """Resumen del cargo de un curso de idiomas (None si el curso es gratis o no hay cargo vigente)."""
    if cargo is None:
        return None
    return {
        'descripcion': cargo.descripcion,
        'monto': cargo.monto,
        'pagado': cargo.pagado,
        'saldo': cargo.saldo,
        'estado': cargo.estado,
        'fecha_limite': cargo.fecha_limite,
        'vencido': cargo.vencido,
    }


class ContenidoDeCursoIdiomas(viewsets.ModelViewSet):
    """Clases y materiales: el staff los administra; el alumno solo lee los de los cursos en que está inscrito."""
    permission_classes = [IsAuthenticated, SoloStaffEscribe]

    def para_alumno(self, qs):
        return qs

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request.user.is_staff:
            estudiante = estudiante_de(self.request.user)
            if estudiante is None:
                return qs.none()
            qs = self.para_alumno(qs.filter(curso__estudiantes_inscritos=estudiante, curso__activo=True))
        curso = self.request.query_params.get('curso')
        if curso is not None:
            if not curso.isdigit():
                raise ValidationError({'curso': 'Debe ser un id numérico.'})
            qs = qs.filter(curso_id=curso)
        return qs


class ClaseIdiomasViewSet(ContenidoDeCursoIdiomas):
    queryset = ClaseIdiomas.objects.select_related('curso')
    serializer_class = ClaseIdiomasSerializer


class MaterialIdiomasViewSet(ContenidoDeCursoIdiomas):
    queryset = MaterialIdiomas.objects.select_related('curso')
    serializer_class = MaterialIdiomasSerializer

    def para_alumno(self, qs):
        return qs.filter(publicado=True)  # los borradores son del staff
