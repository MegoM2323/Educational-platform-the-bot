# Generated manually to resolve migration conflict
# Merges 0004_auto_20251026_0956 with 0009_studyplan
# 
# This migration resolves the conflict between:
# - 0004_auto_20251026_0956 (recreated as placeholder)
# - 0009_studyplan (current leaf node)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        # Depend on both conflicting leaf nodes
        ('materials', '0004_auto_20251026_0956'),  # Recreated placeholder
        ('materials', '0009_studyplan'),  # The other leaf node
    ]

    operations = [
        # Empty merge migration - just resolves the conflict in the migration graph
        # The actual database state is already correct since both migrations were applied
    ]

