"""
Тесты для системы приватных полей профилей.

Проверяем что:
- Пользователи НЕ видят свои приватные поля
- Админы видят все поля
- Teacher/Tutor видят приватные поля студентов
- Admin видит приватные поля teacher/tutor
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from accounts.models import StudentProfile, TeacherProfile, TutorProfile, ParentProfile
from accounts.serializers import (
    StudentProfilePublicSerializer,
    StudentProfileFullSerializer,
    TeacherProfilePublicSerializer,
    TeacherProfileFullSerializer,
    TutorProfilePublicSerializer,
    TutorProfileFullSerializer,
    get_profile_serializer,
)
from accounts.permissions import can_view_private_fields

User = get_user_model()


@pytest.fixture
def student_user(django_db_setup, db):
    """Создает студента с профилем"""
    user = User.objects.create_user(
        username='student_test',
        email='student@test.com',
        password='testpass123',
        role=User.Role.STUDENT,
        first_name='Иван',
        last_name='Студентов'
    )
    StudentProfile.objects.create(
        user=user,
        grade='10',
        goal='Поступить в МГУ',  # Приватное поле
        progress_percentage=75,
        streak_days=10,
        total_points=1000,
        accuracy_percentage=85
    )
    return user


@pytest.fixture
def teacher_user(django_db_setup, db):
    """Создает преподавателя с профилем"""
    user = User.objects.create_user(
        username='teacher_test',
        email='teacher@test.com',
        password='testpass123',
        role=User.Role.TEACHER,
        first_name='Петр',
        last_name='Преподавателев'
    )
    TeacherProfile.objects.create(
        user=user,
        subject='Математика',
        bio='Опытный преподаватель математики',  # Приватное поле
        experience_years=10  # Приватное поле
    )
    return user


@pytest.fixture
def tutor_user(django_db_setup, db):
    """Создает тьютора с профилем"""
    user = User.objects.create_user(
        username='tutor_test',
        email='tutor@test.com',
        password='testpass123',
        role=User.Role.TUTOR,
        first_name='Мария',
        last_name='Тьюторова'
    )
    TutorProfile.objects.create(
        user=user,
        specialization='Общее развитие',
        bio='Опытный тьютор',  # Приватное поле
        experience_years=5  # Приватное поле
    )
    return user


@pytest.fixture
def admin_user(django_db_setup, db):
    """Создает админа"""
    return User.objects.create_user(
        username='admin_test',
        email='admin@test.com',
        password='testpass123',
        is_staff=True,
        is_superuser=True,
        role=User.Role.STUDENT  # Роль не важна для админа
    )


@pytest.fixture
def parent_user(django_db_setup, db):
    """Создает родителя с профилем"""
    user = User.objects.create_user(
        username='parent_test',
        email='parent@test.com',
        password='testpass123',
        role=User.Role.PARENT,
        first_name='Анна',
        last_name='Родительница'
    )
    ParentProfile.objects.create(user=user)
    return user


# ============= ТЕСТЫ ФУНКЦИИ can_view_private_fields =============


@pytest.mark.django_db
class TestCanViewPrivateFields:
    """Тесты функции проверки прав на просмотр приватных полей"""

    def test_student_cannot_view_own_private_fields(self, student_user):
        """Студент НЕ видит свои приватные поля"""
        can_view = can_view_private_fields(student_user, student_user, 'student')
        assert can_view is False

    def test_teacher_can_view_student_private_fields(self, teacher_user, student_user):
        """Преподаватель видит приватные поля студента"""
        can_view = can_view_private_fields(teacher_user, student_user, 'student')
        assert can_view is True

    def test_tutor_can_view_student_private_fields(self, tutor_user, student_user):
        """Тьютор видит приватные поля студента"""
        can_view = can_view_private_fields(tutor_user, student_user, 'student')
        assert can_view is True

    def test_admin_can_view_student_private_fields(self, admin_user, student_user):
        """Админ видит приватные поля студента"""
        can_view = can_view_private_fields(admin_user, student_user, 'student')
        assert can_view is True

    def test_teacher_cannot_view_own_private_fields(self, teacher_user):
        """Преподаватель НЕ видит свои приватные поля"""
        can_view = can_view_private_fields(teacher_user, teacher_user, 'teacher')
        assert can_view is False

    def test_admin_can_view_teacher_private_fields(self, admin_user, teacher_user):
        """Админ видит приватные поля преподавателя"""
        can_view = can_view_private_fields(admin_user, teacher_user, 'teacher')
        assert can_view is True

    def test_tutor_cannot_view_own_private_fields(self, tutor_user):
        """Тьютор НЕ видит свои приватные поля"""
        can_view = can_view_private_fields(tutor_user, tutor_user, 'tutor')
        assert can_view is False

    def test_admin_can_view_tutor_private_fields(self, admin_user, tutor_user):
        """Админ видит приватные поля тьютора"""
        can_view = can_view_private_fields(admin_user, tutor_user, 'tutor')
        assert can_view is True

    def test_parent_viewing_own_profile(self, parent_user):
        """Родитель смотрит свой профиль (пока нет приватных полей)"""
        can_view = can_view_private_fields(parent_user, parent_user, 'parent')
        assert can_view is False


# ============= ТЕСТЫ SERIALIZERS =============


@pytest.mark.django_db
class TestStudentProfileSerializers:
    """Тесты serializers для StudentProfile"""

    def test_public_serializer_excludes_private_fields(self, student_user):
        """PublicSerializer НЕ включает приватные поля"""
        profile = student_user.student_profile
        serializer = StudentProfilePublicSerializer(profile)
        data = serializer.data

        # Проверяем что приватных полей нет
        assert 'goal' not in data
        assert 'tutor' not in data
        assert 'parent' not in data

        # Проверяем что публичные поля есть
        assert 'grade' in data
        assert 'progress_percentage' in data
        assert data['progress_percentage'] == 75

    def test_full_serializer_includes_private_fields(self, student_user):
        """FullSerializer включает приватные поля"""
        profile = student_user.student_profile
        serializer = StudentProfileFullSerializer(profile)
        data = serializer.data

        # Проверяем что приватные поля есть
        assert 'goal' in data
        assert data['goal'] == 'Поступить в МГУ'

        # Проверяем что публичные поля тоже есть
        assert 'grade' in data
        assert 'progress_percentage' in data


@pytest.mark.django_db
class TestTeacherProfileSerializers:
    """Тесты serializers для TeacherProfile"""

    def test_public_serializer_excludes_private_fields(self, teacher_user):
        """PublicSerializer НЕ включает приватные поля"""
        profile = teacher_user.teacher_profile
        serializer = TeacherProfilePublicSerializer(profile)
        data = serializer.data

        # Проверяем что приватных полей нет
        assert 'bio' not in data
        assert 'experience_years' not in data

        # Проверяем что публичные поля есть
        assert 'subject' in data
        assert data['subject'] == 'Математика'

    def test_full_serializer_includes_private_fields(self, teacher_user):
        """FullSerializer включает приватные поля"""
        profile = teacher_user.teacher_profile
        serializer = TeacherProfileFullSerializer(profile)
        data = serializer.data

        # Проверяем что приватные поля есть
        assert 'bio' in data
        assert data['bio'] == 'Опытный преподаватель математики'
        assert 'experience_years' in data
        assert data['experience_years'] == 10


@pytest.mark.django_db
class TestTutorProfileSerializers:
    """Тесты serializers для TutorProfile"""

    def test_public_serializer_excludes_private_fields(self, tutor_user):
        """PublicSerializer НЕ включает приватные поля"""
        profile = tutor_user.tutor_profile
        serializer = TutorProfilePublicSerializer(profile)
        data = serializer.data

        # Проверяем что приватных полей нет
        assert 'bio' not in data
        assert 'experience_years' not in data

        # Проверяем что публичные поля есть
        assert 'specialization' in data
        assert data['specialization'] == 'Общее развитие'

    def test_full_serializer_includes_private_fields(self, tutor_user):
        """FullSerializer включает приватные поля"""
        profile = tutor_user.tutor_profile
        serializer = TutorProfileFullSerializer(profile)
        data = serializer.data

        # Проверяем что приватные поля есть
        assert 'bio' in data
        assert data['bio'] == 'Опытный тьютор'
        assert 'experience_years' in data
        assert data['experience_years'] == 5


# ============= ТЕСТЫ ФУНКЦИИ get_profile_serializer =============


@pytest.mark.django_db
class TestGetProfileSerializer:
    """Тесты функции выбора serializer"""

    def test_student_views_own_profile_gets_public_serializer(self, student_user):
        """Студент смотрит свой профиль → PublicSerializer"""
        profile = student_user.student_profile
        SerializerClass = get_profile_serializer(profile, student_user, student_user)
        assert SerializerClass == StudentProfilePublicSerializer

    def test_teacher_views_student_profile_gets_full_serializer(self, teacher_user, student_user):
        """Преподаватель смотрит профиль студента → FullSerializer"""
        profile = student_user.student_profile
        SerializerClass = get_profile_serializer(profile, teacher_user, student_user)
        assert SerializerClass == StudentProfileFullSerializer

    def test_admin_views_teacher_profile_gets_full_serializer(self, admin_user, teacher_user):
        """Админ смотрит профиль преподавателя → FullSerializer"""
        profile = teacher_user.teacher_profile
        SerializerClass = get_profile_serializer(profile, admin_user, teacher_user)
        assert SerializerClass == TeacherProfileFullSerializer

    def test_teacher_views_own_profile_gets_public_serializer(self, teacher_user):
        """Преподаватель смотрит свой профиль → PublicSerializer"""
        profile = teacher_user.teacher_profile
        SerializerClass = get_profile_serializer(profile, teacher_user, teacher_user)
        assert SerializerClass == TeacherProfilePublicSerializer


# ============= ИНТЕГРАЦИОННЫЕ ТЕСТЫ ЧЕРЕЗ API =============


@pytest.mark.django_db
class TestDashboardAPIPrivateFields:
    """Интеграционные тесты через API endpoints"""

    def test_student_dashboard_hides_private_fields(self, student_user):
        """Student dashboard скрывает приватные поля от студента"""
        client = APIClient()
        client.force_authenticate(user=student_user)

        response = client.get('/api/dashboard/student/')

        assert response.status_code == 200
        data = response.json()

        # Проверяем что профиль есть
        assert 'profile' in data

        if data['profile']:
            # Проверяем что приватные поля скрыты
            assert 'goal' not in data['profile']
            assert 'tutor' not in data['profile']
            assert 'parent' not in data['profile']

            # Проверяем что публичные поля есть
            assert 'grade' in data['profile']
            assert 'progress_percentage' in data['profile']

    def test_teacher_dashboard_hides_private_fields(self, teacher_user):
        """Teacher dashboard скрывает приватные поля от преподавателя"""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        response = client.get('/api/dashboard/teacher/')

        assert response.status_code == 200
        data = response.json()

        # Проверяем что профиль есть
        assert 'profile' in data

        if data['profile']:
            # Проверяем что приватные поля скрыты
            assert 'bio' not in data['profile']
            assert 'experience_years' not in data['profile']

            # Проверяем что публичные поля есть
            assert 'subject' in data['profile']

    def test_tutor_dashboard_hides_private_fields(self, tutor_user):
        """Tutor dashboard скрывает приватные поля от тьютора"""
        client = APIClient()
        client.force_authenticate(user=tutor_user)

        response = client.get('/api/materials/dashboard/tutor/')

        assert response.status_code == 200
        data = response.json()

        # Проверяем что профиль есть
        assert 'profile' in data

        if data['profile']:
            # Проверяем что приватные поля скрыты
            assert 'bio' not in data['profile']
            assert 'experience_years' not in data['profile']

            # Проверяем что публичные поля есть
            assert 'specialization' in data['profile']
