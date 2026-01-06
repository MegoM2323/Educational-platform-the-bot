#!/usr/bin/env python
"""
Create admin user for E2E testing
Usage: python manage.py shell < backend/scripts/development/create_admin_for_e2e.py
"""

import os
import sys
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Create admin user
admin_username = 'admin_test'
admin_email = 'admin@test.com'
admin_password = 'AdminTest123!'

try:
    # Check if admin already exists
    if User.objects.filter(username=admin_username).exists():
        print(f"Admin user '{admin_username}' already exists")
        admin = User.objects.get(username=admin_username)
    else:
        # Create superuser
        admin = User.objects.create_superuser(
            username=admin_username,
            email=admin_email,
            password=admin_password,
            first_name='Admin',
            last_name='Test',
        )
        print(f"Created admin user: {admin_username}")

    print(f"Admin user '{admin_username}' is ready")
    print(f"  Email: {admin_email}")
    print(f"  Password: {admin_password}")
    print(f"  Is staff: {admin.is_staff}")
    print(f"  Is superuser: {admin.is_superuser}")

except Exception as e:
    print(f"Error: {e}")
    sys.exit(1)
