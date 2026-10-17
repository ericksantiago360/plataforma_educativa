from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission, SAFE_METHODS

from .roles import PROFESOR, STAFF, ESTUDIANTE, es_profesor, estudiante_de, rol_de

ACCIONES_ESCRITURA = ('create', 'update', 'partial_update', 'destroy')


class SoloStaffEscribe(BasePermission):
    """Cualquier usuario autenticado lee; solo el staff escribe."""

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or request.user.is_staff


class ProfesorEscribe(BasePermission):
    """
    Cualquier usuario autenticado lee; staff y profesores escriben.
    Que el profesor solo toque sus propios cursos lo garantiza AlcancePorRolMixin.
    La vista puede limitar qué acciones tiene el profesor con `acciones_profesor`.
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS or request.user.is_staff:
            return True
        acciones = getattr(view, 'acciones_profesor', ACCIONES_ESCRITURA)
        return es_profesor(request.user) and view.action in acciones


class EstudianteAutor(BasePermission):
    """
    Para registros que firma un estudiante (mensajes de foro, tickets).
    Cualquier usuario autenticado lee; el staff hace todo.
    El estudiante puede hacer las acciones de `acciones_autor`, y solo sobre lo suyo.
    El profesor puede hacer las de `acciones_profesor` (el queryset ya lo limita a sus cursos).
    """

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS or request.user.is_staff:
            return True
        rol = rol_de(request.user)
        if rol == ESTUDIANTE:
            return view.action in getattr(view, 'acciones_autor', ('create',))
        if rol == PROFESOR:
            return view.action in getattr(view, 'acciones_profesor', ())
        return False

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS or request.user.is_staff:
            return True
        if rol_de(request.user) == ESTUDIANTE:
            return obj.estudiante_id == estudiante_de(request.user).pk
        return True


class AutorDelMensaje(BasePermission):
    """
    Mensajes de foro: estudiantes, profesores y staff publican (la vista valida a qué foros).
    Cada quien edita solo lo suyo; los estudiantes borran lo suyo y
    profesores y staff borran cualquier mensaje visible para moderar.
    """

    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or rol_de(request.user) is not None

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS or request.user.is_staff:
            return True
        if view.action == 'destroy' and es_profesor(request.user):
            return True
        return obj.autor_id == request.user.pk


def _lookup(ruta, campo):
    return f'{ruta}__{campo}' if ruta else campo


class AlcancePorRolMixin:
    """
    Limita el queryset a lo que le corresponde a cada rol:
      - staff: todo
      - profesor: registros de los cursos donde es titular
      - estudiante: sus propios registros (ruta_estudiante) o los de los cursos que cursa (ruta_curso)

    ruta_curso: lookup del modelo al Curso ('' si el modelo es el propio Curso).
    ruta_estudiante: lookup del modelo al Estudiante dueño del registro ('' si es el propio Estudiante).
    """
    ruta_curso = None
    ruta_estudiante = None

    def get_queryset(self):
        qs = super().get_queryset()
        user = self.request.user
        rol = rol_de(user)

        if rol == STAFF:
            return qs
        if rol == PROFESOR and self.ruta_curso is not None:
            return qs.filter(**{_lookup(self.ruta_curso, 'titular'): user}).distinct()
        if rol == ESTUDIANTE:
            estudiante = estudiante_de(user)
            if self.ruta_estudiante is not None:
                return qs.filter(**{_lookup(self.ruta_estudiante, 'pk'): estudiante.pk})
            if self.ruta_curso is not None:
                return qs.filter(**{_lookup(self.ruta_curso, 'estudiantes'): estudiante}).distinct()
        return qs.none()

    def perform_create(self, serializer):
        self.verificar_curso_propio(serializer)
        super().perform_create(serializer)

    def perform_update(self, serializer):
        self.verificar_curso_propio(serializer)
        super().perform_update(serializer)

    def verificar_curso_propio(self, serializer):
        """Impide que un profesor cree o mueva registros hacia cursos que no imparte."""
        user = self.request.user
        if user.is_staff or not es_profesor(user):
            return
        if self._titular_resultante(serializer) != user.pk:
            raise PermissionDenied('Solo puedes modificar registros de tus propios cursos.')

    def _titular_resultante(self, serializer):
        datos, instancia = serializer.validated_data, serializer.instance

        def valor(campo):
            return datos[campo] if campo in datos else getattr(instancia, campo, None)

        if not self.ruta_curso:
            titular = valor('titular')
            return titular.pk if titular else None

        primero, *resto = self.ruta_curso.split('__')
        obj = valor(primero)
        for campo in resto:
            obj = getattr(obj, campo, None)
        return obj.titular_id if obj else None
