"""
Unit тесты для валидации моделей профилей и новых полей.

Покрытие:
- Telegram поле для всех профилей
- Валидация и граничные случаи для новых полей
- Ограничения и constraints
"""
import pytest
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from accounts.models import (
    StudentProfile, TeacherProfile, TutorProfile, ParentProfile
)

User = get_user_model()


@pytest.mark.unit
@pytest.mark.django_db
class TestStudentProfileTelegram:
    """Тесты поля Telegram в StudentProfile"""

    def test_create_student_profile_with_telegram(self):
        """Тест создания профиля студента с Telegram"""
        user = User.objects.create_user(
            username='student_tg',
            email='student_tg@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(
            user=user,
            grade='10',
            telegram='@student_username'
        )

        assert profile.telegram == '@student_username'

    def test_student_profile_telegram_blank(self):
        """Тест что Telegram может быть пустым"""
        user = User.objects.create_user(
            username='student_notg',
            email='student_notg@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(
            user=user,
            grade='11'
        )

        assert profile.telegram == ''

    def test_student_profile_telegram_max_length(self):
        """Тест максимальной длины Telegram"""
        user = User.objects.create_user(
            username='student_tg_long',
            email='student_tg_long@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        # Telegram может быть до 100 символов
        long_tg = '@' + 'a' * 99
        profile = StudentProfile.objects.create(
            user=user,
            grade='9',
            telegram=long_tg
        )

        assert len(profile.telegram) == 100


@pytest.mark.unit
@pytest.mark.django_db
class TestTeacherProfileTelegram:
    """Тесты поля Telegram в TeacherProfile"""

    def test_create_teacher_profile_with_telegram(self):
        """Тест создания профиля преподавателя с Telegram"""
        user = User.objects.create_user(
            username='teacher_tg',
            email='teacher_tg@example.com',
            password='testpass123',
            role=User.Role.TEACHER
        )

        profile = TeacherProfile.objects.create(
            user=user,
            subject='Математика',
            telegram='@math_teacher'
        )

        assert profile.telegram == '@math_teacher'
        assert profile.subject == 'Математика'

    def test_teacher_profile_telegram_blank(self):
        """Тест что Telegram может быть пустым"""
        user = User.objects.create_user(
            username='teacher_notg',
            email='teacher_notg@example.com',
            password='testpass123',
            role=User.Role.TEACHER
        )

        profile = TeacherProfile.objects.create(
            user=user,
            subject='Физика'
        )

        assert profile.telegram == ''

    def test_teacher_profile_experience_boundary_values(self):
        """Тест граничных значений опыта работы"""
        user = User.objects.create_user(
            username='teacher_exp',
            email='teacher_exp@example.com',
            password='testpass123',
            role=User.Role.TEACHER
        )

        # Ноль лет опыта
        profile = TeacherProfile.objects.create(
            user=user,
            subject='Химия',
            experience_years=0
        )
        assert profile.experience_years == 0

        # 50 лет опыта
        profile.experience_years = 50
        profile.save()
        assert profile.experience_years == 50


@pytest.mark.unit
@pytest.mark.django_db
class TestTutorProfileTelegram:
    """Тесты поля Telegram в TutorProfile"""

    def test_create_tutor_profile_with_telegram(self):
        """Тест создания профиля тьютора с Telegram"""
        user = User.objects.create_user(
            username='tutor_tg',
            email='tutor_tg@example.com',
            password='testpass123',
            role=User.Role.TUTOR
        )

        profile = TutorProfile.objects.create(
            user=user,
            specialization='ОГЭ по математике',
            telegram='@tutor_pro'
        )

        assert profile.telegram == '@tutor_pro'
        assert profile.specialization == 'ОГЭ по математике'

    def test_tutor_profile_telegram_blank(self):
        """Тест что Telegram может быть пустым"""
        user = User.objects.create_user(
            username='tutor_notg',
            email='tutor_notg@example.com',
            password='testpass123',
            role=User.Role.TUTOR
        )

        profile = TutorProfile.objects.create(
            user=user,
            specialization='ЕГЭ по русскому'
        )

        assert profile.telegram == ''

    def test_tutor_profile_bio_max_length(self):
        """Тест максимальной длины биографии"""
        user = User.objects.create_user(
            username='tutor_bio',
            email='tutor_bio@example.com',
            password='testpass123',
            role=User.Role.TUTOR
        )

        # Биография может быть длинной
        long_bio = 'Это биография тьютора. ' * 20
        profile = TutorProfile.objects.create(
            user=user,
            specialization='Подготовка к экзаменам',
            bio=long_bio
        )

        assert len(profile.bio) > 200
        assert profile.bio.startswith('Это биография')


@pytest.mark.unit
@pytest.mark.django_db
class TestParentProfileTelegram:
    """Тесты поля Telegram в ParentProfile"""

    def test_create_parent_profile_with_telegram(self):
        """Тест создания профиля родителя с Telegram"""
        user = User.objects.create_user(
            username='parent_tg',
            email='parent_tg@example.com',
            password='testpass123',
            role=User.Role.PARENT
        )

        profile = ParentProfile.objects.create(
            user=user,
            telegram='@parent_name'
        )

        assert profile.telegram == '@parent_name'

    def test_parent_profile_telegram_blank(self):
        """Тест что Telegram может быть пустым"""
        user = User.objects.create_user(
            username='parent_notg',
            email='parent_notg@example.com',
            password='testpass123',
            role=User.Role.PARENT
        )

        profile = ParentProfile.objects.create(user=user)

        assert profile.telegram == ''

    def test_parent_profile_children_property(self):
        """Тест свойства children для получения детей"""
        parent = User.objects.create_user(
            username='parent_children',
            email='parent_children@example.com',
            password='testpass123',
            role=User.Role.PARENT
        )

        student1 = User.objects.create_user(
            username='student_child1',
            email='student_child1@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        student2 = User.objects.create_user(
            username='student_child2',
            email='student_child2@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        parent_profile = ParentProfile.objects.create(user=parent)
        StudentProfile.objects.create(user=student1, grade='9', parent=parent)
        StudentProfile.objects.create(user=student2, grade='10', parent=parent)

        children = parent_profile.children
        assert children.count() == 2
        assert student1 in children
        assert student2 in children


@pytest.mark.unit
@pytest.mark.django_db
class TestProfileFieldConstraints:
    """Тесты ограничений полей профилей"""

    def test_student_profile_grade_required(self):
        """Тест что класс может быть пустым (используется валидация в serializer)"""
        user = User.objects.create_user(
            username='student_no_grade',
            email='student_no_grade@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        # На уровне модели пустой grade не вызывает ошибку
        # Валидация происходит в serializer
        profile = StudentProfile.objects.create(user=user, grade='')
        assert profile.grade == ''

    def test_student_profile_progress_defaults(self):
        """Тест значений по умолчанию для прогресса"""
        user = User.objects.create_user(
            username='student_defaults',
            email='student_defaults@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(user=user, grade='8')

        assert profile.progress_percentage == 0
        assert profile.streak_days == 0
        assert profile.total_points == 0
        assert profile.accuracy_percentage == 0

    def test_teacher_profile_subject_required(self):
        """Тест что предмет может быть пустым (используется валидация в serializer)"""
        user = User.objects.create_user(
            username='teacher_no_subject',
            email='teacher_no_subject@example.com',
            password='testpass123',
            role=User.Role.TEACHER
        )

        # На уровне модели пустой subject не вызывает ошибку
        # Валидация происходит в serializer
        profile = TeacherProfile.objects.create(user=user, subject='')
        assert profile.subject == ''

    def test_tutor_profile_specialization_required(self):
        """Тест что специализация может быть пустой (используется валидация в serializer)"""
        user = User.objects.create_user(
            username='tutor_no_spec',
            email='tutor_no_spec@example.com',
            password='testpass123',
            role=User.Role.TUTOR
        )

        # На уровне модели пустая specialization не вызывает ошибку
        # Валидация происходит в serializer
        profile = TutorProfile.objects.create(user=user, specialization='')
        assert profile.specialization == ''

    def test_profile_one_to_one_cascade_delete(self):
        """Тест каскадного удаления профиля при удалении пользователя"""
        user = User.objects.create_user(
            username='user_cascade',
            email='user_cascade@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(user=user, grade='7')
        profile_id = profile.id

        # Удаляем пользователя
        user.delete()

        # Профиль должен быть удален
        assert not StudentProfile.objects.filter(id=profile_id).exists()
