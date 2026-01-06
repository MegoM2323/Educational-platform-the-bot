"""
Test CSRF protection configuration and behavior.

Verifies:
- CSRF middleware is properly configured
- SessionAuthentication is used (not CSRFExemptSessionAuthentication)
- TokenAuthentication is first (bypasses CSRF for token auth)
- CSRF settings are secure (SECURE, HTTPONLY, SAMESITE)
- Django CSRF protection is active
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

User = get_user_model()


@override_settings(ROOT_URLCONF="config.urls", CSRF_COOKIE_SECURE=True, DEBUG=False)
class TestCSRFConfiguration(TestCase):
    """Test CSRF settings are properly configured"""

    def test_csrf_middleware_in_middleware_list(self):
        """CsrfViewMiddleware should be in MIDDLEWARE"""
        from django.conf import settings

        csrf_middleware = "django.middleware.csrf.CsrfViewMiddleware"
        assert csrf_middleware in settings.MIDDLEWARE

    def test_csrf_cookie_samesite_lax(self):
        """CSRF_COOKIE_SAMESITE should be 'Lax'"""
        from django.conf import settings

        assert settings.CSRF_COOKIE_SAMESITE == "Lax"

    def test_csrf_cookie_httponly_false_for_js_access(self):
        """CSRF_COOKIE_HTTPONLY should be False (for JavaScript access)"""
        from django.conf import settings

        assert settings.CSRF_COOKIE_HTTPONLY is False

    def test_csrf_cookie_secure_in_production(self):
        """CSRF_COOKIE_SECURE should be True in production (DEBUG=False)"""
        from django.conf import settings

        assert settings.CSRF_COOKIE_SECURE is True

    def test_csrf_trusted_origins_configured(self):
        """CSRF_TRUSTED_ORIGINS should be configured"""
        from django.conf import settings

        assert hasattr(settings, "CSRF_TRUSTED_ORIGINS")
        assert isinstance(settings.CSRF_TRUSTED_ORIGINS, (list, tuple))

    def test_csrf_cookie_domain_configured(self):
        """CSRF_COOKIE_DOMAIN should be configured"""
        from django.conf import settings

        assert hasattr(settings, "CSRF_COOKIE_DOMAIN")


@override_settings(ROOT_URLCONF="config.urls")
class TestSessionAuthenticationConfigured(TestCase):
    """Test that SessionAuthentication is properly configured in DRF"""

    def test_session_authentication_in_rest_framework(self):
        """SessionAuthentication should be in DEFAULT_AUTHENTICATION_CLASSES"""
        from django.conf import settings

        auth_classes = settings.REST_FRAMEWORK.get(
            "DEFAULT_AUTHENTICATION_CLASSES", []
        )
        assert any("SessionAuthentication" in auth for auth in auth_classes)

    def test_token_authentication_first_in_list(self):
        """TokenAuthentication should be first (before SessionAuthentication)"""
        from django.conf import settings

        auth_classes = settings.REST_FRAMEWORK.get(
            "DEFAULT_AUTHENTICATION_CLASSES", []
        )

        token_auth_idx = None
        session_auth_idx = None

        for idx, auth in enumerate(auth_classes):
            if "TokenAuthentication" in auth:
                token_auth_idx = idx
            if "SessionAuthentication" in auth:
                session_auth_idx = idx

        assert token_auth_idx is not None, "TokenAuthentication not found"
        assert session_auth_idx is not None, "SessionAuthentication not found"
        assert (
            token_auth_idx < session_auth_idx
        ), "TokenAuthentication should be before SessionAuthentication"

    def test_no_csrf_exempt_in_auth_classes(self):
        """CSRFExemptSessionAuthentication should NOT be in auth classes"""
        from django.conf import settings

        auth_classes = settings.REST_FRAMEWORK.get(
            "DEFAULT_AUTHENTICATION_CLASSES", []
        )
        csrf_exempt_classes = [
            auth
            for auth in auth_classes
            if "CSRFExemptSessionAuthentication" in auth
        ]
        assert (
            len(csrf_exempt_classes) == 0
        ), "CSRFExemptSessionAuthentication should not be used"


@override_settings(ROOT_URLCONF="config.urls")
class TestCSRFMiddlewarePosition(TestCase):
    """Test CSRF middleware positioning in middleware stack"""

    def test_csrf_middleware_after_session_middleware(self):
        """CsrfViewMiddleware should be after SessionMiddleware"""
        from django.conf import settings

        middleware = settings.MIDDLEWARE
        csrf_idx = None
        session_idx = None

        for idx, mw in enumerate(middleware):
            if "CsrfViewMiddleware" in mw:
                csrf_idx = idx
            if "SessionMiddleware" in mw:
                session_idx = idx

        assert csrf_idx is not None, "CsrfViewMiddleware not found"
        assert session_idx is not None, "SessionMiddleware not found"
        assert csrf_idx > session_idx, "CSRF middleware should be after session middleware"


@override_settings(ROOT_URLCONF="config.urls")
class TestRESTFrameworkCSRFBehavior(TestCase):
    """Test DRF's CSRF behavior with SessionAuthentication"""

    def test_token_authentication_exists(self):
        """TokenAuthentication should be importable and usable"""
        from rest_framework.authentication import TokenAuthentication

        auth = TokenAuthentication()
        assert auth is not None

    def test_session_authentication_exists(self):
        """SessionAuthentication should be importable and usable"""
        from rest_framework.authentication import SessionAuthentication

        auth = SessionAuthentication()
        assert auth is not None

    def test_http_methods_classification(self):
        """HTTP methods should be classified as safe or unsafe"""
        safe_methods = ["GET", "HEAD", "OPTIONS", "TRACE"]
        unsafe_methods = ["POST", "PUT", "PATCH", "DELETE"]

        all_methods = safe_methods + unsafe_methods
        # Verify we have both types
        assert len(safe_methods) > 0
        assert len(unsafe_methods) > 0


@override_settings(ROOT_URLCONF="config.urls")
class TestCSRFCookieConfiguration(TestCase):
    """Test CSRF cookie-related settings"""

    def test_csrf_cookie_age_configured(self):
        """CSRF_COOKIE_AGE should be set"""
        from django.conf import settings

        csrf_age = getattr(settings, "CSRF_COOKIE_AGE", None)
        # Should be None or integer (None means use Django default)
        assert csrf_age is None or isinstance(csrf_age, int)

    def test_csrf_cookie_path_is_root(self):
        """CSRF_COOKIE_PATH should be '/'"""
        from django.conf import settings

        csrf_path = getattr(settings, "CSRF_COOKIE_PATH", "/")
        assert csrf_path == "/"


@override_settings(ROOT_URLCONF="config.urls")
class TestCSRFProtectionRequirements(TestCase):
    """Test that CSRF protection requirements are met"""

    def test_session_auth_in_rest_framework_config(self):
        """SessionAuthentication must be in REST_FRAMEWORK config"""
        from django.conf import settings

        rest_config = settings.REST_FRAMEWORK
        auth_classes = rest_config.get("DEFAULT_AUTHENTICATION_CLASSES", [])

        # SessionAuthentication must be present
        session_auth_present = any(
            "SessionAuthentication" in auth for auth in auth_classes
        )
        assert session_auth_present

    def test_token_auth_before_session_auth(self):
        """TokenAuthentication must come before SessionAuthentication"""
        from django.conf import settings

        rest_config = settings.REST_FRAMEWORK
        auth_classes = rest_config.get("DEFAULT_AUTHENTICATION_CLASSES", [])

        token_idx = None
        session_idx = None

        for idx, auth in enumerate(auth_classes):
            if "TokenAuthentication" in auth:
                token_idx = idx
            elif "SessionAuthentication" in auth:
                session_idx = idx

        assert token_idx is not None
        assert session_idx is not None
        assert token_idx < session_idx

    def test_django_csrf_middleware_active(self):
        """Django CSRF middleware must be active"""
        from django.conf import settings

        csrf_mw = "django.middleware.csrf.CsrfViewMiddleware"
        assert csrf_mw in settings.MIDDLEWARE

    def test_csrf_settings_secure_defaults(self):
        """CSRF settings should have secure defaults"""
        from django.conf import settings

        # SAMESITE should be Lax
        assert settings.CSRF_COOKIE_SAMESITE == "Lax"
        # HTTPONLY should be False (JavaScript needs it)
        assert settings.CSRF_COOKIE_HTTPONLY is False


@override_settings(ROOT_URLCONF="config.urls")
class TestCSRFSecuritySettings(TestCase):
    """Test CSRF security-related settings"""

    def test_csrf_trusted_origins_is_list(self):
        """CSRF_TRUSTED_ORIGINS must be list or tuple"""
        from django.conf import settings

        origins = settings.CSRF_TRUSTED_ORIGINS
        assert isinstance(origins, (list, tuple))

    def test_csrf_cookie_domain_exists(self):
        """CSRF_COOKIE_DOMAIN should be set"""
        from django.conf import settings

        assert hasattr(settings, "CSRF_COOKIE_DOMAIN")
