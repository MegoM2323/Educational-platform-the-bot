from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.db import models
from django.db.models import Count, Q, Prefetch
from django.utils.html import escape
from .models import (
    User,
    StudentProfile,
    TeacherProfile,
    TutorProfile,
    ParentProfile,
    TelegramLinkToken,
)
from reports.models import TeacherWeeklyReport, TutorWeeklyReport
from .permissions import (
    can_view_private_fields,
)


def _validate_role_for_assignment(user_obj, expected_role, role_name):
    """
    Общая валидация для проверки роли и активности пользователя.

    Args:
        user_obj: User object
        expected_role: User.Role.TUTOR or User.Role.PARENT
        role_name: Название роли для сообщения об ошибке ('тьютор', 'родитель')

    Raises:
        serializers.ValidationError: если роль не совпадает или пользователь неактивен
    """
    if user_obj:
        if user_obj.role != expected_role:
            raise serializers.ValidationError(
                f"Указанный пользователь не является {role_name}ом"
            )
        if not user_obj.is_active:
            raise serializers.ValidationError(
                f"{role_name.capitalize()} должен быть активным"
            )


__all__ = [
    "UserMinimalSerializer",
    "UserLoginSerializer",
    "UserSerializer",
    "UserPublicSerializer",
    "StudentProfileSerializer",
    "TeacherProfileSerializer",
    "TutorProfileSerializer",
    "TutorProfileDetailSerializer",
    "ParentProfileSerializer",
    "ParentProfileListSerializer",
    "StudentUserListSerializer",
    "ParentUserListSerializer",
    "ChangePasswordSerializer",
    "StudentListSerializer",
    "EnrollmentDetailSerializer",
    "StudentDetailSerializer",
    "UserUpdateSerializer",
    "StudentProfileUpdateSerializer",
    "TeacherProfileUpdateSerializer",
    "TutorProfileUpdateSerializer",
    "ParentProfileUpdateSerializer",
    "UserCreateSerializer",
    "StudentProfilePublicSerializer",
    "StudentProfileFullSerializer",
    "TeacherProfilePublicSerializer",
    "TeacherProfileFullSerializer",
    "TutorProfilePublicSerializer",
    "TutorProfileFullSerializer",
    "get_profile_serializer",
    "StudentCreateSerializer",
    "ParentCreateSerializer",
    "CurrentUserProfileSerializer",
    "TelegramLinkTokenSerializer",
    "TelegramLinkRequestSerializer",
    "TelegramStatusSerializer",
    "TelegramConfirmSerializer",
    "optimize_teacher_profile_queryset",
    "optimize_tutor_profile_queryset",
]


class UserMinimalSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for User - used in nested relationships
    """

    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name")
        read_only_fields = fields


class UserLoginSerializer(serializers.Serializer):
    """
    Сериализатор для входа пользователя (поддерживает email и username)
    """

    email = serializers.CharField(required=False, allow_blank=True)
    username = serializers.CharField(required=False, allow_blank=True)
    password = serializers.CharField(required=True)

    def validate_email(self, value):
        if value and isinstance(value, str):
            value = value.strip()
        return value

    def validate_username(self, value):
        if value and isinstance(value, str):
            value = value.strip()
        return value

    def validate_password(self, value):
        if not value:
            raise serializers.ValidationError("Пароль не может быть пустым")
        return value

    def validate(self, attrs):
        email = attrs.get("email")
        username = attrs.get("username")
        password = attrs.get("password")

        if not email and not username:
            raise serializers.ValidationError(
                "Необходимо указать email или имя пользователя"
            )

        attrs["email"] = email if email else None
        attrs["username"] = username if username else None
        attrs["password"] = password

        return attrs


class UserSerializer(serializers.ModelSerializer):
    """
    Сериализатор для отображения пользователя
    """

    role_display = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "role_display",
            "phone",
            "avatar",
            "is_verified",
            "is_active",
            "is_staff",
            "date_joined",
            "full_name",
        )
        read_only_fields = ("id", "role", "date_joined", "is_verified", "is_staff")

    def get_role_display(self, obj):
        if obj.is_superuser:
            return "Администратор"
        return obj.get_role_display()

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class StudentProfileSerializer(serializers.ModelSerializer):
    """
    Сериализатор для профиля студента
    """

    user = UserSerializer(read_only=True)
    tutor_name = serializers.CharField(source="tutor.get_full_name", read_only=True)
    parent_name = serializers.CharField(source="parent.get_full_name", read_only=True)

    class Meta:
        model = StudentProfile
        fields = (
            "id",
            "user",
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
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")

        if self.instance and request:
            viewer_user = request.user
            profile_owner_user = self.instance.user

            if not can_view_private_fields(
                viewer_user, profile_owner_user, User.Role.STUDENT
            ):
                self.fields.pop("goal", None)
                self.fields.pop("tutor", None)
                self.fields.pop("tutor_name", None)
                self.fields.pop("parent", None)
                self.fields.pop("parent_name", None)


class TeacherProfileSerializer(serializers.ModelSerializer):
    """
    Сериализатор для профиля преподавателя
    """

    user = UserSerializer(read_only=True)
    subjects_list = serializers.SerializerMethodField()

    class Meta:
        model = TeacherProfile
        fields = (
            "id",
            "user",
            "subject",
            "experience_years",
            "bio",
            "telegram",
            "subjects_list",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")

        if self.instance and request:
            viewer_user = request.user
            profile_owner_user = self.instance.user

            if not can_view_private_fields(
                viewer_user, profile_owner_user, User.Role.TEACHER
            ):
                self.fields.pop("bio", None)
                self.fields.pop("experience_years", None)

    def get_subjects_list(self, obj):
        """Возвращает список предметов преподавателя из prefetched TeacherSubject"""
        teacher_subjects = getattr(obj.user, "_prefetched_teacher_subjects", [])
        return [ts.subject.name for ts in teacher_subjects]


class TutorProfileSerializer(serializers.ModelSerializer):
    """
    Сериализатор для профиля тьютора
    """

    user = UserSerializer(read_only=True)
    reportsCount = serializers.SerializerMethodField()

    class Meta:
        model = TutorProfile
        fields = (
            "id",
            "user",
            "specialization",
            "experience_years",
            "bio",
            "telegram",
            "reportsCount",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")

        if self.instance and request:
            viewer_user = request.user
            profile_owner_user = self.instance.user

            if not can_view_private_fields(
                viewer_user, profile_owner_user, User.Role.TUTOR
            ):
                self.fields.pop("bio", None)
                self.fields.pop("experience_years", None)

    def get_reportsCount(self, obj):
        """Получить количество отправленных отчётов тьютора из annotated поля"""
        return getattr(obj, "reports_count", 0)


class ParentProfileSerializer(serializers.ModelSerializer):
    """
    Сериализатор для профиля родителя
    """

    user = UserSerializer(read_only=True)
    children = UserSerializer(many=True, read_only=True)

    class Meta:
        model = ParentProfile
        fields = ("id", "user", "children")


class ParentProfileListSerializer(serializers.ModelSerializer):
    """
    Optimized serializer for parent list view (without children details to avoid N+1)
    """

    user = UserSerializer(read_only=True)
    children_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ParentProfile
        fields = ("id", "user", "children_count")


class ChangePasswordSerializer(serializers.Serializer):
    """
    Сериализатор для смены пароля
    """

    old_password = serializers.CharField()
    new_password = serializers.CharField(validators=[validate_password])
    new_password_confirm = serializers.CharField()

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError("Новые пароли не совпадают")
        return attrs

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль")
        return value


class StudentListSerializer(serializers.ModelSerializer):
    """
    Сериализатор для списка студентов (краткая информация для админ-панели)

    IMPORTANT: This serializer expects StudentProfile entries where user.role='STUDENT'.
    The API view (list_students) filters at queryset level to ensure this requirement.

    For admin users, returns nested structure:
    {
        "id": <user_id>,
        "student_profile": {
            "goal": "...",
            "tutor": <tutor_id>,
            "parent": <parent_id>,
            ...
        }
    }

    Скрывает email адреса тьюторов и родителей в целях приватности.
    """

    user = UserSerializer(read_only=True)
    tutor_info = serializers.SerializerMethodField()
    parent_info = serializers.SerializerMethodField()
    enrollments_count = serializers.IntegerField(read_only=True)
    student_profile = serializers.SerializerMethodField()
    id = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = (
            "id",
            "user",
            "grade",
            "goal",
            "tutor_info",
            "parent_info",
            "progress_percentage",
            "streak_days",
            "total_points",
            "accuracy_percentage",
            "enrollments_count",
            "student_profile",
        )

    def get_id(self, obj):
        """Return user_id instead of StudentProfile id"""
        return obj.user_id

    def get_tutor_info(self, obj):
        """Information about tutor (with role and active status validation, email excluded for privacy)"""
        if obj.tutor:
            if obj.tutor.role != User.Role.TUTOR or not obj.tutor.is_active:
                return None
            return {
                "id": obj.tutor.id,
                "name": obj.tutor.get_full_name(),
                "avatar": getattr(obj.tutor.avatar, "url", None)
                if obj.tutor.avatar
                else None,
            }
        return None

    def get_parent_info(self, obj):
        """Information about parent (with role and active status validation, email excluded for privacy)"""
        if obj.parent:
            if obj.parent.role != User.Role.PARENT or not obj.parent.is_active:
                return None
            return {
                "id": obj.parent.id,
                "name": obj.parent.get_full_name(),
                "avatar": getattr(obj.parent.avatar, "url", None)
                if obj.parent.avatar
                else None,
            }
        return None

    def get_student_profile(self, obj):
        """Return nested student_profile with private fields for admin"""
        return {
            "goal": obj.goal,
            "tutor": obj.tutor_id,
            "parent": obj.parent_id,
            "grade": obj.grade,
            "progress_percentage": obj.progress_percentage,
            "streak_days": obj.streak_days,
            "total_points": obj.total_points,
            "accuracy_percentage": obj.accuracy_percentage,
        }


class StudentUserListSerializer(serializers.Serializer):
    """
    Сериализатор для списка студентов работающий с User объектами
    (вместо StudentProfile).

    Используется когда студент создан но не имеет StudentProfile.
    """

    id = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    grade = serializers.SerializerMethodField()
    goal = serializers.SerializerMethodField()
    tutor_info = serializers.SerializerMethodField()
    parent_info = serializers.SerializerMethodField()
    progress_percentage = serializers.SerializerMethodField()
    streak_days = serializers.SerializerMethodField()
    total_points = serializers.SerializerMethodField()
    accuracy_percentage = serializers.SerializerMethodField()
    enrollments_count = serializers.IntegerField(read_only=True)

    def get_id(self, obj):
        """Get id from User object"""
        return obj.id

    def get_user(self, obj):
        """Get user data serialized"""
        return UserSerializer(obj).data

    def get_grade(self, obj):
        """Get grade from student_profile if exists"""
        profile = getattr(obj, "student_profile", None)
        return profile.grade if profile else None

    def get_goal(self, obj):
        """Get goal from student_profile if exists"""
        profile = getattr(obj, "student_profile", None)
        return profile.goal if profile else None

    def get_tutor_info(self, obj):
        """Get tutor info from student_profile if exists"""
        profile = getattr(obj, "student_profile", None)
        if profile and profile.tutor:
            if profile.tutor.role != User.Role.TUTOR or not profile.tutor.is_active:
                return None
            return {
                "id": profile.tutor.id,
                "name": profile.tutor.get_full_name(),
                "avatar": getattr(profile.tutor.avatar, "url", None)
                if profile.tutor.avatar
                else None,
            }
        return None

    def get_parent_info(self, obj):
        """Get parent info from student_profile if exists"""
        profile = getattr(obj, "student_profile", None)
        if profile and profile.parent:
            if profile.parent.role != User.Role.PARENT or not profile.parent.is_active:
                return None
            return {
                "id": profile.parent.id,
                "name": profile.parent.get_full_name(),
                "avatar": getattr(profile.parent.avatar, "url", None)
                if profile.parent.avatar
                else None,
            }
        return None

    def get_progress_percentage(self, obj):
        """Get progress from student_profile if exists"""
        profile = getattr(obj, "student_profile", None)
        return profile.progress_percentage if profile else 0

    def get_streak_days(self, obj):
        """Get streak days from student_profile if exists"""
        profile = getattr(obj, "student_profile", None)
        return profile.streak_days if profile else 0

    def get_total_points(self, obj):
        """Get total points from student_profile if exists"""
        profile = getattr(obj, "student_profile", None)
        return profile.total_points if profile else 0

    def get_accuracy_percentage(self, obj):
        """Get accuracy from student_profile if exists"""
        profile = getattr(obj, "student_profile", None)
        return profile.accuracy_percentage if profile else 0


class ParentUserListSerializer(serializers.Serializer):
    """
    Сериализатор для списка родителей работающий с User объектами
    (вместо ParentProfile).

    Используется когда родитель создан но не имеет ParentProfile.
    """

    id = serializers.SerializerMethodField()
    user = serializers.SerializerMethodField()
    children_count = serializers.IntegerField(read_only=True)

    def get_id(self, obj):
        """Get id from User object"""
        return obj.id

    def get_user(self, obj):
        """Get user data serialized"""
        return UserSerializer(obj).data


class EnrollmentDetailSerializer(serializers.Serializer):
    """
    Сериализатор для детальной информации о зачислении
    """

    id = serializers.IntegerField()
    subject_name = serializers.CharField()
    teacher_name = serializers.CharField()
    teacher_email = serializers.CharField()
    enrolled_at = serializers.DateTimeField()
    is_active = serializers.BooleanField()
    materials_count = serializers.IntegerField()
    completed_materials = serializers.IntegerField()
    subscription_status = serializers.CharField()
    next_payment_date = serializers.DateTimeField(allow_null=True)


class StudentDetailSerializer(serializers.ModelSerializer):
    """
    Сериализатор для детальной информации о студенте (для админ-панели)
    """

    user = UserSerializer(read_only=True)
    tutor_info = serializers.SerializerMethodField()
    parent_info = serializers.SerializerMethodField()
    enrollments = serializers.SerializerMethodField()
    payment_history = serializers.SerializerMethodField()
    reports_count = serializers.SerializerMethodField()
    statistics = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = (
            "id",
            "user",
            "grade",
            "goal",
            "tutor_info",
            "parent_info",
            "progress_percentage",
            "streak_days",
            "total_points",
            "accuracy_percentage",
            "enrollments",
            "payment_history",
            "reports_count",
            "statistics",
        )

    def get_tutor_info(self, obj):
        """Information about tutor (with role validation)"""
        if obj.tutor and obj.tutor.is_active:
            if obj.tutor.role != User.Role.TUTOR:
                return None
            return {
                "id": obj.tutor.id,
                "name": obj.tutor.get_full_name(),
                "avatar": getattr(obj.tutor.avatar, "url", None)
                if obj.tutor.avatar
                else None,
            }
        return None

    def get_parent_info(self, obj):
        """Information about parent (with role validation)"""
        if obj.parent and obj.parent.is_active:
            if obj.parent.role != User.Role.PARENT:
                return None
            return {
                "id": obj.parent.id,
                "name": obj.parent.get_full_name(),
                "avatar": getattr(obj.parent.avatar, "url", None)
                if obj.parent.avatar
                else None,
            }
        return None

    def get_enrollments(self, obj):
        """Список зачислений с детальной информацией"""
        try:
            from materials.models import SubjectEnrollment, MaterialProgress, Material
        except ModuleNotFoundError:
            # Materials module not available (e.g., in tests)
            return []

        enrollments = (
            SubjectEnrollment.objects.filter(student=obj.user)
            .select_related("subject", "teacher", "teacher__teacher_profile")
            .prefetch_related("subscription")
            .order_by("-enrolled_at")
        )

        result = []
        for enrollment in enrollments:
            # Подсчет материалов
            materials_count = Material.objects.filter(
                subject=enrollment.subject, status="active"
            ).count()

            # Подсчет завершенных материалов
            completed_materials = MaterialProgress.objects.filter(
                student=obj.user,
                material__subject=enrollment.subject,
                is_completed=True,
            ).count()

            # Информация о подписке
            subscription_status = "inactive"
            next_payment_date = None
            if hasattr(enrollment, "subscription"):
                subscription_status = enrollment.subscription.status
                next_payment_date = enrollment.subscription.next_payment_date

            result.append(
                {
                    "id": enrollment.id,
                    "subject_name": enrollment.get_subject_name(),
                    "teacher_name": enrollment.teacher.get_full_name(),
                    "teacher_email": enrollment.teacher.email,
                    "enrolled_at": enrollment.enrolled_at,
                    "is_active": enrollment.is_active,
                    "materials_count": materials_count,
                    "completed_materials": completed_materials,
                    "subscription_status": subscription_status,
                    "next_payment_date": next_payment_date,
                }
            )

        return result

    def get_payment_history(self, obj):
        """История платежей студента"""
        try:
            from materials.models import SubjectPayment
        except ModuleNotFoundError:
            # Materials module not available (e.g., in tests)
            return []

        payments = (
            SubjectPayment.objects.filter(enrollment__student=obj.user)
            .select_related("payment", "enrollment__subject")
            .order_by("-created_at")[:10]
        )  # Последние 10 платежей

        return [
            {
                "id": payment.id,
                "amount": str(payment.amount),
                "status": payment.status,
                "subject_name": payment.enrollment.get_subject_name(),
                "created_at": payment.created_at,
                "paid_at": payment.paid_at,
            }
            for payment in payments
        ]

    def get_reports_count(self, obj):
        """Количество отчетов о студенте"""
        teacher_reports = TeacherWeeklyReport.objects.filter(student=obj.user).count()
        tutor_reports = TutorWeeklyReport.objects.filter(student=obj.user).count()

        return {
            "teacher_reports": teacher_reports,
            "tutor_reports": tutor_reports,
            "total": teacher_reports + tutor_reports,
        }

    def get_statistics(self, obj):
        """Статистика по студенту"""
        try:
            from materials.models import MaterialProgress, MaterialSubmission
            from assignments.models import Assignment, AssignmentSubmission
        except ModuleNotFoundError:
            # Materials or assignments modules not available (e.g., in tests)
            return {}

        # Статистика по материалам
        total_materials = MaterialProgress.objects.filter(student=obj.user).count()
        completed_materials = MaterialProgress.objects.filter(
            student=obj.user, is_completed=True
        ).count()

        # Статистика по заданиям
        total_assignments = AssignmentSubmission.objects.filter(
            student=obj.user
        ).count()
        reviewed_assignments = AssignmentSubmission.objects.filter(
            student=obj.user, status="reviewed"
        ).count()

        # Средний прогресс
        avg_progress = (
            MaterialProgress.objects.filter(student=obj.user).aggregate(
                avg=models.Avg("progress_percentage")
            )["avg"]
            or 0
        )

        return {
            "total_materials": total_materials,
            "completed_materials": completed_materials,
            "total_assignments": total_assignments,
            "reviewed_assignments": reviewed_assignments,
            "average_progress": round(avg_progress, 2),
        }


# ============= SERIALIZERS ДЛЯ РЕДАКТИРОВАНИЯ ПОЛЬЗОВАТЕЛЕЙ (ADMIN) =============


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления данных пользователя (admin-only)

    Поля для обновления:
    - email: Уникальный email (с валидацией)
    - first_name: Имя
    - last_name: Фамилия
    - phone: Телефон
    - is_active: Активация/деактивация аккаунта
    """

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "phone", "is_active")

    def validate_email(self, value):
        """
        Валидация email на уникальность.
        Проверяем что email не занят другим пользователем (кроме текущего).
        """
        if not value:
            raise serializers.ValidationError("Email обязателен")

        value = value.strip().lower()

        # Получаем текущего пользователя из instance
        user = self.instance

        # Проверяем уникальность email (исключая текущего пользователя)
        if User.objects.filter(email=value).exclude(id=user.id).exists():
            raise serializers.ValidationError(
                "Пользователь с таким email уже существует"
            )

        return value

    def validate_is_active(self, value):
        """
        Проверка что пользователь не деактивирует сам себя.
        Эта проверка делается в view, здесь просто возвращаем значение.
        """
        return value


class StudentProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления профиля студента (admin-only)

    Поля для обновления:
    - grade: Класс обучения
    - goal: Цель обучения (текст)
    - tutor: ID тьютора (nullable)
    - parent: ID родителя (nullable)
    """

    tutor = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.TUTOR, is_active=True),
        required=False,
        allow_null=True,
    )
    parent = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.PARENT, is_active=True),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = StudentProfile
        fields = ("grade", "goal", "tutor", "parent")

    def validate_tutor(self, value):
        """Валидация что tutor является активным тьютором и не является самим студентом."""
        _validate_role_for_assignment(value, User.Role.TUTOR, "тьютор")

        if value and self.instance and value.id == self.instance.user.id:
            raise serializers.ValidationError(
                "Студент не может быть назначен тьютором самому себе"
            )

        return value

    def validate_parent(self, value):
        """Валидация что parent является активным родителем."""
        _validate_role_for_assignment(value, User.Role.PARENT, "родитель")
        return value

    def validate_goal(self, value):
        """
        XSS защита для goal - экранирование HTML и спецсимволов.
        """
        if value:
            value = escape(value)
        return value

    def validate_grade(self, value):
        """
        Валидация что grade находится в диапазоне 1-12.
        """
        if value is not None:
            if not isinstance(value, int) or value < 1 or value > 12:
                raise serializers.ValidationError(
                    "Grade must be an integer between 1 and 12"
                )
        return value


class TeacherProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления профиля преподавателя (admin-only)

    Поля для обновления:
    - experience_years: Опыт работы (лет)
    - bio: Биография (приватное поле для админов)

    Примечание: subject (основной предмет) deprecated,
    используйте endpoint /api/staff/teachers/{id}/subjects/
    """

    class Meta:
        model = TeacherProfile
        fields = ("experience_years", "bio")

    def validate_experience_years(self, value):
        """Валидация опыта работы (не может быть отрицательным)"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Опыт работы не может быть отрицательным")
        return value

    def validate_bio(self, value):
        """
        XSS защита для bio - экранирование HTML и спецсимволов.
        """
        if value:
            value = escape(value)
        return value


class TutorProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления профиля тьютора (admin-only)

    Поля для обновления:
    - specialization: Специализация
    - experience_years: Опыт работы (лет)
    - bio: Биография (приватное поле для админов)
    """

    class Meta:
        model = TutorProfile
        fields = ("specialization", "experience_years", "bio")

    def validate_experience_years(self, value):
        """Валидация опыта работы (не может быть отрицательным)"""
        if value is not None and value < 0:
            raise serializers.ValidationError("Опыт работы не может быть отрицательным")
        return value

    def validate_bio(self, value):
        """
        XSS защита для bio - экранирование HTML и спецсимволов.
        """
        if value:
            value = escape(value)
        return value


class TutorProfileDetailSerializer(serializers.ModelSerializer):
    """
    Детальный сериализатор для профиля тьютора с поддержкой avatar загрузки.
    Используется для обновления профиля через PUT/PATCH с файлом avatar.
    """

    user = UserSerializer(read_only=True)
    avatar = serializers.ImageField(required=False, allow_null=True, write_only=True)
    reportsCount = serializers.SerializerMethodField()

    class Meta:
        model = TutorProfile
        fields = (
            "id",
            "user",
            "specialization",
            "experience_years",
            "bio",
            "telegram",
            "avatar",
            "reportsCount",
        )
        read_only_fields = ("id", "user", "reportsCount")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")

        if self.instance and request:
            viewer_user = request.user
            profile_owner_user = self.instance.user

            if not can_view_private_fields(
                viewer_user, profile_owner_user, User.Role.TUTOR
            ):
                self.fields.pop("bio", None)
                self.fields.pop("experience_years", None)

    def validate(self, attrs):
        """Валидация профиля при обновлении"""
        if "experience_years" in attrs and attrs["experience_years"] is not None:
            if attrs["experience_years"] < 0:
                raise serializers.ValidationError(
                    {"experience_years": "Опыт работы не может быть отрицательным"}
                )

        return attrs

    def get_reportsCount(self, obj):
        """Получить количество отправленных отчётов тьютора из annotated поля"""
        return getattr(obj, "reports_count", 0)

    def update(self, instance, validated_data):
        """Обновить профиль тьютора, включая обработку avatar"""
        from .profile_service import ProfileService

        avatar = validated_data.pop("avatar", None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()

        if avatar:
            ProfileService.handle_avatar_upload(instance.user, avatar)

        return instance


class ParentProfileUpdateSerializer(serializers.ModelSerializer):
    """
    Сериализатор для обновления профиля родителя (admin-only)

    Примечание: ParentProfile пока не имеет дополнительных полей,
    но сериализатор создан для будущего расширения.
    """

    class Meta:
        model = ParentProfile
        fields = ()


class UserCreateSerializer(serializers.Serializer):
    """
    Сериализатор для создания пользователя с профилем (admin-only)

    Обязательные поля:
    - email: Email пользователя (уникальный)
    - first_name: Имя
    - last_name: Фамилия
    - role: Роль (student, teacher, tutor, parent)

    Опциональные общие поля:
    - phone: Телефон
    - password: Пароль (если не указан - генерируется автоматически)

    Роль-специфичные поля:

    Для student:
    - grade: Класс (обязательно)
    - goal: Цель обучения (опционально)
    - tutor_id: ID тьютора (опционально)
    - parent_id: ID родителя (опционально)

    Для teacher:
    - subject: Основной предмет (опционально, deprecated)
    - experience_years: Опыт работы (опционально)
    - bio: Биография (опционально)

    Для tutor:
    - specialization: Специализация (обязательно)
    - experience_years: Опыт работы (опционально)
    - bio: Биография (опционально)

    Для parent:
    - Пока нет дополнительных полей
    """

    # Общие обязательные поля
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    role = serializers.ChoiceField(choices=User.Role.choices, required=True)

    # Общие опциональные поля
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    password = serializers.CharField(required=False, allow_blank=True, min_length=8)

    # Поля для студента
    grade = serializers.CharField(required=False, allow_blank=True, max_length=10)
    goal = serializers.CharField(required=False, allow_blank=True)
    tutor_id = serializers.IntegerField(required=False, allow_null=True)
    parent_id = serializers.IntegerField(required=False, allow_null=True)

    # Поля для преподавателя и тьютора
    subject = serializers.CharField(required=False, allow_blank=True, max_length=100)
    specialization = serializers.CharField(
        required=False, allow_blank=True, max_length=200
    )
    experience_years = serializers.IntegerField(
        required=False, allow_null=True, min_value=0
    )
    bio = serializers.CharField(required=False, allow_blank=True)

    def validate_email(self, value):
        """Проверка формата и уникальности email"""
        if not value:
            raise serializers.ValidationError("Email обязателен")

        value = value.strip().lower()

        from django.core.validators import EmailValidator
        from django.core.exceptions import ValidationError as DjangoValidationError

        validator = EmailValidator()
        try:
            validator(value)
        except DjangoValidationError:
            raise serializers.ValidationError("Невалидный формат email")

        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                "Пользователь с таким email уже существует"
            )

        return value

    def validate_tutor_id(self, value):
        """Проверка существования и роли тьютора"""
        if value:
            try:
                tutor = User.objects.get(id=value, is_active=True)
                if tutor.role != User.Role.TUTOR:
                    raise serializers.ValidationError(
                        "Указанный пользователь не является тьютором"
                    )
            except User.DoesNotExist:
                raise serializers.ValidationError("Тьютор не найден")

        return value

    def validate_parent_id(self, value):
        """Проверка существования и роли родителя"""
        if value:
            try:
                parent = User.objects.get(id=value, is_active=True)
                if parent.role != User.Role.PARENT:
                    raise serializers.ValidationError(
                        "Указанный пользователь не является родителем"
                    )
            except User.DoesNotExist:
                raise serializers.ValidationError("Родитель не найден")

        return value

    def validate_phone(self, value):
        """Проверка формата телефона согласно User model"""
        if value:
            phone_field = User._meta.get_field("phone")
            for validator in phone_field.validators:
                validator(value)
        return value

    def validate(self, attrs):
        """
        Дополнительная валидация в зависимости от роли
        """
        role = attrs.get("role")

        # Для студента проверяем обязательные поля
        if role == User.Role.STUDENT:
            if not attrs.get("grade"):
                raise serializers.ValidationError(
                    {"grade": "Поле обязательно для студента"}
                )

        # Для тьютора проверяем обязательные поля
        elif role == User.Role.TUTOR:
            if not attrs.get("specialization"):
                raise serializers.ValidationError(
                    {"specialization": "Поле обязательно для тьютора"}
                )

        return attrs


# ============= SERIALIZERS С РАЗДЕЛЕНИЕМ НА ПУБЛИЧНЫЕ И ПРИВАТНЫЕ ПОЛЯ =============


class UserPublicSerializer(serializers.ModelSerializer):
    """
    Minimal serializer for User - excludes email for privacy
    """

    role_display = serializers.SerializerMethodField()
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "first_name",
            "last_name",
            "role",
            "role_display",
            "is_active",
            "date_joined",
            "full_name",
        )
        read_only_fields = fields

    def get_role_display(self, obj):
        if obj.is_superuser:
            return "Администратор"
        return obj.get_role_display()

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class StudentProfilePublicSerializer(serializers.ModelSerializer):
    """
    Serializer для StudentProfile БЕЗ приватных полей (для самого студента).

    Скрывает приватные поля:
    - goal - цель обучения
    - tutor - назначенный тьютор
    - parent - назначенный родитель

    Показывает публичные поля:
    - grade, progress_percentage, streak_days, total_points, accuracy_percentage

    Также скрывает email студента для приватности.
    """

    user = UserPublicSerializer(read_only=True)

    class Meta:
        model = StudentProfile
        exclude = ["tutor", "parent", "goal"]  # Исключаем приватные поля


class StudentProfileFullSerializer(serializers.ModelSerializer):
    """
    Serializer для StudentProfile с ПРИВАТНЫМИ полями (для teacher/tutor/admin).

    Включает все поля профиля студента, включая приватные:
    - goal - цель обучения
    - tutor_info - информация о тьюторе
    - parent_info - информация о родителе
    """

    user = UserSerializer(read_only=True)
    tutor_info = serializers.SerializerMethodField()
    parent_info = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = "__all__"

    def get_tutor_info(self, obj):
        """Information about tutor (with role validation)"""
        if obj.tutor:
            if obj.tutor.role != User.Role.TUTOR:
                return None
            return {
                "id": obj.tutor.id,
                "name": obj.tutor.get_full_name(),
                "email": obj.tutor.email,
            }
        return None

    def get_parent_info(self, obj):
        """Information about parent (with role validation)"""
        if obj.parent:
            if obj.parent.role != User.Role.PARENT:
                return None
            return {
                "id": obj.parent.id,
                "name": obj.parent.get_full_name(),
                "email": obj.parent.email,
            }
        return None


class TeacherProfilePublicSerializer(serializers.ModelSerializer):
    """
    Serializer для TeacherProfile БЕЗ приватных полей (для самого преподавателя).

    Скрывает приватные поля:
    - bio - биография
    - experience_years - опыт работы

    Показывает публичные поля:
    - subject, subjects (через TeacherSubject)
    """

    user = UserPublicSerializer(read_only=True)
    subjects = serializers.SerializerMethodField()

    class Meta:
        model = TeacherProfile
        exclude = ["bio", "experience_years"]  # Исключаем приватные поля

    def get_subjects(self, obj):
        """Возвращает список предметов преподавателя из prefetched TeacherSubject"""
        teacher_subjects = getattr(obj.user, "_prefetched_teacher_subjects", [])
        return [
            {"id": ts.subject.id, "name": ts.subject.name} for ts in teacher_subjects
        ]


class TeacherProfileFullSerializer(serializers.ModelSerializer):
    """
    Serializer для TeacherProfile с ПРИВАТНЫМИ полями (для admin).

    Включает все поля профиля преподавателя, включая приватные:
    - bio - биография
    - experience_years - опыт работы
    """

    user = UserSerializer(read_only=True)
    subjects = serializers.SerializerMethodField()

    class Meta:
        model = TeacherProfile
        fields = "__all__"

    def get_subjects(self, obj):
        """Возвращает список предметов преподавателя из prefetched TeacherSubject"""
        teacher_subjects = getattr(obj.user, "_prefetched_teacher_subjects", [])
        return [
            {"id": ts.subject.id, "name": ts.subject.name} for ts in teacher_subjects
        ]


class TutorProfilePublicSerializer(serializers.ModelSerializer):
    """
    Serializer для TutorProfile БЕЗ приватных полей (для самого тьютора).

    Скрывает приватные поля:
    - bio - биография
    - experience_years - опыт работы

    Показывает публичные поля:
    - specialization
    """

    user = UserSerializer(read_only=True)

    class Meta:
        model = TutorProfile
        exclude = ["bio", "experience_years"]  # Исключаем приватные поля


class TutorProfileFullSerializer(serializers.ModelSerializer):
    """
    Serializer для TutorProfile с ПРИВАТНЫМИ полями (для admin).

    Включает все поля профиля тьютора, включая приватные:
    - bio - биография
    - experience_years - опыт работы
    """

    user = UserSerializer(read_only=True)

    class Meta:
        model = TutorProfile
        fields = "__all__"


# ============= ФУНКЦИЯ ВЫБОРА SERIALIZER В ЗАВИСИМОСТИ ОТ ПРАВ =============


def get_profile_serializer(profile, viewer_user, profile_owner_user):
    """
    Возвращает подходящий serializer в зависимости от прав viewer_user.

    Логика выбора:
    - Если viewer имеет право видеть приватные поля → Full serializer
    - Иначе → Public serializer (без приватных полей)
    - Для PARENT: всегда ParentProfileSerializer (нет приватных полей)

    Args:
        profile: Экземпляр профиля (StudentProfile, TeacherProfile, etc.)
        viewer_user (User): Пользователь который смотрит профиль
        profile_owner_user (User): Владелец профиля

    Returns:
        Serializer class: Подходящий serializer (Public или Full)

    Examples:
        >>> # Студент смотрит свой профиль - получит StudentProfilePublicSerializer
        >>> get_profile_serializer(student_profile, student_user, student_user)
        <class 'StudentProfilePublicSerializer'>

        >>> # Преподаватель смотрит профиль студента - получит StudentProfileFullSerializer
        >>> get_profile_serializer(student_profile, teacher_user, student_user)
        <class 'StudentProfileFullSerializer'>

        >>> # Админ смотрит профиль учителя - получит TeacherProfileFullSerializer
        >>> get_profile_serializer(teacher_profile, admin_user, teacher_user)
        <class 'TeacherProfileFullSerializer'>

        >>> # Учитель смотрит свой профиль - получит TeacherProfilePublicSerializer (не видит свои приватные)
        >>> get_profile_serializer(teacher_profile, teacher_user, teacher_user)
        <class 'TeacherProfilePublicSerializer'>
    """
    profile_type = profile_owner_user.role

    can_view_private = can_view_private_fields(
        viewer_user, profile_owner_user, profile_type
    )

    if profile_type == User.Role.STUDENT:
        return (
            StudentProfileFullSerializer
            if can_view_private
            else StudentProfilePublicSerializer
        )
    elif profile_type == User.Role.TEACHER:
        return (
            TeacherProfileFullSerializer
            if can_view_private
            else TeacherProfilePublicSerializer
        )
    elif profile_type == User.Role.TUTOR:
        return (
            TutorProfileFullSerializer
            if can_view_private
            else TutorProfilePublicSerializer
        )
    elif profile_type == User.Role.PARENT:
        return ParentProfileSerializer

    return None


# ============= STUDENT CREATION SERIALIZER (ADMIN) =============


class StudentCreateSerializer(serializers.Serializer):
    """
    Serializer для создания студента через админ-панель.

    Обязательные поля:
    - email: Email студента (уникальный)
    - first_name: Имя
    - last_name: Фамилия
    - grade: Класс обучения

    Опциональные поля:
    - phone: Телефон
    - goal: Цель обучения
    - tutor_id: ID тьютора
    - parent_id: ID родителя
    - password: Пароль (если не указан - генерируется автоматически)
    """

    # Обязательные поля
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)
    grade = serializers.CharField(required=True, max_length=10)

    # Опциональные поля
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    goal = serializers.CharField(required=False, allow_blank=True)
    tutor_id = serializers.IntegerField(required=False, allow_null=True)
    parent_id = serializers.IntegerField(required=False, allow_null=True)
    password = serializers.CharField(required=False, allow_blank=True, min_length=8)

    def validate_email(self, value):
        """
        Проверка формата email.

        NOTE: Uniqueness check moved to view inside transaction to prevent race conditions.
        """
        if not value:
            raise serializers.ValidationError("Email обязателен")

        value = value.strip().lower()

        from django.core.validators import EmailValidator
        from django.core.exceptions import ValidationError as DjangoValidationError

        validator = EmailValidator()
        try:
            validator(value)
        except DjangoValidationError:
            raise serializers.ValidationError("Невалидный формат email")

        return value

    def validate_phone(self, value):
        """Проверка формата телефона согласно User model"""
        if value:
            # Apply User's phone validator
            phone_field = User._meta.get_field("phone")
            for validator in phone_field.validators:
                validator(value)
        return value

    def validate_password(self, value):
        """Проверка требований к паролю Django"""
        if value:
            validate_password(value)
        return value

    def validate_tutor_id(self, value):
        """Проверка существования и роли тьютора"""
        if value:
            try:
                tutor = User.objects.get(id=value)
                _validate_role_for_assignment(tutor, User.Role.TUTOR, "тьютор")
            except User.DoesNotExist:
                raise serializers.ValidationError("Тьютор не найден")

        return value

    def validate_parent_id(self, value):
        """Проверка существования и роли родителя"""
        if value:
            try:
                parent = User.objects.get(id=value)
                _validate_role_for_assignment(parent, User.Role.PARENT, "родитель")
            except User.DoesNotExist:
                raise serializers.ValidationError("Родитель не найден")

        return value

    def validate(self, data):
        """Валидация на уровне объекта"""
        tutor_id = data.get("tutor_id")
        parent_id = data.get("parent_id")

        if tutor_id and parent_id and tutor_id == parent_id:
            raise serializers.ValidationError(
                "Тьютор и родитель не могут быть одним и тем же пользователем"
            )

        return data


class ParentCreateSerializer(serializers.Serializer):
    """
    Serializer для создания родителя через админ-панель.

    Обязательные поля:
    - email: Email родителя (уникальный, RFC 5322 compliant)
    - first_name: Имя
    - last_name: Фамилия

    Опциональные поля:
    - phone: Телефон (валидируется согласно User model regex)
    - password: Пароль (если не указан - генерируется автоматически, проверяется на сложность)
    """

    # Обязательные поля
    email = serializers.EmailField(required=True)
    first_name = serializers.CharField(required=True, max_length=150)
    last_name = serializers.CharField(required=True, max_length=150)

    # Опциональные поля
    phone = serializers.CharField(required=False, allow_blank=True, max_length=20)
    password = serializers.CharField(required=False, allow_blank=True, min_length=8)

    def validate_email(self, value):
        """
        Проверка email на формат.
        EmailField уже валидирует формат по RFC 5322.

        NOTE: Uniqueness check moved to view inside transaction to prevent race conditions.
        """
        if not value:
            raise serializers.ValidationError("Email обязателен")

        value = value.strip().lower()

        from django.core.validators import EmailValidator
        from django.core.exceptions import ValidationError as DjangoValidationError

        validator = EmailValidator()
        try:
            validator(value)
        except DjangoValidationError:
            raise serializers.ValidationError("Невалидный формат email")

        return value

    def validate_phone(self, value):
        r"""
        Проверка формата телефона согласно User model.
        Применяет RegexValidator из модели User: ^\+?1?\d{9,15}$
        """
        if value:
            # Apply User's phone validator
            phone_field = User._meta.get_field("phone")
            for validator in phone_field.validators:
                validator(value)
        return value

    def validate_password(self, value):
        """
        Проверка требований к паролю Django.
        Использует встроенные валидаторы из AUTH_PASSWORD_VALIDATORS.
        """
        if value:
            validate_password(value)
        return value


# ============= UNIFIED PROFILE SERIALIZERS FOR CURRENT USER =============


class CurrentUserProfileSerializer(serializers.Serializer):
    """
    Unified serializer для профиля текущего пользователя.
    Автоматически выбирает правильный serializer на основе роли пользователя.

    Возвращает структуру:
    {
        "user": {...user data...},
        "profile": {...role-specific profile data...},
        "notification_settings": {...notification settings...}
    }
    """

    def to_representation(self, instance):
        """
        Преобразует экземпляр User в unified представление с профилем и настройками уведомлений.

        Args:
            instance: User object

        Returns:
            dict с полями 'user', 'profile' и 'notification_settings'
        """
        user = instance

        # Базовые данные пользователя
        user_data = UserSerializer(user).data
        profile_data = None
        notification_settings_data = None

        # Получаем профиль в зависимости от роли
        try:
            if user.role == User.Role.STUDENT:
                profile = user.student_profile
                profile_data = StudentProfileSerializer(profile).data
            elif user.role == User.Role.TEACHER:
                profile = user.teacher_profile
                profile_data = TeacherProfileSerializer(profile).data
            elif user.role == User.Role.TUTOR:
                profile = user.tutor_profile
                profile_data = TutorProfileSerializer(profile).data
            elif user.role == User.Role.PARENT:
                profile = user.parent_profile
                profile_data = ParentProfileSerializer(profile).data
        except (
            StudentProfile.DoesNotExist,
            TeacherProfile.DoesNotExist,
            TutorProfile.DoesNotExist,
            ParentProfile.DoesNotExist,
        ):
            # Профиль не существует, но это не ошибка
            profile_data = None

        # Получаем настройки уведомлений
        try:
            from notifications.models import NotificationSettings
            from notifications.serializers import NotificationSettingsSerializer

            notification_settings, _ = NotificationSettings.objects.get_or_create(
                user=user
            )
            notification_settings_data = NotificationSettingsSerializer(
                notification_settings
            ).data
        except Exception:
            # Если настройки уведомлений недоступны, просто пропускаем
            notification_settings_data = None

        return {
            "user": user_data,
            "profile": profile_data,
            "notification_settings": notification_settings_data,
        }


class TelegramLinkTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramLinkToken
        fields = ["token", "created_at", "expires_at", "is_expired"]
        read_only_fields = ["created_at", "expires_at"]

    is_expired = serializers.SerializerMethodField()

    def get_is_expired(self, obj):
        return obj.is_expired()


class TelegramLinkRequestSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=100)
    telegram_id = serializers.IntegerField()


class TelegramStatusSerializer(serializers.Serializer):
    is_linked = serializers.BooleanField()
    telegram_id = serializers.IntegerField(allow_null=True)


class TelegramConfirmSerializer(serializers.Serializer):
    """Serializer for Telegram link confirmation endpoint"""

    token = serializers.CharField(max_length=255, required=True)
    telegram_id = serializers.IntegerField(required=True, min_value=1)

    def validate_token(self, value):
        """Validate token is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Token cannot be empty")
        return value.strip()

    def validate_telegram_id(self, value):
        """Validate telegram_id is positive integer"""
        if value <= 0:
            raise serializers.ValidationError("Telegram ID must be a positive integer")
        return value


# ============= OPTIMIZER HELPERS FOR QUERYSETS =============


def optimize_teacher_profile_queryset(queryset):
    """
    Оптимизирует queryset TeacherProfile для избежания N+1 queries.

    Используется в views для профилей преподавателей.

    Оптимизирует:
    - select_related('user'): User FK
    - prefetch_related с Prefetch для TeacherSubject с фильтром is_active=True

    Example:
        queryset = TeacherProfile.objects.all()
        queryset = optimize_teacher_profile_queryset(queryset)
        serializer = TeacherProfileSerializer(queryset, many=True)
    """
    from materials.models import TeacherSubject, Subject

    teacher_subjects_prefetch = Prefetch(
        "user__teacher_subjects",
        queryset=TeacherSubject.objects.filter(is_active=True).select_related(
            "subject"
        ),
    )

    return queryset.select_related("user").prefetch_related(teacher_subjects_prefetch)


def optimize_tutor_profile_queryset(queryset):
    """
    Оптимизирует queryset TutorProfile для избежания N+1 queries.

    Используется в views для профилей тьюторов.

    Оптимизирует:
    - select_related('user'): User FK
    - annotate с Count для подсчета отчетов (исключая DRAFT статус)

    Example:
        queryset = TutorProfile.objects.all()
        queryset = optimize_tutor_profile_queryset(queryset)
        serializer = TutorProfileSerializer(queryset, many=True)
    """
    return queryset.select_related("user").annotate(
        reports_count=Count(
            "user__sent_tutor_reports",
            filter=Q(
                user__sent_tutor_reports__status__in=[
                    TutorWeeklyReport.Status.SENT,
                    TutorWeeklyReport.Status.READ,
                    TutorWeeklyReport.Status.ARCHIVED,
                ]
            ),
        )
    )
