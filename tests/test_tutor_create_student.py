"""
Тест создания ученика тьютором
"""
import pytest
import os
import sys
import django

# Настройка Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import StudentProfile, ParentProfile
from accounts.tutor_service import StudentCreationService

User = get_user_model()


@pytest.mark.django_db
def test_create_student_by_tutor():
    """Тест создания ученика тьютором"""
    import time
    timestamp = int(time.time())
    
    # Создаем тьютора
    tutor = User.objects.create_user(
        username=f'tutor_test_{timestamp}',
        email=f'tutor_test_{timestamp}@test.com',
        password='testpass123',
        role=User.Role.TUTOR,
        first_name='Тест',
        last_name='Тьютор'
    )
    
    # Создаем ученика через сервис
    student_user, parent_user, student_creds, parent_creds = StudentCreationService.create_student_with_parent(
        tutor=tutor,
        student_first_name='Иван',
        student_last_name='Иванов',
        grade='7А',
        goal='Улучшение знаний по математике',
        parent_first_name='Анна',
        parent_last_name='Иванова',
        parent_email='anna@example.com',
        parent_phone='+79991234567'
    )
    
    # Проверяем, что пользователи созданы
    assert student_user is not None
    assert parent_user is not None
    assert student_user.role == User.Role.STUDENT
    assert parent_user.role == User.Role.PARENT
    
    # Проверяем учетные данные
    assert student_creds.username is not None
    assert student_creds.password is not None
    assert parent_creds.username is not None
    assert parent_creds.password is not None
    
    # Проверяем профили
    student_profile = StudentProfile.objects.get(user=student_user)
    assert student_profile.tutor == tutor
    assert student_profile.parent == parent_user
    assert student_profile.grade == '7А'
    assert student_profile.goal == 'Улучшение знаний по математике'
    assert student_profile.generated_username == student_creds.username
    assert student_profile.generated_password == student_creds.password
    
    parent_profile = ParentProfile.objects.get(user=parent_user)
    assert student_user in parent_profile.children.all()
    
    # Проверяем связь с тьютором
    assert student_user.created_by_tutor == tutor
    assert parent_user.created_by_tutor == tutor
    
    print("✓ Ученик и родитель успешно созданы тьютором!")


@pytest.mark.django_db
def test_create_student_validation():
    """Тест валидации при создании ученика"""
    import time
    timestamp = int(time.time())
    
    # Создаем не-тьютора
    teacher = User.objects.create_user(
        username=f'teacher_{timestamp}',
        email=f'teacher_{timestamp}@test.com',
        password='testpass123',
        role=User.Role.TEACHER
    )
    
    # Пытаемся создать ученика (должно быть PermissionError)
    with pytest.raises(PermissionError):
        StudentCreationService.create_student_with_parent(
            tutor=teacher,
            student_first_name='Тест',
            student_last_name='Тестов',
            grade='7Б',
            parent_first_name='Родитель',
            parent_last_name='Тестов'
        )
    
    print("✓ Валидация роли работает правильно!")


if __name__ == '__main__':
    print("Запуск тестов создания ученика...")
    pytest.main([__file__, '-v'])

