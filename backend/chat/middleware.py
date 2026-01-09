# backend/chat/middleware.py

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth.models import AnonymousUser
from rest_framework.authtoken.models import Token
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from urllib.parse import parse_qs
import logging

logger = logging.getLogger(__name__)


class TokenAuthMiddleware(BaseMiddleware):
    """
    Middleware to extract and validate JWT token from WebSocket connections.
    Replaces session-based auth for WebSocket connections.

    Supports two authentication methods (in priority order):
    1. Authorization header: Authorization: Bearer <token>
    2. Query string: ?token=<token> (deprecated, for backward compatibility)

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
        1. Authorization header: ws://host/ws/chat/room_id/
           (headers: Authorization: Bearer <api_token>)
        2. Query string (legacy): ws://host/ws/chat/room_id/?token=<api_token>
    """

    async def __call__(self, scope, receive, send):
        # Only process WebSocket connections
        if scope["type"] != "websocket":
            return await super().__call__(scope, receive, send)

        try:
            # Debug full scope (only in DEBUG mode)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f'[TokenAuthMiddleware] Full path: {scope.get("path", "")}'
                )
                logger.debug(
                    f'[TokenAuthMiddleware] Raw query_string bytes: {scope.get("query_string", b"")}'
                )

            token = None
            token_source = None

            # Priority 1: Try to extract token from Authorization header
            headers = dict(scope.get("headers", []))
            token_from_header = self._extract_token_from_headers(headers)
            if token_from_header:
                token = token_from_header
                token_source = "Authorization header"
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        f"[TokenAuthMiddleware] Token extracted from Authorization header: {token[:20]}..."
                    )
            else:
                # Priority 2: Fallback to query string (deprecated)
                query_string = scope.get("query_string", b"").decode()
                logger.info(f"[TokenAuthMiddleware] Raw query_string: {query_string}")
                query_params = parse_qs(query_string)
                token_list = query_params.get("token", [])
                logger.info(f"[TokenAuthMiddleware] Parsed query params: {list(query_params.keys())}")
                if token_list:
                    token = token_list[0]
                    token_source = "query string (legacy)"
                    logger.info(f"[TokenAuthMiddleware] Token extracted from query string: {token[:30]}...")
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            f"[TokenAuthMiddleware] Token extracted from query string (legacy): {token[:20]}..."
                        )
                else:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            "[TokenAuthMiddleware] No token provided in either header or query"
                        )

            # Authenticate user if token provided
            if token:
                logger.info(f"[TokenAuthMiddleware] Attempting to validate token from {token_source}")
                user = await self.get_user_from_token(token)
                if user:
                    scope["user"] = user
                    logger.info(
                        f"[TokenAuthMiddleware] ✓ Authenticated: {user.email} (role: {user.role}) from {token_source}"
                    )
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(
                            f"[TokenAuthMiddleware] ✓ Authenticated: {user.email} (role: {user.role}) from {token_source}"
                        )
                else:
                    scope["user"] = AnonymousUser()
                    logger.warning(
                        f"[TokenAuthMiddleware] ✗ Token validation failed from {token_source}: {token[:30]}..."
                    )
            else:
                # No token provided, let AuthMiddlewareStack try session auth
                scope["user"] = AnonymousUser()
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(
                        f"[TokenAuthMiddleware] No token - trying session auth"
                    )

        except Exception as e:
            logger.error(f"[TokenAuthMiddleware] Error in __call__: {e}", exc_info=True)
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)

    def _extract_token_from_headers(self, headers: dict) -> str | None:
        """
        Extract JWT token from Authorization header.

        Expected format: Authorization: Bearer <token>

        Args:
            headers: Dictionary of request headers (bytes keys and values)

        Returns:
            Token string if present and valid format, None otherwise
        """
        try:
            auth_header = headers.get(b"authorization", b"").decode()
            if auth_header.startswith("Bearer "):
                return auth_header[7:]
        except (UnicodeDecodeError, AttributeError):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    "[TokenAuthMiddleware] Failed to decode Authorization header"
                )
        return None

    @database_sync_to_async
    def get_user_from_token(self, token):
        """
        Validate token and return associated user.
        Supports both JWT (simplejwt) and DRF Token model (backward compatibility).
        Returns None if token invalid.
        """
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Priority 1: Try JWT validation
        try:
            access_token = AccessToken(token)
            user_id = access_token.get("user_id")
            if user_id:
                user = User.objects.get(id=user_id)
                if not user.is_active:
                    logger.warning(
                        f"[WebSocket Auth] JWT user {user.email} is inactive"
                    )
                    return None
                logger.debug(
                    f"[WebSocket Auth] JWT token validated for user_id={user_id}"
                )
                return user
        except (InvalidToken, TokenError) as e:
            logger.debug(f"[WebSocket Auth] JWT validation failed: {type(e).__name__}")
        except User.DoesNotExist:
            logger.warning(f"[WebSocket Auth] JWT user not found")
            return None
        except Exception as e:
            logger.debug(f"[WebSocket Auth] JWT processing error: {type(e).__name__}")

        # Priority 2: Fallback to DRF Token model (backward compatibility)
        try:
            token_obj = Token.objects.select_related("user").get(key=token)
            user = token_obj.user

            if not user.is_active:
                logger.warning(
                    f"[WebSocket Auth] Token model user {user.email} is inactive"
                )
                return None

            logger.debug(
                f"[WebSocket Auth] Token model validated for user_id={user.id}"
            )
            return user

        except Token.DoesNotExist:
            logger.warning(
                f"[WebSocket Auth] Invalid token (neither JWT nor Token model): {token[:10]}..."
            )
            return None
        except Exception as e:
            logger.error(f"[WebSocket Auth] Error validating token: {str(e)}")
            return None
