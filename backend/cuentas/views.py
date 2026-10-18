from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework import status

from estudiantes.serializers import EstudianteSerializer
from .models import debe_cambiar_password
from .roles import dado_de_baja, estudiante_de, rol_de


def datos_usuario(user):
    estudiante = estudiante_de(user)
    return {
        'id': user.pk,
        'usuario': user.username,
        'nombre': user.get_full_name() or user.username,
        'rol': rol_de(user),
        'estudiante': EstudianteSerializer(estudiante).data if estudiante else None,
        'debe_cambiar_password': debe_cambiar_password(user),
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


class CambiarPasswordView(APIView):
    """El usuario de la sesión cambia su contraseña escribiendo la actual."""
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = 'cambiar_password'  # limita adivinar la contraseña actual con una sesión robada

    def post(self, request):
        user = request.user
        actual = request.data.get('password_actual', '')
        nueva = request.data.get('password_nueva', '')

        if not user.check_password(actual):
            return Response({'password_actual': ['La contraseña actual no es correcta.']},
                            status=status.HTTP_400_BAD_REQUEST)
        if nueva == actual:
            return Response({'password_nueva': ['La nueva contraseña debe ser distinta de la actual.']},
                            status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(nueva, user)  # longitud mínima, no parecida al usuario, no común, no solo números
        except ValidationError as error:
            return Response({'password_nueva': error.messages}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(nueva)
        user.save(update_fields=['password'])
        # Conserva esta sesión; las demás sesiones abiertas de la cuenta dejan de valer
        update_session_auth_hash(request, user)
        estado = getattr(user, 'estado_cuenta', None)
        if estado and estado.debe_cambiar_password:
            estado.debe_cambiar_password = False
            estado.save(update_fields=['debe_cambiar_password'])
        return Response(datos_usuario(user))
