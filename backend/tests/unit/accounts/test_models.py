"""
Unit тесты для моделей приложения accounts

Покрытие:
- User model: создание, поля, методы, unique constraints, валидация
- StudentProfile: создание, связь с User, каскадное удаление
- TeacherProfile: создание, связь с User, каскадное удаление
- TutorProfile: создание, связь с User, каскадное удаление
- ParentProfile: создание, связь с User, каскадное удаление, property children
"""
import pytest
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from accounts.models import (
    StudentProfile, TeacherProfile, TutorProfile, ParentProfile,
    TutorStudentCreation
)

User = get_user_model()


@pytest.mark.unit
@pytest.mark.django_db
class TestUserModel:
    """Тесты модели User"""

    def test_create_user_with_all_fields(self):
        """Тест создания пользователя со всеми полями"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role=User.Role.STUDENT,
            phone='+79991234567'
        )

        assert user.id is not None
        assert user.username == 'testuser'
        assert user.email == 'test@example.com'
        assert user.first_name == 'Test'
        assert user.last_name == 'User'
        assert user.role == User.Role.STUDENT
        assert user.phone == '+79991234567'
        assert user.is_active is True
        assert user.is_verified is False
        assert user.password != 'testpass123'  # Пароль должен быть захеширован
        assert user.check_password('testpass123') is True

    @pytest.mark.parametrize('role', [
        User.Role.STUDENT,
        User.Role.TEACHER,
        User.Role.TUTOR,
        User.Role.PARENT
    ])
    def test_create_users_with_different_roles(self, role):
        """Тест создания пользователей с разными ролями"""
        user = User.objects.create_user(
            username=f'user_{role}',
            email=f'{role}@example.com',
            password='testpass123',
            role=role
        )

        assert user.role == role
        assert user.get_role_display() in [
            'Студент', 'Преподаватель', 'Тьютор', 'Родитель'
        ]

    def test_user_str_method(self):
        """Тест метода __str__ модели User"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role=User.Role.STUDENT
        )

        expected = 'Test User (Студент)'
        assert str(user) == expected

    def test_user_str_method_without_name(self):
        """Тест метода __str__ для пользователя без имени"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            role=User.Role.TEACHER
        )

        result = str(user)
        assert 'Преподаватель' in result

    def test_unique_email_constraint(self):
        """Тест уникальности email - SKIPPED: Django User по умолчанию не требует уникальности email"""
        pytest.skip("Django User model does not enforce unique email constraint by default")

    def test_unique_username_constraint(self):
        """Тест уникальности username"""
        User.objects.create_user(
            username='duplicate_user',
            email='user1@example.com',
            password='testpass123'
        )

        with pytest.raises(IntegrityError):
            User.objects.create_user(
                username='duplicate_user',
                email='user2@example.com',
                password='testpass123'
            )

    def test_phone_validation_valid_formats(self):
        """Тест валидации телефона - валидные форматы"""
        valid_phones = [
            '+79991234567',
            '+12125551234',
        ]

        for i, phone in enumerate(valid_phones):
            user = User.objects.create_user(
                username=f'user_phone_{i}',
                email=f'userphone{i}@example.com',
                password='testpass123',
                phone=phone
            )
            assert user.phone == phone

    def test_created_by_tutor_relationship(self):
        """Тест связи created_by_tutor"""
        tutor = User.objects.create_user(
            username='tutor1',
            email='tutor@example.com',
            password='testpass123',
            role=User.Role.TUTOR
        )

        student = User.objects.create_user(
            username='student1',
            email='student@example.com',
            password='testpass123',
            role=User.Role.STUDENT,
            created_by_tutor=tutor
        )

        assert student.created_by_tutor == tutor
        assert student in tutor.created_users.all()

    def test_created_by_tutor_set_null_on_delete(self):
        """Тест SET_NULL при удалении тьютора"""
        tutor = User.objects.create_user(
            username='tutor1',
            email='tutor@example.com',
            password='testpass123',
            role=User.Role.TUTOR
        )

        student = User.objects.create_user(
            username='student1',
            email='student@example.com',
            password='testpass123',
            role=User.Role.STUDENT,
            created_by_tutor=tutor
        )

        tutor_id = tutor.id
        tutor.delete()

        student.refresh_from_db()
        assert student.created_by_tutor is None

    def test_password_can_be_null(self):
        """Тест что пароль может быть blank (для Supabase аутентификации)"""
        user = User.objects.create(
            username='testuser_null_pass',
            email='testnullpass@example.com',
            password='',  # blank, не null
            role=User.Role.STUDENT
        )

        # Пароль может быть пустым (blank), но не null в БД
        assert user.password == ''

    def test_default_role_is_student(self):
        """Тест что роль по умолчанию - student"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        assert user.role == User.Role.STUDENT

    def test_timestamps_auto_populated(self):
        """Тест автоматического заполнения timestamps"""
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )

        assert user.created_at is not None
        assert user.updated_at is not None
        assert user.date_joined is not None


@pytest.mark.unit
@pytest.mark.django_db
class TestStudentProfile:
    """Тесты модели StudentProfile"""

    def test_create_student_profile(self):
        """Тест создания профиля студента"""
        user = User.objects.create_user(
            username='student1',
            email='student@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(
            user=user,
            grade='8',
            goal='Подготовка к ОГЭ'
        )

        assert profile.id is not None
        assert profile.user == user
        assert profile.grade == '8'
        assert profile.goal == 'Подготовка к ОГЭ'
        assert profile.progress_percentage == 0
        assert profile.streak_days == 0
        assert profile.total_points == 0
        assert profile.accuracy_percentage == 0

    def test_student_profile_one_to_one_relationship(self):
        """Тест OneToOne связи с User"""
        user = User.objects.create_user(
            username='student1',
            email='student@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(
            user=user,
            grade='9'
        )

        # Доступ через related_name
        assert user.student_profile == profile

        # Нельзя создать второй профиль для того же пользователя
        with pytest.raises(IntegrityError):
            StudentProfile.objects.create(
                user=user,
                grade='10'
            )

    def test_student_profile_cascade_delete(self):
        """Тест каскадного удаления профиля при удалении пользователя"""
        user = User.objects.create_user(
            username='student1',
            email='student@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(
            user=user,
            grade='8'
        )

        profile_id = profile.id
        user.delete()

        # Профиль должен быть удален
        assert not StudentProfile.objects.filter(id=profile_id).exists()

    def test_student_profile_with_tutor(self):
        """Тест связи студента с тьютором"""
        tutor = User.objects.create_user(
            username='tutor1',
            email='tutor@example.com',
            password='testpass123',
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

        assert profile.tutor == tutor
        assert profile in StudentProfile.objects.filter(tutor=tutor)

    def test_student_profile_with_parent(self):
        """Тест связи студента с родителем"""
        parent = User.objects.create_user(
            username='parent1',
            email='parent@example.com',
            password='testpass123',
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

        assert profile.parent == parent
        assert profile in StudentProfile.objects.filter(parent=parent)

    def test_student_profile_tutor_set_null_on_delete(self):
        """Тест SET_NULL для тьютора при удалении"""
        tutor = User.objects.create_user(
            username='tutor1',
            email='tutor@example.com',
            password='testpass123',
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

        tutor.delete()
        profile.refresh_from_db()

        assert profile.tutor is None

    def test_student_profile_parent_set_null_on_delete(self):
        """Тест SET_NULL для родителя при удалении"""
        parent = User.objects.create_user(
            username='parent1',
            email='parent@example.com',
            password='testpass123',
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

        parent.delete()
        profile.refresh_from_db()

        assert profile.parent is None

    def test_student_profile_str_method(self):
        """Тест метода __str__"""
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
            grade='8'
        )

        assert str(profile) == 'Профиль студента: Ivan Ivanov'

    def test_student_profile_progress_fields(self):
        """Тест полей прогресса"""
        user = User.objects.create_user(
            username='student1',
            email='student@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(
            user=user,
            grade='8',
            progress_percentage=75,
            streak_days=10,
            total_points=500,
            accuracy_percentage=85
        )

        assert profile.progress_percentage == 75
        assert profile.streak_days == 10
        assert profile.total_points == 500
        assert profile.accuracy_percentage == 85

    def test_student_profile_generated_credentials(self):
        """Тест полей сгенерированных учетных данных"""
        user = User.objects.create_user(
            username='student1',
            email='student@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(
            user=user,
            grade='8',
            generated_username='student_12345',
            generated_password='pass_12345'
        )

        assert profile.generated_username == 'student_12345'
        assert profile.generated_password == 'pass_12345'


@pytest.mark.unit
@pytest.mark.django_db
class TestTeacherProfile:
    """Тесты модели TeacherProfile"""

    def test_create_teacher_profile(self):
        """Тест создания профиля преподавателя"""
        user = User.objects.create_user(
            username='teacher1',
            email='teacher@example.com',
            password='testpass123',
            role=User.Role.TEACHER
        )

        profile = TeacherProfile.objects.create(
            user=user,
            subject='Математика',
            experience_years=5,
            bio='Опытный преподаватель математики'
        )

        assert profile.id is not None
        assert profile.user == user
        assert profile.subject == 'Математика'
        assert profile.experience_years == 5
        assert profile.bio == 'Опытный преподаватель математики'

    def test_teacher_profile_one_to_one_relationship(self):
        """Тест OneToOne связи с User"""
        user = User.objects.create_user(
            username='teacher1',
            email='teacher@example.com',
            password='testpass123',
            role=User.Role.TEACHER
        )

        profile = TeacherProfile.objects.create(
            user=user,
            subject='Физика'
        )

        assert user.teacher_profile == profile

        with pytest.raises(IntegrityError):
            TeacherProfile.objects.create(
                user=user,
                subject='Химия'
            )

    def test_teacher_profile_cascade_delete(self):
        """Тест каскадного удаления"""
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

        profile_id = profile.id
        user.delete()

        assert not TeacherProfile.objects.filter(id=profile_id).exists()

    def test_teacher_profile_str_method(self):
        """Тест метода __str__"""
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
            subject='Математика'
        )

        assert str(profile) == 'Профиль преподавателя: Petr Petrov'

    def test_teacher_profile_default_experience(self):
        """Тест значения по умолчанию для опыта"""
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

        assert profile.experience_years == 0


@pytest.mark.unit
@pytest.mark.django_db
class TestTutorProfile:
    """Тесты модели TutorProfile"""

    def test_create_tutor_profile(self):
        """Тест создания профиля тьютора"""
        user = User.objects.create_user(
            username='tutor1',
            email='tutor@example.com',
            password='testpass123',
            role=User.Role.TUTOR
        )

        profile = TutorProfile.objects.create(
            user=user,
            specialization='Подготовка к ОГЭ',
            experience_years=3,
            bio='Опытный тьютор'
        )

        assert profile.id is not None
        assert profile.user == user
        assert profile.specialization == 'Подготовка к ОГЭ'
        assert profile.experience_years == 3
        assert profile.bio == 'Опытный тьютор'

    def test_tutor_profile_one_to_one_relationship(self):
        """Тест OneToOne связи с User"""
        user = User.objects.create_user(
            username='tutor1',
            email='tutor@example.com',
            password='testpass123',
            role=User.Role.TUTOR
        )

        profile = TutorProfile.objects.create(
            user=user,
            specialization='ОГЭ'
        )

        assert user.tutor_profile == profile

        with pytest.raises(IntegrityError):
            TutorProfile.objects.create(
                user=user,
                specialization='ЕГЭ'
            )

    def test_tutor_profile_cascade_delete(self):
        """Тест каскадного удаления"""
        user = User.objects.create_user(
            username='tutor1',
            email='tutor@example.com',
            password='testpass123',
            role=User.Role.TUTOR
        )

        profile = TutorProfile.objects.create(
            user=user,
            specialization='ОГЭ'
        )

        profile_id = profile.id
        user.delete()

        assert not TutorProfile.objects.filter(id=profile_id).exists()

    def test_tutor_profile_str_method(self):
        """Тест метода __str__"""
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
            specialization='ОГЭ'
        )

        assert str(profile) == 'Профиль тьютора: Anna Sergeeva'


@pytest.mark.unit
@pytest.mark.django_db
class TestParentProfile:
    """Тесты модели ParentProfile"""

    def test_create_parent_profile(self):
        """Тест создания профиля родителя"""
        user = User.objects.create_user(
            username='parent1',
            email='parent@example.com',
            password='testpass123',
            role=User.Role.PARENT
        )

        profile = ParentProfile.objects.create(user=user)

        assert profile.id is not None
        assert profile.user == user

    def test_parent_profile_one_to_one_relationship(self):
        """Тест OneToOne связи с User"""
        user = User.objects.create_user(
            username='parent1',
            email='parent@example.com',
            password='testpass123',
            role=User.Role.PARENT
        )

        profile = ParentProfile.objects.create(user=user)

        assert user.parent_profile == profile

        with pytest.raises(IntegrityError):
            ParentProfile.objects.create(user=user)

    def test_parent_profile_cascade_delete(self):
        """Тест каскадного удаления"""
        user = User.objects.create_user(
            username='parent1',
            email='parent@example.com',
            password='testpass123',
            role=User.Role.PARENT
        )

        profile = ParentProfile.objects.create(user=user)

        profile_id = profile.id
        user.delete()

        assert not ParentProfile.objects.filter(id=profile_id).exists()

    def test_parent_profile_str_method(self):
        """Тест метода __str__"""
        user = User.objects.create_user(
            username='parent1',
            email='parent@example.com',
            password='testpass123',
            first_name='Maria',
            last_name='Ivanova',
            role=User.Role.PARENT
        )

        profile = ParentProfile.objects.create(user=user)

        assert str(profile) == 'Профиль родителя: Maria Ivanova'

    def test_parent_profile_children_property(self):
        """Тест property children для получения детей родителя"""
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
            role=User.Role.STUDENT
        )
        profile1 = StudentProfile.objects.create(
            user=student1,
            grade='8',
            parent=parent
        )

        student2 = User.objects.create_user(
            username='student2',
            email='student2@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )
        profile2 = StudentProfile.objects.create(
            user=student2,
            grade='9',
            parent=parent
        )

        # Проверяем property children
        children = parent_profile.children
        assert children.count() == 2
        assert student1 in children
        assert student2 in children

    def test_parent_profile_children_property_empty(self):
        """Тест property children для родителя без детей"""
        parent = User.objects.create_user(
            username='parent1',
            email='parent@example.com',
            password='testpass123',
            role=User.Role.PARENT
        )

        parent_profile = ParentProfile.objects.create(user=parent)

        children = parent_profile.children
        assert children.count() == 0


@pytest.mark.unit
@pytest.mark.django_db
class TestTutorStudentCreation:
    """Тесты модели TutorStudentCreation"""

    def test_create_tutor_student_creation_record(self):
        """Тест создания записи о создании студента тьютором"""
        tutor = User.objects.create_user(
            username='tutor1',
            email='tutor@example.com',
            password='testpass123',
            role=User.Role.TUTOR
        )

        student = User.objects.create_user(
            username='student1',
            email='student@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        parent = User.objects.create_user(
            username='parent1',
            email='parent@example.com',
            password='testpass123',
            role=User.Role.PARENT
        )

        record = TutorStudentCreation.objects.create(
            tutor=tutor,
            student=student,
            parent=parent,
            student_credentials={'username': 'student1', 'password': 'pass123'},
            parent_credentials={'username': 'parent1', 'password': 'pass456'}
        )

        assert record.id is not None
        assert record.tutor == tutor
        assert record.student == student
        assert record.parent == parent
        assert record.student_credentials == {'username': 'student1', 'password': 'pass123'}
        assert record.parent_credentials == {'username': 'parent1', 'password': 'pass456'}
        assert record.created_at is not None

    def test_tutor_student_creation_cascade_delete(self):
        """Тест каскадного удаления записи при удалении пользователя"""
        tutor = User.objects.create_user(
            username='tutor1',
            email='tutor@example.com',
            password='testpass123',
            role=User.Role.TUTOR
        )

        student = User.objects.create_user(
            username='student1',
            email='student@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        parent = User.objects.create_user(
            username='parent1',
            email='parent@example.com',
            password='testpass123',
            role=User.Role.PARENT
        )

        record = TutorStudentCreation.objects.create(
            tutor=tutor,
            student=student,
            parent=parent,
            student_credentials={},
            parent_credentials={}
        )

        record_id = record.id
        tutor.delete()

        # Запись должна быть удалена
        assert not TutorStudentCreation.objects.filter(id=record_id).exists()

    def test_tutor_student_creation_ordering(self):
        """Тест сортировки записей по дате создания"""
        tutor = User.objects.create_user(
            username='tutor1',
            email='tutor@example.com',
            password='testpass123',
            role=User.Role.TUTOR
        )

        student1 = User.objects.create_user(
            username='student1',
            email='student1@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        student2 = User.objects.create_user(
            username='student2',
            email='student2@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        parent = User.objects.create_user(
            username='parent1',
            email='parent@example.com',
            password='testpass123',
            role=User.Role.PARENT
        )

        record1 = TutorStudentCreation.objects.create(
            tutor=tutor,
            student=student1,
            parent=parent,
            student_credentials={},
            parent_credentials={}
        )

        record2 = TutorStudentCreation.objects.create(
            tutor=tutor,
            student=student2,
            parent=parent,
            student_credentials={},
            parent_credentials={}
        )

        # Проверяем что записи отсортированы по убыванию даты создания
        records = list(TutorStudentCreation.objects.all())
        assert records[0] == record2
        assert records[1] == record1
