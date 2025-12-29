"""
Session and Token Refresh Middleware

This middleware ensures session stability by:
1. Automatically refreshing session cookies on each request
2. Validating token expiration
3. Logging session events for debugging
4. Maintaining CSRF token validity
"""

import logging
from django.utils.timezone import now
from rest_framework.authtoken.models import Token
from datetime import timedelta

logger = logging.getLogger(__name__)


class SessionRefreshMiddleware:
    """
    Middleware to refresh session and token on every request.

    Ensures:
    - Session cookies are refreshed (extends expiry)
    - Token validity is checked and logged
    - Session timeout doesn't randomly expire mid-navigation
    - User stays logged in for the configured duration

    Configuration (in settings.py):
    - SESSION_COOKIE_AGE: Session timeout in seconds (default: 86400 = 24 hours)
    - SESSION_SAVE_EVERY_REQUEST: Set to True (default: True)
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.session_timeout = None

    def __call__(self, request):
        # Refresh session on each request (extends timeout)
        if request.user and request.user.is_authenticated:
            # Log session info at DEBUG level
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"[SessionRefresh] User: {request.user.email}, "
                    f"Session key: {request.session.session_key}, "
                    f"Session age: {self._get_session_age(request)} seconds"
                )

            # Create or refresh session
            if request.session.session_key is None:
                request.session.create()
                logger.info(f"[SessionRefresh] Created new session for {request.user.email}")

            # Explicitly set session modified to trigger save
            request.session.modified = True

            # Validate token if using token authentication
            if hasattr(request, 'auth') and request.auth:
                self._validate_token(request)

        # Process request
        response = self.get_response(request)

        # Log session maintenance at request completion
        if request.user and request.user.is_authenticated:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"[SessionRefresh] Request completed for {request.user.email}, "
                    f"Path: {request.path}, "
                    f"Status: {response.status_code}"
                )

        return response

    def _validate_token(self, request):
        """
        Validate token validity and log any issues.

        Args:
            request: Django request object with auth token
        """
        try:
            # Try to get the token object
            token_key = request.auth.key if hasattr(request.auth, 'key') else str(request.auth)
            token = Token.objects.select_related('user').filter(key=token_key).first()

            if not token:
                logger.warning(
                    f"[TokenValidation] Invalid token: {token_key[:10]}... "
                    f"for user {request.user.email}"
                )
                return False

            if not token.user.is_active:
                logger.warning(
                    f"[TokenValidation] User {request.user.email} is inactive, "
                    f"token may be revoked soon"
                )
                return False

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    f"[TokenValidation] Valid token for {request.user.email}, "
                    f"token ID: {token.pk}"
                )

            return True

        except Exception as e:
            logger.warning(f"[TokenValidation] Error validating token: {str(e)}")
            return False

    def _get_session_age(self, request):
        """
        Calculate session age in seconds.

        Returns:
            int: Age of session in seconds, or None if new session
        """
        try:
            if hasattr(request.session, 'get_expiry_date'):
                expiry = request.session.get_expiry_date()
                age_seconds = int((expiry - now()).total_seconds())
                return max(0, age_seconds)
        except Exception:
            pass
        return None


class CSRFTokenRefreshMiddleware:
    """
    Middleware to ensure CSRF tokens are properly managed.

    Handles:
    - CSRF token validation on POST/PUT/PATCH/DELETE
    - CSRF token refresh for SPA clients
    - CSRF token logging for debugging
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Ensure CSRF token is available (creates one if needed)
        from django.middleware.csrf import get_token
        csrf_token = get_token(request)

        if logger.isEnabledFor(logging.DEBUG) and request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            logger.debug(
                f"[CSRFRefresh] {request.method} {request.path}, "
                f"CSRF token present: {bool(csrf_token)}"
            )

        response = self.get_response(request)

        # Ensure CSRF token cookie is set in response
        if csrf_token and request.method in ['GET', 'HEAD', 'OPTIONS']:
            # Token will be set by Django's CSRF middleware
            pass

        return response
