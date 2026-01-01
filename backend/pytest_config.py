"""
Configuration for pytest tests
"""
import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ.setdefault('ENVIRONMENT', 'test')

if not settings.configured:
    django.setup()
