# Empty migration to restore migration chain

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("invoices", "0002_fix_partial_indexes"),
    ]

    operations = []
