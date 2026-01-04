# Generated migration to fix dependencies

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('invoices', '0006_invoice_enrollment_and_more'),
        ('knowledge_graph', '0001_initial'),
        ('reports', '0003_teacherweeklyreport_tutorweeklyreport'),
    ]

    operations = [
    ]
