# Generated migration for BulkAssignmentAuditLog model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('materials', '0030_add_progress_audit_trail'),
    ]

    operations = [
        migrations.CreateModel(
            name='BulkAssignmentAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('operation_type', models.CharField(
                    choices=[
                        ('bulk_assign_to_students', 'Bulk Assign Material to Students'),
                        ('bulk_assign_materials', 'Bulk Assign Materials to Student'),
                        ('bulk_assign_to_class', 'Bulk Assign Materials to Class'),
                        ('bulk_remove', 'Bulk Remove Assignments'),
                        ('bulk_update', 'Bulk Update Material Properties'),
                        ('bulk_delete', 'Bulk Delete Materials'),
                    ],
                    max_length=50,
                    verbose_name='Operation Type'
                )),
                ('status', models.CharField(
                    choices=[
                        ('processing', 'Processing'),
                        ('completed', 'Completed'),
                        ('partial_failure', 'Partial Failure'),
                        ('failed', 'Failed'),
                    ],
                    default='processing',
                    max_length=20,
                    verbose_name='Status'
                )),
                ('total_items', models.IntegerField(default=0, verbose_name='Total Items')),
                ('created_count', models.IntegerField(default=0, verbose_name='Created')),
                ('skipped_count', models.IntegerField(default=0, verbose_name='Skipped')),
                ('failed_count', models.IntegerField(default=0, verbose_name='Failed')),
                ('failed_items', models.JSONField(blank=True, default=list, verbose_name='Failed Items')),
                ('error_message', models.TextField(blank=True, null=True, verbose_name='Error Message')),
                ('metadata', models.JSONField(blank=True, default=dict, verbose_name='Metadata')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='Completed At')),
                ('duration_seconds', models.FloatField(default=0, verbose_name='Duration (seconds)')),
                ('performed_by', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='bulk_assignment_logs', to=settings.AUTH_USER_MODEL, verbose_name='Performed By')),
            ],
            options={
                'verbose_name': 'Bulk Assignment Audit Log',
                'verbose_name_plural': 'Bulk Assignment Audit Logs',
                'app_label': 'materials',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='bulkassignmentauditlog',
            index=models.Index(fields=['performed_by', '-created_at'], name='materials_bu_perform_idx'),
        ),
        migrations.AddIndex(
            model_name='bulkassignmentauditlog',
            index=models.Index(fields=['operation_type', '-created_at'], name='materials_bu_operati_idx'),
        ),
        migrations.AddIndex(
            model_name='bulkassignmentauditlog',
            index=models.Index(fields=['status'], name='materials_bu_status_idx'),
        ),
    ]
