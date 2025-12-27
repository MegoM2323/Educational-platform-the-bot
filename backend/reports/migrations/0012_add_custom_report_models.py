# Generated migration for CustomReport models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('reports', '0011_add_access_control_models'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='User-friendly name for the report', max_length=255, verbose_name='Report Name')),
                ('description', models.TextField(blank=True, help_text='Detailed description of what the report shows', verbose_name='Description')),
                ('is_shared', models.BooleanField(default=False, help_text='If true, other teachers can use/clone this report', verbose_name='Is Shared')),
                ('config', models.JSONField(default=dict, help_text='JSON config with fields, filters, chart_type, etc.', verbose_name='Report Configuration')),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('archived', 'Archived')], default='draft', max_length=20, verbose_name='Status')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deleted_at', models.DateTimeField(blank=True, null=True, verbose_name='Deleted At')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_custom_reports', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
                ('shared_with', models.ManyToManyField(blank=True, limit_choices_to={'role': 'teacher'}, related_name='shared_custom_reports', to=settings.AUTH_USER_MODEL, verbose_name='Shared With')),
            ],
            options={
                'verbose_name': 'Custom Report',
                'verbose_name_plural': 'Custom Reports',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CustomReportExecution',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rows_returned', models.IntegerField(default=0, verbose_name='Rows Returned')),
                ('execution_time_ms', models.IntegerField(default=0, verbose_name='Execution Time (ms)')),
                ('result_summary', models.JSONField(default=dict, verbose_name='Result Summary')),
                ('executed_at', models.DateTimeField(auto_now_add=True)),
                ('executed_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='report_executions', to=settings.AUTH_USER_MODEL, verbose_name='Executed By')),
                ('report', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='executions', to='reports.customreport', verbose_name='Report')),
            ],
            options={
                'verbose_name': 'Custom Report Execution',
                'verbose_name_plural': 'Custom Report Executions',
                'ordering': ['-executed_at'],
            },
        ),
        migrations.CreateModel(
            name='CustomReportBuilderTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Template Name')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('template_type', models.CharField(choices=[('class_progress', 'Class Progress'), ('student_grades', 'Student Grades'), ('assignment_analysis', 'Assignment Analysis'), ('attendance', 'Attendance Report'), ('engagement', 'Student Engagement')], max_length=50, verbose_name='Template Type')),
                ('base_config', models.JSONField(default=dict, verbose_name='Base Configuration')),
                ('is_system', models.BooleanField(default=False, verbose_name='Is System Template')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='custom_report_templates', to=settings.AUTH_USER_MODEL, verbose_name='Created By')),
            ],
            options={
                'verbose_name': 'Custom Report Builder Template',
                'verbose_name_plural': 'Custom Report Builder Templates',
                'ordering': ['template_type', 'name'],
            },
        ),
        migrations.AddIndex(
            model_name='customreport',
            index=models.Index(fields=['created_by', 'status'], name='reports_cus_created_98a7e8_idx'),
        ),
        migrations.AddIndex(
            model_name='customreport',
            index=models.Index(fields=['is_shared', 'deleted_at'], name='reports_cus_is_shar_7f4c2a_idx'),
        ),
        migrations.AddIndex(
            model_name='customreportexecution',
            index=models.Index(fields=['report', '-executed_at'], name='reports_cus_report__3f2c1e_idx'),
        ),
        migrations.AddIndex(
            model_name='customreportexecution',
            index=models.Index(fields=['executed_by', '-executed_at'], name='reports_cus_execute_4a5b6d_idx'),
        ),
    ]
