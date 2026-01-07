import os
import sys

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Импортируем WS-роутинг только после инициализации Django,
# чтобы избежать ошибок загрузки приложений и моделей
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
from chat.routing import websocket_urlpatterns as chat_websocket_urlpatterns
from invoices.routing import websocket_urlpatterns as invoice_websocket_urlpatterns
from reports.routing import websocket_urlpatterns as reports_websocket_urlpatterns
from notifications.routing import websocket_urlpatterns as notifications_websocket_urlpatterns
from chat.middleware import TokenAuthMiddleware

# Объединяем все WebSocket роуты
websocket_urlpatterns = (
    chat_websocket_urlpatterns
    + invoice_websocket_urlpatterns
    + reports_websocket_urlpatterns
    + notifications_websocket_urlpatterns
)

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            TokenAuthMiddleware(  # Extract token from query parameter
                AuthMiddlewareStack(  # Fallback to session auth if no token
                    URLRouter(websocket_urlpatterns)
                )
            )
        ),
    }
)

import logging

logger = logging.getLogger(__name__)

try:
    from config.sentry import init_sentry

    init_sentry(sys.modules["config.settings"])
    logger.info("[ASGI] Sentry initialized successfully")
except Exception as e:
    logger.error(f"[ASGI] Sentry initialization failed: {e}", exc_info=True)
