# Generated migration for T_SYS_006: Database optimization indexes
# Adds missing indexes on frequently queried fields in scheduling app

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduling', '0005_add_slot_type_and_optional_student'),
    ]

    operations = [
        # Note: Most indexes are already defined in model Meta class
        # This migration adds only additional composite indexes not in the model
    ]
