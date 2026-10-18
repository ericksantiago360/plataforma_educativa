import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Django se inicializa antes de importar el chat (sus consumidores usan los modelos)
aplicacion_http = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

import chat.routing  # noqa: E402

application = ProtocolTypeRouter({
    'http': aplicacion_http,
    # El WebSocket usa la misma cookie de sesión que la API; solo se aceptan orígenes de ALLOWED_HOSTS
    'websocket': AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(chat.routing.websocket_urlpatterns))),
})
