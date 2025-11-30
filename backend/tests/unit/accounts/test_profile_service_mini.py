"""
Unit тесты для ProfileService (минимальный набор).
"""

import pytest
from io import BytesIO
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError

from accounts.models import StudentProfile, TeacherProfile, TutorProfile, ParentProfile
from accounts.profile_service import ProfileService

User = get_user_model()


def create_test_image():
    """Создать тестовое изображение"""
    image = Image.new('RGB', (400, 400), color='red')
    image_io = BytesIO()
    image.save(image_io, format='PNG')
    image_io.seek(0)
    return SimpleUploadedFile(
        'test_avatar.png',
        image_io.getvalue(),
        content_type='image/png'
    )


@pytest.mark.django_db
class TestGetUserProfile:
    """Тесты для ProfileService.get_user_profile()"""

    def test_get_student_profile(self):
        """Получить профиль студента"""
        user = User.objects.create_user(
            username='test_student',
            email='student@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT
        )
        profile = StudentProfile.objects.create(user=user, grade='10A')

        result = ProfileService.get_user_profile(user)

        assert result is not None
        assert isinstance(result, StudentProfile)
        assert result.id == profile.id

    def test_get_teacher_profile(self):
        """Получить профиль преподавателя"""
        user = User.objects.create_user(
            username='test_teacher',
            email='teacher@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER
        )
        profile = TeacherProfile.objects.create(user=user, subject='Math')

        result = ProfileService.get_user_profile(user)

        assert result is not None
        assert isinstance(result, TeacherProfile)

    def test_get_tutor_profile(self):
        """Получить профиль тьютора"""
        user = User.objects.create_user(
            username='test_tutor',
            email='tutor@test.com',
            password='TestPass123!',
            role=User.Role.TUTOR
        )
        profile = TutorProfile.objects.create(user=user, specialization='Math')

        result = ProfileService.get_user_profile(user)

        assert result is not None
        assert isinstance(result, TutorProfile)

    def test_get_parent_profile(self):
        """Получить профиль родителя"""
        user = User.objects.create_user(
            username='test_parent',
            email='parent@test.com',
            password='TestPass123!',
            role=User.Role.PARENT
        )
        profile = ParentProfile.objects.create(user=user)

        result = ProfileService.get_user_profile(user)

        assert result is not None
        assert isinstance(result, ParentProfile)

    def test_get_nonexistent_profile(self):
        """Возвращает None если профиль не существует"""
        user = User.objects.create_user(
            username='no_profile',
            email='noprofile@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT
        )

        result = ProfileService.get_user_profile(user)
        assert result is None

    def test_invalid_role_raises_error(self):
        """Ошибка если роль неизвестна"""
        user = User.objects.create_user(
            username='unknown_role',
            email='unknown@test.com',
            password='TestPass123!',
            role='unknown'
        )

        with pytest.raises(ValueError) as exc_info:
            ProfileService.get_user_profile(user)
        assert 'Неизвестная роль' in str(exc_info.value)


@pytest.mark.django_db
class TestValidateAvatar:
    """Тесты для ProfileService.validate_avatar()"""

    def test_valid_image_png(self):
        """Валиден PNG файл"""
        file = create_test_image()
        result = ProfileService.validate_avatar(file)
        assert result is True

    def test_invalid_file_type(self):
        """Ошибка если файл - не изображение"""
        file = SimpleUploadedFile(
            'test.txt',
            b'Not an image',
            content_type='text/plain'
        )
        with pytest.raises(ValidationError) as exc_info:
            ProfileService.validate_avatar(file)
        assert 'Недопустимый тип файла' in str(exc_info.value)

    def test_file_too_large(self):
        """Ошибка если файл слишком большой"""
        large_content = b'x' * (6 * 1024 * 1024)
        file = SimpleUploadedFile(
            'large.png',
            large_content,
            content_type='image/png'
        )
        with pytest.raises(ValidationError) as exc_info:
            ProfileService.validate_avatar(file)
        assert 'превышает максимум' in str(exc_info.value)


@pytest.mark.django_db
class TestHandleAvatarUpload:
    """Тесты для ProfileService.handle_avatar_upload()"""

    def test_avatar_upload_success(self):
        """Успешная загрузка аватара"""
        user = User.objects.create_user(
            username='test_user',
            email='test@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT
        )
        file = create_test_image()

        result = ProfileService.handle_avatar_upload(user, file)

        assert result is not None
        assert 'avatars' in str(result)

    def test_avatar_invalid_file_raises_error(self):
        """Ошибка при загрузке невалидного файла"""
        user = User.objects.create_user(
            username='test_user',
            email='test@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT
        )
        file = SimpleUploadedFile(
            'test.txt',
            b'Not an image',
            content_type='text/plain'
        )

        with pytest.raises(ValidationError):
            ProfileService.handle_avatar_upload(user, file)


@pytest.mark.django_db
class TestUpdateProfileWithValidation:
    """Тесты для ProfileService.update_profile_with_validation()"""

    def test_update_student_profile_success(self):
        """Успешное обновление профиля студента"""
        user = User.objects.create_user(
            username='test_student',
            email='student@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT
        )
        profile = StudentProfile.objects.create(user=user, grade='10A')

        data = {'grade': '11A', 'goal': 'Learn math'}
        result = ProfileService.update_profile_with_validation(user, data, 'student')

        assert result.grade == '11A'
        assert result.goal == 'Learn math'

    def test_update_teacher_profile_success(self):
        """Успешное обновление профиля преподавателя"""
        user = User.objects.create_user(
            username='test_teacher',
            email='teacher@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER
        )
        profile = TeacherProfile.objects.create(user=user, subject='Math')

        data = {'experience_years': 10, 'bio': 'Senior teacher'}
        result = ProfileService.update_profile_with_validation(user, data, 'teacher')

        assert result.experience_years == 10

    def test_invalid_student_data_raises_error(self):
        """Ошибка при невалидных данных студента"""
        user = User.objects.create_user(
            username='test_student',
            email='student@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=user, grade='10A')

        data = {'grade': ''}
        from rest_framework.serializers import ValidationError as DRFValidationError
        with pytest.raises(DRFValidationError):
            ProfileService.update_profile_with_validation(user, data, 'student')
