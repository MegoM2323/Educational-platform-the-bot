"""
Полное тестирование создания ученика и родителя тьютором
Включает проверку backend API, frontend интеграции и работы в связке
"""
import pytest
import os
import sys
import django

# Настройка Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from accounts.models import StudentProfile, ParentProfile, TutorStudentCreation
from accounts.tutor_service import StudentCreationService
from accounts.tutor_views import TutorStudentsViewSet, IsTutor
from rest_framework.test import APIClient

User = get_user_model()


@pytest.fixture(scope='function')
def tutor():
    """Создаем тьютора с токеном"""
    import time
    timestamp = int(time.time())
    
    tutor = User.objects.create_user(
        username=f'tutor_{timestamp}',
        email=f'tutor_{timestamp}@test.com',
        password='testpass123',
        role=User.Role.TUTOR,
        first_name='Тест',
        last_name='Тьютор'
    )
    
    # Создаем токен для аутентификации
    token, _ = Token.objects.get_or_create(user=tutor)
    
    return tutor, token.key


@pytest.fixture(scope='function')
def non_tutor():
    """Создаем пользователя не-тьютора"""
    import time
    timestamp = int(time.time())
    
    return User.objects.create_user(
        username=f'teacher_{timestamp}',
        email=f'teacher_{timestamp}@test.com',
        password='testpass123',
        role=User.Role.TEACHER
    )


@pytest.mark.django_db
def test_tutor_authentication(tutor):
    """Тест аутентификации тьютора"""
    tutor_user, token = tutor
    
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    
    response = client.get('/api/tutor/students/')
    
    print(f"Response status: {response.status_code}")
    print(f"Response data: {response.data}")
    
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.data}"


@pytest.mark.django_db
def test_create_student_full_flow(tutor):
    """Полный тест создания ученика и родителя"""
    tutor_user, token = tutor
    
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    
    # Данные для создания
    form_data = {
        'first_name': 'Иван',
        'last_name': 'Иванов',
        'grade': '7А',
        'goal': 'Улучшение знаний',
        'parent_first_name': 'Анна',
        'parent_last_name': 'Иванова',
        'parent_email': 'anna@example.com',
        'parent_phone': '+79991234567'
    }
    
    print(f"\n=== Creating student with data: {form_data} ===")
    
    # Отправляем запрос на создание
    response = client.post('/api/tutor/students/', form_data, format='json')
    
    print(f"Response status: {response.status_code}")
    print(f"Response data: {response.data}")
    
    assert response.status_code == 201, f"Expected 201, got {response.status_code}. Error: {response.data}"
    
    # Проверяем ответ
    assert 'student' in response.data
    assert 'parent' in response.data
    assert 'credentials' in response.data
    
    student_data = response.data['student']
    parent_data = response.data['parent']
    credentials = response.data['credentials']
    
    # Проверяем данные студента
    assert student_data['full_name'] == 'Иван Иванов'
    assert student_data['grade'] == '7А'
    
    # Проверяем учетные данные
    assert 'student' in credentials
    assert 'parent' in credentials
    assert 'username' in credentials['student']
    assert 'password' in credentials['student']
    
    print("✓ Student created successfully via API")


@pytest.mark.django_db
def test_service_layer_creation(tutor):
    """Тест создания через сервисный слой"""
    tutor_user, token = tutor
    
    student_user, parent_user, student_creds, parent_creds = StudentCreationService.create_student_with_parent(
        tutor=tutor_user,
        student_first_name='Мария',
        student_last_name='Петрова',
        grade='8Б',
        goal='Подготовка к экзаменам',
        parent_first_name='Ольга',
        parent_last_name='Петрова',
        parent_email='olga@example.com',
        parent_phone='+79998765432'
    )
    
    # Проверяем создание
    assert student_user is not None
    assert parent_user is not None
    assert student_user.role == User.Role.STUDENT
    assert parent_user.role == User.Role.PARENT
    
    # Проверяем профили
    student_profile = StudentProfile.objects.get(user=student_user)
    assert student_profile.tutor == tutor_user
    assert student_profile.parent == parent_user
    assert student_profile.grade == '8Б'
    
    # Проверяем родителя
    parent_profile = ParentProfile.objects.get(user=parent_user)
    assert student_user in parent_profile.children.all()
    
    print("✓ Service layer creation works correctly")


@pytest.mark.django_db
def test_list_students(tutor):
    """Тест получения списка студентов"""
    tutor_user, token = tutor
    
    # Создаем нескольких студентов
    for i in range(3):
        StudentCreationService.create_student_with_parent(
            tutor=tutor_user,
            student_first_name=f'Студент{i}',
            student_last_name='Тестов',
            grade=f'{i+5}А',
            parent_first_name=f'Родитель{i}',
            parent_last_name='Тестов'
        )
    
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {token}')
    
    response = client.get('/api/tutor/students/')
    
    assert response.status_code == 200
    assert len(response.data) == 3
    
    print(f"✓ Listed {len(response.data)} students")


@pytest.mark.django_db
def test_non_tutor_cannot_create_student(non_tutor):
    """Тест что не-тьютор не может создавать студентов"""
    # Создаем токен
    token, _ = Token.objects.get_or_create(user=non_tutor)
    
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    
    form_data = {
        'first_name': 'Тест',
        'last_name': 'Тестов',
        'grade': '7А',
        'parent_first_name': 'Родитель',
        'parent_last_name': 'Тестов'
    }
    
    response = client.post('/api/tutor/students/', form_data, format='json')
    
    print(f"Response status: {response.status_code}")
    print(f"Response data: {response.data}")
    
    assert response.status_code == 403, "Non-tutor should get 403 Forbidden"
    print("✓ Non-tutor correctly denied access")


@pytest.mark.django_db
def test_unauthenticated_cannot_access():
    """Тест что неавторизованный пользователь не может получить доступ"""
    client = APIClient()
    
    response = client.get('/api/tutor/students/')
    
    assert response.status_code == 401, "Unauthenticated user should get 401 Unauthorized"
    print("✓ Unauthenticated access correctly denied")


@pytest.mark.django_db
def test_credentials_generation(tutor):
    """Тест генерации уникальных учетных данных"""
    tutor_user, token = tutor
    
    credentials_set = set()
    
    # Создаем несколько студентов
    for i in range(5):
        _, _, student_creds, parent_creds = StudentCreationService.create_student_with_parent(
            tutor=tutor_user,
            student_first_name=f'Student{i}',
            student_last_name='Unique',
            grade='7А',
            parent_first_name='Parent',
            parent_last_name='Unique'
        )
        
        student_key = f"{student_creds.username}:{student_creds.password}"
        parent_key = f"{parent_creds.username}:{parent_creds.password}"
        
        # Проверяем уникальность
        assert student_key not in credentials_set, "Student credentials should be unique"
        assert parent_key not in credentials_set, "Parent credentials should be unique"
        
        credentials_set.add(student_key)
        credentials_set.add(parent_key)
    
    print(f"✓ Generated {len(credentials_set)} unique credential pairs")


@pytest.mark.django_db
def test_student_parent_linkage(tutor):
    """Тест связи студента с родителем"""
    tutor_user, token = tutor
    
    student_user, parent_user, _, _ = StudentCreationService.create_student_with_parent(
        tutor=tutor_user,
        student_first_name='Связь',
        student_last_name='Тест',
        grade='9А',
        parent_first_name='Связь',
        parent_last_name='Родитель'
    )
    
    # Проверяем связь через профиль студента
    student_profile = StudentProfile.objects.get(user=student_user)
    assert student_profile.parent == parent_user
    
    # Проверяем связь через профиль родителя
    parent_profile = ParentProfile.objects.get(user=parent_user)
    assert student_user in parent_profile.children.all()
    
    print("✓ Student-Parent linkage works correctly")


if __name__ == '__main__':
    print("Запуск полных тестов создания ученика и родителя...")
    pytest.main([__file__, '-v', '--tb=short'])

