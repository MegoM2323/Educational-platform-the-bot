# Migration to fix enrollment field reference issue in invoices
from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('invoices', '0004_remove_invoice_check_invoice_amount_positive'),
        ('materials', '0001_initial'),  # Ensure materials.SubjectEnrollment exists
    ]

    operations = [
        # No operations needed - just ensuring dependency order
    ]
