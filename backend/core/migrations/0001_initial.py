# Generated manually for core models

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='FailedTask',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_id', models.CharField(db_index=True, max_length=255, unique=True)),
                ('task_name', models.CharField(db_index=True, max_length=255)),
                ('status', models.CharField(choices=[('failed', 'Failed'), ('investigating', 'Investigating'), ('resolved', 'Resolved'), ('ignored', 'Ignored')], db_index=True, default='failed', max_length=20)),
                ('error_message', models.TextField()),
                ('error_type', models.CharField(max_length=255)),
                ('traceback', models.TextField(blank=True)),
                ('retry_count', models.IntegerField(default=0)),
                ('is_transient', models.BooleanField(default=False)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('failed_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('investigated_at', models.DateTimeField(blank=True, null=True)),
                ('resolved_at', models.DateTimeField(blank=True, null=True)),
                ('investigation_notes', models.TextField(blank=True)),
                ('resolution_notes', models.TextField(blank=True)),
            ],
            options={
                'db_table': 'core_failed_task',
                'ordering': ['-failed_at'],
            },
        ),
        migrations.CreateModel(
            name='TaskExecutionLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('task_id', models.CharField(db_index=True, max_length=255)),
                ('task_name', models.CharField(db_index=True, max_length=255)),
                ('status', models.CharField(choices=[('success', 'Success'), ('failed', 'Failed'), ('retrying', 'Retrying')], db_index=True, default='success', max_length=20)),
                ('started_at', models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('duration_seconds', models.FloatField(blank=True, null=True)),
                ('retry_count', models.IntegerField(default=0)),
                ('result', models.JSONField(blank=True, default=dict)),
                ('error_message', models.TextField(blank=True)),
            ],
            options={
                'db_table': 'core_task_execution_log',
                'ordering': ['-started_at'],
            },
        ),
        migrations.AddIndex(
            model_name='failedtask',
            index=models.Index(fields=['task_name', 'status'], name='core_failed_task_na_6c8b65_idx'),
        ),
        migrations.AddIndex(
            model_name='failedtask',
            index=models.Index(fields=['failed_at', 'status'], name='core_failed_failed__a3e6b8_idx'),
        ),
        migrations.AddIndex(
            model_name='taskexecutionlog',
            index=models.Index(fields=['task_name', 'status', 'started_at'], name='core_task_e_task_na_eb8f45_idx'),
        ),
    ]
