from django.conf import settings
from django.db import models
from cursos.models import Curso

class Conversacion(models.Model):
    """
    Sala de un curso (profesor titular + alumnos inscritos, calculado al momento) o conversación privada
    entre dos usuarios (participantes). Las reglas de quién puede estar en cada una viven en chat/acceso.py.
    """
    TIPOS = [('curso', 'Sala del curso'), ('privada', 'Privada')]

    tipo = models.CharField(max_length=10, choices=TIPOS)
    curso = models.OneToOneField(Curso, on_delete=models.CASCADE, null=True, blank=True, related_name='sala_chat')
    # Privadas: "<id menor>-<id mayor>", para que entre dos personas haya una sola conversación
    clave = models.CharField(max_length=50, unique=True, null=True, blank=True)
    participantes = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='conversaciones_privadas')
    creada = models.DateTimeField(auto_now_add=True)
    ultimo_mensaje = models.DateTimeField(null=True, blank=True)  # para ordenar la lista de conversaciones

    class Meta:
        verbose_name = 'Conversación'
        verbose_name_plural = 'Conversaciones'

    def __str__(self):
        return f'Sala {self.curso}' if self.tipo == 'curso' else f'Privada {self.clave}'

class Mensaje(models.Model):
    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name='mensajes')
    autor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='mensajes_chat')
    texto = models.TextField()
    enviado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f'{self.autor} → {self.conversacion}: {self.texto[:40]}'

class Lectura(models.Model):
    """Hasta qué mensaje leyó cada usuario cada conversación (para contar los no leídos)."""
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lecturas_chat')
    conversacion = models.ForeignKey(Conversacion, on_delete=models.CASCADE, related_name='lecturas')
    ultimo_leido = models.PositiveBigIntegerField(default=0)  # id del último mensaje leído

    class Meta:
        unique_together = ['usuario', 'conversacion']
