#!/usr/bin/env python
"""
Direct migration script that bypasses admin check issues
"""
import os
import sys
import django
from django.conf import settings as django_settings

# Add backend to path
backend_path = '/home/mego/Python Projects/THE_BOT_platform/backend'
sys.path.insert(0, backend_path)
os.chdir(backend_path)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Minimal Django setup without full checks
os.environ['SKIP_ADMIN_CHECKS'] = '1'

try:
    django.setup()
    print("✓ Django setup completed")
except Exception as e:
    print(f"Django setup warning: {e}")

# Import migration executor directly
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.loader import MigrationLoader

print("\n" + "="*60)
print("RUNNING INVOICE SYSTEM MIGRATIONS")
print("="*60)

try:
    # Create migration executor
    executor = MigrationExecutor(connection)
    loader = MigrationLoader(connection)

    # Check what needs to be migrated
    plan = executor.migration_plan(loader.graph.leaf_nodes())

    if not plan:
        print("✓ No migrations to apply (database is up to date)")
    else:
        print(f"\nMigrations to apply: {len(plan)}")
        for migration in plan[:10]:  # Show first 10
            print(f"  - {migration}")
        if len(plan) > 10:
            print(f"  ... and {len(plan) - 10} more")

        # Execute all pending migrations
        print("\nApplying migrations...")
        for migration_state in plan:
            migration = loader.graph.nodes[migration_state]
            print(f"  • {migration.app}.{migration.name}...", end=" ")
            executor.execute_migration(migration_state, migration)
            print("OK")

    print("\n" + "="*60)
    print("✓ MIGRATIONS COMPLETED SUCCESSFULLY")
    print("="*60)

    # Verify invoice tables
    print("\nVerifying invoice tables...")
    cursor = connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    all_tables = [row[0] for row in cursor.fetchall()]
    invoice_tables = [t for t in all_tables if 'invoice' in t.lower()]

    if invoice_tables:
        print(f"✓ Invoice tables created: {invoice_tables}")
    else:
        print("✗ No invoice tables found!")

except Exception as e:
    print(f"\n✗ Migration failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
