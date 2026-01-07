# backend/chat/middleware.py

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
from urllib.parse import parse_qs
import logging

logger = logging.getLogger(__name__)


class TokenAuthMiddleware(BaseMiddleware):
    """
    Middleware to extract and validate API token from WebSocket query parameters.
    Replaces session-based auth for WebSocket connections.

    Usage in ASGI:
        from chat.middleware import TokenAuthMiddleware

        application = ProtocolTypeRouter({
            "websocket": TokenAuthMiddleware(
                AuthMiddlewareStack(
                    URLRouter(websocket_urlpatterns)
                )
            )
        })

    Frontend connects with:
        ws://host/ws/chat/room_id/?token=<api_token>
    """

    async def __call__(self, scope, receive, send):
        # Only process WebSocket connections
        if scope["type"] != "websocket":
            return await super().__call__(scope, receive, send)

        try:
            # Debug full scope (only in DEBUG mode)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'[TokenAuthMiddleware] Full path: {scope.get("path", "")}')
                logger.debug(
                    f'[TokenAuthMiddleware] Raw query_string bytes: {scope.get("query_string", b"")}'
                )

            # Extract token from query parameters
            query_string = scope.get("query_string", b"").decode()
            query_params = parse_qs(query_string)
            token_list = query_params.get("token", [])
            token = token_list[0] if token_list else None

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"[TokenAuthMiddleware] Decoded query string: {query_string}")
                logger.debug(f"[TokenAuthMiddleware] Token present: {bool(token)}")

            if token:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"[TokenAuthMiddleware] Token from query: {token[:20]}...")
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("[TokenAuthMiddleware] No token in query parameters")

            # Authenticate user if token provided
            if token:
                user = await self.get_user_from_token(token)
                if user:
                    scope["user"] = user
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            f"[TokenAuthMiddleware] ✓ Authenticated: {user.email} (role: {user.role})"
                        )
                else:
                    scope["user"] = AnonymousUser()
                    logger.warning(
                        f"[TokenAuthMiddleware] ✗ Token invalid: {token[:20]}"
                    )  # Keep as warning - auth failure
            else:
                # No token provided, let AuthMiddlewareStack try session auth
                scope["user"] = AnonymousUser()
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"[TokenAuthMiddleware] No token - trying session auth")

        except Exception as e:
            logger.error(f"[TokenAuthMiddleware] Error in __call__: {e}", exc_info=True)
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_user_from_token(self, token):
        """
        Validate token and return associated user.
        Returns None if token invalid.
        """
        try:
            token_obj = Token.objects.select_related("user").get(key=token)
            user = token_obj.user

            # Check user is active
            if not user.is_active:
                logger.warning(f"[WebSocket Auth] User {user.email} is inactive")
                return None

            return user

        except Token.DoesNotExist:
            logger.warning(f"[WebSocket Auth] Invalid token: {token[:10]}...")
            return None
        except Exception as e:
            logger.error(f"[WebSocket Auth] Error validating token: {str(e)}")
            return None
