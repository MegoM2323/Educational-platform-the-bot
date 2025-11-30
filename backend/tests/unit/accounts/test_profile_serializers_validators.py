"""
Unit тесты для валидации сериализеров профилей.

Покрытие:
- StudentProfileDetailSerializer: валидация всех полей
- TeacherProfileDetailSerializer: валидация всех полей
- TutorProfileDetailSerializer: валидация всех полей
- ParentProfileDetailSerializer: валидация всех полей
- UserProfileUpdateSerializer: валидация полей пользователя
- Telegram валидация
- Телефон валидация
- Аватар валидация
"""
import pytest
from io import BytesIO
from PIL import Image
from django.contrib.auth import get_user_model
from rest_framework.test import APIRequestFactory

from accounts.serializers import UserSerializer
from accounts.profile_serializers import (
    StudentProfileDetailSerializer,
    TeacherProfileDetailSerializer,
    TutorProfileDetailSerializer,
    ParentProfileDetailSerializer,
    UserProfileUpdateSerializer,
    TelegramValidator,
    PhoneValidator
)
from accounts.models import StudentProfile, TeacherProfile, TutorProfile, ParentProfile

User = get_user_model()


@pytest.fixture
def request_factory():
    """Fixture для создания request объектов"""
    return APIRequestFactory()


def create_test_image(name='test.jpg', size=(100, 100), format='JPEG'):
    """Помощник для создания тестовых изображений"""
    image = Image.new('RGB', size)
    image_io = BytesIO()
    image.save(image_io, format=format)
    image_io.seek(0)
    return image_io


@pytest.mark.unit
class TestTelegramValidator:
    """Тесты валидатора Telegram"""

    def test_valid_telegram_with_at_symbol(self):
        """Тест валидного Telegram с @"""
        validator = TelegramValidator()
        # Не должно быть исключений
        validator('@username123')

    def test_valid_telegram_without_at_symbol(self):
        """Тест валидного Telegram без @"""
        validator = TelegramValidator()
        validator('username123')

    def test_invalid_telegram_too_short(self):
        """Тест невалидного Telegram - слишком короткий"""
        validator = TelegramValidator()
        with pytest.raises(Exception):  # ValidationError
            validator('@usr')

    def test_invalid_telegram_special_chars(self):
        """Тест невалидного Telegram - недопустимые символы"""
        validator = TelegramValidator()
        with pytest.raises(Exception):
            validator('@user-name')

    def test_invalid_telegram_empty(self):
        """Тест что пустой Telegram - OK (опционально)"""
        validator = TelegramValidator()
        # Пустое значение должно быть OK
        validator('')

    def test_valid_telegram_max_length(self):
        """Тест Telegram максимальной длины"""
        validator = TelegramValidator()
        long_username = '@' + 'a' * 32  # 32 символа username (без @)
        validator(long_username)

    def test_invalid_telegram_too_long(self):
        """Тест Telegram слишком длинный"""
        validator = TelegramValidator()
        too_long = '@' + 'a' * 33  # 33 символа username (слишком много)
        with pytest.raises(Exception):
            validator(too_long)


@pytest.mark.unit
class TestPhoneValidator:
    """Тесты валидатора телефона"""

    def test_valid_phone_with_plus(self):
        """Тест валидного телефона с +"""
        validator = PhoneValidator()
        validator('+79991234567')

    def test_valid_phone_with_dashes(self):
        """Тест валидного телефона с дефисами"""
        validator = PhoneValidator()
        validator('+7-999-123-45-67')

    def test_valid_phone_with_spaces(self):
        """Тест валидного телефона с пробелами"""
        validator = PhoneValidator()
        validator('+7 999 123 45 67')

    def test_valid_phone_with_parentheses(self):
        """Тест валидного телефона со скобками"""
        validator = PhoneValidator()
        validator('+7 (999) 123-45-67')

    def test_invalid_phone_too_short(self):
        """Тест телефона - слишком короткий"""
        validator = PhoneValidator()
        with pytest.raises(Exception):
            validator('+1234')

    def test_invalid_phone_empty(self):
        """Тест пустого телефона - OK"""
        validator = PhoneValidator()
        # Пустое значение должно быть OK
        validator('')


@pytest.mark.unit
@pytest.mark.django_db
class TestStudentProfileDetailSerializer:
    """Тесты StudentProfileDetailSerializer"""

    def test_serialize_student_profile_all_fields(self):
        """Тест сериализации всех полей профиля студента"""
        user = User.objects.create_user(
            username='student_serial',
            email='student_serial@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(
            user=user,
            grade='10',
            goal='Подготовка к ЕГЭ',
            telegram='@student_username',
            progress_percentage=45,
            total_points=1200
        )

        serializer = StudentProfileDetailSerializer(profile)
        data = serializer.data

        assert data['grade'] == '10'
        assert data['goal'] == 'Подготовка к ЕГЭ'
        assert data['telegram'] == '@student_username'
        assert data['progress_percentage'] == 45
        assert data['total_points'] == 1200

    def test_validate_grade_required(self):
        """Тест что класс обязателен"""
        user = User.objects.create_user(
            username='student_no_grade',
            email='student_no_grade@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(
            user=user,
            grade='9'
        )

        serializer = StudentProfileDetailSerializer(
            profile,
            data={'grade': ''},
            partial=True
        )

        assert not serializer.is_valid()
        assert 'grade' in serializer.errors

    def test_validate_grade_max_length(self):
        """Тест максимальной длины класса"""
        user = User.objects.create_user(
            username='student_grade_len',
            email='student_grade_len@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(
            user=user,
            grade='9'
        )

        serializer = StudentProfileDetailSerializer(
            profile,
            data={'grade': 'A' * 20},
            partial=True
        )

        assert not serializer.is_valid()
        assert 'grade' in serializer.errors

    def test_validate_goal_max_length(self):
        """Тест максимальной длины цели"""
        user = User.objects.create_user(
            username='student_goal',
            email='student_goal@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(
            user=user,
            grade='8'
        )

        long_goal = 'A' * 1001
        serializer = StudentProfileDetailSerializer(
            profile,
            data={'goal': long_goal},
            partial=True
        )

        assert not serializer.is_valid()
        assert 'goal' in serializer.errors

    def test_validate_telegram_format(self):
        """Тест валидации формата Telegram"""
        user = User.objects.create_user(
            username='student_tg',
            email='student_tg@example.com',
            password='testpass123',
            role=User.Role.STUDENT
        )

        profile = StudentProfile.objects.create(
            user=user,
            grade='11'
        )

        serializer = StudentProfileDetailSerializer(
            profile,
            data={'telegram': '@invalid-name'},
            partial=True
        )

        assert not serializer.is_valid()
        assert 'telegram' in serializer.errors


@pytest.mark.unit
@pytest.mark.django_db
class TestTeacherProfileDetailSerializer:
    """Тесты TeacherProfileDetailSerializer"""

    def test_serialize_teacher_profile_all_fields(self):
        """Тест сериализации всех полей профиля преподавателя"""
        user = User.objects.create_user(
            username='teacher_serial',
            email='teacher_serial@example.com',
            password='testpass123',
            role=User.Role.TEACHER
        )

        profile = TeacherProfile.objects.create(
            user=user,
            subject='Математика',
            experience_years=15,
            bio='Опытный преподаватель',
            telegram='@math_teacher'
        )

        serializer = TeacherProfileDetailSerializer(profile)
        data = serializer.data

        assert data['subject'] == 'Математика'
        assert data['experience_years'] == 15
        assert data['bio'] == 'Опытный преподаватель'
        assert data['telegram'] == '@math_teacher'

    def test_validate_experience_years_negative(self):
        """Тест что опыт не может быть отрицательным"""
        user = User.objects.create_user(
            username='teacher_exp_neg',
            email='teacher_exp_neg@example.com',
            password='testpass123',
            role=User.Role.TEACHER
        )

        profile = TeacherProfile.objects.create(
            user=user,
            subject='Физика',
            experience_years=5
        )

        serializer = TeacherProfileDetailSerializer(
            profile,
            data={'experience_years': -1},
            partial=True
        )

        assert not serializer.is_valid()
        assert 'experience_years' in serializer.errors

    def test_validate_experience_years_too_high(self):
        """Тест что опыт не может быть больше 80 лет"""
        user = User.objects.create_user(
            username='teacher_exp_high',
            email='teacher_exp_high@example.com',
            password='testpass123',
            role=User.Role.TEACHER
        )

        profile = TeacherProfile.objects.create(
            user=user,
            subject='Русский язык',
            experience_years=10
        )

        serializer = TeacherProfileDetailSerializer(
            profile,
            data={'experience_years': 100},
            partial=True
        )

        assert not serializer.is_valid()
        assert 'experience_years' in serializer.errors

    def test_validate_bio_max_length(self):
        """Тест максимальной длины биографии"""
        user = User.objects.create_user(
            username='teacher_bio',
            email='teacher_bio@example.com',
            password='testpass123',
            role=User.Role.TEACHER
        )

        profile = TeacherProfile.objects.create(
            user=user,
            subject='История',
            bio='Короткая биография'
        )

        long_bio = 'A' * 1001
        serializer = TeacherProfileDetailSerializer(
            profile,
            data={'bio': long_bio},
            partial=True
        )

        assert not serializer.is_valid()
        assert 'bio' in serializer.errors


@pytest.mark.unit
@pytest.mark.django_db
class TestTutorProfileDetailSerializer:
    """Тесты TutorProfileDetailSerializer"""

    def test_serialize_tutor_profile_all_fields(self):
        """Тест сериализации всех полей профиля тьютора"""
        user = User.objects.create_user(
            username='tutor_serial',
            email='tutor_serial@example.com',
            password='testpass123',
            role=User.Role.TUTOR
        )

        profile = TutorProfile.objects.create(
            user=user,
            specialization='Подготовка к ОГЭ',
            experience_years=8,
            bio='Профессиональный тьютор',
            telegram='@pro_tutor'
        )

        serializer = TutorProfileDetailSerializer(profile)
        data = serializer.data

        assert data['specialization'] == 'Подготовка к ОГЭ'
        assert data['experience_years'] == 8
        assert data['bio'] == 'Профессиональный тьютор'
        assert data['telegram'] == '@pro_tutor'

    def test_validate_specialization_required(self):
        """Тест что специализация обязательна"""
        user = User.objects.create_user(
            username='tutor_no_spec',
            email='tutor_no_spec@example.com',
            password='testpass123',
            role=User.Role.TUTOR
        )

        profile = TutorProfile.objects.create(
            user=user,
            specialization='ЕГЭ по математике',
            experience_years=5
        )

        serializer = TutorProfileDetailSerializer(
            profile,
            data={'specialization': ''},
            partial=True
        )

        assert not serializer.is_valid()
        assert 'specialization' in serializer.errors

    def test_validate_specialization_max_length(self):
        """Тест максимальной длины специализации"""
        user = User.objects.create_user(
            username='tutor_spec_len',
            email='tutor_spec_len@example.com',
            password='testpass123',
            role=User.Role.TUTOR
        )

        profile = TutorProfile.objects.create(
            user=user,
            specialization='Подготовка',
            experience_years=3
        )

        long_spec = 'A' * 201
        serializer = TutorProfileDetailSerializer(
            profile,
            data={'specialization': long_spec},
            partial=True
        )

        assert not serializer.is_valid()
        assert 'specialization' in serializer.errors


@pytest.mark.unit
@pytest.mark.django_db
class TestParentProfileDetailSerializer:
    """Тесты ParentProfileDetailSerializer"""

    def test_serialize_parent_profile(self):
        """Тест сериализации профиля родителя"""
        user = User.objects.create_user(
            username='parent_serial',
            email='parent_serial@example.com',
            password='testpass123',
            role=User.Role.PARENT
        )

        profile = ParentProfile.objects.create(
            user=user,
            telegram='@parent_contact'
        )

        serializer = ParentProfileDetailSerializer(profile)
        data = serializer.data

        assert data['telegram'] == '@parent_contact'

    def test_validate_telegram_invalid_format(self):
        """Тест валидации неправильного формата Telegram"""
        user = User.objects.create_user(
            username='parent_bad_tg',
            email='parent_bad_tg@example.com',
            password='testpass123',
            role=User.Role.PARENT
        )

        profile = ParentProfile.objects.create(user=user)

        serializer = ParentProfileDetailSerializer(
            profile,
            data={'telegram': '@bad-user-name'},
            partial=True
        )

        assert not serializer.is_valid()
        assert 'telegram' in serializer.errors


@pytest.mark.unit
@pytest.mark.django_db
class TestUserProfileUpdateSerializer:
    """Тесты UserProfileUpdateSerializer"""

    def test_update_user_basic_fields(self):
        """Тест обновления базовых полей пользователя"""
        user = User.objects.create_user(
            username='user_update',
            email='user_update@example.com',
            password='testpass123'
        )

        serializer = UserProfileUpdateSerializer(
            user,
            data={
                'first_name': 'John',
                'last_name': 'Doe',
                'phone': '+79991234567'
            },
            partial=True
        )

        assert serializer.is_valid()
        updated_user = serializer.save()
        assert updated_user.first_name == 'John'
        assert updated_user.last_name == 'Doe'
        assert updated_user.phone == '+79991234567'

    def test_validate_first_name_max_length(self):
        """Тест максимальной длины имени"""
        user = User.objects.create_user(
            username='user_fname',
            email='user_fname@example.com',
            password='testpass123'
        )

        serializer = UserProfileUpdateSerializer(
            user,
            data={'first_name': 'A' * 151},
            partial=True
        )

        assert not serializer.is_valid()
        assert 'first_name' in serializer.errors

    def test_validate_last_name_max_length(self):
        """Тест максимальной длины фамилии"""
        user = User.objects.create_user(
            username='user_lname',
            email='user_lname@example.com',
            password='testpass123'
        )

        serializer = UserProfileUpdateSerializer(
            user,
            data={'last_name': 'A' * 151},
            partial=True
        )

        assert not serializer.is_valid()
        assert 'last_name' in serializer.errors

    def test_validate_phone_invalid_format(self):
        """Тест невалидного формата телефона"""
        user = User.objects.create_user(
            username='user_phone',
            email='user_phone@example.com',
            password='testpass123'
        )

        serializer = UserProfileUpdateSerializer(
            user,
            data={'phone': '123'},  # Слишком короткий
            partial=True
        )

        assert not serializer.is_valid()
        assert 'phone' in serializer.errors

    def test_validate_avatar_file_size(self):
        """Тест проверки размера аватара"""
        user = User.objects.create_user(
            username='user_avatar',
            email='user_avatar@example.com',
            password='testpass123'
        )

        # Создаем большой файл (более 5MB)
        large_image = BytesIO(b'x' * (6 * 1024 * 1024))
        large_image.name = 'large.jpg'

        serializer = UserProfileUpdateSerializer(
            user,
            data={'avatar': large_image},
            partial=True
        )

        assert not serializer.is_valid()
        assert 'avatar' in serializer.errors

    def test_validate_avatar_file_extension(self):
        """Тест проверки расширения файла аватара"""
        user = User.objects.create_user(
            username='user_avatar_ext',
            email='user_avatar_ext@example.com',
            password='testpass123'
        )

        # Пытаемся загрузить файл с неправильным расширением
        bad_file = BytesIO(b'fake content')
        bad_file.name = 'photo.exe'

        serializer = UserProfileUpdateSerializer(
            user,
            data={'avatar': bad_file},
            partial=True
        )

        assert not serializer.is_valid()
        assert 'avatar' in serializer.errors
