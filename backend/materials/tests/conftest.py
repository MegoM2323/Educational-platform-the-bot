import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

if not settings.configured:
    django.setup()

import pytest
from rest_framework.test import APIClient


@pytest.fixture(scope="session")
def django_db_setup():
    """Setup test database"""
    pass


@pytest.fixture
def api_client():
    """Provide API client for tests"""
    return APIClient()
