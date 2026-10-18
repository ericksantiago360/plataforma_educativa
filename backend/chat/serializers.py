from rest_framework import serializers
from cuentas.roles import rol_de
from .acceso import nombre_de
from .models import Conversacion, Lectura, Mensaje


class MensajeSerializer(serializers.ModelSerializer):
    autor_nombre = serializers.SerializerMethodField()
    autor_rol = serializers.SerializerMethodField()

    def get_autor_nombre(self, obj):
        return nombre_de(obj.autor) if obj.autor else 'Usuario eliminado'

    def get_autor_rol(self, obj):
        return rol_de(obj.autor) if obj.autor else None

    class Meta:
        model = Mensaje
        fields = ['id', 'conversacion', 'autor', 'autor_nombre', 'autor_rol', 'texto', 'enviado']


class ConversacionSerializer(serializers.ModelSerializer):
    """El título y los no leídos dependen de quién pregunta (request.user)."""
    titulo = serializers.SerializerMethodField()
    subtitulo = serializers.SerializerMethodField()
    ultimo = serializers.SerializerMethodField()
    no_leidos = serializers.SerializerMethodField()

    def _user(self):
        return self.context['request'].user

    def _otro(self, obj):
        return next((u for u in obj.participantes.all() if u.pk != self._user().pk), None)

    def get_titulo(self, obj):
        if obj.tipo == 'curso':
            return obj.curso.nombre
        otro = self._otro(obj)
        return nombre_de(otro) if otro else 'Conversación'

    def get_subtitulo(self, obj):
        if obj.tipo == 'curso':
            return 'Sala del curso'
        otro = self._otro(obj)
        return {'staff': 'Control Escolar', 'profesor': 'Profesor', 'estudiante': 'Estudiante'}.get(rol_de(otro), '') if otro else ''

    def get_ultimo(self, obj):
        mensaje = obj.mensajes.select_related('autor').last()
        return MensajeSerializer(mensaje).data if mensaje else None

    def get_no_leidos(self, obj):
        lectura = Lectura.objects.filter(usuario=self._user(), conversacion=obj).first()
        return obj.mensajes.filter(id__gt=lectura.ultimo_leido if lectura else 0).exclude(autor=self._user()).count()

    class Meta:
        model = Conversacion
        fields = ['id', 'tipo', 'curso', 'titulo', 'subtitulo', 'ultimo', 'no_leidos', 'ultimo_mensaje']
