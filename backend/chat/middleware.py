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
            # LOGGING POINT 1: Log when middleware is called with connection scope
            path = scope.get("path", "")
            query_string_bytes = scope.get("query_string", b"")
            headers = dict(scope.get("headers", []))

            logger.debug(
                f"[MIDDLEWARE: connection_scope] WebSocket connection: path={path}, "
                f"query_string_length={len(query_string_bytes)}, headers_count={len(headers)}"
            )

            # Log header keys (not values, for security)
            header_keys = [
                h[0].decode("utf-8", errors="ignore") for h in scope.get("headers", [])
            ]
            logger.debug(f"[MIDDLEWARE: headers_keys] {header_keys}")

            logger.info(f"[TokenAuthMiddleware] WebSocket connection attempt: {path}")

            token = None
            token_source = None

            # Priority 1: Try to extract token from Authorization header
            # LOGGING POINT 2: Log when attempting to extract token from Authorization header
            logger.debug(
                f"[MIDDLEWARE: token_extraction] Attempting Authorization header extraction"
            )

            token_from_header = self._extract_token_from_headers(headers)
            if token_from_header:
                token = token_from_header
                token_source = "Authorization header"
                logger.debug(
                    f"[MIDDLEWARE: token_extraction] Token found in Authorization header: "
                    f"token_format={self._get_token_preview(token_from_header)}, length={len(token_from_header)}"
                )
            else:
                logger.debug(
                    f"[MIDDLEWARE: token_extraction] No token found in Authorization header"
                )

                # Priority 2: Fallback to query string (deprecated)
                # LOGGING POINT 3: Log when attempting to extract token from query string
                logger.debug(
                    f"[MIDDLEWARE: token_extraction] Attempting query string extraction"
                )
                query_string = query_string_bytes.decode()
                logger.debug(
                    f"[MIDDLEWARE: token_extraction] Raw query_string: {query_string}"
                )
                query_params = parse_qs(query_string)
                token_list = query_params.get("token", [])
                logger.debug(
                    f"[MIDDLEWARE: token_extraction] Parsed query params keys: {list(query_params.keys())}"
                )

                if token_list:
                    token = token_list[0].strip()
                    if token:
                        token_source = "query string (legacy)"
                        logger.debug(
                            f"[MIDDLEWARE: token_extraction] Token found in query string: "
                            f"token_format={self._get_token_preview(token)}, length={len(token)}"
                        )
                    else:
                        token = None
                        logger.debug(
                            f"[MIDDLEWARE: token_extraction] Query string token is empty after stripping"
                        )
                else:
                    logger.debug(
                        f"[MIDDLEWARE: token_extraction] No token found in query string"
                    )

            # Authenticate user if token provided
            if token:
                # LOGGING POINT 4: Log JWT token validation attempt
                # LOGGING POINT 5: Log DRF Token validation attempt
                logger.info(
                    f"[TokenAuthMiddleware] Attempting to validate token from {token_source}: "
                    f"{self._get_token_preview(token)}"
                )
                logger.debug(
                    f"[MIDDLEWARE: token_validation] Starting token validation - source={token_source}, "
                    f"token_preview={self._get_token_preview(token)}"
                )

                user = await self.get_user_from_token(token)
                if user:
                    scope["user"] = user
                    # LOGGING POINT 6: Log final scope["user"] state (authenticated)
                    logger.info(
                        f"[TokenAuthMiddleware] ✓ Authenticated: {user.email} (id={user.id}, role: {user.role}, is_active: {user.is_active}) from {token_source}"
                    )
                    logger.debug(
                        f"[MIDDLEWARE: final_state] scope['user'] set to authenticated user - "
                        f"user_id={user.id}, email={user.email}, is_active={user.is_active}"
                    )
                else:
                    scope["user"] = AnonymousUser()
                    # LOGGING POINT 6: Log final scope["user"] state (validation failed)
                    logger.warning(
                        f"[TokenAuthMiddleware] ✗ Token validation failed from {token_source}: "
                        f"{self._get_token_preview(token)}"
                    )
                    logger.debug(
                        f"[MIDDLEWARE: final_state] Token validation returned None - "
                        f"scope['user'] set to AnonymousUser"
                    )
            else:
                # No token provided, let AuthMiddlewareStack try session auth
                scope["user"] = AnonymousUser()
                # LOGGING POINT 6: Log final scope["user"] state (no token provided)
                logger.debug(
                    f"[MIDDLEWARE: final_state] No token provided - scope['user'] set to AnonymousUser"
                )

        except Exception as e:
            # LOGGING POINT 7: Log any exceptions during token validation
            logger.error(
                f"[MIDDLEWARE: exception] Error in TokenAuthMiddleware.__call__: {type(e).__name__}: {str(e)}",
                exc_info=True,
            )
            logger.debug(
                f"[MIDDLEWARE: exception_traceback] Full exception details in previous error log"
            )
            scope["user"] = AnonymousUser()

        return await super().__call__(scope, receive, send)

    def _get_token_preview(self, token: str) -> str:
        """
        Get safe preview of token (first 10 chars + '...').
        Used in logging to avoid exposing full tokens.

        Args:
            token: Token string to preview

        Returns:
            Safe token preview string
        """
        if not token:
            return "<empty>"
        if len(token) <= 10:
            return f"{token}..."
        return f"{token[:10]}..."

    def _extract_token_from_headers(self, headers: dict) -> str | None:
        """
        Extract JWT token from Authorization header (case-insensitive).

        Expected format: Authorization: Bearer <token> or Authorization: Token <token>

        Handles:
        - Case-insensitive header lookup (Authorization, authorization, AUTHORIZATION)
        - Both Bearer and Token prefixes (for DRF Token backward compatibility)
        - Proper bytes decoding
        - Empty/malformed headers

        Args:
            headers: Dictionary of request headers (bytes keys and values)

        Returns:
            Token string if present and valid format, None otherwise
        """
        try:
            auth_header_bytes = None
            auth_header_value = None

            for header_name, header_value in headers.items():
                if isinstance(header_name, bytes):
                    if header_name.lower() == b"authorization":
                        auth_header_bytes = header_value
                        break

            if not auth_header_bytes:
                logger.debug(
                    f"[MIDDLEWARE: header_extraction] Authorization header not found"
                )
                return None

            try:
                auth_header_value = auth_header_bytes.decode("utf-8")
            except (UnicodeDecodeError, AttributeError) as e:
                logger.debug(
                    f"[MIDDLEWARE: header_extraction] Failed to decode Authorization header bytes: {type(e).__name__}"
                )
                return None

            logger.debug(
                f"[MIDDLEWARE: header_extraction] Authorization header found: value_length={len(auth_header_value)}"
            )

            auth_header_value = auth_header_value.strip()
            if not auth_header_value:
                logger.debug(
                    f"[MIDDLEWARE: header_extraction] Authorization header is empty after stripping"
                )
                return None

            if auth_header_value.startswith("Bearer ") or auth_header_value.startswith("bearer "):
                token = auth_header_value[7:].strip()
                if token:
                    logger.debug(
                        f"[MIDDLEWARE: header_extraction] Bearer format detected, token extracted: length={len(token)}"
                    )
                    return token
                else:
                    logger.debug(
                        f"[MIDDLEWARE: header_extraction] Bearer prefix found but token is empty"
                    )
                    return None

            elif auth_header_value.startswith("Token ") or auth_header_value.startswith("token "):
                token = auth_header_value[6:].strip()
                if token:
                    logger.debug(
                        f"[MIDDLEWARE: header_extraction] Token format detected, token extracted: length={len(token)}"
                    )
                    return token
                else:
                    logger.debug(
                        f"[MIDDLEWARE: header_extraction] Token prefix found but token is empty"
                    )
                    return None

            else:
                logger.debug(
                    f"[MIDDLEWARE: header_extraction] Authorization header present but missing Bearer/Token prefix"
                )
                return None

        except Exception as e:
            logger.debug(
                f"[MIDDLEWARE: header_extraction] Unexpected error extracting Authorization header: {type(e).__name__}: {str(e)}"
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

        # LOGGING POINT 4: Log JWT token validation attempt
        logger.debug(
            f"[MIDDLEWARE: jwt_validation] Attempting JWT validation - token_length={len(token)}"
        )

        # Priority 1: Try JWT validation
        try:
            access_token = AccessToken(token)
            logger.debug(
                f"[MIDDLEWARE: jwt_validation] AccessToken object created successfully"
            )

            user_id = access_token.get("user_id")
            logger.debug(
                f"[MIDDLEWARE: jwt_validation] JWT decoded - user_id extracted: {user_id is not None}"
            )

            if user_id:
                try:
                    user = User.objects.get(id=user_id)
                    logger.debug(
                        f"[MIDDLEWARE: jwt_validation] User found in database - user_id={user_id}, "
                        f"email={user.email}, is_active={user.is_active}"
                    )

                    if not user.is_active:
                        logger.warning(
                            f"[MIDDLEWARE: jwt_validation] JWT user is inactive - user_id={user_id}, "
                            f"email={user.email}"
                        )
                        return None

                    logger.info(
                        f"[MIDDLEWARE: jwt_validation] ✓ JWT token validated successfully for user_id={user_id}"
                    )
                    logger.debug(
                        f"[MIDDLEWARE: jwt_validation] JWT validation result: success, user_id={user_id}, "
                        f"email={user.email}"
                    )
                    return user

                except User.DoesNotExist:
                    logger.warning(
                        f"[MIDDLEWARE: jwt_validation] JWT user not found in database - user_id={user_id}"
                    )
                    return None
            else:
                logger.debug(
                    f"[MIDDLEWARE: jwt_validation] JWT decoded but no user_id claim found"
                )

        except (InvalidToken, TokenError) as e:
            logger.debug(
                f"[MIDDLEWARE: jwt_validation] JWT validation failed - exception={type(e).__name__}, "
                f"message={str(e)}"
            )
        except Exception as e:
            logger.debug(
                f"[MIDDLEWARE: jwt_validation] JWT processing error - exception={type(e).__name__}, "
                f"message={str(e)}"
            )

        # LOGGING POINT 5: Log DRF Token validation attempt
        logger.debug(
            f"[MIDDLEWARE: drf_token_validation] Attempting DRF Token model validation - "
            f"token_length={len(token)}"
        )

        # Priority 2: Fallback to DRF Token model (backward compatibility)
        try:
            token_obj = Token.objects.select_related("user").get(key=token)
            logger.debug(
                f"[MIDDLEWARE: drf_token_validation] Token object found in database"
            )

            user = token_obj.user
            logger.debug(
                f"[MIDDLEWARE: drf_token_validation] User associated with token - user_id={user.id}, "
                f"email={user.email}, is_active={user.is_active}"
            )

            if not user.is_active:
                logger.warning(
                    f"[MIDDLEWARE: drf_token_validation] DRF Token user is inactive - user_id={user.id}, "
                    f"email={user.email}"
                )
                return None

            logger.info(
                f"[MIDDLEWARE: drf_token_validation] ✓ DRF Token validated successfully for user_id={user.id}"
            )
            logger.debug(
                f"[MIDDLEWARE: drf_token_validation] DRF Token validation result: success, user_id={user.id}, "
                f"email={user.email}"
            )
            return user

        except Token.DoesNotExist:
            logger.warning(
                f"[MIDDLEWARE: drf_token_validation] Token not found - neither JWT nor DRF Token model valid"
            )
            return None

        except Exception as e:
            logger.error(
                f"[MIDDLEWARE: drf_token_validation] Error validating DRF token - exception={type(e).__name__}, "
                f"message={str(e)}",
                exc_info=True,
            )
            return None
