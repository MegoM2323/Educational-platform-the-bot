import os
import sys

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

os.environ['ENVIRONMENT'] = 'test'
os.environ['DB_NAME'] = 'test_thebot_db'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_USER'] = 'postgres'
os.environ['DB_PASSWORD'] = 'postgres'
os.environ['DB_PORT'] = '5432'
os.environ['DB_SSLMODE'] = 'disable'

import django
from django.conf import settings

if not settings.configured:
    django.setup()
else:
    db_config = settings.DATABASES['default'].copy()
    db_config['NAME'] = 'test_thebot_db'
    settings.DATABASES['default'] = db_config
