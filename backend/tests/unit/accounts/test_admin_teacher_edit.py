"""
Тесты для AdminTeacherProfileEditView

Проверка обновления профиля преподавателя администратором,
включая управление subject_ids через TeacherSubject.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from materials.models import Subject, TeacherSubject
from accounts.models import TeacherProfile

User = get_user_model()


@pytest.fixture
def admin_client(db):
    """Аутентифицированный администратор"""
    admin_user = User.objects.create_user(
        username='admin',
        email='admin@test.com',
        password='testpass123',
        is_staff=True,
        is_superuser=True,
        role='teacher'
    )
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client, admin_user


@pytest.fixture
def teacher_user(db):
    """Преподаватель для редактирования"""
    teacher = User.objects.create_user(
        username='teacher',
        email='teacher@test.com',
        password='testpass123',
        first_name='John',
        last_name='Smith',
        phone='+79991234567',
        role='teacher'
    )
    TeacherProfile.objects.create(
        user=teacher,
        subject='Old Subject',
        experience_years=3,
        bio='Old bio'
    )
    return teacher


@pytest.fixture
def subjects(db):
    """Создать тестовые предметы"""
    math = Subject.objects.create(name='Mathematics', description='Math course')
    physics = Subject.objects.create(name='Physics', description='Physics course')
    chemistry = Subject.objects.create(name='Chemistry', description='Chemistry course')
    biology = Subject.objects.create(name='Biology', description='Biology course')
    return {
        'math': math,
        'physics': physics,
        'chemistry': chemistry,
        'biology': biology
    }


class TestAdminTeacherProfileEdit:
    """Тесты редактирования профиля преподавателя администратором"""

    def test_update_basic_fields_without_subjects(self, admin_client, teacher_user):
        """Обновление базовых полей без subject_ids"""
        client, admin_user = admin_client
        response = client.patch(
            f'/api/admin/teachers/{teacher_user.id}/',
            {
                'first_name': 'Jane',
                'last_name': 'Doe',
                'phone': '+79997654321',
                'experience_years': 5,
                'bio': 'New bio'
            },
            format='json'
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.data}"
        assert response.data['success'] is True
        assert response.data['user']['first_name'] == 'Jane'
        assert response.data['user']['last_name'] == 'Doe'
        assert response.data['user']['phone'] == '+79997654321'
        assert response.data['profile']['experience_years'] == 5
        assert response.data['profile']['bio'] == 'New bio'

        # Проверка сохранения в БД
        teacher_user.refresh_from_db()
        assert teacher_user.first_name == 'Jane'
        assert teacher_user.last_name == 'Doe'

    def test_add_subjects_to_teacher(self, admin_client, teacher_user, subjects):
        """Добавление предметов преподавателю через subject_ids"""
        client, admin_user = admin_client
        response = client.patch(
            f'/api/admin/teachers/{teacher_user.id}/',
            {
                'subject_ids': [subjects['math'].id, subjects['physics'].id]
            },
            format='json'
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.data}"
        assert response.data['success'] is True

        # Проверка создания TeacherSubject записей
        teacher_subjects = TeacherSubject.objects.filter(
            teacher=teacher_user,
            is_active=True
        ).values_list('subject_id', flat=True)

        assert set(teacher_subjects) == {subjects['math'].id, subjects['physics'].id}

        # Проверка subjects_list в ответе
        subjects_list = response.data['profile']['subjects_list']
        assert 'Mathematics' in subjects_list
        assert 'Physics' in subjects_list
        assert len(subjects_list) == 2

    def test_remove_subjects_from_teacher(self, admin_client, teacher_user, subjects):
        """Удаление предметов преподавателя через subject_ids"""
        # Сначала добавим предметы
        client, admin_user = admin_client
        TeacherSubject.objects.create(teacher=teacher_user, subject=subjects['math'], is_active=True)
        TeacherSubject.objects.create(teacher=teacher_user, subject=subjects['physics'], is_active=True)
        TeacherSubject.objects.create(teacher=teacher_user, subject=subjects['chemistry'], is_active=True)

        # Теперь оставим только математику
        response = client.patch(
            f'/api/admin/teachers/{teacher_user.id}/',
            {
                'subject_ids': [subjects['math'].id]
            },
            format='json'
        )

        assert response.status_code == 200
        assert response.data['success'] is True

        # Проверка что physics и chemistry помечены is_active=False
        active_subjects = TeacherSubject.objects.filter(
            teacher=teacher_user,
            is_active=True
        ).values_list('subject_id', flat=True)

        assert set(active_subjects) == {subjects['math'].id}

        # Проверка что удалённые записи всё ещё существуют, но is_active=False
        inactive_subjects = TeacherSubject.objects.filter(
            teacher=teacher_user,
            is_active=False
        ).count()
        assert inactive_subjects == 2

    def test_empty_subject_ids_removes_all(self, admin_client, teacher_user, subjects):
        """Пустой subject_ids удаляет все предметы"""
        # Добавим предметы
        client, admin_user = admin_client
        TeacherSubject.objects.create(teacher=teacher_user, subject=subjects['math'], is_active=True)
        TeacherSubject.objects.create(teacher=teacher_user, subject=subjects['physics'], is_active=True)

        response = client.patch(
            f'/api/admin/teachers/{teacher_user.id}/',
            {
                'subject_ids': []
            },
            format='json'
        )

        assert response.status_code == 200
        assert response.data['success'] is True

        # Проверка что все предметы помечены is_active=False
        active_count = TeacherSubject.objects.filter(
            teacher=teacher_user,
            is_active=True
        ).count()
        assert active_count == 0

        # subjects_list должен быть пустым
        assert response.data['profile']['subjects_list'] == []

    def test_partial_update_subjects(self, admin_client, teacher_user, subjects):
        """Частичное обновление предметов (добавление + удаление)"""
        # Начальные предметы: math, physics
        client, admin_user = admin_client
        TeacherSubject.objects.create(teacher=teacher_user, subject=subjects['math'], is_active=True)
        TeacherSubject.objects.create(teacher=teacher_user, subject=subjects['physics'], is_active=True)

        # Обновим на: physics, chemistry, biology (убрать math, добавить chemistry и biology)
        response = client.patch(
            f'/api/admin/teachers/{teacher_user.id}/',
            {
                'subject_ids': [
                    subjects['physics'].id,
                    subjects['chemistry'].id,
                    subjects['biology'].id
                ]
            },
            format='json'
        )

        assert response.status_code == 200
        assert response.data['success'] is True

        active_subjects = set(
            TeacherSubject.objects.filter(
                teacher=teacher_user,
                is_active=True
            ).values_list('subject_id', flat=True)
        )

        expected_subjects = {
            subjects['physics'].id,
            subjects['chemistry'].id,
            subjects['biology'].id
        }
        assert active_subjects == expected_subjects

        # math должен быть is_active=False
        math_record = TeacherSubject.objects.get(teacher=teacher_user, subject=subjects['math'])
        assert math_record.is_active is False

    def test_update_subjects_with_other_fields(self, admin_client, teacher_user, subjects):
        """Обновление subject_ids вместе с другими полями"""
        client, admin_user = admin_client
        response = client.patch(
            f'/api/admin/teachers/{teacher_user.id}/',
            {
                'first_name': 'Updated',
                'experience_years': 10,
                'bio': 'Updated bio',
                'subject_ids': [subjects['math'].id, subjects['physics'].id]
            },
            format='json'
        )

        assert response.status_code == 200
        assert response.data['success'] is True
        assert response.data['user']['first_name'] == 'Updated'
        assert response.data['profile']['experience_years'] == 10
        assert response.data['profile']['bio'] == 'Updated bio'
        assert len(response.data['profile']['subjects_list']) == 2

    def test_subject_field_in_profile_still_works(self, admin_client, teacher_user):
        """Проверка что поле 'subject' в TeacherProfile всё ещё работает"""
        client, admin_user = admin_client
        response = client.patch(
            f'/api/admin/teachers/{teacher_user.id}/',
            {
                'subject': 'Updated Subject String'
            },
            format='json'
        )

        assert response.status_code == 200
        assert response.data['success'] is True
        assert response.data['profile']['subject'] == 'Updated Subject String'

        # Проверка в БД
        teacher_user.teacher_profile.refresh_from_db()
        assert teacher_user.teacher_profile.subject == 'Updated Subject String'

    def test_invalid_subject_ids_type(self, admin_client, teacher_user):
        """Проверка что subject_ids должен быть списком"""
        client, admin_user = admin_client
        response = client.patch(
            f'/api/admin/teachers/{teacher_user.id}/',
            {
                'subject_ids': 'not a list'
            },
            format='json'
        )

        assert response.status_code == 400
        assert 'detail' in response.data or 'error' in response.data

    def test_nonexistent_subject_id(self, admin_client, teacher_user):
        """Попытка добавить несуществующий предмет (должна проигнорировать)"""
        client, admin_user = admin_client
        response = client.patch(
            f'/api/admin/teachers/{teacher_user.id}/',
            {
                'subject_ids': [99999]  # Несуществующий ID
            },
            format='json'
        )

        # Операция должна пройти успешно, но предмет не добавится
        assert response.status_code == 200
        assert response.data['success'] is True

        # Проверка что предмет не добавлен
        count = TeacherSubject.objects.filter(teacher=teacher_user, is_active=True).count()
        assert count == 0

    def test_update_is_active_field(self, admin_client, teacher_user):
        """Обновление is_active статуса преподавателя"""
        client, admin_user = admin_client
        assert teacher_user.is_active is True

        response = client.patch(
            f'/api/admin/teachers/{teacher_user.id}/',
            {
                'is_active': False
            },
            format='json'
        )

        assert response.status_code == 200
        assert response.data['success'] is True
        assert response.data['user']['is_active'] is False

        teacher_user.refresh_from_db()
        assert teacher_user.is_active is False

    def test_teacher_not_found(self, admin_client):
        """Попытка обновить несуществующего преподавателя"""
        client, admin_user = admin_client
        response = client.patch(
            '/api/admin/teachers/99999/',
            {'first_name': 'Test'},
            format='json'
        )

        assert response.status_code == 404
        error_data = response.data.get('detail') or response.data.get('error')
        assert error_data is not None
        assert 'not found' in str(error_data).lower()

    def test_non_admin_user_forbidden(self, db, teacher_user):
        """Обычный пользователь не может редактировать профиль"""
        regular_user = User.objects.create_user(
            username='regular',
            email='regular@test.com',
            password='testpass123',
            role='student'
        )
        client = APIClient()
        client.force_authenticate(user=regular_user)

        response = client.patch(
            f'/api/admin/teachers/{teacher_user.id}/',
            {'first_name': 'Hacked'},
            format='json'
        )

        assert response.status_code == 403
        assert 'detail' in response.data or 'error' in response.data
