"""
Root conftest for pytest
"""
import os
import sys
import django
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
