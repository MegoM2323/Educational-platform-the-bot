"""
Тесты для API управления предметами преподавателей
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token
from materials.models import Subject, TeacherSubject

User = get_user_model()


@pytest.fixture
def api_client():
    """Фикстура для API клиента"""
    return APIClient()


@pytest.fixture
def admin_user(db):
    """Фикстура для создания admin пользователя"""
    user = User.objects.create_user(
        username='admin_test',
        email='admin@test.com',
        password='testpass123',
        is_staff=True,
        is_superuser=True,
        role='student'  # Роль не важна, главное is_staff=True
    )
    return user


@pytest.fixture
def admin_token(admin_user):
    """Фикстура для создания токена админа"""
    token, _ = Token.objects.get_or_create(user=admin_user)
    return token


@pytest.fixture
def teacher_user(db):
    """Фикстура для создания преподавателя"""
    user = User.objects.create_user(
        username='teacher_test',
        email='teacher@test.com',
        password='testpass123',
        role='teacher',
        first_name='Test',
        last_name='Teacher'
    )
    return user


@pytest.fixture
def subjects(db):
    """Фикстура для создания тестовых предметов"""
    subjects = []
    subjects_data = [
        ('Математика', '#FF6B6B'),
        ('Физика', '#4ECDC4'),
        ('Химия', '#45B7D1'),
    ]
    for name, color in subjects_data:
        subject = Subject.objects.create(
            name=name,
            color=color,
            description=f'Предмет {name}'
        )
        subjects.append(subject)
    return subjects


@pytest.mark.django_db
class TestSubjectsListAPI:
    """Тесты для GET /api/materials/subjects/all/"""

    def test_list_all_subjects_success(self, api_client, admin_token, subjects):
        """Тест успешного получения списка всех предметов"""
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token.key}')
        response = api_client.get('/api/materials/subjects/all/')

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['count'] >= 3
        assert len(data['results']) >= 3

        # Проверяем структуру объекта предмета
        first_subject = data['results'][0]
        assert 'id' in first_subject
        assert 'name' in first_subject
        assert 'color' in first_subject
        assert 'description' in first_subject

    def test_list_subjects_requires_authentication(self, api_client):
        """Тест что endpoint требует аутентификации"""
        response = api_client.get('/api/materials/subjects/all/')
        assert response.status_code == 401

    def test_list_subjects_with_search(self, api_client, admin_token, subjects):
        """Тест поиска предметов по названию"""
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token.key}')
        response = api_client.get('/api/materials/subjects/all/?search=Мат')

        assert response.status_code == 200
        data = response.json()
        assert data['count'] >= 1
        assert 'Математика' in data['results'][0]['name']


@pytest.mark.django_db
class TestTeacherSubjectsAPI:
    """Тесты для PATCH /api/auth/staff/teachers/{id}/subjects/"""

    def test_update_teacher_subjects_success(self, api_client, admin_token, teacher_user, subjects):
        """Тест успешного обновления предметов преподавателя"""
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token.key}')
        subject_ids = [subjects[0].id, subjects[1].id]

        response = api_client.patch(
            f'/api/auth/staff/teachers/{teacher_user.id}/subjects/',
            {'subject_ids': subject_ids},
            format='json'
        )

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['teacher_id'] == teacher_user.id
        assert len(data['subjects']) == 2

        # Проверяем что в БД созданы записи
        db_count = TeacherSubject.objects.filter(
            teacher=teacher_user,
            is_active=True
        ).count()
        assert db_count == 2

    def test_update_teacher_subjects_empty_list(self, api_client, admin_token, teacher_user, subjects):
        """Тест удаления всех предметов (пустой массив)"""
        # Сначала назначаем предметы
        TeacherSubject.objects.create(
            teacher=teacher_user,
            subject=subjects[0],
            is_active=True
        )

        api_client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token.key}')
        response = api_client.patch(
            f'/api/auth/staff/teachers/{teacher_user.id}/subjects/',
            {'subject_ids': []},
            format='json'
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data['subjects']) == 0

        # Проверяем что в БД удалены все записи
        db_count = TeacherSubject.objects.filter(
            teacher=teacher_user,
            is_active=True
        ).count()
        assert db_count == 0

    def test_update_teacher_subjects_invalid_subject_id(self, api_client, admin_token, teacher_user):
        """Тест валидации - несуществующий предмет"""
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token.key}')
        response = api_client.patch(
            f'/api/auth/staff/teachers/{teacher_user.id}/subjects/',
            {'subject_ids': [99999]},
            format='json'
        )

        assert response.status_code == 400
        data = response.json()
        assert 'subject_ids' in data

    def test_update_teacher_subjects_teacher_not_found(self, api_client, admin_token, subjects):
        """Тест валидации - несуществующий преподаватель"""
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token.key}')
        response = api_client.patch(
            '/api/auth/staff/teachers/99999/subjects/',
            {'subject_ids': [subjects[0].id]},
            format='json'
        )

        assert response.status_code == 404
        data = response.json()
        assert 'detail' in data
        assert 'не найден' in data['detail']

    def test_update_teacher_subjects_requires_staff_permission(self, api_client, teacher_user, subjects):
        """Тест что endpoint требует прав staff/admin"""
        # Создаем обычного пользователя (не admin)
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@test.com',
            password='testpass123',
            role='student'
        )
        token, _ = Token.objects.get_or_create(user=regular_user)

        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
        response = api_client.patch(
            f'/api/auth/staff/teachers/{teacher_user.id}/subjects/',
            {'subject_ids': [subjects[0].id]},
            format='json'
        )

        assert response.status_code == 403

    def test_update_replaces_existing_subjects(self, api_client, admin_token, teacher_user, subjects):
        """Тест что обновление заменяет (а не добавляет) предметы"""
        # Сначала назначаем первый предмет
        TeacherSubject.objects.create(
            teacher=teacher_user,
            subject=subjects[0],
            is_active=True
        )

        # Обновляем на второй предмет
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token.key}')
        response = api_client.patch(
            f'/api/auth/staff/teachers/{teacher_user.id}/subjects/',
            {'subject_ids': [subjects[1].id]},
            format='json'
        )

        assert response.status_code == 200

        # Проверяем что остался только второй предмет
        db_subjects = TeacherSubject.objects.filter(
            teacher=teacher_user,
            is_active=True
        ).values_list('subject_id', flat=True)
        assert list(db_subjects) == [subjects[1].id]


@pytest.mark.django_db
class TestStaffListWithSubjects:
    """Тесты для проверки что GET /api/auth/staff/ возвращает предметы"""

    def test_teacher_list_includes_subjects(self, api_client, admin_token, teacher_user, subjects):
        """Тест что список преподавателей включает их предметы"""
        # Назначаем предметы преподавателю
        for subject in subjects[:2]:
            TeacherSubject.objects.create(
                teacher=teacher_user,
                subject=subject,
                is_active=True
            )

        api_client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token.key}')
        response = api_client.get('/api/auth/staff/?role=teacher')

        assert response.status_code == 200
        data = response.json()

        # Находим нашего тестового преподавателя
        teacher_data = None
        for item in data['results']:
            if item['user']['id'] == teacher_user.id:
                teacher_data = item
                break

        assert teacher_data is not None
        assert 'subjects' in teacher_data
        assert len(teacher_data['subjects']) == 2

        # Проверяем структуру объекта предмета
        first_subject = teacher_data['subjects'][0]
        assert 'id' in first_subject
        assert 'name' in first_subject
        assert 'color' in first_subject
        assert 'is_active' in first_subject
        assert 'assigned_at' in first_subject
