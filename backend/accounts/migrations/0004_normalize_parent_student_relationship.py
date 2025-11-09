# Generated manually for normalizing Parent-Student relationship
# Убираем ManyToMany из ParentProfile, оставляем ForeignKey в StudentProfile

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_studentprofile_generated_password_and_more'),
    ]

    operations = [
        # Изменяем related_name поля parent в StudentProfile
        migrations.AlterField(
            model_name='studentprofile',
            name='parent',
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={'role': 'parent'},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='children_students',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Родитель'
            ),
        ),
        # Удаляем ManyToMany поле children из ParentProfile
        # ManyToMany создает промежуточную таблицу, которую нужно удалить безопасно
        migrations.SeparateDatabaseAndState(
            database_operations=[
                # Удаляем промежуточную таблицу ManyToMany, если она существует
                migrations.RunSQL(
                    sql="DROP TABLE IF EXISTS accounts_parentprofile_children;",
                    reverse_sql=migrations.RunSQL.noop,
                ),
            ],
            state_operations=[
                migrations.RemoveField(
                    model_name='parentprofile',
                    name='children',
                ),
            ],
        ),
    ]

