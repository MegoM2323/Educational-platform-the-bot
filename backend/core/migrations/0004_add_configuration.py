# Generated migration for Configuration model

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0003_auditlog'),
    ]

    operations = [
        migrations.CreateModel(
            name='Configuration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.CharField(db_index=True, max_length=255, unique=True, verbose_name='Configuration Key')),
                ('value', models.JSONField(blank=True, default=None, null=True, verbose_name='Value')),
                ('value_type', models.CharField(choices=[('string', 'String'), ('integer', 'Integer'), ('boolean', 'Boolean'), ('list', 'List'), ('json', 'JSON')], default='string', max_length=20, verbose_name='Value Type')),
                ('description', models.TextField(blank=True, help_text='What this configuration does', verbose_name='Description')),
                ('group', models.CharField(blank=True, db_index=True, max_length=100, verbose_name='Configuration Group')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='config_changes', to=settings.AUTH_USER_MODEL, verbose_name='Updated By')),
            ],
            options={
                'verbose_name': 'Configuration',
                'verbose_name_plural': 'Configurations',
                'db_table': 'core_configuration',
                'ordering': ['group', 'key'],
            },
        ),
        migrations.AddIndex(
            model_name='configuration',
            index=models.Index(fields=['group', 'key'], name='core_configu_group_key_idx'),
        ),
        migrations.AddIndex(
            model_name='configuration',
            index=models.Index(fields=['updated_at'], name='core_configu_updated_idx'),
        ),
    ]
