# Generated migration for AuditLog model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0002_rename_core_failed_task_na_6c8b65_idx_core_failed_task_na_0a7b09_idx_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(
                    choices=[
                        ('login', 'Login'),
                        ('logout', 'Logout'),
                        ('view_material', 'View Material'),
                        ('download_material', 'Download Material'),
                        ('submit_assignment', 'Submit Assignment'),
                        ('view_assignment', 'View Assignment'),
                        ('create_material', 'Create Material'),
                        ('edit_material', 'Edit Material'),
                        ('delete_material', 'Delete Material'),
                        ('grade_assignment', 'Grade Assignment'),
                        ('create_chat', 'Create Chat'),
                        ('send_message', 'Send Message'),
                        ('view_chat', 'View Chat'),
                        ('delete_message', 'Delete Message'),
                        ('create_invoice', 'Create Invoice'),
                        ('process_payment', 'Process Payment'),
                        ('view_report', 'View Report'),
                        ('export_report', 'Export Report'),
                        ('create_knowledge_graph', 'Create Knowledge Graph'),
                        ('update_knowledge_graph', 'Update Knowledge Graph'),
                        ('user_update', 'User Update'),
                        ('role_change', 'Role Change'),
                        ('password_change', 'Password Change'),
                        ('permission_change', 'Permission Change'),
                        ('api_call', 'API Call'),
                        ('admin_action', 'Admin Action'),
                        ('data_export', 'Data Export'),
                        ('data_import', 'Data Import'),
                        ('error', 'Error'),
                    ],
                    db_index=True,
                    max_length=50,
                    verbose_name='Action'
                )),
                ('target_type', models.CharField(blank=True, help_text='Type of object affected (material, assignment, user, etc.)', max_length=50, verbose_name='Target Type')),
                ('target_id', models.IntegerField(blank=True, help_text='ID of the object affected', null=True, verbose_name='Target ID')),
                ('ip_address', models.GenericIPAddressField(help_text='Client IP address', verbose_name='IP Address')),
                ('user_agent', models.CharField(help_text='Browser/client user-agent string', max_length=500, verbose_name='User-Agent')),
                ('metadata', models.JSONField(blank=True, default=dict, help_text='Additional context in JSON format', verbose_name='Metadata')),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Timestamp')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to=settings.AUTH_USER_MODEL, db_index=True, verbose_name='User')),
            ],
            options={
                'verbose_name': 'Audit Log',
                'verbose_name_plural': 'Audit Logs',
                'db_table': 'core_audit_log',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['user', 'timestamp'], name='core_audit_log_user_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['action', 'timestamp'], name='core_audit_log_action_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['ip_address', 'timestamp'], name='core_audit_log_ip_address_timestamp_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['target_type', 'target_id'], name='core_audit_log_target_type_target_id_idx'),
        ),
    ]
