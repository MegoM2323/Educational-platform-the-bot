"""
Root conftest for pytest
"""
import os
import sys
import django
import pytest
from pathlib import Path

# Set environment before Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ.setdefault('ENVIRONMENT', 'test')

# Add backend to path
backend_path = Path(__file__).parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

# Setup Django
django.setup()

# Import fixtures AFTER Django setup
from rest_framework.test import APIClient
from tests.fixtures.auth import *  # noqa
from tests.fixtures.mocks import *  # noqa


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


@pytest.fixture(scope='session')
def django_db_setup(django_db_blocker):
    """Configure test database settings"""
    with django_db_blocker.unblock():
        pass
    yield


# ========== PYTEST CONFIGURATION ==========

def pytest_configure(config):
    """Configure pytest markers and settings"""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "api: marks tests as API endpoint tests"
    )
