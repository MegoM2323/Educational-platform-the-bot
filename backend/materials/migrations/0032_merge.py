# Generated migration to merge conflicting migrations

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('materials', '0030_add_progress_audit_trail'),
        ('materials', '0030_create_submission_file_model'),
        ('materials', '0031_add_bulk_assignment_audit_log'),
        ('materials', '0013_alter_subjectpayment_unique_together'),
    ]

    operations = [
    ]
