from rest_framework.authentication import SessionAuthentication

from .roles import dado_de_baja


class SesionAuthentication(SessionAuthentication):
    """
    Sesión por cookie que además corta el acceso a los estudiantes dados de baja.
    Se revisa en cada petición, así que una sesión abierta antes de la baja deja de servir de inmediato.
    """

    def authenticate(self, request):
        resultado = super().authenticate(request)
        if resultado and dado_de_baja(resultado[0]):
            return None
        return resultado
