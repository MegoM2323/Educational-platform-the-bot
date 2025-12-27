# Generated migration for late submission handling (T_ASN_007)

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('assignments', '0016_add_assignment_attempt_model'),
    ]

    operations = [
        migrations.CreateModel(
            name='StudentDeadlineExtension',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('extended_deadline', models.DateTimeField(help_text='Новый срок сдачи для этого студента', verbose_name='Новый срок сдачи')),
                ('reason', models.TextField(blank=True, help_text='Объяснение причины расширения срока', verbose_name='Причина расширения')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Обновлено')),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deadline_extensions', to='assignments.assignment', verbose_name='Задание')),
                ('extended_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='granted_extensions', to=settings.AUTH_USER_MODEL, verbose_name='Расширено')),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='deadline_extensions', to=settings.AUTH_USER_MODEL, verbose_name='Студент')),
            ],
            options={
                'verbose_name': 'Расширение сроков',
                'verbose_name_plural': 'Расширения сроков',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='studentdeadlineextension',
            index=models.Index(
                fields=['assignment', 'student'],
                name='deadline_ext_assignment_student_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='studentdeadlineextension',
            index=models.Index(
                fields=['student', '-extended_deadline'],
                name='deadline_ext_student_deadline_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='studentdeadlineextension',
            index=models.Index(
                fields=['extended_by', '-created_at'],
                name='deadline_ext_creator_date_idx',
            ),
        ),
        migrations.AlterUniqueTogether(
            name='studentdeadlineextension',
            unique_together={('assignment', 'student')},
        ),
    ]
