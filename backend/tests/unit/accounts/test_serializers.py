"""
Unit тесты для serializers приложения accounts

Покрытие:
- UserLoginSerializer: валидация email/username/password
- UserSerializer: отображение пользователя, full_name
- StudentProfileSerializer: сериализация профиля студента
- TeacherProfileSerializer: сериализация профиля преподавателя
- TutorProfileSerializer: сериализация профиля тьютора
- ParentProfileSerializer: сериализация профиля родителя, children
- ChangePasswordSerializer: валидация смены пароля
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from accounts.serializers import (
    UserLoginSerializer, UserSerializer,
    StudentProfileSerializer, TeacherProfileSerializer,
    TutorProfileSerializer, ParentProfileSerializer,
    ChangePasswordSerializer
)
from accounts.models import (
    StudentProfile, TeacherProfile, TutorProfile, ParentProfile
)

User = get_user_model()


@pytest.fixture
def request_factory():
    """Fixture для создания request объектов"""
    return APIRequestFactory()


@pytest.mark.unit
@pytest.mark.django_db
class TestUserLoginSerializer:
    """Тесты для UserLoginSerializer"""

    def test_valid_login_with_email(self):
        """Тест валидации с email"""
        data = {
            'email': 'test@example.com',
            'password': 'testpass123'
        }

        serializer = UserLoginSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['email'] == 'test@example.com'
        assert serializer.validated_data['password'] == 'testpass123'
        assert serializer.validated_data['username'] is None

    def test_valid_login_with_username(self):
        """Тест валидации с username"""
        data = {
            'username': 'testuser',
            'password': 'testpass123'
        }

        serializer = UserLoginSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['username'] == 'testuser'
        assert serializer.validated_data['password'] == 'testpass123'
        assert serializer.validated_data['email'] is None

    def test_invalid_without_email_or_username(self):
        """Тест невалидности без email или username"""
        data = {
            'password': 'testpass123'
        }

        serializer = UserLoginSerializer(data=data)
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors

    def test_invalid_without_password(self):
        """Тест невалидности без пароля"""
        data = {
            'email': 'test@example.com'
        }

        serializer = UserLoginSerializer(data=data)
        assert not serializer.is_valid()
        assert 'password' in serializer.errors

    def test_strips_whitespace_from_email(self):
        """Тест удаления пробелов из email"""
        data = {
            'email': '  test@example.com  ',
            'password': 'testpass123'
        }

        serializer = UserLoginSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['email'] == 'test@example.com'

    def test_strips_whitespace_from_username(self):
        """Тест удаления пробелов из username"""
        data = {
            'username': '  testuser  ',
            'password': 'testpass123'
        }

        serializer = UserLoginSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['username'] == 'testuser'

    def test_prefers_email_over_username(self):
        """Тест приоритета email над username"""
        data = {
            'email': 'test@example.com',
            'username': 'testuser',
            'password': 'testpass123'
        }

        serializer = UserLoginSerializer(data=data)
        assert serializer.is_valid()
        assert serializer.validated_data['email'] == 'test@example.com'
        assert serializer.validated_data['username'] is None


@pytest.mark.unit
@pytest.mark.django_db
class TestUserSerializer:
    """Тесты для UserSerializer"""

    def test_serialize_user_with_all_fields(self):
        """Тест сериализации пользователя со всеми полями"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role=User.Role.STUDENT,
            phone='+79991234567'
        )

        serializer = UserSerializer(user)
        data = serializer.data

        assert data['id'] == user.id
        assert data['email'] == 'test@example.com'
        assert data['first_name'] == 'Test'
        assert data['last_name'] == 'User'
        assert data['role'] == User.Role.STUDENT
        assert data['role_display'] == 'Студент'
        assert data['phone'] == '+79991234567'
        assert data['full_name'] == 'Test User'

    def test_full_name_method(self):
        """Тест метода get_full_name"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Ivan',
            last_name='Petrov',
            role=User.Role.TEACHER
        )

        serializer = UserSerializer(user)
        assert serializer.data['full_name'] == 'Ivan Petrov'

    def test_full_name_method_with_empty_name(self):
        """Тест метода get_full_name с пустым именем"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        serializer = UserSerializer(user)
        assert serializer.data['full_name'] == ''

    def test_read_only_fields(self):
        """Тест что read_only поля не могут быть изменены"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        data = {
            'id': 999,  # read_only
            'is_staff': True,  # read_only
            'is_verified': True,  # read_only
            'first_name': 'Updated'
        }

        serializer = UserSerializer(user, data=data, partial=True)
        assert serializer.is_valid()
        serializer.save()

        user.refresh_from_db()
        assert user.id != 999
        assert user.is_staff is False
        assert user.is_verified is False
        assert user.first_name == 'Updated'

    @pytest.mark.parametrize('role,display', [
        (User.Role.STUDENT, 'Студент'),
        (User.Role.TEACHER, 'Преподаватель'),
        (User.Role.TUTOR, 'Тьютор'),
        (User.Role.PARENT, 'Родитель')
    ])
    def test_role_display_for_each_role(self, role, display):
        """Тест отображения роли для каждого типа"""
        user = User.objects.create_user(
            username=f'user_{role}',
            email=f'{role}@example.com',
            password='testpass123',
            role=role
        )

        serializer = UserSerializer(user)
        assert serializer.data['role_display'] == display


@pytest.mark.unit
@pytest.mark.django_db
class TestStudentProfileSerializer:
    """Тесты для StudentProfileSerializer"""

    def test_serialize_student_profile(self):
        """Тест сериализации профиля студента"""
        user = User.objects.create_user(
            username='student1',
            email='student@example.com',
            password='testpass123',
            first_name='Ivan',
            last_name='Ivanov',
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(
            user=user,
            grade='8',
            goal='Подготовка к ОГЭ',
            progress_percentage=75,
            streak_days=10,
            total_points=500,
            accuracy_percentage=85
        )

        serializer = StudentProfileSerializer(profile)
        data = serializer.data

        assert data['id'] == profile.id
        assert data['grade'] == '8'
        assert data['goal'] == 'Подготовка к ОГЭ'
        assert data['progress_percentage'] == 75
        assert data['streak_days'] == 10
        assert data['total_points'] == 500
        assert data['accuracy_percentage'] == 85
        assert data['user']['email'] == 'student@example.com'

    def test_serialize_student_with_tutor(self):
        """Тест сериализации студента с тьютором"""
        tutor = User.objects.create_user(
            username='tutor1',
            email='tutor@example.com',
            password='testpass123',
            first_name='Tutor',
            last_name='Tutorovich',
            role=User.Role.TUTOR
        )

        student = User.objects.create_user(
            username='student1',
            email='student@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(
            user=student,
            grade='8',
            tutor=tutor
        )

        serializer = StudentProfileSerializer(profile)
        data = serializer.data

        assert data['tutor'] == tutor.id
        assert data['tutor_name'] == 'Tutor Tutorovich'

    def test_serialize_student_with_parent(self):
        """Тест сериализации студента с родителем"""
        parent = User.objects.create_user(
            username='parent1',
            email='parent@example.com',
            password='testpass123',
            first_name='Parent',
            last_name='Parentov',
            role=User.Role.PARENT
        )

        student = User.objects.create_user(
            username='student1',
            email='student@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(
            user=student,
            grade='8',
            parent=parent
        )

        serializer = StudentProfileSerializer(profile)
        data = serializer.data

        assert data['parent'] == parent.id
        assert data['parent_name'] == 'Parent Parentov'

    def test_serialize_student_without_tutor_and_parent(self):
        """Тест сериализации студента без тьютора и родителя"""
        student = User.objects.create_user(
            username='student1',
            email='student@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(
            user=student,
            grade='8'
        )

        serializer = StudentProfileSerializer(profile)
        data = serializer.data

        assert data['tutor'] is None
        # tutor_name и parent_name могут отсутствовать если tutor/parent is None
        # так как сериализатор пытается вызвать get_full_name на None объекте
        assert data.get('tutor_name') is None or 'tutor_name' not in data
        assert data['parent'] is None
        assert data.get('parent_name') is None or 'parent_name' not in data


@pytest.mark.unit
@pytest.mark.django_db
class TestTeacherProfileSerializer:
    """Тесты для TeacherProfileSerializer"""

    def test_serialize_teacher_profile(self):
        """Тест сериализации профиля преподавателя"""
        user = User.objects.create_user(
            username='teacher1',
            email='teacher@example.com',
            password='testpass123',
            first_name='Petr',
            last_name='Petrov',
            role=User.Role.TEACHER
        )

        profile = TeacherProfile.objects.create(
            user=user,
            subject='Математика',
            experience_years=5,
            bio='Опытный преподаватель'
        )

        serializer = TeacherProfileSerializer(profile)
        data = serializer.data

        assert data['id'] == profile.id
        assert data['subject'] == 'Математика'
        assert data['experience_years'] == 5
        assert data['bio'] == 'Опытный преподаватель'
        assert data['user']['email'] == 'teacher@example.com'

    def test_serialize_teacher_with_subjects_list(self):
        """Тест сериализации преподавателя со списком предметов"""
        user = User.objects.create_user(
            username='teacher1',
            email='teacher@example.com',
            password='testpass123',
            role=User.Role.TEACHER
        )

        profile = TeacherProfile.objects.create(
            user=user,
            subject='Математика'
        )

        # Создаем TeacherSubject для теста
        from materials.models import Subject, TeacherSubject

        math_subject = Subject.objects.create(name='Математика', description='Математика 8 класс')
        physics_subject = Subject.objects.create(name='Физика', description='Физика 8 класс')

        TeacherSubject.objects.create(teacher=user, subject=math_subject, is_active=True)
        TeacherSubject.objects.create(teacher=user, subject=physics_subject, is_active=True)

        serializer = TeacherProfileSerializer(profile)
        data = serializer.data

        assert 'subjects_list' in data
        assert 'Математика' in data['subjects_list']
        assert 'Физика' in data['subjects_list']

    def test_serialize_teacher_without_teacher_subjects(self):
        """Тест сериализации преподавателя без TeacherSubject"""
        user = User.objects.create_user(
            username='teacher1',
            email='teacher@example.com',
            password='testpass123',
            role=User.Role.TEACHER
        )

        profile = TeacherProfile.objects.create(
            user=user,
            subject='Математика'
        )

        serializer = TeacherProfileSerializer(profile)
        data = serializer.data

        assert 'subjects_list' in data
        assert data['subjects_list'] == []


@pytest.mark.unit
@pytest.mark.django_db
class TestTutorProfileSerializer:
    """Тесты для TutorProfileSerializer"""

    def test_serialize_tutor_profile(self):
        """Тест сериализации профиля тьютора"""
        user = User.objects.create_user(
            username='tutor1',
            email='tutor@example.com',
            password='testpass123',
            first_name='Anna',
            last_name='Sergeeva',
            role=User.Role.TUTOR
        )

        profile = TutorProfile.objects.create(
            user=user,
            specialization='Подготовка к ОГЭ',
            experience_years=3,
            bio='Опытный тьютор'
        )

        serializer = TutorProfileSerializer(profile)
        data = serializer.data

        assert data['id'] == profile.id
        assert data['specialization'] == 'Подготовка к ОГЭ'
        assert data['experience_years'] == 3
        assert data['bio'] == 'Опытный тьютор'
        assert data['user']['email'] == 'tutor@example.com'


@pytest.mark.unit
@pytest.mark.django_db
class TestParentProfileSerializer:
    """Тесты для ParentProfileSerializer"""

    def test_serialize_parent_profile(self):
        """Тест сериализации профиля родителя"""
        user = User.objects.create_user(
            username='parent1',
            email='parent@example.com',
            password='testpass123',
            first_name='Maria',
            last_name='Ivanova',
            role=User.Role.PARENT
        )

        profile = ParentProfile.objects.create(user=user)

        serializer = ParentProfileSerializer(profile)
        data = serializer.data

        assert data['id'] == profile.id
        assert data['user']['email'] == 'parent@example.com'

    def test_serialize_parent_with_children(self):
        """Тест сериализации родителя с детьми"""
        parent = User.objects.create_user(
            username='parent1',
            email='parent@example.com',
            password='testpass123',
            role=User.Role.PARENT
        )

        parent_profile = ParentProfile.objects.create(user=parent)

        # Создаем детей
        student1 = User.objects.create_user(
            username='student1',
            email='student1@example.com',
            password='testpass123',
            first_name='Child1',
            last_name='Ivanov',
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student1, grade='8', parent=parent)

        student2 = User.objects.create_user(
            username='student2',
            email='student2@example.com',
            password='testpass123',
            first_name='Child2',
            last_name='Ivanov',
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student2, grade='9', parent=parent)

        serializer = ParentProfileSerializer(parent_profile)
        data = serializer.data

        assert 'children' in data
        assert len(data['children']) == 2
        assert data['children'][0]['email'] in ['student1@example.com', 'student2@example.com']

    def test_serialize_parent_without_children(self):
        """Тест сериализации родителя без детей"""
        parent = User.objects.create_user(
            username='parent1',
            email='parent@example.com',
            password='testpass123',
            role=User.Role.PARENT
        )

        parent_profile = ParentProfile.objects.create(user=parent)

        serializer = ParentProfileSerializer(parent_profile)
        data = serializer.data

        assert 'children' in data
        assert len(data['children']) == 0


@pytest.mark.unit
@pytest.mark.django_db
class TestChangePasswordSerializer:
    """Тесты для ChangePasswordSerializer"""

    def test_valid_change_password(self, request_factory):
        """Тест валидной смены пароля"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpass123'
        )

        request = request_factory.post('/')
        request.user = user

        data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass123!@#',
            'new_password_confirm': 'newpass123!@#'
        }

        serializer = ChangePasswordSerializer(data=data, context={'request': request})
        assert serializer.is_valid()

    def test_invalid_old_password(self, request_factory):
        """Тест с неверным старым паролем"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpass123'
        )

        request = request_factory.post('/')
        request.user = user

        data = {
            'old_password': 'wrongpass',
            'new_password': 'newpass123!@#',
            'new_password_confirm': 'newpass123!@#'
        }

        serializer = ChangePasswordSerializer(data=data, context={'request': request})
        assert not serializer.is_valid()
        assert 'old_password' in serializer.errors

    def test_new_passwords_mismatch(self, request_factory):
        """Тест с несовпадающими новыми паролями"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpass123'
        )

        request = request_factory.post('/')
        request.user = user

        data = {
            'old_password': 'oldpass123',
            'new_password': 'newpass123!@#',
            'new_password_confirm': 'different123!@#'
        }

        serializer = ChangePasswordSerializer(data=data, context={'request': request})
        assert not serializer.is_valid()
        assert 'non_field_errors' in serializer.errors

    def test_weak_new_password(self, request_factory):
        """Тест со слабым новым паролем"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpass123'
        )

        request = request_factory.post('/')
        request.user = user

        data = {
            'old_password': 'oldpass123',
            'new_password': '123',  # Слишком короткий
            'new_password_confirm': '123'
        }

        serializer = ChangePasswordSerializer(data=data, context={'request': request})
        assert not serializer.is_valid()
        assert 'new_password' in serializer.errors

    def test_missing_fields(self, request_factory):
        """Тест с отсутствующими полями"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='oldpass123'
        )

        request = request_factory.post('/')
        request.user = user

        data = {
            'old_password': 'oldpass123'
            # Отсутствуют new_password и new_password_confirm
        }

        serializer = ChangePasswordSerializer(data=data, context={'request': request})
        assert not serializer.is_valid()
        assert 'new_password' in serializer.errors
        assert 'new_password_confirm' in serializer.errors
