import os
import django
from django.conf import settings

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Setup Django before importing any Django modules
if not settings.configured:
    django.setup()

import pytest


@pytest.fixture(scope="session")
def django_db_setup():
    """Setup test database"""
    pass


@pytest.fixture
def api_client():
    """Provide API client for tests"""
    from rest_framework.test import APIClient
    return APIClient()
