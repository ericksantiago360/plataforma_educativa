import os
import re

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from cuentas.permisos import ACCIONES_ESCRITURA, AlcancePorRolMixin, AutorDelMensaje, ProfesorEscribe, SoloStaffEscribe
from cuentas.roles import ESTUDIANTE, es_profesor, estudiante_de, rol_de
from .archivos import respuesta_de_descarga, validar_archivo
from .models import Materia, ClaseEnLinea, ForoClase, MensajeForo, ControlEscolar, ContenidoMateria, ArchivoContenido
from .serializers import (MateriaSerializer, ClaseEnLineaSerializer, ForoClaseSerializer, MensajeForoSerializer,
                          ControlEscolarSerializer, ContenidoMateriaSerializer, ArchivoContenidoSerializer)

MAXIMO_ARCHIVOS_POR_CONTENIDO = 20

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

    # Tras capturar o borrar una calificación, el perfil (promedio, progreso) debe reflejarlo
    def perform_create(self, serializer):
        super().perform_create(serializer)
        self._recalcular_perfil(serializer.instance.estudiante)

    def perform_update(self, serializer):
        super().perform_update(serializer)
        self._recalcular_perfil(serializer.instance.estudiante)

    def perform_destroy(self, instance):
        estudiante = instance.estudiante
        super().perform_destroy(instance)
        self._recalcular_perfil(estudiante)

    def _recalcular_perfil(self, estudiante):
        perfil = getattr(estudiante, 'perfil', None)
        if perfil:
            perfil.recalcular()

class ContenidoMateriaViewSet(AlcancePorRolMixin, viewsets.ModelViewSet):
    queryset = ContenidoMateria.objects.select_related('materia__curso', 'autor').prefetch_related('archivos')
    serializer_class = ContenidoMateriaSerializer
    permission_classes = [IsAuthenticated, ProfesorEscribe]
    acciones_profesor = ACCIONES_ESCRITURA + ('subir_archivo',)
    ruta_curso = 'materia__curso'

    def get_queryset(self):
        qs = super().get_queryset()
        # Los estudiantes solo ven lo publicado de materias activas; los borradores son del profesor
        if rol_de(self.request.user) == ESTUDIANTE:
            qs = qs.filter(publicado=True, materia__activo=True)
        materia = self.request.query_params.get('materia')
        if materia is not None:
            if not materia.isdigit():
                raise ValidationError({'materia': 'Debe ser un id numérico.'})
            qs = qs.filter(materia_id=materia)
        return qs

    def perform_create(self, serializer):
        self.verificar_curso_propio(serializer)
        serializer.save(autor=self.request.user)

    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser])
    def subir_archivo(self, request, pk=None):
        contenido = self.get_object()  # para el profesor, solo contenidos de sus cursos
        archivo = request.FILES.get('archivo')
        if archivo is None:
            return Response({'archivo': ['Adjunta un archivo.']}, status=status.HTTP_400_BAD_REQUEST)
        try:
            tipo = validar_archivo(archivo)
        except DjangoValidationError as error:
            return Response({'archivo': error.messages}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Bloquea el contenido para que dos subidas simultáneas no rebasen el máximo de archivos
            ContenidoMateria.objects.select_for_update().get(pk=contenido.pk)
            if contenido.archivos.count() >= MAXIMO_ARCHIVOS_POR_CONTENIDO:
                return Response({'archivo': [f'Máximo {MAXIMO_ARCHIVOS_POR_CONTENIDO} archivos por contenido.']},
                                status=status.HTTP_400_BAD_REQUEST)
            nuevo = ArchivoContenido.objects.create(
                contenido=contenido,
                archivo=archivo,
                nombre=os.path.basename(archivo.name)[:255],
                tipo=tipo,
                tamano=archivo.size,
            )
        return Response(ArchivoContenidoSerializer(nuevo).data, status=status.HTTP_201_CREATED)

class ArchivoContenidoViewSet(AlcancePorRolMixin, mixins.RetrieveModelMixin, mixins.DestroyModelMixin,
                              viewsets.GenericViewSet):
    queryset = ArchivoContenido.objects.select_related('contenido__materia__curso')
    serializer_class = ArchivoContenidoSerializer
    permission_classes = [IsAuthenticated, ProfesorEscribe]
    acciones_profesor = ('destroy',)
    ruta_curso = 'contenido__materia__curso'

    def get_queryset(self):
        qs = super().get_queryset()
        if rol_de(self.request.user) == ESTUDIANTE:
            qs = qs.filter(contenido__publicado=True, contenido__materia__activo=True)
        return qs

    @action(detail=True, methods=['get'])
    def descargar(self, request, pk=None):
        return respuesta_de_descarga(self.get_object())  # get_object aplica los mismos permisos que ver el contenido
