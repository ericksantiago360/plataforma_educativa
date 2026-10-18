from django.contrib.auth import authenticate, login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework import status

from estudiantes.serializers import EstudianteSerializer
from .roles import dado_de_baja, estudiante_de, rol_de


def datos_usuario(user):
    estudiante = estudiante_de(user)
    return {
        'id': user.pk,
        'usuario': user.username,
        'nombre': user.get_full_name() or user.username,
        'rol': rol_de(user),
        'estudiante': EstudianteSerializer(estudiante).data if estudiante else None,
    }


@method_decorator(ensure_csrf_cookie, name='get')
class CsrfView(APIView):
    """Entrega la cookie csrftoken que el frontend debe reenviar en el header X-CSRFToken."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(csrf_protect, name='post')
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'login'

    def post(self, request):
        user = authenticate(
            request,
            username=request.data.get('usuario', ''),
            password=request.data.get('password', ''),
        )
        if user is None:
            return Response(
                {'detail': 'Usuario o contraseña incorrectos.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # Solo se avisa después de comprobar la contraseña, para no revelar qué matrículas están de baja
        if dado_de_baja(user):
            return Response(
                {'detail': 'Tu inscripción está dada de baja. Comunícate con Control Escolar.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        login(request, user)
        return Response(datos_usuario(user))


class LogoutView(APIView):
    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    def get(self, request):
        return Response(datos_usuario(request.user))
