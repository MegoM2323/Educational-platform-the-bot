# Generated manually on 2025-12-27

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0005_add_tutor_to_student_report'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # Add parent report sharing fields to StudentReport
        migrations.AddField(
            model_name='studentreport',
            name='show_to_parent',
            field=models.BooleanField(default=True, verbose_name='Показывать родителю'),
        ),
        migrations.AddField(
            model_name='studentreport',
            name='parent_acknowledged',
            field=models.BooleanField(default=False, verbose_name='Родитель подтвердил'),
        ),
        migrations.AddField(
            model_name='studentreport',
            name='parent_acknowledged_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Дата подтверждения родителем'),
        ),
        # Create ParentReportPreference model
        migrations.CreateModel(
            name='ParentReportPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('notify_on_report_created', models.BooleanField(default=True, verbose_name='Уведомление при создании отчета')),
                ('notify_on_grade_posted', models.BooleanField(default=True, verbose_name='Уведомление при выставлении оценки')),
                ('show_grades', models.BooleanField(default=True, verbose_name='Показывать оценки')),
                ('show_progress', models.BooleanField(default=True, verbose_name='Показывать прогресс')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('parent', models.OneToOneField(limit_choices_to={'role': 'parent'}, on_delete=django.db.models.deletion.CASCADE, related_name='report_preferences', to=settings.AUTH_USER_MODEL, verbose_name='Родитель')),
            ],
            options={
                'verbose_name': 'Настройки отчетов родителя',
                'verbose_name_plural': 'Настройки отчетов родителей',
            },
        ),
    ]
