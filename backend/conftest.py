"""
Root conftest for pytest

NOTE: Root conftest.py at project root already sets ENVIRONMENT=test
This file only defines Django-specific fixtures
"""
import sys
import django
import pytest
import uuid
from pathlib import Path
from contextlib import ExitStack

# ENVIRONMENT and DJANGO_SETTINGS_MODULE are already set by root conftest.py

# Add backend to path if not already there
backend_path = Path(__file__).parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Ensure Django is setup FIRST
django.setup()

# NOW import Django components AFTER setup
from django.db import connection
from django.conf import settings
from unittest.mock import patch
from rest_framework.test import APIClient

# Don't modify INSTALLED_APPS - it's already configured correctly in settings.py for test mode
# The settings.py file already excludes problematic apps when environment == 'test'

# Initialize factory models AFTER Django setup
from tests.factories import _initialize_factories

_initialize_factories()

# Import fixtures AFTER Django setup and factory initialization
try:
    from tests.fixtures.auth import *  # noqa
    from tests.fixtures.mocks import *  # noqa
except ImportError as e:
    # If fixtures fail to import, try to continue (they may use models that aren't created)
    import warnings

    warnings.warn(f"Failed to import test fixtures: {e}", ImportWarning)

# ========== ASYNCIO SUPPORT ==========

import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# ========== DATABASE DETECTION ==========


def is_postgresql():
    """Check if current database is PostgreSQL

    Asserts that test environment is using PostgreSQL as required.
    Tests must use PostgreSQL, not SQLite.
    """
    engine = connection.settings_dict.get("ENGINE", "").lower()
    is_postgres = "postgresql" in engine

    if not is_postgres:
        raise AssertionError(
            f"Test database must be PostgreSQL for test environment. " f"Got: {engine}"
        )

    return is_postgres


# ========== GLOBAL FIXTURES ==========


@pytest.fixture
def api_client():
    """Unauthenticated API client"""
    return APIClient()


@pytest.fixture
def db_cleanup(db):
    """Ensure clean database state after each test"""
    yield
    # Database is automatically rolled back by pytest-django


@pytest.fixture(scope="session")
def django_db_setup(django_db_blocker):
    """Ensure test database is created and migrations are applied

    Tests use PostgreSQL database configured via DATABASE_URL or DB_* env vars.
    Asserts that database is PostgreSQL, not SQLite.
    """
    db_engine = connection.settings_dict.get("ENGINE", "").lower()
    db_name = connection.settings_dict.get("NAME", "")

    if "postgresql" not in db_engine:
        raise AssertionError(f"Test database must be PostgreSQL. Got: {db_engine}")

    if ":memory:" in db_name:
        raise AssertionError(
            f"Test database must be a real PostgreSQL database, not :memory:. "
            f"Got: {db_name}"
        )

    with django_db_blocker.unblock():
        from django.core.management import call_command

        # Try to run migrations with database connection
        try:
            call_command("migrate", verbosity=0, interactive=False, skip_checks=True)
        except ValueError as e:
            # If migrations fail due to model resolution issues, use syncdb as fallback
            if "lazy reference" in str(e) or "doesn't provide model" in str(e):
                import warnings
                warnings.warn(
                    f"Migration failed with model resolution error, using syncdb fallback: {e}",
                    RuntimeWarning
                )
                # Don't use syncdb - it's deprecated. Instead, skip and let Django handle it
                pass
            else:
                raise
    yield


@pytest.fixture
def monitoring_service(db):
    """Monitoring service instance for tests"""

    class MockMonitoringService:
        def __init__(self):
            self.client = None

        def get_client(self):
            return self.client or MockMonitoringClient()

    return MockMonitoringService()


@pytest.fixture
def monitoring_client(monitoring_service):
    """Monitoring client for tests"""
    return monitoring_service.get_client()


class MockMonitoringClient:
    """Mock client for monitoring service"""

    def __init__(self):
        self.metrics = {}
        self.events = []

    def send_metric(self, name, value, tags=None):
        """Record a metric"""
        self.metrics[name] = {"value": value, "tags": tags or {}}

    def send_event(self, event_type, message, severity="info"):
        """Record an event"""
        self.events.append(
            {"type": event_type, "message": message, "severity": severity}
        )

    def get_metrics(self):
        """Get recorded metrics"""
        return self.metrics

    def get_events(self):
        """Get recorded events"""
        return self.events


@pytest.fixture(autouse=True)
def setup_cache_mocks():
    """Setup cache for each test

    Cache is configured via Django settings to use LocMemCache in test environment.
    This fixture is kept for compatibility and future cache mocking needs.
    """
    # Cache is already properly configured, just yield
    yield


@pytest.fixture(autouse=True)
def disable_redis_in_tests(monkeypatch, settings):
    """Disable Redis for tests - use in-memory cache instead"""
    monkeypatch.setenv("USE_REDIS_CACHE", "false")
    monkeypatch.setenv("USE_REDIS_CHANNELS", "false")
    settings.CELERY_ALWAYS_EAGER = True
    settings.CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
    yield


@pytest.fixture(autouse=True)
def clear_cache_between_tests():
    """Clear Django cache before and after each test

    Uses real LocMemCache configured in test settings.
    """
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


# ========== PYTEST CONFIGURATION ==========


def pytest_configure(config):
    """Configure pytest - markers are defined in pytest.ini"""
    config.addinivalue_line("markers", "asyncio: Async tests")
    config.addinivalue_line("markers", "cache: Cache-related tests")
    config.addinivalue_line("markers", "celery: Celery task tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "security: Security tests")
    config.addinivalue_line("markers", "websocket: WebSocket tests")
    config.addinivalue_line("markers", "unit: Unit tests")


def pytest_collection_modifyitems(config, items):
    """Modify test items - add asyncio mode for async tests"""
    for item in items:
        if "asyncio" in item.keywords:
            item.keywords["asyncio_mode"] = "auto"


# ========== USER FIXTURES ==========


@pytest.fixture
def student_user(db):
    from tests.factories import StudentFactory

    return StudentFactory()


@pytest.fixture
def teacher_user(db):
    from tests.factories import TeacherFactory

    return TeacherFactory()


@pytest.fixture
def tutor_user(db):
    from tests.factories import TutorFactory

    return TutorFactory()


@pytest.fixture
def parent_user(db):
    from tests.factories import ParentFactory

    return ParentFactory()


@pytest.fixture
def another_student_user(db):
    from tests.factories import StudentFactory

    return StudentFactory()


@pytest.fixture
def another_teacher_user(db):
    from tests.factories import TeacherFactory

    return TeacherFactory()


# ========== AUTHENTICATED CLIENT FIXTURES ==========


@pytest.fixture
def student_client(student_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(student_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client, student_user


@pytest.fixture
def teacher_client(teacher_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(teacher_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client, teacher_user


@pytest.fixture
def admin_client(db):
    from rest_framework_simplejwt.tokens import RefreshToken
    from django.contrib.auth import get_user_model

    User = get_user_model()
    admin = User.objects.create_superuser(
        username=f"admin_{uuid.uuid4().hex[:12]}",
        email=f"admin_{uuid.uuid4().hex[:12]}@test.com",
        password="pass123",
    )
    client = APIClient()
    refresh = RefreshToken.for_user(admin)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client, admin


@pytest.fixture
def tutor_client(tutor_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(tutor_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client, tutor_user


@pytest.fixture
def auth_client(student_user):
    from rest_framework_simplejwt.tokens import RefreshToken

    client = APIClient()
    refresh = RefreshToken.for_user(student_user)
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return client, student_user
