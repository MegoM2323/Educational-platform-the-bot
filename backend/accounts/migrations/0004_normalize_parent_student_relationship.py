# Generated manually for normalizing Parent-Student relationship
# Убираем ManyToMany из ParentProfile, оставляем ForeignKey в StudentProfile

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def migrate_children_to_parent_reference(apps, schema_editor):
    """
    Переносим данные из ParentProfile.children (ManyToMany) в StudentProfile.parent (ForeignKey)
    Для каждого родителя находим его детей и устанавливаем parent в их StudentProfile
    """
    StudentProfile = apps.get_model('accounts', 'StudentProfile')
    ParentProfile = apps.get_model('accounts', 'ParentProfile')
    
    # Проходим по всем ParentProfile
    for parent_profile in ParentProfile.objects.all():
        parent_user = parent_profile.user
        
        # Получаем детей через ManyToMany (если оно еще существует)
        try:
            children = parent_profile.children.all()
            for child in children:
                # Устанавливаем родителя в StudentProfile ребенка
                try:
                    student_profile = child.student_profile
                    student_profile.parent = parent_user
                    student_profile.save()
                except StudentProfile.DoesNotExist:
                    pass
        except AttributeError:
            # Если ManyToMany уже не существует, пропускаем
            pass


def reverse_migrate_parent_reference_to_children(apps, schema_editor):
    """
    Обратный перенос: берем parent из StudentProfile и добавляем в ParentProfile.children (ManyToMany)
    """
    StudentProfile = apps.get_model('accounts', 'StudentProfile')
    ParentProfile = apps.get_model('accounts', 'ParentProfile')
    
    # Проходим по всем StudentProfile с указанным parent
    for student_profile in StudentProfile.objects.filter(parent__isnull=False).select_related('user', 'parent'):
        student_user = student_profile.user
        parent_user = student_profile.parent
        
        # Получаем ParentProfile родителя
        try:
            parent_profile = parent_user.parent_profile
            # Добавляем ребенка в ManyToMany (если оно еще существует)
            try:
                if student_user not in parent_profile.children.all():
                    parent_profile.children.add(student_user)
            except AttributeError:
                pass
        except ParentProfile.DoesNotExist:
            pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_studentprofile_generated_password_and_more'),
    ]

    operations = [
        # Изменяем related_name поля parent в StudentProfile (если оно существует)
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
        # Переносим данные из ManyToMany в ForeignKey
        migrations.RunPython(
            migrate_children_to_parent_reference,
            reverse_migrate_parent_reference_to_children
        ),
        # Удаляем ManyToMany поле children из ParentProfile
        migrations.RemoveField(
            model_name='parentprofile',
            name='children',
        ),
    ]

