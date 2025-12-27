# Generated migration for access control models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reports', '0010_add_composite_indexes_optimization'),
    ]

    operations = [
        migrations.CreateModel(
            name='ReportAccessToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(db_index=True, max_length=64, unique=True, verbose_name='Access Token')),
                ('status', models.CharField(choices=[('active', 'Active'), ('expired', 'Expired'), ('revoked', 'Revoked')], default='active', max_length=20, verbose_name='Status')),
                ('expires_at', models.DateTimeField(help_text='Token becomes inactive after this time', verbose_name='Expires At')),
                ('access_count', models.PositiveIntegerField(default=0, verbose_name='Access Count')),
                ('max_accesses', models.PositiveIntegerField(blank=True, help_text='Limit token usage, null means unlimited', null=True, verbose_name='Max Accesses')),
                ('last_accessed_at', models.DateTimeField(blank=True, null=True, verbose_name='Last Accessed At')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_access_tokens', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='access_tokens', to='reports.report', verbose_name='Report')),
            ],
            options={
                'verbose_name': 'Report Access Token',
                'verbose_name_plural': 'Report Access Tokens',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='ReportAccessAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('access_type', models.CharField(choices=[('view', 'Viewed'), ('download', 'Downloaded'), ('share', 'Shared'), ('print', 'Printed'), ('export', 'Exported')], default='view', max_length=20, verbose_name='Access Type')),
                ('access_method', models.CharField(choices=[('direct', 'Direct Access'), ('token_link', 'Temporary Link'), ('shared_access', 'Shared Access'), ('role_based', 'Role-Based Access')], default='direct', max_length=50, verbose_name='Access Method')),
                ('session_id', models.CharField(blank=True, max_length=100, verbose_name='Session ID')),
                ('ip_address', models.GenericIPAddressField(verbose_name='IP Address')),
                ('user_agent', models.TextField(blank=True, verbose_name='User Agent')),
                ('access_duration_seconds', models.PositiveIntegerField(default=0, verbose_name='Access Duration (seconds)')),
                ('metadata', models.JSONField(blank=True, default=dict, help_text='Custom data like device info, referer, etc.', verbose_name='Additional Metadata')),
                ('accessed_at', models.DateTimeField(auto_now_add=True, verbose_name='Accessed At')),
                ('accessed_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='report_access_logs', to=settings.AUTH_USER_MODEL, verbose_name='Accessed By')),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='access_logs', to='reports.report', verbose_name='Report')),
            ],
            options={
                'verbose_name': 'Report Access Audit Log',
                'verbose_name_plural': 'Report Access Audit Logs',
                'ordering': ['-accessed_at'],
            },
        ),
        migrations.CreateModel(
            name='ReportSharing',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('share_type', models.CharField(choices=[('user', 'Shared with User'), ('role', 'Shared with Role'), ('link', 'Shared via Link')], default='user', max_length=20, verbose_name='Share Type')),
                ('shared_role', models.CharField(blank=True, choices=[('student', 'Student'), ('teacher', 'Teacher'), ('tutor', 'Tutor'), ('parent', 'Parent'), ('admin', 'Admin')], max_length=20, verbose_name='Shared Role')),
                ('permission', models.CharField(choices=[('view', 'Can View'), ('view_download', 'Can View & Download'), ('view_download_export', 'Can View, Download & Export')], default='view', max_length=50, verbose_name='Permission')),
                ('expires_at', models.DateTimeField(blank=True, null=True, verbose_name='Expires At')),
                ('is_active', models.BooleanField(default=True, verbose_name='Is Active')),
                ('share_message', models.TextField(blank=True, verbose_name='Share Message')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sharings', to='reports.report', verbose_name='Report')),
                ('shared_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_report_sharings', to=settings.AUTH_USER_MODEL, verbose_name='Shared By')),
                ('shared_with_user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='received_report_sharings', to=settings.AUTH_USER_MODEL, verbose_name='Shared With User')),
            ],
            options={
                'verbose_name': 'Report Sharing',
                'verbose_name_plural': 'Report Sharings',
                'ordering': ['-created_at'],
                'unique_together': {('report', 'shared_with_user', 'shared_role')},
            },
        ),
        migrations.AddIndex(
            model_name='reportsharing',
            index=models.Index(fields=['report', 'is_active'], name='reports_rep_report_8f2c4a_idx'),
        ),
        migrations.AddIndex(
            model_name='reportsharing',
            index=models.Index(fields=['shared_with_user', 'is_active'], name='reports_rep_shared_a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='reportsharing',
            index=models.Index(fields=['share_type', 'shared_role'], name='reports_rep_share__d4e5f6_idx'),
        ),
        migrations.AddIndex(
            model_name='reportsharing',
            index=models.Index(fields=['expires_at'], name='reports_rep_expires_g7h8i9_idx'),
        ),
        migrations.AddIndex(
            model_name='reportaccessauditlog',
            index=models.Index(fields=['report', '-accessed_at'], name='reports_rep_report_a1b2c3_idx'),
        ),
        migrations.AddIndex(
            model_name='reportaccessauditlog',
            index=models.Index(fields=['accessed_by', '-accessed_at'], name='reports_rep_accesse_d4e5f6_idx'),
        ),
        migrations.AddIndex(
            model_name='reportaccessauditlog',
            index=models.Index(fields=['access_type', '-accessed_at'], name='reports_rep_access__g7h8i9_idx'),
        ),
        migrations.AddIndex(
            model_name='reportaccessauditlog',
            index=models.Index(fields=['access_method'], name='reports_rep_access_j0k1l2_idx'),
        ),
        migrations.AddIndex(
            model_name='reportaccessauditlog',
            index=models.Index(fields=['ip_address'], name='reports_rep_ip_addr_m3n4o5_idx'),
        ),
        migrations.AddIndex(
            model_name='reportaccesstoken',
            index=models.Index(fields=['token'], name='reports_rep_token_p6q7r8_idx'),
        ),
        migrations.AddIndex(
            model_name='reportaccesstoken',
            index=models.Index(fields=['report', 'status'], name='reports_rep_report_s9t0u1_idx'),
        ),
        migrations.AddIndex(
            model_name='reportaccesstoken',
            index=models.Index(fields=['created_by', 'status'], name='reports_rep_created_v2w3x4_idx'),
        ),
        migrations.AddIndex(
            model_name='reportaccesstoken',
            index=models.Index(fields=['expires_at', 'status'], name='reports_rep_expires_y5z6a7_idx'),
        ),
    ]
