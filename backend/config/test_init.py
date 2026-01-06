"""
Test environment initialization.
This module is imported BEFORE settings.py is fully evaluated.
Use it to set up test-specific configuration.
"""
import os
import sys

if 'pytest' in sys.modules or 'test' in sys.argv:
    os.environ['ENVIRONMENT'] = 'test'
    os.environ['DB_NAME'] = 'test_thebot_db'
    os.environ['DB_HOST'] = 'localhost'
    os.environ['DB_USER'] = 'postgres'
    os.environ['DB_PASSWORD'] = 'postgres'
    os.environ['DB_PORT'] = '5432'
    os.environ['DB_SSLMODE'] = 'disable'
