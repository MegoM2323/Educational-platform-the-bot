from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_rename_core_audit_log_user_timestamp_idx_core_audit__user_id_66db5a_idx_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='auditlog',
            name='action',
            field=models.CharField(
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
                    ('admin_create', 'Admin Create'),
                    ('admin_update', 'Admin Update'),
                    ('admin_delete', 'Admin Delete'),
                    ('admin_reset_password', 'Admin Reset Password'),
                    ('data_export', 'Data Export'),
                    ('data_import', 'Data Import'),
                    ('error', 'Error'),
                ],
                db_index=True,
                max_length=50,
                verbose_name='Action',
            ),
        ),
    ]
