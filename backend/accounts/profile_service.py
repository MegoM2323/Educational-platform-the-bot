"""
Service layer для управления профилями пользователей.
"""

import re
from io import BytesIO
from typing import Optional, Dict, Any

from django.core.files.base import ContentFile
from django.core.exceptions import ValidationError
from django.db import transaction
from django.conf import settings
from rest_framework.serializers import ValidationError as DRFValidationError
from PIL import Image

from .models import User, StudentProfile, TeacherProfile, TutorProfile, ParentProfile


class ProfileService:
    """Service для управления профилями пользователей."""

    ALLOWED_AVATAR_TYPES = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    MAX_AVATAR_SIZE = settings.MAX_FILE_SIZE  # 100 MB (from Django settings)
    AVATAR_SIZE = (400, 400)

    @staticmethod
    def get_user_profile(user: User) -> Optional[Any]:
        """Получить профиль пользователя по его роли."""
        if user.role == User.Role.STUDENT:
            return StudentProfile.objects.filter(user=user).first()
        elif user.role == User.Role.TEACHER:
            return TeacherProfile.objects.filter(user=user).first()
        elif user.role == User.Role.TUTOR:
            return TutorProfile.objects.filter(user=user).first()
        elif user.role == User.Role.PARENT:
            return ParentProfile.objects.filter(user=user).first()
        else:
            raise ValueError(f"Неизвестная роль пользователя: {user.role}")

    @staticmethod
    @transaction.atomic
    def update_profile_with_validation(user: User, data: Dict[str, Any], profile_type: str) -> Any:
        """Обновить профиль пользователя с валидацией."""
        profile = ProfileService.get_user_profile(user)
        if not profile:
            raise DRFValidationError(f"Профиль типа {profile_type} не найден")

        if profile_type == "student":
            ProfileService._validate_student_profile_data(data)
        elif profile_type == "teacher":
            ProfileService._validate_teacher_profile_data(data)
        elif profile_type == "tutor":
            ProfileService._validate_tutor_profile_data(data)
        elif profile_type == "parent":
            ProfileService._validate_parent_profile_data(data)

        for field, value in data.items():
            if hasattr(profile, field):
                setattr(profile, field, value)

        profile.save()
        return profile

    @staticmethod
    def validate_avatar(file) -> bool:
        """Валидировать загруженный файл аватара."""
        max_size_mb = ProfileService.MAX_AVATAR_SIZE / (1024 * 1024)
        if file.size > ProfileService.MAX_AVATAR_SIZE:
            raise ValidationError(f"Размер файла превышает максимум ({max_size_mb:.0f} MB)")

        if file.content_type not in ProfileService.ALLOWED_AVATAR_TYPES:
            allowed_types = ", ".join(ProfileService.ALLOWED_AVATAR_TYPES)
            raise ValidationError(f"Недопустимый тип файла. Допустимые: {allowed_types}")

        try:
            image = Image.open(file)
            image.verify()
            file.seek(0)
        except Exception as e:
            raise ValidationError(f"Файл не валидное изображение: {str(e)}")

        return True

    @staticmethod
    def handle_avatar_upload(profile: User, file) -> str:
        """Обработать загрузку аватара - resize, optimize и сохранить.

        Args:
            profile: User объект (передается из view как request.user)
            file: Загруженный файл изображения

        Returns:
            URL сохраненного аватара
        """
        try:
            ProfileService.validate_avatar(file)
            image = Image.open(file)

            if image.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", image.size, (255, 255, 255))
                background.paste(image, mask=image.split()[-1] if image.mode == "RGBA" else None)
                image = background

            image.thumbnail(ProfileService.AVATAR_SIZE, Image.Resampling.LANCZOS)

            square_image = Image.new("RGB", ProfileService.AVATAR_SIZE, (255, 255, 255))
            offset = (
                (ProfileService.AVATAR_SIZE[0] - image.size[0]) // 2,
                (ProfileService.AVATAR_SIZE[1] - image.size[1]) // 2,
            )
            square_image.paste(image, offset)

            output = BytesIO()
            square_image.save(output, format="JPEG", quality=85, optimize=True)
            output.seek(0)

            filename = f"{profile.id}_avatar.jpg"
            avatar_file = ContentFile(output.getvalue(), name=filename)

            # Сохраняем файл в storage через ImageField
            profile.avatar.save(filename, avatar_file, save=True)

            return profile.avatar.url

        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Ошибка при обработке аватара: {str(e)}")

    @staticmethod
    def _validate_student_profile_data(data: Dict[str, Any]) -> None:
        """Валидировать данные профиля студента."""
        errors = {}
        if "grade" in data:
            grade = data.get("grade")
            if not grade or not str(grade).strip():
                errors["grade"] = "Поле класса обязательно"
            elif len(str(grade)) > 10:
                errors["grade"] = "Класс не может быть длиннее 10 символов"
        if "goal" in data:
            goal = data.get("goal", "")
            if goal and len(str(goal)) > 1000:
                errors["goal"] = "Цель не может быть длиннее 1000 символов"
        if "telegram" in data:
            telegram = data.get("telegram", "")
            if telegram:
                ProfileService._validate_telegram(telegram)
        if errors:
            raise DRFValidationError(errors)

    @staticmethod
    def _validate_teacher_profile_data(data: Dict[str, Any]) -> None:
        """Валидировать данные профиля преподавателя."""
        errors = {}
        if "subject" in data and len(str(data.get("subject", ""))) > 100:
            errors["subject"] = "Предмет не может быть длиннее 100 символов"
        if "experience_years" in data and data.get("experience_years") is not None:
            exp = int(data.get("experience_years", 0))
            if exp < 0 or exp > 80:
                errors["experience_years"] = "Опыт должен быть 0-80 лет"
        if "bio" in data and len(str(data.get("bio", ""))) > 1000:
            errors["bio"] = "Биография не может быть длиннее 1000 символов"
        if "telegram" in data and data.get("telegram"):
            ProfileService._validate_telegram(data.get("telegram"))
        if errors:
            raise DRFValidationError(errors)

    @staticmethod
    def _validate_tutor_profile_data(data: Dict[str, Any]) -> None:
        """Валидировать данные профиля тьютора."""
        errors = {}
        if "specialization" in data and len(str(data.get("specialization", ""))) > 200:
            errors["specialization"] = "Специализация не может быть длиннее 200 символов"
        if "experience_years" in data and data.get("experience_years") is not None:
            exp = int(data.get("experience_years", 0))
            if exp < 0 or exp > 80:
                errors["experience_years"] = "Опыт должен быть 0-80 лет"
        if "bio" in data and len(str(data.get("bio", ""))) > 1000:
            errors["bio"] = "Биография не может быть длиннее 1000 символов"
        if "telegram" in data and data.get("telegram"):
            ProfileService._validate_telegram(data.get("telegram"))
        if errors:
            raise DRFValidationError(errors)

    @staticmethod
    def _validate_parent_profile_data(data: Dict[str, Any]) -> None:
        """Валидировать данные профиля родителя."""
        if "telegram" in data and data.get("telegram"):
            ProfileService._validate_telegram(data.get("telegram"))

    @staticmethod
    def _validate_telegram(value: str) -> None:
        """Валидировать Telegram username."""
        if not value:
            return
        username = value.lstrip("@")
        if not re.match(r"^[a-zA-Z0-9_]{5,32}$", username):
            raise ValidationError("Telegram должен быть @username с 5-32 символами")
