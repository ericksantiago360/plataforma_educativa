from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView
from cuentas.roles import rol_de
from .acceso import contactos, conversaciones_de, nombre_de, privada_entre, puede_conversar
from .consumers import grupo_usuario
from .models import Lectura
from .serializers import ConversacionSerializer, MensajeSerializer

MENSAJES_POR_PAGINA = 50

class ConversacionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    """Mis conversaciones e historial. Los mensajes se envían por WebSocket (chat/consumers.py)."""
    serializer_class = ConversacionSerializer
    pagination_class = None  # son pocas por usuario

    def get_queryset(self):
        return (conversaciones_de(self.request.user)
                .select_related('curso').prefetch_related('participantes')
                .order_by('-ultimo_mensaje', '-creada'))

    @action(detail=True, methods=['get'])
    def mensajes(self, request, pk=None):
        """Los últimos 50 mensajes; ?antes=<id> trae los anteriores a ese mensaje."""
        conversacion = self.get_object()
        qs = conversacion.mensajes.select_related('autor__estudiante').prefetch_related('autor__groups')
        antes = request.query_params.get('antes')
        if antes is not None:
            if not antes.isdigit():
                raise ValidationError({'antes': 'Debe ser un id numérico.'})
            qs = qs.filter(id__lt=antes)
        pagina = list(qs.order_by('-id')[:MENSAJES_POR_PAGINA + 1])
        return Response({
            'mensajes': MensajeSerializer(reversed(pagina[:MENSAJES_POR_PAGINA]), many=True).data,
            'hay_mas': len(pagina) > MENSAJES_POR_PAGINA,
        })

    @action(detail=True, methods=['post'])
    def leer(self, request, pk=None):
        conversacion = self.get_object()
        ultimo = conversacion.mensajes.order_by('-id').values_list('id', flat=True).first() or 0
        Lectura.objects.update_or_create(usuario=request.user, conversacion=conversacion, defaults={'ultimo_leido': ultimo})
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'])
    def privada(self, request):
        """Abre (o devuelve, si ya existe) la conversación privada con {usuario}."""
        try:
            otro = User.objects.get(pk=int(request.data.get('usuario')))
        except (TypeError, ValueError, User.DoesNotExist):
            raise ValidationError({'usuario': ['Usuario no válido.']})
        if not puede_conversar(request.user, otro):
            raise PermissionDenied('No puedes abrir una conversación con este usuario.')

        conversacion, creada = privada_entre(request.user, otro)
        if creada:
            # Las pestañas abiertas de ambos se suscriben a la conversación nueva
            capa = get_channel_layer()
            def avisar():
                for usuario in (request.user, otro):
                    async_to_sync(capa.group_send)(grupo_usuario(usuario.pk),
                                                   {'type': 'conversacion.nueva', 'conversacion': conversacion.pk})
            transaction.on_commit(avisar)
        datos = self.get_serializer(conversacion).data
        return Response(datos, status=status.HTTP_201_CREATED if creada else status.HTTP_200_OK)

class ContactosView(APIView):
    """Con quién puedo abrir una conversación privada."""
    def get(self, request):
        return Response([
            {'id': u.pk, 'nombre': nombre_de(u), 'rol': rol_de(u)}
            for u in contactos(request.user).select_related('estudiante').order_by('first_name', 'last_name', 'username')
        ])
