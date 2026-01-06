import pytest
import django
from django.conf import settings

@pytest.fixture(scope="session")
def django_db_setup():
    """Setup test database"""
    pass
