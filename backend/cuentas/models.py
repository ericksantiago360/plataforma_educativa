from django.conf import settings
from django.db import models


class EstadoCuenta(models.Model):
    """Datos de la cuenta que no caben en User. Hoy: si debe cambiar la contraseña temporal del alta."""
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='estado_cuenta')
    debe_cambiar_password = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Estado de cuenta'
        verbose_name_plural = 'Estados de cuenta'

    def __str__(self):
        return f"{self.usuario.username} ({'debe cambiar contraseña' if self.debe_cambiar_password else 'al día'})"


def debe_cambiar_password(user):
    estado = getattr(user, 'estado_cuenta', None)
    return bool(estado and estado.debe_cambiar_password)
