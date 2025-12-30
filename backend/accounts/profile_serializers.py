"""
Улучшенные сериализеры для профилей пользователей с полной валидацией.

Этот модуль содержит сериализеры для обновления и создания профилей
с подробной валидацией всех полей.
"""
import re
from rest_framework import serializers
from .models import User, StudentProfile, TeacherProfile, TutorProfile, ParentProfile


# Валидаторы для Telegram
class TelegramValidator:
    """Валидатор для проверки формата Telegram username"""

    def __call__(self, value):
        """Проверяет что Telegram имеет формат @username или username"""
        if not value:
            return

        # Удаляем @ если присутствует
        username = value.lstrip("@")

        # Telegram username должен быть 5-32 символа, только буквы/цифры/подчеркивание
        if not re.match(r"^[a-zA-Z0-9_]{5,32}$", username):
            raise serializers.ValidationError(
                "Telegram должен быть в формате @username или username, "
                "содержать только буквы, цифры и подчеркивание (5-32 символа)"
            )


# Валидаторы для телефона
class PhoneValidator:
    """Валидатор для проверки формата телефонного номера"""

    def __call__(self, value):
        """Проверяет что телефон имеет корректный формат"""
        if not value:
            return

        # Убираем пробелы, тире и скобки для проверки
        clean_phone = re.sub(r"[\s\-\(\)]", "", value)

        # Телефон должен содержать минимум 9 цифр
        digits = re.findall(r"\d", clean_phone)
        if len(digits) < 9:
            raise serializers.ValidationError(
                "Телефон должен содержать как минимум 9 цифр"
            )


class StudentProfileDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детального отображения профиля студента.

    Включает все поля профиля с полной информацией о связях.
    """

    tutor_name = serializers.CharField(
        source="tutor.get_full_name", read_only=True, required=False
    )
    parent_name = serializers.CharField(
        source="parent.get_full_name", read_only=True, required=False
    )
    telegram_id = serializers.IntegerField(
        read_only=True, source="user.telegram_id", allow_null=True
    )
    is_telegram_linked = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = (
            "id",
            "grade",
            "goal",
            "tutor",
            "tutor_name",
            "parent",
            "parent_name",
            "progress_percentage",
            "streak_days",
            "total_points",
            "accuracy_percentage",
            "telegram",
            "telegram_id",
            "is_telegram_linked",
        )
        read_only_fields = (
            "id",
            "progress_percentage",
            "streak_days",
            "total_points",
            "accuracy_percentage",
        )

    def get_is_telegram_linked(self, obj):
        return bool(obj.user.telegram_id) if hasattr(obj, "user") else False

    def validate_grade(self, value):
        """Валидация поля класса"""
        # При partial update, если поле не передано, оно не должно валидироваться
        if value is None:
            return value

        if not str(value).strip():
            raise serializers.ValidationError("Поле класса не может быть пустым")

        # Класс должен быть разумной длины
        if len(str(value)) > 10:
            raise serializers.ValidationError("Класс не может быть длиннее 10 символов")

        return str(value).strip()

    def validate_goal(self, value):
        """Валидация цели обучения"""
        if value and len(value) > 1000:
            raise serializers.ValidationError(
                "Цель обучения не может быть длиннее 1000 символов"
            )

        return value or ""

    def validate_telegram(self, value):
        """Валидация Telegram username"""
        if value:
            validator = TelegramValidator()
            validator(value)
        return value or ""


class TeacherProfileDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детального отображения профиля преподавателя.

    Включает информацию об опыте работы, биографию и контактные данные.
    """

    subjects_list = serializers.SerializerMethodField()
    telegram_id = serializers.IntegerField(
        read_only=True, source="user.telegram_id", allow_null=True
    )
    is_telegram_linked = serializers.SerializerMethodField()

    class Meta:
        model = TeacherProfile
        fields = (
            "id",
            "subject",
            "experience_years",
            "bio",
            "telegram",
            "subjects_list",
            "telegram_id",
            "is_telegram_linked",
        )

    def get_is_telegram_linked(self, obj):
        return bool(obj.user.telegram_id) if hasattr(obj, "user") else False

    def validate_subject(self, value):
        """Валидация предмета"""
        if value and len(value) > 100:
            raise serializers.ValidationError(
                "Предмет не может быть длиннее 100 символов"
            )
        return value or ""

    def validate_experience_years(self, value):
        """Валидация опыта работы"""
        if value is not None:
            if value < 0:
                raise serializers.ValidationError(
                    "Опыт работы не может быть отрицательным"
                )
            if value > 80:
                raise serializers.ValidationError(
                    "Опыт работы не может быть больше 80 лет"
                )
        return value or 0

    def validate_bio(self, value):
        """Валидация биографии"""
        if value and len(value) > 1000:
            raise serializers.ValidationError(
                "Биография не может быть длиннее 1000 символов"
            )
        return value or ""

    def validate_telegram(self, value):
        """Валидация Telegram username"""
        if value:
            validator = TelegramValidator()
            validator(value)
        return value or ""

    def get_subjects_list(self, obj):
        """Возвращает список предметов преподавателя из TeacherSubject"""
        from materials.models import TeacherSubject

        teacher_subjects = TeacherSubject.objects.filter(
            teacher=obj.user, is_active=True
        ).select_related("subject")
        return [ts.subject.name for ts in teacher_subjects]


class TutorProfileDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детального отображения профиля тьютора.

    Включает информацию о специализации, опыте и контактных данных.
    """

    reportsCount = serializers.SerializerMethodField()
    telegram_id = serializers.IntegerField(
        read_only=True, source="user.telegram_id", allow_null=True
    )
    is_telegram_linked = serializers.SerializerMethodField()

    class Meta:
        model = TutorProfile
        fields = (
            "id",
            "specialization",
            "experience_years",
            "bio",
            "telegram",
            "reportsCount",
            "telegram_id",
            "is_telegram_linked",
        )

    def get_is_telegram_linked(self, obj):
        return bool(obj.user.telegram_id) if hasattr(obj, "user") else False

    def validate_specialization(self, value):
        """Валидация специализации"""
        if self.partial and value is None:
            return self.instance.specialization if self.instance else ""

        if not value or not str(value).strip():
            if self.partial:
                return self.instance.specialization if self.instance else ""
            raise serializers.ValidationError("Специализация обязательна")

        if len(value) > 200:
            raise serializers.ValidationError(
                "Специализация не может быть длиннее 200 символов"
            )

        return value.strip()

    def validate_experience_years(self, value):
        """Валидация опыта работы"""
        if value is not None:
            if value < 0:
                raise serializers.ValidationError(
                    "Опыт работы не может быть отрицательным"
                )
            if value > 80:
                raise serializers.ValidationError(
                    "Опыт работы не может быть больше 80 лет"
                )
        return value or 0

    def validate_bio(self, value):
        """Валидация биографии"""
        if value and len(value) > 1000:
            raise serializers.ValidationError(
                "Биография не может быть длиннее 1000 символов"
            )
        return value or ""

    def validate_telegram(self, value):
        """Валидация Telegram username"""
        if value:
            validator = TelegramValidator()
            validator(value)
        return value or ""

    def get_reportsCount(self, obj):
        """Получить количество отправленных отчётов тьютора"""
        from reports.models import TutorWeeklyReport

        return (
            TutorWeeklyReport.objects.filter(tutor=obj.user)
            .exclude(status=TutorWeeklyReport.Status.DRAFT)
            .count()
        )


class ParentProfileDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детального отображения профиля родителя.

    Включает информацию о детях и контактные данные.
    """

    telegram_id = serializers.IntegerField(
        read_only=True, source="user.telegram_id", allow_null=True
    )
    is_telegram_linked = serializers.SerializerMethodField()

    class Meta:
        model = ParentProfile
        fields = ("id", "telegram", "telegram_id", "is_telegram_linked")

    def get_is_telegram_linked(self, obj):
        return bool(obj.user.telegram_id) if hasattr(obj, "user") else False

    def validate_telegram(self, value):
        """Валидация Telegram username"""
        if value:
            validator = TelegramValidator()
            validator(value)
        return value or ""


class UserProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления профиля текущего пользователя.

    Позволяет обновить основные поля пользователя: имя, фамилию, email, телефон и аватар.
    """

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email", "phone", "avatar")

    def validate_first_name(self, value):
        """Валидация имени"""
        if value and len(value) > 150:
            raise serializers.ValidationError("Имя не может быть длиннее 150 символов")
        return value or ""

    def validate_last_name(self, value):
        """Валидация фамилии"""
        if value and len(value) > 150:
            raise serializers.ValidationError(
                "Фамилия не может быть длиннее 150 символов"
            )
        return value or ""

    def validate_email(self, value):
        """Валидация email"""
        if value:
            # Django's built-in email validator
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError

            try:
                validate_email(value)
            except ValidationError:
                raise serializers.ValidationError("Введите корректный email адрес")
        return value or ""

    def validate_phone(self, value):
        """Валидация телефонного номера"""
        if value:
            validator = PhoneValidator()
            validator(value)
        return value or ""

    def validate_avatar(self, value):
        """Валидация аватара"""
        if value:
            # Проверяем размер файла (максимум 5MB)
            if value.size > 5 * 1024 * 1024:
                raise serializers.ValidationError(
                    "Размер файла не должен превышать 5MB"
                )

            # Проверяем расширение файла
            allowed_extensions = ["jpg", "jpeg", "png", "gif", "webp"]
            file_extension = value.name.split(".")[-1].lower()
            if file_extension not in allowed_extensions:
                raise serializers.ValidationError(
                    f"Поддерживаются только форматы: {', '.join(allowed_extensions)}"
                )

        return value
