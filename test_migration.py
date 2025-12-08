#!/usr/bin/env python
"""
Direct migration test script for invoice system
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
sys.path.insert(0, '/home/mego/Python Projects/THE_BOT_platform/backend')

# Disable admin checks to avoid the autocomplete_fields issue
from django.core.management.base import SystemCheckError

try:
    django.setup()
except SystemCheckError as e:
    print(f"WARNING: System checks failed (ignoring admin issues): {e}")
except Exception as e:
    print(f"Django setup error: {e}")

# Now run migrations
from django.core.management import call_command

try:
    print("Testing invoice migration...")
    call_command('migrate', 'invoices', verbosity=2)
    print("\n✓ Migration completed successfully!")
except Exception as e:
    print(f"✗ Migration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Verify tables exist
print("\nVerifying invoice tables...")
from django.db import connection

cursor = connection.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'invoices_%'")
tables = cursor.fetchall()
print(f"Invoice tables created: {tables}")

# List migration status
print("\nInvoice app migration status:")
call_command('showmigrations', 'invoices')
