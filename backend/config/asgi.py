import os
import sys
import signal
import logging

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
from notifications.routing import (
    websocket_urlpatterns as notifications_websocket_urlpatterns,
)
from chat.middleware import TokenAuthMiddleware

logger = logging.getLogger(__name__)

# Объединяем все WebSocket роуты
websocket_urlpatterns = (
    chat_websocket_urlpatterns
    + invoice_websocket_urlpatterns
    + reports_websocket_urlpatterns
    + notifications_websocket_urlpatterns
)


def setup_signal_handlers():
    """Setup SIGTERM handler for graceful shutdown"""
    import asyncio

    def sigterm_handler(signum, frame):
        logger.info("SIGTERM received, initiating graceful shutdown...")
        try:
            from chat.signals import shutdown_all_connections

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(shutdown_all_connections())
                else:
                    asyncio.run(shutdown_all_connections())
            except RuntimeError:
                logger.error("No event loop available for graceful shutdown")
        except Exception as e:
            logger.error(
                f"Error in SIGTERM handler: {type(e).__name__}: {str(e)}",
                exc_info=True,
            )

    signal.signal(signal.SIGTERM, sigterm_handler)
    logger.debug("SIGTERM handler registered for graceful shutdown")


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

setup_signal_handlers()

try:
    from config.sentry import init_sentry

    init_sentry(sys.modules["config.settings"])
    logger.info("[ASGI] Sentry initialized successfully")
except Exception as e:
    logger.error(f"[ASGI] Sentry initialization failed: {e}", exc_info=True)
