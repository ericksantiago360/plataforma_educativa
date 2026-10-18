"""
Una conexión WebSocket por pestaña en /ws/chat/. Al conectarse, el usuario queda suscrito a todas sus
conversaciones; cada mensaje se guarda y se reparte a quienes estén en esa conversación.
Protocolo (JSON):
  cliente → servidor: {"tipo": "mensaje", "conversacion": <id>, "texto": "..."}
  servidor → cliente: {"tipo": "mensaje", "mensaje": {...}}
                      {"tipo": "conversacion_nueva", "conversacion": <id>}
                      {"tipo": "error", "detalle": "..."}
"""
import time
from collections import deque

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth.models import User
from django.utils import timezone

from cuentas.roles import dado_de_baja, rol_de
from .acceso import MAXIMO_TEXTO, conversaciones_de, puede_ver
from .models import Conversacion, Lectura, Mensaje
from .serializers import MensajeSerializer

# Límite contra el spam: mensajes por ventana de segundos, por conexión
LIMITE_MENSAJES, VENTANA_SEGUNDOS = 10, 10
SIN_SESION = 4401  # código de cierre: la página vuelve al login en lugar de reintentar


def grupo_conversacion(conversacion_id):
    return f'chat_{conversacion_id}'


def grupo_usuario(user_id):
    return f'usuario_{user_id}'


class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.user = self.scope['user']
        self.conversaciones = set()
        # Sin sesión, sin rol o dado de baja: se rechaza (la página vuelve al login)
        if not self.user.is_authenticated or not await self._puede_entrar():
            await self.close(code=SIN_SESION)
            return
        self.conversaciones = set(await self._mis_conversaciones())
        self.envios = deque()
        await self.accept()
        for conversacion_id in self.conversaciones:
            await self.channel_layer.group_add(grupo_conversacion(conversacion_id), self.channel_name)
        # Para enterarse de privadas nuevas que se abran mientras está conectado
        await self.channel_layer.group_add(grupo_usuario(self.user.pk), self.channel_name)

    async def disconnect(self, code):
        for conversacion_id in self.conversaciones:
            await self.channel_layer.group_discard(grupo_conversacion(conversacion_id), self.channel_name)
        if self.user.is_authenticated:
            await self.channel_layer.group_discard(grupo_usuario(self.user.pk), self.channel_name)

    async def receive_json(self, contenido, **kwargs):
        if contenido.get('tipo') != 'mensaje':
            return await self._error('Tipo de mensaje desconocido.')
        texto = str(contenido.get('texto', '')).strip()
        if not texto:
            return await self._error('Escribe un mensaje.')
        if len(texto) > MAXIMO_TEXTO:
            return await self._error(f'El mensaje no puede pasar de {MAXIMO_TEXTO} caracteres.')
        try:
            conversacion_id = int(contenido.get('conversacion'))
        except (TypeError, ValueError):
            return await self._error('Conversación no válida.')

        ahora = time.monotonic()
        while self.envios and ahora - self.envios[0] > VENTANA_SEGUNDOS:
            self.envios.popleft()
        if len(self.envios) >= LIMITE_MENSAJES:
            return await self._error('Estás enviando mensajes muy rápido; espera unos segundos.')

        mensaje = await self._guardar(conversacion_id, texto)
        if mensaje is None:
            return await self._error('No puedes escribir en esta conversación.')
        if mensaje == 'baja':
            return await self.close(code=SIN_SESION)
        self.envios.append(ahora)
        await self.channel_layer.group_send(grupo_conversacion(conversacion_id), {'type': 'chat.mensaje', 'mensaje': mensaje})

    # ---------- Eventos del grupo ----------

    async def chat_mensaje(self, evento):
        await self.send_json({'tipo': 'mensaje', 'mensaje': evento['mensaje']})

    async def conversacion_nueva(self, evento):
        conversacion_id = evento['conversacion']
        if conversacion_id not in self.conversaciones:
            self.conversaciones.add(conversacion_id)
            await self.channel_layer.group_add(grupo_conversacion(conversacion_id), self.channel_name)
        await self.send_json({'tipo': 'conversacion_nueva', 'conversacion': conversacion_id})

    # ---------- Base de datos ----------

    async def _error(self, detalle):
        await self.send_json({'tipo': 'error', 'detalle': detalle})

    @database_sync_to_async
    def _puede_entrar(self):
        return rol_de(self.user) is not None and not dado_de_baja(self.user)

    @database_sync_to_async
    def _mis_conversaciones(self):
        return list(conversaciones_de(self.user).values_list('pk', flat=True))

    @database_sync_to_async
    def _guardar(self, conversacion_id, texto):
        # El usuario se vuelve a leer de la base en cada mensaje: el de la conexión trae en caché su registro
        # de estudiante, y pudo darse de baja, desactivarse o dejar el curso después de conectarse
        user = User.objects.select_related('estudiante').filter(pk=self.user.pk, is_active=True).first()
        if user is None or dado_de_baja(user):
            return 'baja'
        conversacion = Conversacion.objects.filter(pk=conversacion_id).first()
        if conversacion is None or not puede_ver(user, conversacion):
            return None
        mensaje = Mensaje.objects.create(conversacion=conversacion, autor=user, texto=texto)
        Conversacion.objects.filter(pk=conversacion.pk).update(ultimo_mensaje=timezone.now())
        # Lo que uno escribe ya está leído para uno mismo
        Lectura.objects.update_or_create(usuario=user, conversacion=conversacion,
                                         defaults={'ultimo_leido': mensaje.pk})
        return MensajeSerializer(mensaje).data
